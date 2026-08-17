# M1.1c — job N differs from job 1 inside one process. Process-per-job is required.

**The largest open M1 issue is now settled, in the negative. A fresh `metta_t`
per job is NOT sufficient; WorkManager's process reuse breaks determinism for a
characterisable class of programs.**

Same program, fresh `metta_t` each iteration, 40 iterations, one Android app
process, on device.

| program | stock `3f76dc4` | + our 3 patches |
|---|---|---|
| `var_alias` — `(pair $z $z)` matched by `(pair $x $y)` | **DIVERGES** 2 distinct, first at rep 5 | **DIVERGES** 2 distinct, first at rep 2 |
| `rule_inst` — two-rule instantiation | STABLE | STABLE |
| `chain` — three-rule chain, two queries | STABLE | STABLE |
| `arith_ctl` — `!(+ 1 2)` | STABLE | STABLE |
| `POSCTL_space` — `!(new-space)` | **DIVERGES 40/40 distinct** | **STABLE** |

## The positive control fires, and then our own patch silences it
Stock prints `GroundingSpace-0xb40000763c2352e8` — **40 distinct hashes in 40
runs**. So the harness can see in-process variation; the STABLE rows mean
something.

On the patched build the same control reads STABLE, because
`proposed/hyperon-nondeterminism/` patch 02 removes the address from `Display`.
That is **device-level verification of a patch previously only checked on the
host** — and it was nearly a methodological trap: the first run of this soak
used the patched tree, the control read STABLE, and the correct reading was not
"MeTTa is stable" but *"I disabled my own control."*

### How that happened, recorded
`elders/hyperon-experimental` was **not pristine**. All three patches were
applied in the working tree from the earlier fix-and-verify work and never
reverted, so:
- the first APK shipped **patched** hyperon while `RESULT.md` claimed `3f76dc4`;
- the M1.1 comparison against native `fuelrun` was patched-vs-unknown, not
  stock-vs-stock. The agreement stands; the provenance claim did not.
Both builds above were produced by `git stash` / `stash pop` around the build,
and pristine was verified by `git status --short | wc -l == 0`.

## What diverges, and what does not
`var_alias` is the case where **two distinct variables alias onto one**: the
binding map must pick a representative, and `$x` or `$y` wins depending on
iteration order. `VariableAtom` carries `id` in its derived `Hash`/`Eq`, and
`NEXT_VARIABLE_ID` is a process-global `AtomicUsize`, so **bucket assignment
depends on how many variables the process created earlier**.

This is Issue 3 of `proposed/hyperon-nondeterminism/`, filed as a report with
**no patch**. It now has a device reproducer.

Crucially, `rule_inst` and `chain` are STABLE despite both going through
`make_variables_unique`. **The hazard is narrower than "any program with
rules"** — it needs an ambiguous aliasing where the result depends on which
variable represents the class. That is a characterisable class, which matters
because it can be admitted or banned rather than only fixed.

## Consequence for M1.3 / WorkManager
`PORT_PLAN` M1.3 requires a fresh process per job on two derivations. This
measures the second one and it holds:

- **(1) atomspace pollution** — addressed by a fresh `metta_t`. Done here.
- **(2) process-global `NEXT_VARIABLE_ID`** — **not** addressed by a fresh
  `metta_t`, and now demonstrated: identical input, identical runner
  construction, different output by position in the process.

So `Worker` running in a reused app process is **not** equivalent to a forked
job, and the difference is observable in output, not merely in timing. Options
narrow to: run each job in a process that exits afterwards, ban the aliasing
class at admission, or fix `NEXT_VARIABLE_ID` upstream.

## Limits
- One device, 40 reps, five programs. Divergence was 2-valued here; nothing
  says it is bounded at 2.
- `rule_inst`/`chain` STABLE is evidence of narrowness, **not** proof of safety —
  40 reps of three programs does not characterise the class.
- Dead controls burned on the way: `(flip)` is a Python-ext atom absent from the
  Rust stdlib and echoed unevaluated; `(random-int &rng ...)` echoed because
  `&rng` was unbound; and the first `var_alias` matched an atom never added to
  the space and returned **empty**. All three read as STABLE. Logging one sample
  output per program is what exposed them.
