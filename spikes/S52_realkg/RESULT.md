# S52 — the shaping matrix on a real knowledge graph

**Verdict: GREEN, and it cuts both ways. Every S47/S48 direction survives on real data; every magnitude shrinks by ~10×; and the catastrophic collapse that made me retract claim D turns out to be a synthetic artefact.**

Every constant in S5, S10, S11, S17, S47 and S48 was fitted on one self-authored graph: 100k triples, 10 predicates, 1,000 subjects, 1,000 objects, uniform. This is the same experiment on **FB15k-237** — 272,115 real Freebase triples, 237 predicates, 14,505 entities, subjects and objects sharing one entity space.

Two S48 defects fixed in passing: **120 sampled queries per cell** with the median reported, instead of one literal; and the shortlist reported as **% of store checked**, which makes "a scan wearing a prefilter costume" visible.

## How different the real graph is

| | synthetic | FB15k-237 |
|---|---|---|
| predicates | 10, uniform (10.0% each) | 237; max 15,989 vs median 373 |
| objects | 1,000, uniform | 14,505; top 1% hold **28%** of triples |
| **`(p,s)` answers per query** | **~10 by construction** | **median 1**, mean 2.91, max 843 |

That last row is why this test mattered. S48's collapse mechanism was *homogeneous buckets bury single-answer targets*, and real queries are overwhelmingly single-answer — so the synthetic result predicted real data would be **worse**. It is the opposite.

## Measured — B=64, 120 queries/cell, median, pinned to cpu7

| cluster key | `(p s ?o)` | `(p ?s o)` | `(?p s o)` |
|---|---|---|---|
| **(pred,subj)** | **13.5 µs** (0.2% checked) | 14.4 (1.0%) | 23.0 (8.8%) |
| **(pred,obj)** | 14.3 (0.9%) | **13.5** (0.2%) | 27.6 (12.9%) |
| **(subj,obj)** | 13.4 (0.0%) | **67.5 (49.2%)** | **13.3** (0.0%) |
| RANDOM | 58.8 (41.4%) | 76.2 (57.2%) | 19.0 (5.2%) |

## 1. Shaping is worth 4–5×, not 54×
Shaped cells: 13.3–14.4 µs, checking **0.0–1.0%** of the store. Random: 58.8–76.2 µs, checking **41–57%**.

The direction is emphatically confirmed — an unshaped store turns the prefilter into a half-scan — but the magnitude on real data is **4.1–5.6×**, against the 54× and 12.8× S47 reported. Those figures were products of a uniform graph with ~10 answers per query and a 100k store. **Any proposal quoting 54× or 12.8× is quoting an artefact.**

## 2. The collapse that killed claim D does not happen on real data
This partially **un-retracts** my own retraction, and I have to report it against my own interest in a tidy story.

On synthetic data the worst mis-shaping was 16× worse than random (S48 reseeds), which is what falsified "bad shaping == no shaping". On FB15k-237:

- the worst mismatch, `(subj,obj)` asked `(p ?s o)`, costs **67.5 µs against random's 76.2** — mis-shaping is still **better** than no shaping;
- in **four of six** off-diagonal cells, shaping beats random;
- the two cells where shaping loses are `(?p s o)` at 23.0 and 27.6 against random 19.0 — **1.21× and 1.45× worse**, not 16×.

So on real data the downside really is close to bounded, and the economic property S48 claimed is roughly right — for a reason S48 never established, at a magnitude 10× smaller, and only after the synthetic version of the claim was correctly destroyed.

The mechanism explains the reversal. The synthetic store had 1,000 objects, so `(subj,obj)` was near-unique and every `(?p s o)` query had exactly one answer buried in a homogeneous bucket. Real data has 14,505 entities with a heavy tail: the hub entities that dominate real queries appear in many buckets, so no single bucket has to be found.

## 3. Finding 3 replicates, mildly
`(?p s o)`: random (19.0) beats both `pred`-first layouts (23.0, 27.6). Selective queries still do not benefit from shaping, so "don't commission shaping for a shard whose query mix is dominated by selective patterns" survives — at 1.2–1.45×, not the 5.3× synthetic suggested.

## 4. What does not change
The cutoff is still chosen by an oracle reading `truth`, because a fixed cutoff cannot reach recall 1.0 on a bundled store. I kept it and made its cost visible instead: the `%store checked` column *is* the honest statement. At 49.2% and 57.2%, those two cells are scans.

## Consequences
| claim | synthetic | real |
|---|---|---|
| bundling+clustering speedup | 54× | **4.1–5.6×** |
| clustering vs random | 12.8× | **4.1–5.6×** |
| worst mis-shaping vs random | 16× worse | **1.45× worse** |
| selective queries prefer random | 5.3× | 1.2–1.45× |

**M4's justification survives on real data, at a tenth of the advertised size.** That is still a real speedup for a job class whose product is a better shard, and it is now the only version of the number that has met data nobody in this workspace authored.

## Caveats
- One real dataset. FB15k-237 is a benchmark subset with its own selection biases (it was filtered to remove inverse-relation leakage).
- B=64 only; the bundle-factor sweep was not repeated.
- `per_check` measured 0.40 ns/row here against 1.29 on synthetic — different arrays, different cache behaviour — and the attacker's finding that this constant varies 2× run-to-run applies equally.
- Single-threaded, pinned to cpu7, throttling not controlled for.
- Entities share one space, so `(subj,obj)` clustering means something slightly different than it did on the synthetic graph.
