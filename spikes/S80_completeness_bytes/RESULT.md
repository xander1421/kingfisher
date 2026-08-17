# S80 — the third proof kind, and it puts a scope on S77. The rule is point-query-only.

**Verdict: the completeness auth path orders the three key sets DIFFERENTLY from
membership — triples are the most expensive point query (2,269 B) and the
CHEAPEST range query (1,401 B). So S77's *"proof size is set by branching, not
key length"* is a **point-query** claim, and S77/S79 now carry that scope. The
mechanism survives and is sharpened: a proof costs **the branching it actually
passes**, and which branching a query passes depends on where the query stops.
4 controls, all fire; the falsifier fired.**

> **CHANGELOG 2026-08-17 (ATTACKER-1, S23) — THE VERDICT ABOVE IS WITHDRAWN. The
> EVIDENCE is not, and nothing here was mislabelled.** Both quantities compared
> above are AUTHENTICATION PATHS — the column header says so and the measured
> column is honestly named `w2_real_step_bytes_mean`. Both reproduce exactly. The
> withdrawn step is one sentence: **an ordering measured on the auth path was used
> to scope a claim about PROOF SIZE**, and the auth path is exactly the part of a
> completeness proof that omits the answers it exists to deliver
> (`completeness.py:125` calls `steps_bytes`, so `12 · len(pf['keys'])` is charged
> to nobody). **Charge both sides their terminal descriptor on this spike's own
> 120-query sample and the falsifier above does NOT fire:** completeness is dearer
> than membership in ALL THREE sets — 1,727.76 vs 1,689.98 · 2,040.45 vs 1,960.96 ·
> **2,668.35 vs 2,379.67**. Triples is not the cheapest range query, it is the
> dearest, **+81.89% over the 1,467 B published here**, because a triples
> completeness proof carries **100.1 answer keys** against ~12 for either atom set.
> **So the point-query scope this spike placed on S77 and S79 does not follow from
> its own evidence and is withdrawn.** What stands: the three auth-path figures,
> every control, and the sharpened mechanism *"a proof costs the branching it
> actually passes"* — true of the auth path. `completeness.py` deliberately NOT
> edited (family C: its number is what that function returned, and editing the
> source desyncs it from `provenance.json`). Evidence:
> `spikes/S23_consumer_sweep/`, 9 rows, C0 exact on all of them.

Artefacts: `completeness.py` (seed 20260817), `completeness.json`,
`provenance.json` (`certify ok=true`). Run: `python3 completeness.py`.

## The falsifier, stated before the run — and it fired

> If completeness proof cost does **not** order the three key sets the way
> membership and absence do, then "proof size is set by branching" is a claim
> about point queries only, and S77/S79 must say so.

## Measured — 120 queries per set, prefixes at 75% of each key's length

| key set | query B | answer keys | **completeness auth B** | membership B *(same sample)* | W2 real step B |
|---|---|---|---|---|---|
| atoms, original | 80.5 | 11.7 | **1,479** | 1,490 | 1,588 |
| atoms, interned | 42.7 | 12.0 | **1,785** | 1,802 | 1,896 |
| triples | 9.0 | 100.1 | **1,401** | 2,269 | 1,467 |

- by membership: `atoms_original < atoms_interned < triples`
- **by completeness auth path: `triples < atoms_original < atoms_interned`**
- by answer size: `atoms_original < atoms_interned < triples`

## What actually happens, and why it does not overturn S77

A range query stops before the end of the key, so it never pays for the branching
in the tail. **For triples that tail is where the branching lives** — the last 3
of 12 bytes carry the high-fan-out object field, and skipping them drops the auth
path from 2,269 B to 1,401 B, a **38% saving**. For atoms the skipped 26 bytes are
almost unbranched, so the same 25% prefix cut saves **less than 1%** (1,490 →
1,479 B).

So the mechanism S77 identified is not wrong — it is **under-stated**. The correct
form:

> **A proof costs the branching it actually passes.** Key length does not decide
> that, and neither does the key set alone: *where the query stops* decides which
> branching is on the path.

S77's ordering was a fact about full-key queries and was published as a fact about
key sets. That is a scope error, not an arithmetic one, and the numbers behind it
stand.

## The answer set is a separate axis, checked rather than asserted

Triples average **100.1 answer keys** per query against ~12 for both atom sets,
while their auth path is the cheapest. Answer size and auth path therefore order
the sets **oppositely**, which is why a single "completeness proof size" would be
one number standing for two mechanisms (A18). `C_answer_size_is_a_separate_axis`
fails if the two orderings coincide — on a corpus where they did, publishing a
total would have been safe, and this control is what tells the difference.

W2's *"auth path independent of answer size"* holds here: the set with 8.6× the
answers has the smallest auth path.

## Two defects in this spike's own method, both caught by its own controls

**1. A sample mean compared against a population mean.**
`C_queries_are_scale_matched` refused the first run — `certify` printed *"DID NOT
FIRE — run is VOID, not negative"* — because query lengths from a 120-key sample
were checked against S77's whole-corpus mean key length. **Fixed rather than
loosened**: widening the tolerance would have hidden a real mismatch on the next
corpus. The same contamination was then found in the membership comparison and
fixed there too, which is why the `mem B` column is recomputed on the same sample
(1,490 / 1,802 / 2,269 against S77's corpus 1,461 / 1,803 / 2,246 — the sample is
representative, which is now shown rather than hoped).

**2. A control that could not express a negative result (A21).**
The falsifier was first written as a control that fires when the claim holds. It
did not fire — a real, informative negative — and `certify` could only report the
run VOID. `Control` is documented as *"a positive control that MUST fire"*, so a
control whose failure **is** the finding makes every negative indistinguishable
from a broken instrument.

Restated: `C_auth_path_comparison_is_decisive` now checks that the ordering was
**decidable at all** — three sets, real verified proofs, and a max/min spread
above 5% so the ranking is not noise — and the verdict is published in
`completeness.json` under `verdict`, where no reader can mistake it for a passing
check. **This is not weakening a gate to pass it (§5):** the new control asserts
something the old one never checked, and the old one asserted something that was
never an instrument property.

## Controls — four, each naming the input that makes it fail

| control | fails if |
|---|---|
| **`C_completeness_proofs_verify`** | any proof fails `verify_completeness` or any query fails to cover. This is the proof kind whose verifier *is* the anti-omission check — W2 drives it False with `C_omit` / `C_add` / `C_tamper` |
| **`C_auth_path_comparison_is_decisive`** | fewer than three sets produce proofs, or max/min auth-path means are within 5%, making the ranking noise |
| **`C_answer_size_is_a_separate_axis`** | the answer-size ordering matches the auth-path ordering, in which case a single total would be safe and the separation here would be decoration |
| **`C_queries_are_scale_matched`** | mean query length is not within 0.05 of `FRACTION` × the sample's own mean key length. A fixed *byte* depth would sit near the root of a 1,155-byte atom key and near the leaf of a 12-byte triple key |

**All four fire.**

## What this does not settle

- **One query shape, one fraction.** Queries are prefixes at 75% of key length. The
  finding is that the ordering is query-dependent, so a different fraction gives a
  different ordering — that is the point, not a caveat about it. The fraction at
  which the orderings cross is unmeasured.
- **The answer set is counted in keys, not bytes.** A completeness proof must
  carry the answers, and for triples that is 100 keys × 12 B ≈ 1.2 KB, comparable
  to the auth path. Totals are not published here precisely because the two halves
  are separate axes.
- **W2's real step bytes track the modelled auth path** (1,588 / 1,896 / 1,467 vs
  1,479 / 1,785 / 1,401) with the same 4–7% framing residual as S77 and S79.
- One corpus, no timings — valid while `quiet.sh` refuses.
