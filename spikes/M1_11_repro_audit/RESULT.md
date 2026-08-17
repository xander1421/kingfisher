# The reproducers, actually run

`repro: spikes/M1_11_repro_audit/audit.py`

**Falsifier, stated before running:** *all A-grade claims with a named
reproducer still run and still produce their claimed result.*

**Refuted.** Three of thirteen named something that cannot re-derive anything,
and a fourth could not run at all.

`reprocheck` answered "does this claim NAME a reproducer, and does that path
exist". **Existence is not runnability.** Nothing had ever executed them.

## What the run found

| outcome | n | meaning |
|---|---|---|
| `PASS` | 9 | ran, exited 0 |
| `NOT-RUNNABLE` | 3 | the annotation names a document or a prebuilt binary |
| `PRECONDITION` | 1 | driver intact, the environment moved |
| `DECLINED` | 1 | a safety gate refused — the gate working |

### The three that could not re-derive anything

- `spikes/M1_8_quorum3/CORPUS_COMPOSITION.md` — a **document**. Mine, written
  one cycle earlier, in the same cycle I was auditing reproducibility. The real
  reproducer was `classify.py`, sitting beside it.
- `spikes/REGRESSION_SWEEP.md` — a document describing a sweep across 7 drivers.
  A sweep whose only reproducer is its own writeup cannot catch the next
  regression, which is precisely what it exists to describe.
- `spikes/S15_android_device/fuelrun/target/release/soakrun` — a **prebuilt
  binary**. An artifact, not a reproducer: rebuild it from a changed tree and
  nothing says so.

All three are now repointed at commands that run: `classify.py`,
`spikes/sweep.py` (written this cycle), `soak_check.py` (written this cycle).
`reprocheck` now refuses a `.md` or a non-script annotation, so this cannot
recur silently — it had been counting all three as "has a repro".

### Two outcomes that are not failures, and must not be scored as failures

`q3.py --alpha` exited 2. Not broken — the **thermal gate refused**, because the
phone was at 46.7 °C from the previous cycle's 120 adb probe runs. The rail did
its job. An audit that scores a working safety gate as a stale claim is the
mirror image of an inert check: both misreport, one optimistically and one
pessimistically.

`run_lan.py` could not run: the phone had joined a **VPN** (`tun1`, src
`10.184.0.5`) and left the host subnet `192.168.1.25`. The driver is intact and
the environment moved. Scoring that `FAIL` blames the code; folding it into
`DECLINED` hides that a headline path is currently unreproducible. It is its own
category and it is loud.

**Resolved during the cycle.** The phone came back on `192.168.1.20`, same
subnet, and the claim reproduces:

```
over WiFi: 64/64 envelopes in 19.9s, 64 OK
control A, no token:   HTTP 401   (expect 401)
control B, wrong pin:  HTTP 000   (expect refused)
control C, cleartext:  HTTP 000   (expect refused)
```

## The process-reuse claim, rebuilt around its own control

The `soakrun` binary annotation is replaced by `soak_check.py`, which
re-derives the number and asserts the thing that makes it mean anything:

```
probe evaluated at 31 positions in ONE process
  raw   distinct  31   <- control: process history MUST leak here
  canon distinct   1   <- the claim
  alpha distinct   1
```

`canon == 1` is worthless on its own — a program returning `()` gives that
however broken reuse is. The **raw** column is the proof the hazard is live:
hyperon's process-global variable counter reaches printed output, so a reused
process is exactly where drift appears. `soak_check.py` fails if raw comes back
constant, reporting `CONTROL DEAD` rather than a passing claim.

## Standing gap, not closed

**28 of 43 A-grade claims still name no reproducer.** That number has not moved
and is not guessed at here; annotating a claim requires knowing which command
produced it, and inventing one would be worse than leaving it blank.

## The general form

Three cycles have now found the same shape from three directions:

- M1.9 — an edit that applied cleanly to a `#[cfg]`-excluded line and never compiled.
- M1.10 — probes that ran cleanly and tested nothing.
- M1.11 — reproducers that "existed" and could not be run.

Each passed every check in front of it. The defence is the same every time:
**require the check to demonstrate it can fail**, and treat a check that has
never been shown to fail as having an unknown floor.
