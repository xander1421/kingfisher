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

## Standing gap

**28 of 43 A-grade claims name no reproducer**, and this section originally
stopped there — "not guessed at here; inventing one would be worse than leaving
it blank". That was the right instinct and the wrong stopping point: it treated
"I must not invent a reproducer" as if it meant "I cannot find one". The section
below surveys what actually exists, without inventing anything.

## The 28 unannotated claims: not unreproducible, unnamed

**Second falsifier, stated before running:** *the 28 are unannotated because no
runnable reproducer exists for them.* **Refuted.**

| kind | n | what it means |
|---|---|---|
| `script` | 13 | a `.py`/`.sh` already sits in the claim's own spike |
| `binary+source` | 6 | a compiled binary plus its `.c`/`.rs` — reproducible, needs a named command |
| `NO-SPIKE-REF` | 7 | the LEDGER row names no spike, so nothing can be located from it |
| `NONE` | 2 | genuinely bare (S58, S63) |

**19 of 28 have runnable material sitting in their own spike directory.** They
were never unreproducible; nobody wrote down the command.

The first version of this matcher reported **11 NONE**, and that number was an
artifact of the regex: `M1.7d` does not glob to `M1_7_transport`, so claims with
a perfectly good `run_lan.py` beside them scored as having nothing. A prefix
fallback moved 9 of them. **Absence of a match is not absence of a reproducer**,
and reporting the first number would have justified exactly the wrong
conclusion — that the claims were unverifiable rather than undocumented.

Six of the binaries are **Android-only** (`realkg`, `threadcost`, `mc`, `mcx0`,
`probe`): `Exec format error` on the host. They reproduce over adb, not locally,
which is why a host-only sweep will never reach them.

### One converted, as the pattern

`S34_packed_popcount/s34_check.py` turns "bit-exact vs scalar and SDOT, **both
machines**" into a command. A host-only run proves half the claim, so it runs
`kernels_host` here and `kernels` on the phone under the §10 gate:

```
host:    K0 scalar / K1 SDOT / K2 popcount   f4e64fb7d70b9b0c
device:  K0 scalar / K1 SDOT / K2 popcount   f4e64fb7d70b9b0c
kernel hashes: 1 distinct across 2 machines
control (different buffer): b3bfb70e74b94aa7
```

The control is the second hash. Identical hashes prove bit-exactness only if the
hash *can* differ; if every value in the output were equal, "identical" would be
a property of the instrument. `CONTROL DEAD` fails the run instead.

### Two I deliberately did not annotate

- **NNAPI** (`S31`): verified on-device — `NNAPI devices: 1`, the CPU reference
  only, which supports "no accelerator on SM8750". Not annotated, because the
  only artifact is an Android **binary**, and `reprocheck` now refuses binary
  annotations. Annotating it would break the rule I added two hours earlier.
- **Locality routing** (`S61`/`M1.8c`): `fleetsim.py` runs and passes 4/4 of its
  own controls, but the claim says *measured on a real fleet* and fleetsim is
  the **simulation the claim contrasts itself against**. No `M1_8c` directory
  exists. Annotating the nearest runnable file would have named the wrong
  experiment — which is how a reproducer starts certifying something it never
  measured.

`repro:` count is now 17 runnable, 0 gone, 0 inert, **27 unannotated**.

## The general form

Three cycles have now found the same shape from three directions:

- M1.9 — an edit that applied cleanly to a `#[cfg]`-excluded line and never compiled.
- M1.10 — probes that ran cleanly and tested nothing.
- M1.11 — reproducers that "existed" and could not be run.

Each passed every check in front of it. The defence is the same every time:
**require the check to demonstrate it can fail**, and treat a check that has
never been shown to fail as having an unknown floor.
