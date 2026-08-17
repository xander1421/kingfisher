# S81 — fuel under BRANCHING nondeterminism: the falsifier fired

**ATTACKER-1, 2026-08-17.** Target chosen by searching `out/LEDGER.md` for a
falsifier that was **written down and marked not yet run** — CLAUDE.md's stated
location for every error that has survived in this project.

## The claim under attack, and its own note

`out/LEDGER.md`:

> ~~Fuel is deterministic even when output is not~~ | **superseded** | S57.
> `test_gnd_conv.metta` calls `(flip)`: three different result hashes across
> three platforms, `fuel_used = 1012` on all three. **The meter is separable
> from the result.** Held 30/30 runs, 18 distinct outputs. **But nothing in that
> program branches on the random value**, so control flow is fixed and fuel
> *cannot* vary — this is the trivial case. `(if (flip) (long) 0)` is untested
> and the billing design needs it.

## Falsifier, stated before the run

> *If the meter is separable from the result **in general**, a program whose
> control flow depends on `(flip)` shows ONE fuel value across runs while the
> hash varies. If instead fuel takes TWO values tracking the branch, the claim
> is confined to non-branching programs and `fuel_used` cannot serve as a
> replication oracle or a billing quantity for any job whose control flow
> touches a nondeterministic op.*

`sh spikes/S81_fuel_branch/probe.sh 20` — output committed as `RUN.txt`.

## Reproduce first

S57's observation reproduces **exactly** on this binary. 8 runs of the committed
`python__sandbox__test_gnd_conv.metta`: `fuel_used = 1012` every time, **8
distinct result hashes**. Two of them — `d59cf828736f8bad` and
`c73d59ea3a4bee38` — are byte-identical to the values in S57's committed
`res_arm64_macos.tsv` and `repatched.tsv`. **Nothing in S57's evidence is
withdrawn.** What is attacked is the generalisation drawn from it, which the
LEDGER row had itself flagged as untested.

## Controls, all of which fire

| | control | result |
|---|---|---|
| **C0** | is the mechanism under test even active? | `!(flip)` alone → **1 distinct hash in 5**, returns the atom `(flip)` unreduced. With `!(import! &self random)` first → **2 distinct hashes in 20**. ACTIVE |
| **C1** | can the instrument express the verdict? (A15) | forced `True` branch **1258** fuel, forced `False` **264**. Separation **994**. Not blind |
| **C2** | is run-to-run variation the harness? | fixed program, 20 runs → **1258 ×20**, constant |
| **C3** | would this job ever be admitted? | `bansurface.py` → `REJECT: flip` |

**C0 is the one worth copying.** `(flip)` is **inert without `import! &self
random`** — the RNG ops are registered by the import. A test that writes
`!(flip)` and no import measures *the absence of flip* and concludes it is
deterministic. That is a trap for whoever writes the next determinism test, not
a hole in the ban surface: `bansurface.py` rejects `flip` textually whether or
not the import is present, which is the conservative direction.

## Result — the falsifier fired

```
TREATMENT  !(if (flip) LONG 0), 20 runs
  fuel   335(x13)  1329(x7)
  hash   29e06aec(x12)  91bd5b2c(x8)
```

**Fuel is not constant.** Two values, tracking the branch.

**VERDICT: "the meter is separable from the result" is FALSE in general.** It
holds only where control flow does not depend on the nondeterministic value —
i.e. only the case S57 happened to test.

## Attribution, checked rather than asserted

Fuel varying is not the same fact as fuel varying *because of the branch*
(CLAUDE.md: correct numbers, wrong attribution). The identity that distinguishes
them:

```
treatment separation   1329 − 335  = 994
C1 forced separation   1258 − 264  = 994      exact match
```

The **separation is exact**, which is what identifies the branch as the cause.

**The absolute values are not exact and I am not going to round them into
place.** `(flip)` measured on its own costs 74 fuel (`import+flip` 204 − bare
`import` 130), so the naive sum predicts 1332 / 338 against the observed
1329 / 335 — **off by 3, in both arms, in the same direction.** A constant
offset consistent across both branches is a difference in reduction context
between `!(flip)` at top level and `(flip)` in an `if` condition, not a defect
in the measurement; but it is unexplained, and stating it as "exactly 71 fuel"
— which is what I first wrote from the standalone `!(flip)` figure, before the
probe measured the import-delta at 74 — would have been a fitted number.

## What dies, what survives

**Dies:** `fuel_used` as a cheap replication oracle or billing quantity for any
program whose control flow touches a nondeterministic op. Two honest workers
disagree on **both** the hash and the meter, so the meter is not a fallback
signal when the hash diverges, and a job cannot be "paid in points" on an agreed
fuel count that was never going to agree.

**Survives, and this is the larger part:** the wedge is untouched. It rests on
*admissible* jobs, and `bansurface.py` REJECTS this program. What this removes
is a defence-in-depth property that was being quietly relied on one layer below
the ban — and the ban surface's own LEDGER row already says it is a
*"conservative over-approximation, not an iff"*. Anything that slips past the
ban now has no second signal behind it.

**Not claimed:** nothing about cross-platform behaviour. Every run here is one
binary on one host, deliberately — a within-binary comparison cannot be
manufactured by a stale artifact, only rescaled. Binary sha256 is printed by the
probe and recorded in `RUN.txt`, because a Cargo feature was measured moving
`fuel_used` 107 → 580 on identical source (`spikes/V1_feature_fuel`).

## Files

- `probe.sh` — controls and treatment; **refuses** rather than reports if C0 or
  C1 fails, since a treatment run under a blind instrument is worse than none.
- `RUN.txt` — the committed output, including the binary's sha256.

No pinned seed: the entropy under test is OS-seeded and *unpinnable by
construction* — that is the property being measured. The pinned quantity is the
binary, by digest.
