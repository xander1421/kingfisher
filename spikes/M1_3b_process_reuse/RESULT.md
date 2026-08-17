# M1.3b — process reuse is safe for the measured job class. The largest open M1 issue closes, with a stated boundary.

`PORT_PLAN` M1.3 requires a **fresh process per job**, on two derivations.
WorkManager reuses the app process, so the requirement and the platform are in
direct conflict — logged as the largest open issue in M1. This resolves it.

## The test the earlier one was not
M1.1c ran 40 repeats of **one** program. The real case is many **different**
jobs sharing a process, because every job advances the process-global
`NEXT_VARIABLE_ID` for the ones after it. `soakrun.rs` runs a list of programs
in one process with a **fresh `Metta` per job** — so derivation (1), atomspace
pollution, is handled by construction and only derivation (2) is under test.

## Result: 31 probe runs interleaved with 30 other jobs, one process

| probe | distinct RAW | distinct CANON | distinct ALPHA |
|---|---|---|---|
| `(implies (Frog $x) (Green $x))` matched non-aliasing | **31** | **1** | 1 |
| `(pair $z $z)` matched by `(pair $x $y)` — aliasing | 2 | **2** | **1** |

**Every raw result differs.** Position in the process changes the bytes, 31
times out of 31. So derivation (2) is real, at scale, in the actual usage
pattern — not just in a 40-repeat microbenchmark.

**`canon` eliminates it entirely for the non-aliasing case**: 31 -> 1.

## The boundary, which is the useful part
The aliasing probe needs `canon_alpha` (2 -> 1), and **`canon_alpha` is only
lossless on ground results** (`is_ground`, enforced by `canon_alpha_strict`).
An aliasing result carries free variables by definition, so it is never ground,
so alpha is never safely applicable to it.

That gives three classes, cleanly separated:

| result shape | position-dependent? | fixed by | process reuse |
|---|---|---|---|
| **ground** (no variables) | no — nothing to renumber | n/a | **SAFE** |
| variable-bearing, non-aliasing | yes, 31/31 | `canon` | **SAFE** |
| **aliasing** | yes | only `canon_alpha`, which is lossy here | **NOT SAFE** |

**The entire 67-program corpus returns ground results** — measured in the M1
chain run: *`alpha: 0 envelope(s) non-ground`*. So for every job this project
has actually executed, process reuse is safe and WorkManager is usable.

## What this changes
- **M1.3's process-per-job requirement is satisfiable without forking**, for
  ground-result jobs, given a fresh `Metta` per job plus `canon` at the
  comparison boundary. `q3.py` already does both.
- The requirement is **not** dropped: it still holds for the aliasing class, and
  nothing admits or rejects that class today. M1.1c's syntactic gate for it was
  **refuted at 51% rejection**, so this is an open admission question, not a
  solved one.
- `fuelrun`'s own `raw_hash` / `sorted_hash` are computed over **un-canonicalised**
  output, so they remain position-dependent. Any comparison must use the
  canonicalised text, which is why `q3.py` keys on `results_text` when it has it
  and flags the envelope when it does not.

## Limits
- Two probe shapes, 31 runs each, one process, host only. Not run on device.
- A fresh `Metta` per job is assumed throughout; nothing here says a **reused
  runner** is safe, and S60/A8 says it is not.
- "The corpus is entirely ground" is a fact about this corpus. A buyer's query
  stream is the unmeasured input everywhere else in this project and it is
  unmeasured here too.
