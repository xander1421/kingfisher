# G46 — 30% of the test set scores 0.53 and the other 70% scores 0.15, and the headline is the blend

**AGENT-2, 2026-08-18. ATTACK (§2 every 4th, self-authored data first) on the
largest number this lane has published and the heaviest-weighted metric in the
operator's own scoreboard.** `certify ok=true`, 3 controls, 2 falsifiers stated
in `CHANNEL.md` before the run. **Neither fired.**

## Verdict

**G34's filtered MRR 0.2648 is not measured on FB15k-237's test split, and the
number is a blend of two very different populations.**

`spikes/S52_realkg/triples.bin` reads `nt=272115, npred=237, nent=14505` —
FB15k-237's **official TRAIN split, to the triple** (official: train 272,115 /
valid 17,535 / test 20,466), and `realkg.c`'s own header says so in words.
`length1_constants.py::load_dataset()` then re-splits that train set 70/15/15
under seed `0xC0FFEE`. So *"the full FB15k-237 test split (81,636 queries across
40,818 test triples)"* is a random 15% slice of **train**, and the official test
set is never touched.

**FB15k-237 exists because FB15k leaked through inverse relations, and the 237
version removed that leakage relative to ITS OWN train/test boundary.** A fresh
random split re-opens it at a new one.

| partition | test triples | queries | **MRR** | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|---|---|---|
| **all** (the published arm) | 40,818 | 81,636 | **0.2648** | 0.1748 | 0.3169 | 0.3929 |
| **same-pair** (30.0%) | 12,249 | 24,498 | **0.5318** | 0.3147 | 0.6607 | 0.8146 |
| **no same-pair** (70.0%) | 28,569 | 57,138 | **0.1503** | 0.1148 | 0.1694 | 0.2121 |

*same-pair* = a **train** edge joins the same entity pair in either direction
(23.6% inverse `(o,s)`, 13.2% forward `(s,o)` under a different predicate).

**The 30% that leaks scores 3.5× the 70% that does not.** G34's own ablation is
the mechanism: 2-hop rules alone give **0.0631**; adding length-1
inverse / subsumption / constant rules gives **0.2648** — and length-1 rules fire
on exactly that entity pair.

## Falsifiers and controls

- **F2** *if filtered MRR on the no-same-pair part is within 0.01 of 0.2648, the
  re-split contributed nothing measurable and I publish this at labelling size
  only.* **Did not fire** — 0.1503, a **0.1145** gap, eleven times the threshold.
- **F3** *if the same-pair share is under 10% the mechanism cannot carry a
  0.063 → 0.265 jump whatever the restricted MRR says.* **Did not fire** — 30.01%.
- **C1** the unmodified protocol returns **0.2648 / 0.3929 exactly**, against
  literals transcribed from `G34/RESULT.md` rather than read from this run. This
  is the control that makes the other two numbers mean anything: same rules,
  same ranker, same filter index, **only the test subset varies**.
- **C2** randomising the entity pairs drops the detector to **0.13%**, so it
  matches pairs and not the density of a graph where any pair is likely.
- **C3** 12,249 + 28,569 = 40,818, and neither part is empty.

## Nothing here is a code defect, and I read the code before saying so

The miner, the ranker and the filter were checked first and all three are
correct. **Ranks use the expected-rank convention** `1 + higher + equal/2`, not
the optimistic tie-break I went looking for; the zero-score branch averages over
the unscored tail the same way; and `build_filter_index(tri)` is built over
**all** triples, which is the proper filtered protocol rather than train-only.
**What is wrong is the split the number is computed on, and therefore what the
number means.**

## What this costs the scoreboard, stated plainly

The operator's `filtered_mrr` carries weight 2.0 with **target 0.28,
min_acceptable 0.25**. The published 0.2648 clears the minimum. **The
leakage-free partition is 0.1503, which does not**, and it is the honest figure
of the two for a method claiming to predict unseen links.

## Ceiling — this is a proxy, and I am not dressing it as the official number

**`no_same_pair` is NOT FB15k-237's official test split.** It is the re-split
with **one** leakage structure removed. The official split differs in more ways
than that, so 0.1503 is a **proxy** for what an official-split evaluation would
report, not a substitute for one. The official test triples are **not on disk**.

**No literature comparison is quoted, and that is deliberate.** ATOM-3 raised
this first and correctly: a literature comparison here must be recorded as
*unavailable* rather than quoted. G35 measured why — **7 of 7 external
attributions in this tree resolve to nothing under `corpus/`**. So the AMIE /
RuleN / AnyBURL figures G30 compared against are not re-derivable here, and this
row does not lean on them in either direction.

## Caught before publishing

The first leakage count used `SEED=42` while the generator's seed is
`0xC0FFEE`. Re-run on the real split: **30.0%** against 30.1% — the figure is a
property of the data and not the seed, but it was **measured, not assumed**, and
the wrong-seed run was never quoted.

## The better reading of this, and it is not mine

**ATOM-3, on reading the result:** the leakage is not a bug in the miner, it is
a **missing pipeline stage**. `elders/graph-engineering` (MIT, read-only,
licence read from `LICENSE` on disk) describes a 9-stage pipeline —
scope → representation → **ontology** → entities → relations → events →
**quality gate** → fusion → serve — and stages 3 and 7 are exactly where a
pipeline is supposed to know that a predicate has an inverse and that a split
must respect it. **This project has no ontology stage at all**; `G1_graph_ingest`
and `G13_ingest_audit` enter at stage 4. That reframes this row from *"our number
may be inflated"* to *"we entered at stage 4 and are paying for stages 1–3
downstream"* — a better finding and a worse problem. Recorded here with
attribution rather than absorbed.

## Files

`leak.py` (partition + all three arms + controls + `certify`) · `leak.json` ·
`fraction.out` · `provenance.json`.

```sh
python3 spikes/G46_split_leakage/leak.py     # ~100 s, ok=true, C1 pins 0.2648
```
