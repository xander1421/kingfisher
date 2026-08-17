# S28 — in-process concurrency DOES perturb MeTTa results, and canonicalisation repairs it

**ATTACKER-1, 2026-08-17.** `certify ok=true`, 5 controls, all fire.
Reproduce: `python3 spikes/S28_inprocess_concurrency/s28.py --threads 4 --invocations 5 --others 6`

## The target

`out/LEDGER.md` grades **"Co-tenancy does not perturb results — SEPARATE
PROCESSES only"** at **B**, on 8 concurrent *processes*. The row marks the
in-process case `Untested` and names the mechanism it expects to fail:

> `NEXT_VARIABLE_ID.fetch_add(…, Relaxed)` keeps ids unique but makes *which*
> thread gets which id scheduling-dependent. Each process starts its counter at
> 1, which is exactly why this passed.

This is the LEDGER method that has now gone three for three: grep for a
falsifier that was written down and marked **not run**, then run it.

It is load-bearing. M1.1 runs MeTTa **in-process** on the phone and WorkManager
reuses the app process, so the deployed configuration is the untested one.
M1.3b answered only the SEQUENTIAL case — many different jobs, one process, a
fresh `Metta` each — and **a sequential run cannot exhibit a scheduling-dependent
property.**

## Falsifiers, stated in `CHANNEL.md` before the code was written

| | condition | consequence |
|---|---|---|
| **F1** (the kill) | raw digests stable across repeated N-thread invocations | the Relaxed ordering never reaches output; the row's own mechanism is wrong; **B stands unqualified** |
| **F2** (the scope) | raw varies, `canon`/`alpha` stable | in-process concurrency is safe **under canonicalisation**; what dies is the unqualified B, not the co-tenancy claim |
| **F3** (no verdict) | the 1-thread arm also varies | instrument nondeterminism unrelated to threading; report irreproducibility, do **not** treat it as a kill |

**F2 fired.**

## The comparison, which is the whole design

Running threads and diffing inside one run cannot work. The process-global
counter makes every job's raw digest position-dependent whether or not
scheduling reaches the output — that is M1.3b's *result*, and its control. What
isolates threading is running the same command as a **fresh process** several
times and asking whether the run's digest **multiset** is stable across
invocations. A one-thread process has a deterministic counter history, so its
multiset must be identical every time.

Signatures are computed over the **sorted** digest column, so a scheduling
difference that merely reorders output does not register — only a difference in
the digests themselves does.

## Result

13 jobs per invocation (M1.3b's probe/corpus interleave, verbatim), 5
invocations per arm, one process per invocation.

| arm | job-runs / invocation | distinct raw multisets over 5 | distinct canon | distinct alpha | distinct fuel | wall median |
|---|---|---|---|---|---|---|
| **1 thread** | 13 | **1** | 1 | 1 | 1 | 5.11 s |
| **4 threads** | 52 | **5 of 5** | **1** | **1** | **1** | 5.19 s |

**Every one of the five 4-thread invocations produced a different raw digest
multiset**, on identical input, identical binary, identical configuration.

**Effect size, because a verdict is not a magnitude.** Digests recurring against
invocation 0, out of 52 per invocation:

- **raw: 30, 32, 36, 36** — so **16 to 22 of 52 (31–42%) change from run to run**
- **canon: 52, 52, 52, 52** — every one, every time
- **alpha: 52, 52, 52, 52**

Not a fourth decimal under a large intervention. A third of the outputs.

**`fuel_used` is invariant.** Distinct fuel signatures across the five 4-thread
invocations: **1** — every fuel count identical at every position. The
divergence is confined to variable *ids*; the computation itself did not
diverge. This is measured as its own column (`threadrun` v3) rather than
inferred from the fact that `canon` leaves the `fuel=` line alone, because
`fuel_used` is in M1.8's agreement key and an argument about an implementation
is not a measurement.

## Controls — 5, all fire

| control | what it observed | how it could have failed |
|---|---|---|
| `C0_instrument_reproduces_soakrun` | 13/13 rows identical to `soakrun` at 1 thread, keyed on position | any digest column differing on any row |
| `C1_same_build_both_arms` | one binary `00bcc9e0…`, argv differing only in the thread count, binary newer than its source | a rebuild mid-run, different job lists, or a binary predating `threadrun.rs` (A24) |
| `C2_intervention_is_not_a_no_op` | 52 = 13 × 4 job-runs | threads that never spawned, making the counts equal |
| `C3_counter_reaches_printed_output` | probe raw distinct **7/7** across its 7 positions, canon 1 | a constant raw digest — a run that cannot show drift proves nothing by not showing it |
| `C4_threads_are_not_serialised` | **3.94× speedup** vs the serialised expectation | speedup ≤ 1.2×, i.e. wall_4 ≈ 4 × wall_1 |
| `C5_fuel_decides_severity` | fuel signature distinct = 1 at 4 threads | a fuel count differing at any position between any two invocations |

**C4 is the one that separates evidence from conclusion.** If hyperon held a
global lock, the threads would run one at a time and *stability* would be
explained by serialisation rather than by safety — a serialised run cannot
exhibit the scheduling dependence under test. At 3.94× on 4 threads the run is
genuinely concurrent, so the stable `canon` is a real negative and not an
artefact of nothing having happened.

## Verdict

**The unqualified B dies. `canon`-scoped, it survives and is stronger than it
was**, because it now rests on a run that could have killed it.

- The row's **stated mechanism is confirmed**: `Relaxed` variable-id allocation
  does reach printed output under in-process concurrency.
- What is **retracted** is the scope: "co-tenancy does not perturb results" is
  true for separate processes and **false for raw digests inside one process**.
- What **survives**: perturbation is confined to variable ids. `canon`, `alpha`
  and `fuel_used` are invariant across genuinely concurrent runs.

## Scope, stated rather than left to the reader

- **This is a latent hazard, not a live break.** `fuelrun/src/main.rs` contains
  zero `thread::spawn`/`rayon`/`par_iter`, so today's workers are single-threaded
  per process and no published number is affected.
- **It becomes live the moment a host runs two jobs concurrently in one
  process.** M1.8's agreement key is `(status, fuel_used, sorted_hash)`, and
  `sorted_hash` is computed by `fuelrun` from raw output **pre-canon** — the
  caveat already on the M1.3b LEDGER row. Sorting does not help: the id is
  inside the atom text. Two *honest* workers would then disagree, which attacks
  the one asset that has survived every attack.
- **The remedy is already built and already measured**: canonicalise before
  hashing. `canon` is 52/52 stable here.
- **A negative under low load is weaker than a negative under high load**, since
  load is what drives interleaving. The positive result here does not depend on
  that; the `canon`/`fuel` negatives do, and are reported as measured at this
  operating point (4 threads, 14 cores, 5 invocations) rather than as universals.
- **Alpha's known limit is unchanged**: M1.3b established `canon_alpha` is
  lossless only on ground results, so the aliasing job class stays out of scope
  here as it was there.

## Defect found in this spike's own instrument, and it is the reason C0 exists

`threadrun` **v1 sorted a numeric field as a string.** Rows were built as text
beginning `thread\tpos\t…` and sorted as `Vec<String>`, so a 13-job list printed
positions 0,1,10,11,12,2,… **C0 went RED on the 13-job run and GREEN on the
6-job smoke test taken minutes earlier**, because single-digit positions sort
correctly and the defect is invisible below the first two-digit value.

No digest was ever wrong — only the print order. But the control could not tell
me that, so v2 sorts `(thread, pos, text)` tuples on the numbers and C0 is
rekeyed on position, comparing every digest of every job exactly while being
immune to a print-order change.

**CLASS: a numeric field sorted as a string, where the defect cannot appear
below the first two-digit value — so a small smoke test certifies it green.**
Posted to `livechat.log`.
