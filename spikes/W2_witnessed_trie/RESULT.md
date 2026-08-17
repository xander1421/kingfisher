# W2 — witnessed re-execution on the trie substrate, with non-membership that a verifier can actually reject

**Verdict: GREEN for the exact-match trie stage, and it closes W1's one surviving
requirement. Absence is provable at ~2.0–2.6 KB, and completeness — the refusal
of a silently dropped row — costs 1.5–2.4 KB of authentication path independent
of answer size. This does NOT rescue the prefilter: W4's kill stands, and the
verifiable job class is exactly the queries the trie answers alone.**

Artefacts: `trie_witness.py` (stdlib only, seed 20260817), `witness.json`,
`provenance.json`. Corpus: FB15k-237, 272,115 triples — `../S52_realkg/triples.bin`,
the only real KG here. Substrate: radix-256 trie, the shape MORK's `pathmap`
(`elders/PathMap`) is. Run: `python3 trie_witness.py`.

## Why this spike exists, and what it deliberately is not

W1 is **INVALID**: it measured a sorted-array range skip that no engine here
implements, and it had **no proof-verification function at all** — `proof_len`
returned a length. W4 then closed the prefilter route permanently: the HDC
prefilter is a similarity search, its read set is 100% of the index on every
query, and no key ordering can bound it.

W4 left three routes. This takes route 1 — **verify the exact-match stage only,
treating the prefilter as an untrusted accelerator.** The difference from W1 is
structural, not cosmetic: a similarity search has no order in the key, and a
radix trie *is* order in the key. Prefix skipping here is what the data structure
does, not something the spike invented.

W1 also named the thing it did not build:

> "Reads that find **nothing** need non-membership proofs, which demand an
> authenticated **ordered** structure. The substrate is already a trie, which is
> the shape that provides them — but this spike does not implement them."

Built here, with a verifier that returns False.

## What is proved, and why completeness is the one that matters

Three proof kinds over one Merkle root:

| proof | statement |
|---|---|
| membership | key K is in the shard |
| **non-membership** | key K is **not** in the shard |
| **completeness** | the answer to prefix query Q is **exactly** this set |

A dishonest worker's cheapest cheat is **not** a fabricated row — an inclusion
proof catches that for 32 bytes. It is a **silently dropped match**. Only an
ordered authenticated structure can refuse it, because refusing it means proving
nothing lies in a range. That is the whole reason the substrate has to be a trie
and not a hash set.

## Measured — 4,096-triple shard (W1's unit, kept for comparability)

Shard `[0:4096]` of the `(p,s,o)`-sorted corpus: 49,152 B, **3 predicates**,
521 `(p,s)` pairs, fan-out median 3 / max 394.

| query shape | ans med | **auth path B** | answer B | witness B | % shard | vs shard | verified |
|---|---|---|---|---|---|---|---|
| `(p s ?o)` aligned | 25 | **1,461** | 1,080 | 2,541 | 2.20 | **0.05×** | 200/200 |
| `(p ?s o)` | 2 | **75** | 23,550 | 23,625 | 47.91 | 0.48× | 200/200 |
| `(?p s o)` | 1 | **0** | 49,152 | 49,152 | 100.00 | 1.00× | 200/200 |

**Non-membership — two arms, and the flattering one is the easy one:**

| arm | path steps | wit med | wit mean | max | % shard | verified |
|---|---|---|---|---|---|---|
| shallow (uniformly random absent key) | 0.01 | 107 B | 121 B | 2,068 B | 0.247% | 200/200 |
| **deep (`(p,s)` present, `o` absent)** | **2.98** | **2,010 B** | **1,952 B** | 2,736 B | 3.970% | 200/200 |

A uniformly random absent key diverges **at the root**, because this shard holds
3 predicates out of 237 — its 107 B witness is arithmetic about the corpus, not a
property of the proof system. The realistic miss shares the whole clustering
prefix with real rows. **The honest cost of proving absence is ~2.0 KB, not
107 B**, and `C_miss_depth` exists to stop that substitution being made silently.

## The number I nearly published, and the decomposition that caught it

First run, shard `[0:]`: aligned witness **2,541 B**. Re-run on shard
`[136000:]`: **2,474 B**. Two shards, 2.6% apart — it reads as "the witness is
flat in shard composition."

It is a coincidence:

| shard | `(p,s)` pairs | ans med | auth path | answer B | total |
|---|---|---|---|---|---|
| `[0:]` | 521 | 25 | 1,461 | 1,080 | 2,541 |
| `[136000:]` | 1,115 | 5 | **2,391** | **84** | 2,474 |

The mid shard has twice the `(p,s)` pairs, so the trie is wider and the sibling
path costs **64% more**; its answers are 5× smaller, so the data costs **93%
less**. The two moved in opposite directions and cancelled. Reporting the total
as flat would have been a W1-class result — an accidental agreement dressed as a
structural law.

**The claim the decomposition does support:** the *price of verifiability* is the
authentication path, 1.5–2.4 KB, and it is independent of answer size. The answer
bytes are not overhead — the verifier needs the rows to re-execute at all.

## Scaling — the path grows 2.7× for a 64× shard

| shard B | auth path | aligned witness | absence witness | aligned/shard |
|---|---|---|---|---|
| 12,288 | 1,217 | 1,294 | 1,400 | 0.1053× |
| 49,152 | 1,523 | 2,551 | 2,273 | 0.0519× |
| 196,608 | 2,709 | 3,182 | 3,121 | 0.0162× |
| 786,432 | 3,279 | 3,565 | 3,671 | **0.0045×** |

64× the shard costs 2.7× the path. So the aligned witness *fraction* keeps
falling — 10.5% → 0.45% — which is the shape W1 claimed for the wrong reason on
the wrong engine. Growth is sub-logarithmic in triples because the branching
factor at the `(p,s)` depth also changes; it is not a clean `log n` and is not
reported as one.

## Two of the three shape numbers are corpus arithmetic, not measurement

Stated plainly because W1 died of exactly this:

- **`(p ?s o)` = 47.91% of the shard** (67.31% on the mid shard). This is
  ~1/(distinct predicates in the shard), size-weighted. The shard holds 3
  predicates. It is a **shard-composition figure**, and it moves 40% when the
  shard moves.
- **`(p s ?o)` answer mean 90 vs median 25.** S52's uniform-over-triples
  generator samples `(p,s)` pairs **in proportion to their fan-out**, so the mean
  is set by the single 394-row pair. Both are reported; neither is a query-stream
  estimate, because there is still no query stream.
- **`(?p s o)` = 1.00× exactly.** The covering node is the root, so the path is
  0 bytes and the witness *is* the shard. Cleaner than W1's 0.9×, which was an
  artefact of a mis-counted multiproof.

**No claim here reproduces or contradicts S52's 0.2 / 1.0 / 8.8%.** Those are
`checked·B/NT` through the bundled prefilter; these are exact-stage trie read
sets. Different instruments on the same corpus. Dividing one by the other is the
unit error W1 committed.

## Controls — nine, each naming the input that makes it fail

| control | fails if |
|---|---|
| `C_honest` *(negative — bounds resolution)* | any honest proof verifies False; then every rejection below is vacuous |
| **`C_omit`** | a short answer verifies — omission undetectable, completeness is theatre |
| `C_add` | a fabricated row inside the proven prefix verifies |
| `C_tamper` | a one-byte-flipped answer verifies |
| **`C_forged_nonmembership`** | a doctored divergence node verifies as absence — a worker could then deny any row it dislikes |
| `C_wrong_root` | an honest proof verifies under a foreign root; the root would bind nothing |
| `C_child_order` | reversing a node's child order leaves the digest unchanged; the canonical sort would be decorative |
| `C_replay` | key A's proof verifies for key B; proofs would not bind the key they answer |
| `C_miss_depth` | the deep miss arm does not authenticate a longer path than the random arm; "hard miss" would be a label, not a case |

**All nine fire.** Observations persist in `provenance.json`, not in this prose
(A20). `C_forged_nonmembership` is the one that answers W1's dead C-B: the prover
**refuses** to emit an absence proof for a present key, and a hand-doctored one
is rejected because the tampered node no longer folds to the root.

Per A15/N1d: `C_honest` is the negative control that bounds resolution, the other
eight are positive controls that establish detectability. Both are required.

## What this changes

1. **The verifiable job class is now defined by the trie, not by residency.**
   Queries the trie answers alone are witnessable at 0.05× the shard for aligned
   shapes. Queries needing the prefilter are not witnessable at all (W4).
2. **The `(p s ?o)` shaping job class gains its second, independent
   justification** — the one W1 reached for and could not support. S52: shaping
   makes aligned queries 4.1–5.6× faster. W2: shaping is also what makes them
   *cheaply provable*. Alignment is a verification prerequisite, not a
   performance tweak.
3. **`(?p s o)` is not worth witnessing, ever** — 1.00×, provably. Send the
   shard. Not a caveat; a design conclusion with a measured boundary.
4. **The commitment is DAG-shaped for free.** Node digest depends only on
   `(prefix, term, children)`, so identical subtries hash identically — which is
   pathmap's structural sharing expressed in the authentication layer. Untested
   as a size win; noted as an alignment, not a result.
5. **M1.5's deviation gets a second reason to revisit.** Whole-blob sha2-256
   cannot prove a range; this needs exactly the partial-verification primitive
   the row originally justified as "the proofs W1 uses". W1 is dead, but the
   requirement outlived it.

## Caveats
- **One clustering** `(pred,subj)`, one corpus, 4,096-triple shards, two offsets.
- **Python trie, not `pathmap`.** The proof system is faithful to the *shape* of
  a path-compressed radix-256 trie; it is not built on MORK's crate, so constant
  factors (node layout, ACT format, real branching factors) will differ. The
  falsifier: build the same three proofs on `pathmap` and show the auth path
  departs from 1.5–3.3 KB by more than the branching factor explains.
- **Key encoding is big-endian and that is load-bearing** — little-endian gives
  a trie whose prefixes mean nothing. Any real deployment must pin the encoding
  in D2 alongside the result canonicalisation. Currently unpinned.
- **Nothing here reduces compute.** The verifier still re-executes over the
  proven key set; `reexecute()` is the function that does it. This buys
  bandwidth, exactly as W1 intended and 3× execution cost stands.
- **Still no query stream.** Every fraction above is conditioned on S52's
  uniform-over-triples generator, the same missing instrument flagged everywhere
  else.
- Fixed-length 12-byte keys, so the "key ends at a non-terminal node"
  non-membership branch is implemented but **unexercised by this corpus**.

## Changelog
- **2026-08-17, ATTACK cycle 8 (AGENT-1).** Two corrections to how this spike was
  *certified*, none to its numbers. (1) It called `provenance.record` directly for
  four cycles; `CLAUDE.md`'s entry point is `kfcheck.certify`, which also runs
  family **B** (instrument fiction) and family **E** (the number is real, the model
  is wrong) and **refuses a run with no declared falsifier**. Now certified,
  `ok: true`, falsifier recorded. (2) Family E fires on the scaling table:
  `units.check_affine` **REFUSES** an affine model on those four points — adjacent
  slopes span 0.00097–0.0083, **760% of the 25% tolerance**. So the rows are
  *measured points*, the endpoint statement ("2.7× the path for 64× the shard") is
  an endpoint ratio, and **no rate may be fitted to them**. The `0.05× shard`
  figure carries its operating point in the table beside it, per
  `units.ratio_with_operating_point`: it is `1 + path/answer` and moves with answer
  size, which is why this page reports the path and answer bytes separately.
  A soundness bug in `walk`/`prove_non_membership` was also fixed this cycle — see
  `ATTACK.md`. Every published number is byte-identical after it.
