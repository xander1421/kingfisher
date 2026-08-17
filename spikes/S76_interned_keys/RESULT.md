# S76 — intern the symbols, as S75 said to. It works, it is not enough, and it says why.

**Verdict: S75's mechanism claim SURVIVES its falsifier — interning brings the
atom-key depth ratio from 18.39× to 7.86× (4-byte ids) and 5.50× (2-byte ids),
under the 10× bar S75 fixed before reading. But it does NOT reach W2's 2.44×
regime, and a four-point sweep over one atom set shows why: `pathmap` spends
about one node per key BYTE (0.86–1.30 across all five key sets measured) while
W2's trie spends one per STRUCTURAL step (7.6–7.8 for atoms at every id width).
The ratio is therefore bytes-per-structural-node, and interning shortens only
one of the two terms that make up the bytes. S73's ~33 KB insert proof comes
back to ~14 KB, not to 1,770 B. 7 controls, all fire.**

Artefacts: `intern.py` (seed 20260817), `compare.json`, `probe_out.txt`,
`keys_atoms.bin` / `keys_triples.bin` (the headline id4 key sets),
`provenance.json` (`kfcheck.certify`, falsifier declared).
Run: `python3 intern.py`.

## The falsifier, stated before the run

> If interning every symbol to a fixed-width id does **not** bring the
> `pathmap`/Python mean node-depth ratio for atom keys under 10×, then the cause
> of S75's 18.4× is **not** key length and S75's mechanism claim is wrong.

It did bring it under, at all three id widths. **The claim survives.**

## The instrument is S75's, unmodified — and it is checked, not assumed

`pmprobe` reads `../keys_atoms.bin` relative to its CWD, so this spike runs
S75's **committed binary** from `probe_cwd/` and it reads *this* directory's key
files. Nothing in S75 is edited: extending a committed spike's instrument in
place is how an artifact stops being the thing its provenance describes (A24).

That buys the two controls that make this a comparison rather than two runs.
The **original encoding replayed through the same binary in this session
reproduces S75 exactly** — 139.05 mean depth, 83,210 nodes, 1,246 keys — and the
triples arm, which this spike does not touch, reproduces 10.26 / 3,160.

## Measured — one atom set, four encodings, one probe

| variant | id B | key B max | key B mean | py depth | **pathmap depth** | ratio | pathmap nodes |
|---|---|---|---|---|---|---|---|
| original (S73/S74) | — | 1,155 | 106.6 | 7.6 | 139.1 | **18.39×** | 83,210 |
| interned | 4 | 619 | 52.5 | 7.8 | 61.3 | **7.86×** | 32,823 |
| interned | 3 | 533 | 44.6 | 7.8 | 51.9 | **6.66×** | 27,258 |
| interned | 2 | 447 | 36.6 | 7.8 | 42.9 | **5.50×** | 21,637 |
| *W2 triples (reference)* | — | 12 | 12.0 | 4.2 | 10.3 | *2.44×* | 3,160 |

**Not quotable as a rate, and `units` is what says so, not me.** Adjacent slopes
span 0.1455–0.1947, 34% against a 25% tolerance: `check_affine` refuses, so the
four points are reported as points (A18).

## What the sweep shows that one threshold crossing could not

Max node depth against max key bytes, per variant: **1,155→1,148 · 619→611 ·
533→525 · 447→439**, and for triples 12→11. `pathmap`'s node depth *is* the key
length in bytes, less whatever prefix is shared across the set. Mean depth per
mean key byte: **1.30** (original), **1.17 / 1.17 / 1.16** (interned),
**0.86** (triples).

Meanwhile W2's trie depth does not move at all across the three interned widths
— **7.8, 7.8, 7.8** — because it compresses an unbranched run into one node
regardless of its length. Its depth is the atom's *structure*.

So the ratio is not a property of either implementation alone. **It is
bytes-per-structural-node**, and that is the sentence S75 should have carried:
its "key length is the load-bearing variable" is right, and this is the form
that predicts the number instead of describing one.

## Why interning stops at 5.5× and cannot reach 2.44×

An interned atom key at id2 averages **36.6 B**, not 12 B, because interning
shortens only the symbol term. The expression framing costs **3 B per node**
(`E` + 2-byte arity) and is untouched, and a structured atom has several nodes.
To land in W2's regime an atom key would have to be ~12 B total, which for a
nested expression is not an encoding choice — it is a different data model.

| | published | on real `pathmap` (S75) | interned id4 | interned id2 |
|---|---|---|---|---|
| S73 isolated insert proof | 1,770 B | ~33 KB (×18.4) | **~14 KB (×7.9)** | **~9.9 KB (×5.5)** |

**S75's "the fix is in the encoding" is corrected here to: the encoding recovers
about half of it and the residue is structural.** Recorded as a correction to
S75 rather than a new claim beside it; S75's changelog carries the pointer.

**S74 remains untouched**, for the reason S75 gave: a chain step hashes digests
and never walks a path.

## Interning moves the cost, it does not remove it

A 4-byte id means nothing without the table that assigns it, and two parties
verifying one proof must agree on that table or they are verifying different
statements. Measured, not waved at: **1,713 symbols, 41,465 B of UTF-8, 44,891 B
to commit with lengths.** Against 1,246 atoms that is ~36 B per atom of one-time
committed cost, set against ~54 B per atom saved in mean key length.

Ids are assigned by **sorted symbol order**, not first appearance, so two
parties holding the same symbol set derive the same table without
communicating. `C_symbol_ids_are_canonical` is that check, and it is driven by a
shuffle that a first-appearance assignment would fail.

## Controls — seven, each naming the input that makes it fail

| control | fails if |
|---|---|
| **`C_interning_is_injective`** | any atom fails to round-trip, or two distinct atoms encode to one key. **Checked first and separately**: a shorter encoding that collides would produce exactly the depth improvement being claimed |
| **`C_original_replay_reproduces_S75`** | replaying S73's encoding through the same binary now differs from S75's committed 139.05 / 83,210 / 1,246 by any amount — then the instrument moved and no comparison holds |
| `C_triples_arm_reproduces_S75` | the untouched triple arm differs from S75's committed 10.26 / 3,160 |
| `C_key_length_actually_fell` | interned keys are not shorter on both max and mean — the mechanism names key length, so key length must be seen to move (A26) |
| **`C_interning_brings_ratio_under_threshold`** | the interned ratio reads at or above 10× — the declared falsifier |
| **`C_ratio_moves_with_id_width`** | the ratio does not decrease monotonically as mean key bytes decrease across the four variants. One threshold crossing is one point (A18); this is the arm that makes it a relation |
| `C_symbol_ids_are_canonical` | rebuilding the table from a shuffled atom order yields any different id |

**All seven fire.**

## Caveats

- **Depth is a proxy for proof size, not a measurement of it.** No proof was
  generated on `pathmap`; the node depth a proof would have to traverse was
  counted. S75's caveat, carried forward unchanged because it is still the
  binding one — the ×7.9 and ×5.5 are **scaling corrections, not re-measured
  byte counts.**
- **The symbol table is measured, not designed.** Committing it, updating it as
  the corpus grows, and what a verifier does with an id it has never seen are
  all open. An id space that changes between epochs would break S74's chain, and
  that interaction is untested.
- **id2 caps the symbol set at 65,536.** This corpus needs 1,713. A corpus that
  outgrows the width silently changes the encoding, which is a real fault class
  (`FEATURE_EQUIVALENCE`), and nothing here guards it.
- **One corpus, one `pathmap` version** (0.3.0, pre-release, "expect API churn"),
  and the `counters` feature is non-default — enabling it could in principle
  change node layout, unchecked, as in S75.
- **No timings.** Counts and digests only, so this is valid while `quiet.sh`
  refuses.

## Changelog

**2026-08-17, AGENT-1 — the headline proof-size figures on this page are
RETRACTED by S77, roughly an hour after they were published.**

Withdrawn: **~14 KB (id4) and ~9.9 KB (id2)** for S73's isolated insert proof,
and the claim that **"interning recovers about half"**. Both were node depth
multiplied by a digest width, and depth is not what a proof carries. Measured
against `pathmap`'s real paths and cross-checked with W2's implemented prover:
**1,568 B at the original encoding and 1,917 B interned at id4 — interning made
proofs 22% BIGGER.** The design advice on this page is therefore reversed:
shortening keys concentrates branching into fewer positions, which is the wrong
direction for proof size.

Also withdrawn by consequence: this page's correction of S75's "the fix is in
the encoding". There was nothing to fix in the encoding; the number that
motivated it was not a proof size.

**Everything measured here stands and reproduces** — key lengths, node depths,
the four-variant sweep, the monotonicity of depth with key length, the affine
refusal, the symbol table's 44,891 B, and the instrument controls that replay
S75 exactly. They are correct measurements of node depth. Depth was not the
question, and no control on this page could have said so, because every one of
them checked the depth measurement. See `spikes/S77_proof_bytes/RESULT.md`,
section *"How this was missed twice"*.
