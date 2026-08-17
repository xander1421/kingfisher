# M1.3b — the WorkManager half, on real hardware. Two spec defects found.

**The worker runs MeTTa in-process under WorkManager, refuses when it should,
and S6's specified constraint set does not compile.**

## Observed
```
KFWORKER: JOB OK in 16.61 ms, results=[3 | (B C)]
KFWORKER: PREFLIGHT REFUSED: battery:100%<101% -> retry with backoff
```
`kf-now` ran end to end: WorkManager dispatched -> in-worker preflight passed ->
`Metta.run()` via JNI -> `Result.success()`. `kf-refuse`, given an unsatisfiable
101% floor, produced `Result.retry()`. **The gate is proven able to refuse** —
a gate that only ever passes proves nothing (A15).

## Defect 1 — SCHEDULER_SPEC 2 does not build

The spec's constraint block specifies rule 4 and rule 5 together:

```kotlin
.setRequiresDeviceIdle(true)                                   // rule 5
.setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, MINUTES)     // rule 4
```

Runtime result:

```
java.lang.IllegalArgumentException: Cannot set backoff criteria on an idle mode job
    at androidx.work.OneTimeWorkRequest$Builder.buildInternal(OneTimeWorkRequest.kt:58)
```

**Rules 4 and 5 are mutually exclusive.** JobScheduler treats idle as a
deferral mechanism and refuses a second one on top. The spec maps both BOINC
rules onto WorkManager independently and never checks that the mapping composes
— which only an actual `build()` reveals.

Forced choice, and it is a design decision not a detail:
- **keep idle**, lose automatic exponential backoff (hand-roll retry), or
- **keep backoff**, and relax idle to "screen off" — which S6 4 already floats
  as a user preference, and which BOINC accepted as `suspendWhenScreenOn`.

## Defect 2 — confirmed empirically: `setRequiresDeviceIdle` starves

`kf-spec`, carrying all five constraints, was enqueued and **never ran** while
`kf-now` (same worker, no idle constraint) completed in milliseconds. S6 4
warned this could happen; it does, on a charging bench phone. Any demo that
depends on the full constraint set will appear to do nothing.

## The unresolved conflict — process-per-job

`PORT_PLAN` M1.3 states the requirement in bold, with two independent
derivations: **fork a fresh process per job**, because (1) S60/A8, a reused
`Metta` pollutes the atomspace and silently aborts, and (2) `NEXT_VARIABLE_ID`
is process-global so job N occupies a different id space than job 1.

**WorkManager reuses the app process.** A `Worker` is a class instance inside a
long-lived process, and the platform gives no per-job fork. So the requirement
and the platform model are in direct conflict, and this implementation
satisfies the platform, not the requirement.

Options, none implemented:
- a separate `:worker` process (`android:process=":worker"`) plus one job per
  process start — coarse, and WorkManager still reuses it across jobs;
- construct and free a fresh `metta_t` per job **and** prove that is equivalent
  to a fresh process, which requires disproving derivation (2) — the variable-id
  space is global to the process, not the runner;
- accept in-process reuse and drop the determinism guarantee for a device agent,
  which contradicts the project's one surviving claim.

**This is the single largest open issue in M1**, and it was invisible until the
worker existed.

## `onStopped()` — stubbed, honestly
The worker checks `isStopped()` after evaluation and returns `Result.retry()`,
i.e. it re-runs the whole job. Checkpointing at a fuel boundary — what S6 calls
the reason `fuel_limit` exists — needs the state commitment S68 found absent.
