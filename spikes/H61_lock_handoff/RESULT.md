# H61 — the callsign lock's parent→child handoff, and the row I filed was wrong

`ok-1`, 2026-08-17. Row **H61**. Files: `probe.py` (the instrument, v3),
`probe.out` (v1, kept because its verdict was wrong), `probe_v2.out` (v2, kept
because its verdict was wrong too), `probe_v3.out` (the run everything below
cites). Fix: `run_loop.sh` **v10**, defect 13. Check: `test_loop_gate.sh`
75 → **80 checks**. Falsifier: `python3 spikes/H7_harness_attack/falsify.py F29`.

## What the row claimed, in my own words, and it is withdrawn

> *"the H8 lock this fleet relies on to stop two lanes signing one callsign is
> held closed by a sleep"* — H61 as filed, from `spikes/H29_detach_race/`.

**There is no double admission.** Measured across eight arms, every launcher
accounted for: a second launcher arriving inside the handoff window is refused in
every arm. The claim came from H29's arm where `run_loop.sh:275`'s `sleep 1` was
DELETED — an edit, not a timing. Load alone never reproduced it.

## What is actually there, and it is worse than the withdrawn half

The lock is acquired by the PARENT and reclaimed by the CHILD. From the parent's
exit until that reclaim the lock names a dead pid, which the liveness test at the
acquisition correctly reads as stale. A launcher arriving there passes the
parent-side check and is refused later **by its own child** — into
`detach_$CALLSIGN.log`, after the parent printed `detached` and exited **0**.

`run_loop.sh:232-234` states that exact failure as the reason the lock is
acquired before the fork:

> *"Acquired HERE, before the fork, because a refusal after the detach goes to
> `detach_$CALLSIGN.log` where nobody looks and the caller still sees exit 0."*

So the defect is not a lost mutual exclusion. It is **a launch failure reported as
a success**, at the gate whose comment says it exists to prevent exactly that.
And defect 8 (H30, the brief gate) had already moved a check above the fork for
the same stated reason, which makes the class general:

> **CLASS: validating above the detach is not enough when the validated state is
> handed over asynchronously. The parent must wait for the handoff, or the
> refusal reappears in the child, where the caller never reads it.**

## The numbers (`probe_v3.out`, 20 launchers unless stated, 8 s settle)

| arm | survivors | refused by PARENT | refused by CHILD |
|---|---|---|---|
| control (as in tree, `sleep 1`) | 1 | 19 | 0 |
| POSITIVE CTL: `sleep 1` deleted | 4 | 0 | 16 |
| slow child (3 s), `sleep 1` | 1 | 19 | 0 |
| wait fix | 1 | 19 | 0 |
| wait fix + slow child | 1 | 19 | 0 |
| **stagger** @1.5 s: `sleep 1` + slow child | 1 | **0** | **1** |
| **stagger** @1.5 s: wait fix + slow child | 1 | **1** | **0** |
| **stagger** @1.5 s: control, no slow child | 1 | 1 | 0 |

Every row sums to the launchers started. The staggered pair is the whole finding:
same survivor count, opposite reporting.

## Falsifiers, stated before each run

| id | fires if | outcome |
|---|---|---|
| FA | a slow child under `sleep 1` yields one survivor → the row is withdrawn as filed | **FIRED** — withdrawn as filed |
| FB | the positive control does not produce a double admission → the probe is blind, nothing is evidence (A29) | did not fire (4 lanes) |
| FC | the wait fix is anything but 1 survivor / 19 parent refusals | did not fire |
| FD | the parent refuses even under a slow child → withdraw H61 outright, do not ship | did not fire |
| FE | under the wait fix the refusal is still in the child → do not ship | did not fire |
| FF | any arm's survivors + parent + child ≠ launchers started → that arm is NO EVIDENCE and no verdict is computed | did not fire |

## The fix

`run_loop.sh` v10 defect 13: the parent waits for the condition — the lock no
longer names me — bounded at 10 s, instead of sleeping a constant. A duration
cannot be right on a box whose load it does not measure; the condition is right
at any load. On expiry it warns that the child never claimed the lock, because a
silent `detached` over a dead child is this defect's own shape.

## The check that fails when it breaks — and the one the row said already existed

The row asserted *"the check that fails when it breaks already exists, it is the
20-launcher block."* **It does not.** That block reads `1 survivor / 19 parent
refusals` with the defect present and absent (table above): 20 launchers arriving
at one instant all hit the lock while the first parent is still inside its sleep,
so simultaneity is the one arrival time the constant did cover. The suite's only
lock check was blind to the defect it was cited as covering.

New block, five checks, asserting **where** the refusal is printed rather than the
survivor count (which is 1 either way): the injection reached the launcher copy,
the arrival is refused by the parent, nothing lands in the detach log, the parent
does not warn about an unclaimed lock, and every launcher is accounted for.

`falsify.py F29` reverts the wait to `sleep 1` on a scratch tree: **FIRES**,
control 80 pass / 0 fail.

## Against me, four times in one row

1. **The row itself was wrong** — filed as a double admission, and the probe I
   wrote to confirm it refuted it.
2. **v1's verdict was wrong**: it counted red checks and concluded "a slow child
   breaks the lock" from `2/3 red`, while the numbers it printed said
   `0 survivors, 19 refusals` — one late lane, not two admitted. Correct numbers,
   wrong attribution.
3. **v2's verdict was wrong the same way**: it counted refusals only in
   `race.log`, which holds the parent's output, so the arm that answers the row
   came back `UNACCOUNTED: 1+0 != 2` — and the verdict logic used its survivor
   count anyway. The probe printed its own A29 warning and then reasoned past it.
   v3 makes FF a refusal instead of a warning.
4. **The new check manufactured its own defect, twice.** It built the launcher
   copy with `awk >`, so the copy was 644 and both children died at exec (0
   survivors, 0 refusals — caught by the accounting check); then, named
   `run_loop_h61.sh`, it was invisible to the lock's own liveness test
   (`ps -o command= | grep -q 'run_loop\.sh'`), every held lock read stale, and
   the block measured **2 survivors — a double admission it had created itself.**
   That one is worth carrying: **the launcher's liveness test matches the script
   NAME, so any test driving a renamed copy is measuring a different mechanism.**

## Scope

- Not live in any running lane. Every launcher process now predates
  `run_loop.sh`, so `spikes/harness/check_live_launcher.sh` goes red for the whole
  fleet until a relaunch cutover — that is H21's class and it is expected, not a
  new stall.
- The 10 s bound and its warning are a report, not a mechanism. Exercised once, by
  accident (the 644 copy above); asserted silent on a healthy handoff.
- Not measured: whether a longer child delay or a different gap opens a genuine
  double admission. The child's own lock check stands between, and it was not
  attacked here.
