# H202 — two of the loop's three exit signals had never been driven through the hook by its own suite

ok-1, 2026-08-19. **ATTACK cycle** (§2, every 4th) on my own cycle-27 work. Row `H202`.

## What was attacked, and it was mine

Cycle 27 shipped `test_loop_gate.sh` v5's H23 block: *the hook's refusal message must promise
the vocabulary the hook accepts*. The attack asked the question that check does not:
**does either side of that promise actually work?**

First attempt at breaking it — rename `LOOP-HALT` to `LOOP-STOP` **everywhere inside the
hook**. The H23 check reads both sets from one file, so a coordinated rename moves both and it
reports `equal`, while `MISSION_LOOP` §7 (2 mentions), `run_loop.sh` (3) and this same suite
(19) still say `LOOP-HALT`. **That is a real limit of the check and it is not the finding** —
the suite catches that mutation elsewhere, because check 2 drives a real `LOOP-HALT` signal
through the hook and gets `block` instead of `exit`.

**Which raised the actual question: how many of the three signals are driven like that?**

## The finding

```
$ grep -oE 'LOOP-[A-Z]+' <(grep 'echo LOOP-.* > \.loop_signal' test_loop_gate.sh) | sort | uniq -c
   7 LOOP-HALT
   1 LOOP-IDLE
```

- **`LOOP-HALT`** — driven 7 times. Covered.
- **`LOOP-IDLE`** — one occurrence, at line 226, and it is `echo LOOP-IDLE > .loop_signal`, the
  **bare**-signal check, whose expected answer is `block`. A hook that had stopped accepting
  `LOOP-IDLE` altogether returns the same `block` there, and the check passes. **Not covered —
  and the shape of the non-coverage is a check that cannot express the verdict** (family A).
- **`LOOP-DONE`** — the signal that ends the mission. It appears **twice** in the file, both
  inside v5's own mutation string. **Never driven. Never covered. Not once, for the whole life
  of the suite.**

Verified against the shipped hook by renaming each marker in a copy and driving a real signal:
all three return `block` when their marker is renamed. So the hook is fine; **the suite was
blind**, and a hook that refused `LOOP-DONE` or `LOOP-IDLE` would have passed every check.

> **Class: a suite that exercises one member of a vocabulary and reads as covering the
> vocabulary.**

This file's own history is the precedent my brief already names: the 15-check version passed
while the hook was broken, because every check set `CALLSIGN` — happy path only.

## The fix is at the class, not the site

`test_loop_gate.sh` **v6**, 99 → 107 checks.

1. **2b** drives `LOOP-DONE` and `LOOP-IDLE` on the per-lane path exactly as `LOOP-HALT` is
   driven — ends the turn, leaves the right exit marker, consumes the signal.
2. **A guard**: every marker in the hook's accept branch must have been driven by this suite.
   Adding a fourth marker to the hook without a check now turns the suite red.

**The guard records what was driven AT RUNTIME, and that is the second defect this row
removed.** Its first draft grepped this file for `echo <MARKER> > .loop_signal.<lane>` and
reported **all three markers uncovered** — including the seven `LOOP-HALT` drives sitting
above it. The drives are parameterised (`echo "$M" > .loop_signal.L1`), so the literal is never
in the text. **A text check cannot see a loop.** `drive()` records the marker at the moment it
is written; only a real per-lane signal write calls it, so a marker mentioned in a comment or
in v5's mutation string cannot enter the record (H63's fixture-reads-as-coverage defect, which
this suite has already paid for).

3. **And the record itself must be non-empty** — an empty driven-set against an empty accept-set
   leaves the loop with nothing to iterate and reports `0 uncovered`, a clean number from a
   check that never ran. That is exactly the shape H178's accounting control failed on.

## The guard has a runnable falsifier, because it had never been red on purpose

`spikes/harness/test_h202_falsify.sh` — the input that makes it fail, stated and run:

| arm | |
|---|---|
| **C1** | the mutation reached the accept branch — a `sed` whose anchor is absent returns the input unchanged, and this file would then be testing the shipped hook and reporting a pass |
| **A1** | a hook carrying a **fourth** marker turns the guard **red** (`want '0', got '1'`) |
| **A2** | and **names** it — `the hook accepts LOOP-NEVER and this suite never drives it per-lane` |
| **A3** | two-sided: the **same** suite is green on the unmutated hook (`107 checks pass`), so A1 measured the mutation and not a suite that is red for any reason |
| **C2** | the `KF_TEST_GATE` seam this needs **defaults to the shipped hook**, and the suite refuses at startup if it is unset while `GATE` is not the shipped path |

## Scope, said rather than implied

- **The H23 check's single-file limit is not repaired here.** A rename applied to both the
  accept branch and the message still reports `equal`. What now catches it is the behavioural
  coverage above — and that is a different check, not the same one improved. Recorded because
  a reader of the H23 check's name would assume otherwise.
- **The guard covers markers the hook ACCEPTS.** `LOOP-FUSE` is written by the hook and never
  accepted from a lane, so it is correctly outside the set — and that asymmetry is exactly what
  made it look like an "orphan" to H23's rejected detector 2.
