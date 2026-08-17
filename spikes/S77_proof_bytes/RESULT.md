# S77 — S75 and S76 measured the wrong quantity. Both corrections are retracted.

**Verdict: node DEPTH is not a proxy for proof size, and the two spikes that
converted one into the other by multiplying were wrong — one of them by 2.9×
in one direction and 7.2× in the other, on the same instrument, in the same
hour. Measured against `pathmap`'s real paths and cross-checked against an
implemented prover: an authentication path is paid for in SIBLINGS, and a long
key is a long UNBRANCHED run that adds nodes without adding siblings. S73's
published 1,770 B was approximately right on real `pathmap` all along, and
S76's interning made proofs 22% BIGGER, not 2.3× smaller. 6 controls, all fire.**

Artefacts: `measure.py` (seed 20260817), `pmproof/src/main.rs` (Rust, path
dependency on `elders/PathMap`, built and tested **in place** per §10),
`measure.json`, `probe_out.txt`, `provenance.json` (`kfcheck.certify`).
Run: `python3 measure.py`.

## The falsifier, stated before the run

> If the number of **sibling** digests along a `pathmap` path scales with node
> depth — if the extra nodes on a long unbranched run really do cost a proof —
> then depth was a valid proxy, S75 and S76's multiplications stand, and nothing
> here is retracted.

It does not scale. **Both are retracted.**

## Measured — the three key sets those spikes committed, unmodified

| key set | key B | node depth *(S75/S76)* | **siblings on path** | auth bytes (siblings×32) | **what depth implied** | **W2 real proof B** |
|---|---|---|---|---|---|---|
| atoms, original | 106.6 | 139.1 | **45.7** | 1,461 | 4,450 | **1,568** |
| atoms, interned id4 | 52.5 | 61.3 | **56.4** | 1,803 | 1,960 | **1,917** |
| W2 triples | 12.0 | 10.3 | **70.2** | 2,246 | 328 | **2,350** |

**The ordering inverts.** By depth, triples are the cheapest key set by 13×. By
what a proof actually carries, they are the **most expensive**. Depth
over-predicts the atom proof by 2.8× and under-predicts the triple proof by
7.2×, so it is not even wrong by a constant that could be divided out.

## Why depth was the wrong quantity

An authentication path carries, at each position it passes, the digests of the
**sibling subtries it did not take**. A position with one child has no siblings:
it costs the proof nothing but a step the verifier recomputes from key bytes it
already holds.

So a 1,155-byte atom key is a long **unbranched** run — ~1,148 nodes, almost all
single-child, contributing ~0 digests. A 12-byte triple key out of 4,096 dense
keys branches at nearly every position. **Siblings per node on the path: 0.33
(atoms), 0.92 (interned), 6.8 (triples).**

S75 measured node depth, called each node "one authenticated step", and
multiplied. S76 inherited that and measured the same wrong quantity more
carefully, over four encodings, with a sweep and an affine test. `CLAUDE.md`
names this exactly: **"the right measurement of the wrong question"** — one of
the three it says no tool will catch. No tool caught it. Both spikes'
depth numbers are correct and reproduce; every conclusion drawn from them about
proof size was wrong.

## Grounded against a prover that exists, not against arithmetic

Sibling count × 32 B is still arithmetic. So the same keys go through W2's
`prove_membership`, and every sampled proof is checked with `verify_membership`
against the root hash — a prover and verifier written before this spike, free to
rank the sets any way at all.

They agree, and closely: **1,461 vs 1,568 · 1,803 vs 1,917 · 2,246 vs 2,350**,
same order, within 5–7%. The residual is W2's per-step framing, which the
sibling count does not model and which the two implementations do not share.

## What is withdrawn, and what survives

| claim | where | status |
|---|---|---|
| "S73's 1,770 B insert proof is ~33 KB on real `pathmap`" | S75 RESULT, WORK_QUEUE, HANDOFF C10 | **RETRACTED.** ~1.5 KB measured |
| "W2 becomes ~3.6–5.8 KB" | S75 | **RETRACTED.** 2,350 B measured, and W2's published 1.5–2.4 KB was right |
| "~14 KB at id4, ~9.9 KB at id2" | S76 RESULT, WORK_QUEUE, HANDOFF C12 | **RETRACTED.** 1,917 B at id4, and it is *worse* than not interning |
| "interning recovers about half" | S76 | **RETRACTED and reversed.** Interning costs 22% more proof bytes (1,568 → 1,917) |
| mean node depth 7.6→139.1, 4.2→10.3, and the four-variant sweep | S75, S76 | **STAND.** Replayed and reproduced; they are just not proof sizes |
| `pathmap`'s `merkleize` is a dedup pass on a non-cryptographic hash | S75 | **STANDS.** Untouched by this |
| "S74 is untouched — a chain step hashes digests, never walks a path" | S75, S76 | **STANDS**, and is now the only cost claim in the chain that never depended on depth |
| S73's "same shape, different constants" caveat | S73 | **RESTORED.** S75 called it "too weak at 18.4×"; the 18.4× was not a proof-size factor, so the caveat was right and the criticism of it is withdrawn |

## The finding that replaces them

**Proof size is set by branching along the path, not by key length.** That
reverses the design advice both spikes gave. Interning symbols to fixed-width
ids shortens keys and *concentrates* branching into fewer positions, which is
the wrong direction for proof size; S76's own numbers show it, read correctly.
For a corpus whose atoms are long and sparse, the encoding was already close to
optimal for authentication, and the effort spent on it bought nothing.

**This does not say `pathmap` is free.** It says the cost is where the
alternatives are, not where depth suggested. Storage, traversal time and node
count all still scale with key length as S75 measured — 83,210 nodes against
1,852 is real. Only the *proof* does not.

## Controls — six, each naming the input that makes it fail

| control | fails if |
|---|---|
| **`C_probe_reads_the_zipper_correctly`** | keys `aa` and `ab` branch exactly once, so the path to `aa` has exactly 1 sibling; any other answer means `child_count` was misread and this spike measures nothing |
| `C_same_key_files_as_S75_S76` | any key count differs from the reviewed spikes' committed `compare.json` — this is a review of two specific spikes, on their files |
| **`C_depth_and_siblings_disagree`** | depth and sibling count rank the three key sets the same way. Then depth was a valid proxy and **nothing is retracted** |
| **`C_real_prover_agrees_with_the_sibling_walk`** | W2's real proof bytes rank the sets differently from the sibling walk. Then the walk is a model of nothing and neither number publishes |
| `C_every_sampled_proof_verifies` | any sampled proof fails `verify_membership` — W1 shipped four controls with no verification function at all, which is why this one exists |
| **`C_long_keys_add_nodes_not_branches`** | the longest-key set does not have the fewest siblings per node. That is the mechanism, stated so it can be wrong |

**All six fire.**

## How this was missed twice, which is the part worth keeping

Both spikes had firing controls, a stated falsifier, `certify ok=true`, and an
instrument validated against the library's own test set. S76 added a
four-encoding sweep, a monotonicity control, an affine refusal, and an
injectivity check run *before* the measurement. **None of that could see it**,
because every one of those controls was a check on the measurement of depth, and
depth was not the question. A more careful measurement of the wrong quantity
reads as a stronger result.

The one thing that would have caught it, at any point, is the sentence both
spikes wrote down and marked not yet run: *"no proof was actually generated on
`pathmap`."* It sat in the caveats of S75, was carried forward verbatim into
S76 as "the binding one", and was still there when S76 published a corrected
number that depended on it. **State the falsifier before running, then run it** —
this is the third time in this project that the surviving error is the one whose
falsifier was written and deferred.

## Caveats

- **Siblings are counted at LOGICAL byte positions**, which is the trie a Merkle
  proof commits to and the one W2 proves over. `pathmap`'s own `merkleize`
  hashes PHYSICAL nodes instead; a commitment built that way would add a step
  per physical node, though still no digests for single-child ones. Unmeasured,
  and it is the obvious next probe.
- **Membership only.** Non-membership and completeness proofs carry more, and
  W2 measured absence at ~2.0 KB on its own trie; that comparison is not made
  here.
- **32 B digests assumed** for the `pathmap` side. `pathmap` has no
  cryptographic hash at all (S75), so this is the width a real commitment would
  need, not one the library provides.
- **W2's prover is sampled** (~200 keys per set, deterministic stride); the
  `pathmap` walk is every key.
- **One corpus, one `pathmap` version** (0.3.0, pre-release), `counters` a
  non-default feature — carried forward from S75 unchanged.
- **No timings.** Counts and digests only, so valid while `quiet.sh` refuses.
