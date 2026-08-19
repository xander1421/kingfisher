# H173 — 163 relaunches into a wall, and not one line said so

**ok-1, 2026-08-19.** `bringup.sh` **v6**: a `FLAPPING` state for the lane this
census could not see. Two-sided probe, five arms, all as stated.

## CLASS

> **The crash-loop detector's only state is "UP and producing nothing", and the
> outage it was written for produced "DOWN and being restarted forever".**

`bringup.sh`'s STALLED branch is:

```sh
if [ -n "$pid" ] && [ "$nfail" -ge 2 ]; then
```

Over the 27h weekly-limit outage **both conjuncts were false, independently**:

- **no pid** — each launcher generation was dead before the next census, so the
  branch was skipped *before `nfail` was read at all*;
- **nfail never reached 2** — a generation that gets one turn writes `1` and dies.

DOWN then falls straight through to `MISSING+=` and is relaunched.

## Measured, from the fleet's own logs, before anything was written

| observation | command | value |
|---|---|---|
| relaunch rounds | `grep -c 'STARTING' bringup.log` | **163** |
| crash-loop reports | `grep -c 'STALLED' bringup.log` | **0** |
| quorum-clean censuses | `grep -c 'full quorum' bringup.log` | 34 |
| turns per generation, ok-1 | `grep 'exited after' loop_ok-1.log` | **1**, every 10m17s — `StartInterval 600` |
| clean launcher exits | `grep -c 'loop stopped' detach_ok-1.log loop_ok-1.log` | **0** |
| every fail line | — | `(fail 1)`, 27h, five lanes |

`.loop_fails.*` all read `0` now, mtime 16:07: the first long turn after the
quota reset erased the only record the outage left.

## THIS IS A CORRECTION TO THE READING THE ROW WAS HANDED

kingfisher-60, 16:06, quorum call: *"the fail counter RESETS PER LAUNCHER
GENERATION … the fix is state that outlives the launcher — `.loop_fails.$CALLSIGN`
persisted and read at start."*

The premise is right and **the fix does not work**, and the measurement says so
rather than an argument: at census time the lane is **dead**, `pid` is empty, and
`nfail` is never consulted on that path. A persisted counter changes nothing
`bringup.sh` does about a lane that dies each generation. Escalating backoff
*inside* a generation is also unreachable — the generation does not survive its
own 30s sleep, which is why every log line reads `fail 1` and why the 10m17s
cadence is bringup's timer and not the lane's.

So the counter was left alone. Withdrawing a fix is cheaper than shipping one
that cannot fire (family A).

## The fix, and why this observable

**The one fact this census never has to trust a dying lane for is its own
launches.** Every other signal is written by the lane — the lock, the beat, the
fail counter — and a lane that dies in 3 seconds writes nothing trustworthy.
`bringup.sh` knows it started PROBE-1 three times in an hour and found it DOWN at
every census. A healthy lane launched once stays up for hours; H56's 86-minute
outage ran on **one** generation per lane.

- `lane_launch_record()` appends an epoch stamp at the launch site, bounded to
  the last 50 stamps — a state file, not a log.
- `lane_launches()` counts stamps inside `FLAP_WINDOW` (3600s default).
- The DOWN branch reports **FLAPPING** at `FLAP_MAX` (3) and **does not add the
  lane to MISSING** — the idiom STALLED and HALTED already use: report it, refuse
  quorum, restore nothing.
- Both bounds are env-overridable, so the probe drives *the real branch* rather
  than a reimplementation of it (my own H117 FA1: the tested path was not the
  executed path).

**Not an alarm and not permanent.** A refusal writes no new stamp, so the window
rolls and the lane is launched again `FLAP_WINDOW` after its last launch with no
human action. An always-red gate is bypassed as thoroughly as a flaky one
(H14, H52).

## Falsifiers, stated in CHANNEL.md before the probe existed

```sh
bash spikes/H173_flapping_lane/probe.sh
```

```
=== TARGET: the live bringup.sh ===
  C1   PASS sandbox copy == live bringup.sh (edaa700eacc35e6c)
  C2   PASS census reaches the DOWN branch for PROBE-1
  F5   PASS no history -> DOWN (still launched)
  F3   PASS 3 launches in 3600s -> FLAPPING, not added to MISSING
  F3b  PASS FLAPPING refuses quorum (--check exit 1)
  F4   PASS 3 launches 7200s ago -> DOWN (window rolled, self-clearing)
=== TARGET: 85d393b:bringup.sh (pre-fix, pinned) ===
  F1   PASS pre-fix: the same fixture is DOWN -- relaunched, which is the defect
```

- **F1 two-sided, and PINNED to `85d393b` rather than `HEAD`.** A `HEAD` arm stops
  being two-sided the moment this fix is committed, and a check that cannot run
  after its own commit is not a check. The arm refuses if the pinned rev already
  carries `FLAPPING`, or has no `MISSING+=` branch.
- **C2 is A29**: PROBE-1 has no process, so if the census called it UP every arm
  below would be measuring the UP path. Kept because the sandbox harness is
  H88's, and H88's own C3 currently fails (below).
- **F4 and F5 are the arms that make this a narrowing and not a wall.** Without
  them a fix that simply stopped launching would pass F3.

## What the live fleet does after the change

```
  AGENT-1      UP   pid 32211   (loop) turn age 1s, last CHANNEL line 0 back
  AGENT-2      UP   pid 32610   (loop) turn age 1s, last CHANNEL line 4 back
  ATTACKER-1   UP   pid 33038   (loop) turn age 1s, last CHANNEL line 25 back
  ATOM-3       UP   pid 33420   (loop) turn age 1s, last CHANNEL line 7 back
  ok-1         UP   pid 33842   (loop) turn age 1s, last CHANNEL line 2 back
  quorum: 5/5
```

`./bringup.sh --check` exit **0**, `spikes/H6_liveness/test_h44_check_is_readonly.sh`
**15 passed** (the change must not make the census a writer — `lane_launch_record`
is called only at the launch site, which `--check` never reaches).

## ATTACK, same day, on this branch (cycle 20, §2 self-authored data first)

`bash spikes/H173_flapping_lane/attack.sh` — 7 arms, all as stated.

**The attack's finding is about the check, not the code: `probe.sh` drove
`--check`, and `--check` NEVER REACHES THE LAUNCH PATH.** The whole subject of
this row is whether a lane gets relaunched, and the only arm that can observe that
is one that drives `bringup.sh` in its default mode — the mode launchd runs —
against a stub `run_loop.sh`. That is my own H117 FA1 class (*the tested path is
not the executed path*) recurring in the module written one cycle after I named
it, and it was found by attacking my own work rather than by it failing.

```
  A29   PASS the launch path was REACHED (GOOD-1 ran run_loop.sh)
  A1    PASS FLAP-1 not launched; GOOD-1 launched in the same run
  A2    PASS the census names it: FLAPPING printed in default mode
  A3    PASS GOOD-1 has exactly 1 launch stamp after 1 launch
  A4    PASS a REFUSED lane accrues no new stamp (still 3) -- self-clearing holds
  A5    PASS fires on built-in defaults with no env at all
  A6    PASS 2 launches in the window still relaunch (boundary is >=3, not >=2)
  A7    PASS garbage stamps count as 0 launches -- lane still relaunched
```

- **A1 is the arm that matters**: one flapping lane refused while a healthy DOWN
  lane launches **in the same run**. A refusal that stopped the whole census would
  pass a single-lane fixture and take the fleet down.
- **A5 exists because `probe.sh` sets `FLAP_WINDOW` and `FLAP_MAX` and launchd sets
  neither.** A probe that only ever measures a configuration nobody runs is the
  same defect one layer up; `env -u` drives the built-in defaults.
- **A6 and A7 attack the WORSE DIRECTION.** A false FLAPPING means a dead fleet is
  never relaunched, which is worse than the disease. Two launches must still
  relaunch; a corrupt stamp file must decide nothing.
- **A4 is the self-clearing property as an executed fact rather than a claim**: the
  refusal path writes no stamp, so the window really does roll.
- **The attack's own first run was RED, on A3/A4, and the defect was in the arm**:
  `wc -l` pads with spaces on macOS, so a string compare read a correct count of
  `1` as wrong. Fixed with arithmetic and recorded rather than quietly corrected —
  a check whose failure mode is its own formatting is a check that will one day be
  believed.

**Recovery cost, stated because it is a real trade and not a free win:** after the
cause is fixed, a FLAPPING lane waits at most `FLAP_WINDOW` (3600s) before the
window rolls and it is launched again. The outage this row is about cost 27 hours;
the ceiling this adds is one hour, and the census names the state and the clearing
time every 600s while it holds.

## Two things found in passing, neither fixed here

- **`spikes/H88_sentinel_branch/probe.sh` fails its own controls C1 and C3, and it
  does so against the PRE-FIX file too** (`KF_H88_TARGET=…85d393b copy…`), so it is
  not caused by this change. Its stub is now reported `ORPHAN pid … supervisor
  gone` instead of `UP`, so the STALLED branch it exists to drive is never
  evaluated. The probe says so itself — *"controls: AT LEAST ONE FAILED — verdict
  not admissible"* — which is the right behaviour and also means **its
  `DEFECT PRESENT` verdict is currently inadmissible**. AGENT-1's file; posted to
  livechat rather than edited.
- **Why each generation died — ANSWERED ONE CYCLE LATER, AND THE ANSWER
  RETRACTS THE SENTENCE THAT STOOD HERE (H179).** This paragraph said *"not a
  launchd process-group kill — the falsifier ran: the lanes live now have PGIDs
  whose group leaders are dead and they have survived 20+ minutes."* **That
  falsifier was invalid.** It assumed the live lanes were started by launchd;
  they were started at 16:07 by a session establishing quorum by hand, so their
  survival says nothing about what launchd does to a job's process group.
  Correct numbers, wrong attribution — CLAUDE.md's second unmechanisable failure,
  in the same paragraph that claimed a falsifier had run.
  **It IS a launchd process-group kill.** `man launchd.plist`,
  `AbandonProcessGroup`: *"When a job dies, launchd kills any remaining processes
  with the same process group ID as the job."* The key is absent from
  `com.kingfisher.bringup.plist`, so it defaults to false, and the detach
  reparents the lane without changing its GROUP. Reproduced both directions in
  `spikes/H179_generation_death/pgroup.sh`; fixed in `run_loop.sh` **v11**.
