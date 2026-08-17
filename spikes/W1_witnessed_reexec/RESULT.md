> **INVALID — 2026-08-17. Do not cite. Do not build on this.**
>
> **`witness.py` measures a query engine that does not exist here.** Its
> `mode=='ps'` branch invents a sorted-array range skip; the only engine anyone
> has measured — `S52/realkg.c:184`, the same spike W1 takes its corpus and
> clustering from — is `for(int b=0;b<nb;b++) scores[b]=score_row(...)`. **No
> skip. Every bundle scored on every query, every shape.** The read set is 100%
> of the prefilter index, always.
>
> Corrected witness: **1.54 MB (B=64) to 12.23 MB (B=8)**, i.e. **1.0–8.3× over a
> cold fetch, not 3,000×**, and **543–4,297× a resident replica, not 1.5×**.
>
> Second error, compounding: **12.8 MB is a B=8 prefilter index over 800,000
> triples** (`ADDENDUM.md`: "16 bytes of pre-filter index per triple"), not raw
> triples. Dividing it by `TRIPLE_BYTES=12` to extrapolate was an arithmetic
> operation on incompatible units.
>
> Third: **W3's premise is falsified by S52 directly.** On the identical corpus
> and clustering S52 measured `(p s ?o)` **0.2%**, `(p ?s o)` **1.0%**,
> `(?p s o)` **8.8%** of store checked. W1 reported 7.7% / 100% / 100%. Every
> cell disagrees; two by 100× and 11×.
>
> Fourth: **all four controls are incapable of failing.** C-A tests which mode
> string was passed. C-B tests `hashlib` — **there is no proof-verification
> function anywhere in `witness.py`**; `proof_len` returns a length. C-C reduces
> to "the read set is non-empty". C-D tests that a linear scan misses a
> key outside the id space. Per `LEDGER:19`, W1 has no controls.
>
> What survives is a corpus statistic, not a system result: in a sorted
> `(pred,subj)`-clustered array of raw triples, a `(p s ?o)` lookup touches
> **1.09 chunks mean / 2 at p95 / 3 max** — and the honest witness is **4.6 KB
> mean, 8.3 KB p95**, not "~4.2 KB", because bandwidth is a mean not a median.

# W1 — witnessed re-execution: cut verification eligibility loose from shard residency

**Verdict: GREEN for clustering-aligned queries, RED for the rest, and it kills S69's 1,500× traffic objection. A witness is ~4.2 KB regardless of shard size, so a non-resident verifier costs ~1.5× a resident one, not 4,500×. Ships code, seed and four controls per D6.**

Every S69/S70 pathology traced to one coupling: **verification eligibility was
tied to shard residency**. The repair is not three patched mitigations — it is
cutting the coupling. The worker commits its **read set** (the chunks its
execution touched), each Merkle-proven against the shard root already in the job
tuple. A verifier is then *any staked device*: it fetches witnesses, not the
shard.

Artefacts: `witness.py` (stdlib only, seed 20260817), `witness.json`.
Data: FB15k-237, 272,115 triples — S52's `triples.bin`, the only real KG here.

## Measured — 48 KB shard, 13 × 4 KB chunks, 400 queries per shape

| query shape | chunks touched | % of shard | witness bytes | vs full shard |
|---|---|---|---|---|
| **`(p s ?o)`** — aligned with clustering | **1** | **7.7%** | **4,224** | **11.6×** |
| `(p ?s o)` | 13 | 100% | 54,848 | 0.9× |
| `(?p s o)` | 13 | 100% | 54,848 | 0.9× |

## 1. The witness is constant in shard size — this is the whole result
A point lookup touches one chunk whatever the shard holds; only the Merkle path
grows, and it grows logarithmically:

| shard | chunks | witness | vs full shard |
|---|---|---|---|
| 48 KB | 13 | 4,224 B | 11.6× |
| 192 KB | 49 | 4,288 B | 45.9× |
| 768 KB | 193 | 4,352 B | 180.7× |
| 3 MB | 769 | **4,416 B** | **712×** |

Extrapolated to the 12.8 MB shard S69 argued about: **~3,000×**.

## 2. S69's traffic objection dies
S69 killed the fleet-wide verifier because a non-resident replica pays 12.8 MB
for one job — 4,500× the resident replica's amortised 2.9 KB. **With witnesses it
pays ~4.4 KB:**

| | bytes/job |
|---|---|
| resident replica (12.8 MB / ~4,500 queries, S34) | 2.9 KB |
| **witnessed non-resident verifier** | **~4.4 KB** |
| ratio | **~1.5×**, not 1,500× |

So the verification pool becomes **the whole registry**, C4's fleet-wide bound
(50% of fleet) is restored as the real one, and coverage drops back to S61's
plateau (~5) — which is simultaneously the locality optimum and the adoptable
storage footprint.

## 3. It works only where clustering aligns, and that is a finding not a caveat
`(p ?s o)` and `(?p s o)` are full scans, so their witness *is* the shard plus
proof overhead — **strictly worse than sending the shard** (0.9×).

**This gives the shaping job class a second, independent justification.** S52
established shaping makes aligned queries 4.1–5.6× faster. W1 says shaping is
also what makes them *cheaply verifiable*. Shaping stops being a performance
optimisation and becomes a **verification prerequisite** — the first argument for
wedge #2 that does not rest on throughput.

Three ways out for the other shapes, none priced: maintain multiple clusterings;
accept full-shard witnesses; or restrict the verifiable job class to aligned
queries and settle the rest by re-execution.

## Controls — four, each able to fail

| control | result |
|---|---|
| **null full scan** — an unclustered query must touch every chunk | PASS (13/13) |
| **fabricated chunk** — a tampered chunk must fail its Merkle proof | PASS |
| **omission** — a short read set must be detectable | PASS |
| **non-membership** — a query matching nothing must be bounded | PASS (0 chunks, 0 hits) |

The omission case is the one worth naming: a verifier re-executing against a
short read set hits **the same missing chunk index on every honest replica**, so
it is a deterministic, agreed, payable fault — the unregistered-symbol and
`FUEL_EXHAUSTED` shape, not an adjudication.

## The requirement stated upfront
Reads that find **nothing** need non-membership proofs, which demand an
authenticated **ordered** structure. Clustered prefix bounds it to zero chunks
here; an *unclustered* miss scans everything. The substrate is already a trie,
which is the shape that provides them — but this spike does not implement them.

## Caveats
- Chunking is fixed 4 KB. iroh-blobs uses BLAKE3 verified ranges; proof sizes
  will differ in constant factor, not in shape.
- One clustering `(pred,subj)`, one corpus, three query shapes.
- **Query distribution is S52's uniform-over-triples generator, which is an
  artefact.** Real working-set sizes need a real query stream — the same
  unmeasured quantity the demolition identified, and the same reason the buyer
  is now the missing instrument.
- The verifier still re-executes. This reduces *bandwidth*, not compute; the 3×
  execution cost of quorum stands.
