# S79 — absence, the proof this project actually sells. S77's rule holds, and W2's ~2.0 KB is confirmed.

**Verdict: non-membership costs 1.02–1.04× membership and orders the three key
sets identically — so S77's "proof size is set by branching, not key length" is
not membership-only, and its retraction of S75/S76 extends to the absence
figures. Measured 1,589 / 1,930 / 2,291 B against W2's real
`prove_non_membership`, every proof verified. W2's published ~2.0 KB on the
realistic miss is CONFIRMED; S75's restatement of it as ~3.6–5.8 KB stays
retracted. The structural extra an absence proof must carry — every child at the
divergence point rather than all but one — is ~32 B on a ~1,500–2,300 B proof,
i.e. 2–4%. 5 controls, all fire.**

Artefacts: `absence.py` (seed 20260817), `absence.json`, `provenance.json`
(`certify ok=true`). Run: `python3 absence.py`.

## The falsifier, stated before the run

> If non-membership proof cost does **not** track branching the way membership
> does, then S77's *"proof size is set by branching, not key length"* is a
> membership-only statement and S77 overreached.

It tracks. Same ordering under the model, under W2's real prover, and under S77's
membership measurement.

## Why absence and not membership

W2's whole contribution over W1 was that absence is provable at all — W1 had no
verification function, which is why its four controls were dead. The verifiable
job class is trie-only queries, and **the query that needs a proof is the one
that returns nothing.** So the number carrying weight is W2's *"absence provable
at ~2.0 KB on the realistic miss"*, which S75 restated as ~3.6–5.8 KB on real
`pathmap`. S77 retracted that along with everything else derived from depth
**without putting a corrected figure in its place.** This is that figure.

## The model, stated before the numbers

A membership proof charges `(children − 1)` at each branching position: the
siblings not taken. An absence proof charges the same along the shared prefix,
then at the **divergence position** carries **every** child of that node —
`children`, not `children − 1` — because the claim is that the needed byte is not
among them. Showing a subset would let a prover hide the child that makes the key
present. **That +1 is the entire structural difference.**

## Measured

| key set | divergence depth | membership B | absence B (model) | ×mem | **W2 real absence B** |
|---|---|---|---|---|---|
| atoms, original | 95.5 | 1,461 | 1,513 | **1.04×** | **1,589** |
| atoms, interned | 54.3 | 1,803 | 1,856 | **1.03×** | **1,930** |
| triples | 11.0 | 2,246 | 2,299 | **1.02×** | **2,291** |

Ordering by membership, by the absence model, and by W2's real prover: **all
three identical** (`atoms_original < atoms_interned < triples`).

**Absence is nearly free once you are paying for membership.** The +1 digest at
divergence is ~32 B against 1,500–2,300 B of shared-prefix siblings. The intuition
that absence is the expensive case is wrong here, and it is wrong for the same
reason depth was: what a proof costs is the branching it passes, and an absence
proof passes almost exactly the same branching as a membership proof to the same
place.

## Probes are deep misses, deliberately (A27)

Probes are built by walking each real key to **the deepest position the trie still
contains** and then taking a byte that is not a child there — absence by
construction, not by hope. Mean divergence depth **95.5 / 54.3 / 11.0**.

A random-byte probe would diverge at the root and give a small, true, useless
number: that is exactly how S73 published a flat 293 B across a 10× space range,
and `C_probes_are_deep_misses` is what stops it recurring.

## The instrument is the one C14 validated

The sibling walk here is computed in Python from the key sets alone. That is not
a shortcut around Rust: **C14 attacked S77 by recomputing its `pathmap` walk this
exact way and got 0.00% relative difference on all three sets**, so the Python
recount *is* the validated instrument and no new unvalidated code sits under this
number. W2's real `prove_non_membership` runs beside it and every proof is
checked with `verify_non_membership`.

## Controls — five, each naming the input that makes it fail

| control | fails if |
|---|---|
| **`C_probes_are_absent_and_proofs_verify`** | any probe is found present by `prove_membership`, or any absence proof fails verification. An "absence proof" for a present key is a number about nothing |
| **`C_probes_are_deep_misses`** | mean divergence depth is below 2 for any set — the cheap-miss artefact A27 names |
| **`C_absence_tracks_branching_like_membership`** | the absence ordering differs from the membership ordering. Then S77's generalisation is membership-only and it overreached |
| `C_real_prover_agrees_on_absence_ordering` | W2's real absence bytes rank the sets differently from the modelled digest counts |
| `C_absence_costs_more_than_membership` | any set shows absence costing no more than membership — the model says it must, so if it does not, the model is wrong about what an absence proof shows |

**All five fire.**

## What this does not settle

- **Completeness proofs are still unmeasured.** W2 proves membership,
  non-membership *and* completeness; this covers the second. A completeness proof
  covers a whole query range, so it has no single divergence point and this model
  does not extend to it by inspection.
- **The model's absolute bytes are 4–7% under W2's real ones** (1,513 vs 1,589 ·
  1,856 vs 1,930 · 2,299 vs 2,291), the same residual as S77: W2's per-step
  framing, which digest counting does not model. The ordering does not depend on
  it.
- **Membership and absence to the SAME place** are what is compared. A miss that
  diverges shallow is cheaper, and that is the operating point W2's `C_miss_depth`
  control already guards.
- One corpus, no timings — valid while `quiet.sh` refuses.
