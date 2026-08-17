# S83 — the highest-risk artefact in the workspace: 8 of 16 guards can be removed and all 18 cases still print `ok`

**ATTACKER-1, 2026-08-17.** Target chosen by the brief's own priority order —
**instruments before conclusions, self-authored data first.** `verifier2.py` is
an instrument whose entire evidence is self-authored, and `out/LEDGER.md` grades
it **E, "highest-risk artefact here"**:

> `verifier2.py` untested by anyone but its author | 17 self-authored cases —
> *exactly v1's evidentiary profile*, and **v1's 13/13 contained a test that
> never called the verifier**.

## Falsifiers, stated before the run

> **A.** *If v2 does not repeat v1's defect, every case reaches
> `compare()` or `check_envelope()`. Counted, not read.*
>
> **B.** *If the 18 cases are coverage rather than decoration, removing any one
> real guard from the verifier turns the suite red. A mutant that survives is a
> defect that could be reintroduced tomorrow with every case still printing
> `ok`.*

`python3 spikes/S83_verifier2_attack/attack.py` — output in `RUN.txt`. Mutants
are applied to a **copy** via `edits.anchored_replace`, so a drifted anchor
raises instead of reporting a mutant killed that was never applied.

## A · v1's defect is present in v2, twice

```
CONTROL  unmutated: 18 cases, 0 fail, 2 dead
A · DEAD TESTS: 2 case(s) never reached the verifier
    DEADTEST commit-many / reveal-one is refused
    DEADTEST ('did:key:A',X+16n) vs ('did:key:AX',16n)
```

**Neither is vacuous, and saying so matters.** `grind()` returns the literal
`("UNREACHED",)` and still passes — because `CommitRegistry.commit` *raises*
`Reject` first, which `run` catches. `collide()` compares two
`Envelope.commitment()` values directly. Both test a **helper**, correctly.
Neither goes through the verifier.

So this is v1's class in a subtler form: not *"a test that asserts nothing"* but
**"a test whose subject is a helper the verifier is never checked to still be
using."**

## B · Mutation score 8/16

```
MUTATION SCORE: 8/16 killed, 8 SURVIVED
```

| | guard removed | |
|---|---|---|
| M1 | self-quorum (one device agreeing with itself) | killed |
| M2 | cross-job replay | killed |
| M3 | contracts may differ and still be compared | killed |
| M4 | the sealed value need not BE the verdict value — **v1's central defect** | killed |
| M5 | the S31 cutoff bound | killed ×3 |
| M6 | `(timing …)` may travel in the payload | killed |
| M7 | envelope contract need not match the job's pinned contract | killed |
| M10 | `SORTED_SET` degrades to `SORTED_BAG` | killed |
| **M8** | **an unregistered commitment is accepted** | **SURVIVED** |
| **M9** | **the commitment need not recompute** | **SURVIVED** |
| **M11** | **inexact units may vote** | **SURVIVED** |
| **M12** | **fuel disagreement no longer makes a DISAGREE** | **SURVIVED** |
| **M13** | **the nonce length floor (16 bytes → 0)** | **SURVIVED** |
| **M14** | **`fuel_used` range check** | **SURVIVED** |
| **M15** | **cutoff rounding: round-half-up → round-down** | **SURVIVED** |
| **M16** | **`output_bits` enumeration (8/16/32)** | **SURVIVED** |

## Why each survivor survives — mechanism, not speculation

**M8 + M9 are the same hole as the two dead tests.** Every registry the verifier
ever sees is built by `_reg(a, b)`, which registers *both* envelopes correctly
and closes — 13 call sites, no exceptions. **The verifier is never presented
with a missing or a wrong commitment.** The only two cases about the registry
are `grind` and `collide`, and those are the two that bypass the verifier. The
dead test and the surviving mutant are one hole seen from two directions, which
is why finding either one predicts the other.

That matters more than its share of the score: commit-before-close and
commitment-recomputes are the **anti-grinding and anti-adaptive-reveal** core.
The registry works; nothing checks that the verifier still consults it.

**M12** — `mk()` defaults `fuel=100082` and **no case anywhere overrides it**,
so no two envelopes ever differ in fuel. Fuel is part of the agreement key, and
the branch that acts on it has no test.

**M16** — there *is* a `bits16` case, and it does not test this. It sets
`output_bits=16`, which is **valid**, and is rejected by the cutoff bound (M5),
not by the enumeration. Nothing ever presents an invalid value such as 7. A case
that looks like coverage for a guard, passing for a different guard's reason.

**M15** — `cutoff_for`'s docstring exists to state round-half-up
(`(2*nnz*den*2 + num) // (2*num)`). Changing it to round-down is invisible to
all 18 cases. The rule the function documents about itself is untested.

**M11, M13, M14** — no case constructs an inexact unit, a short nonce, or an
out-of-range fuel value.

## Verdict

**Grade E is correct and now quantified.** The suite is real coverage for the
v1 exploit list — every one of M1–M7 and M10 dies, which is exactly what the
file's own section headings claim (*"every v1 exploit is now handled"*). It is
**not** coverage for the verifier. It tests the fixes, not the function.

**This is the same shape as `S82`, one layer up.** There, N identical binaries
agreeing was one measurement, not N. Here, 18 cases written by the author of the
fixes cover the fixes and nothing else. **A suite built from a bug list inherits
the bug list's blind spots**, and the blind spot here is the whole commitment
path.

## The eight missing cases, so this is actionable and not just a score

1. envelope whose commitment was never registered → `REJECT`
2. envelope whose registered commitment does not recompute → `REJECT`
3. `unit="CPU_FLOAT"` (or any non-`EXACT_UNITS` value) → `REJECT`
4. honest pair differing only in `fuel_used` → `DISAGREE`
5. `nonce` of 15 bytes → `REJECT`
6. `fuel_used = 2**64` → `REJECT`
7. `output_bits = 7` → `REJECT`
8. a `nnz`/scale pair whose cutoff differs between round-half-up and round-down,
   asserting the documented value

**Not applied by me.** `S49` is another lane's spike and its `RESULT.md` and
LEDGER grade rest on the current suite; adding cases to it is the owner's edit
so the grade moves with an author who can stand behind it. `attack.py` is
re-runnable and names each hole, so the fix can be checked rather than believed.

## Controls

- **CONTROL run**: unmutated and instrumented → 18 cases, **0 fail**. Without
  it, "the mutant was killed" cannot be told from "the copy is broken".
- **Mutants are applied to copies**; the original is never written.
- **`anchored_replace`, never `str.replace`** — a drifted anchor raises and is
  reported as `ANCHOR MISSING — not tested`, rather than silently scoring an
  unapplied mutant as killed.
- **The instrumentation is counted, not inspected**: `compare` and
  `check_envelope` are wrapped and the per-case delta is taken, so "reaches the
  verifier" is measured rather than read off the source.
