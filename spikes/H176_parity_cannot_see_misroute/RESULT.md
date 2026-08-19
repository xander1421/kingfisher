# H176 — H163's parity control accepts either pin for every task, so 50% of the workload can be misrouted and it still reports 250/250

**ATTACK on H163's *"250 tasks dispatched, 100% bit parity (250/250)"*.**
`certify ok=true`, 3 controls all fired, **all three preregistered falsifiers ran
and none fired.**

## First, an honest negative that kills the hypothesis I was handed

The session on socket 3266 asked whether the multi-device rows read one digest
and compare it to itself. **They do not.** `H163/run.py::run_single` shells a
real binary on each target — `adb shell .../tv` on `R5CY93675MK` and
`emulator-5554`, `xcrun simctl spawn` on the iOS sim, `BIN_HOST` and `BIN_X86`
locally — and parses `Consensus Digest:\s+([0-9a-fA-F]{64})` out of **that
process's own stdout**. Five independent recomputations. That part of H163
stands and is not under attack.

## The finding

H163 dispatches `tasks[i] = "F001" if i%2==0 else "F002_specv1"`, but
`run_single` returns `(rc, dig)` and **the requested fixture is never carried
into `results`**. The verdict (`run.py:160-164`) therefore **disjoins** the pins:

```python
if rc != 0 or (dig != PIN_F001 and dig != PIN_F002):
```

Either pin is accepted for every task.

| arm | tasks wrong | H163's verdict |
|---|---:|---|
| **A** honest — every worker runs its own fixture | 0 | parity 250/250 |
| **B** MUTANT — worker ignores its argument, always computes F001 | **125** | **parity 250/250** |
| **C** positive control — one corrupt digest | 1 | DIVERGENCE |
| **D** positive control — one `rc != 0` | 1 | DIVERGENCE |

**Arm B misroutes 50% of the workload and the check reports 100% parity.**
Arms C and D are what make that mean something: the same predicate, driven by the
same harness, *does* fire on a corrupt digest and on a bad return code. A green
arm B against an inert driver would be worth nothing — that is H124's lesson
(identical broken bytes compare equal) and it is why F3 exists.

`C2_exact_bit_parity` claims *"100% consensus digest match across all 250
distributed swarm tasks"* with `can_fail_because="digest mismatch"`. It **can**
fail on a corrupt digest and **cannot** fail on a misrouted one — which is the
fault a heterogeneous swarm actually has. A15 / family A: the control cannot
contain the effect its name claims.

## Class sweep (§12.2) — this is a regression, not a missing idea

The correct form already exists twice in this repo:

| site | form | sound? |
|---|---|---|
| `H163/run.py:162` | `rc != 0 or (dig != PIN_F001 and dig != PIN_F002)` | **DISJOINS — blind** |
| `H161/run.py:172` | `dig1 != PIN_F001 or dig2 != PIN_F002` | BINDS |
| `H155/run.py:187` | `d1 == PIN_F001 and d2 == PIN_F002` | BINDS |

**And the cause is structural, not carelessness.** H161 and H155 each run exactly
two jobs and can bind *positionally*. H163 drains 250 futures with
`concurrent.futures.as_completed`, **which destroys dispatch order** — so the
disjunction is what you write once the fixture is no longer in hand. Run under
the bound predicate H161 already uses, arm B reports **DIVERGENCE** and arm A
still reports parity.

**The fix is to carry the fixture back, not to re-order the futures:**
`run_single` returns `(rc, dig, fixture_name)`, and the verdict compares against
`{"F001": PIN_F001, "F002_specv1": PIN_F002}[fixture_name]`. Two lines. Not
applied here — it is another lane's spike and §9 says the honest move is to
record the defect, not to edit someone's result under my own claim.

## Scope, stated so it cannot be read wider

**This attacks the CONTROL, not the devices.** Nothing here shows any target
misbehaved, and nothing here shows H163's 250 digests were wrong — they match the
pins. The claim is that the check *would not have noticed* if they had been
misrouted. H163's speedup and its 5-target dispatch are untouched.

## The device arm was GATED, not dropped

`sh spikes/quiet.sh --device` exits **1**: `REFUSED - multiple(R5CY93675MK
emulator-5554)`. The §10 gate refuses while two targets are attached, so no
device job ran. That is the gate working as specified, and the finding does not
need one — the defect is decidable from the predicate. Recorded rather than
silently skipped.

*(Measured correctly on the second attempt: my first reading piped the gate into
`head` and read `$?` from `head`, which reported 0 while the gate exits 1. An
exit code taken through a pipe is not the exit code — my own instrument error,
inside a row about controls that cannot fail.)*

## Falsifiers — preregistered in CHANNEL.md, all three ran

| | fires when | fired? | consequence |
|---|---|---|---|
| **F1** *(refutes ME)* | H163 no longer contains the disjoining predicate | **NO** — pinned byte-for-byte by `SOURCE_ASSERT` | finding stands |
| **F2** *(refutes ME)* | H163's predicate reports divergence on arm B | **NO** — reports parity on 125 wrong tasks | finding stands |
| **F3** *(kills my row)* | arm C or D fails to diverge, i.e. my driver is inert | **NO** — both fire | arm B's green is real |

## Controls — each can fail

- **C1 pins distinct** — if `PIN_F001 == PIN_F002`, "either pin accepted" is not a
  weakening and there is no finding. **PASSED.**
- **C2 honest arm reproduces 250/250** — so the mutant arm changes one variable
  and not my harness. **PASSED.**
- **C3 pins intact.** **PASSED.**

Check: `python3 spikes/H176_parity_cannot_see_misroute/attack.py`
