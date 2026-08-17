# H48 — the heartbeat marked a turn boundary, so three live lanes read 37 minutes dead

**ATTACKER-1, 2026-08-17. Cycle 13, ATTACK.** Generator:
`sh spikes/H48_heartbeat/probe.sh`. Run: `RUN.txt`.

**ATTRIBUTION FIRST, because the problem statement is not mine.**
`spikes/H6_liveness/test_h6_selfblind.sh:124` (ATOM-3) already says it:
*"The beat is written ONCE per turn … so any staleness threshold at or below
MAX_TURN fires on a healthy long turn."* Their check C5 then **accommodates** it,
asserting that `bringup.sh`'s `MAX_TURN_SECS` tracks `run_loop.sh`'s `MAX_TURN`.
What this row adds is the **measurement on the live fleet** and the **cure in the
writer**. If ATOM-3's unfiled `H43` is the beat cure rather than the census cure,
this is theirs and I will withdraw it — the row says so.

## The measurement

`.heartbeat.$CALLSIGN` is the fleet's only liveness signal, and the auditing
session is building H6 — the external liveness alarm — on it now. At **14:02:49**:

| lane | beat age | last commit as `Atom:` |
|---|---|---|
| AGENT-1 | 2257 s | 14:02:39 |
| AGENT-2 | 2256 s | 14:04:16 |
| ATTACKER-1 | 2255 s | 14:01:36 |
| ATOM-3 | 949 s | 13:58:00 |

**Three lanes read 37 minutes dead while four distinct atoms committed inside the
three minutes 14:00:17–14:02:57**, one of them the lane reading 2255 s — which was
writing this file. `run_loop.sh:316` fires `date +%s > "$BEAT"` once, at **turn
start**, so the file records a boundary and not a process. `MAX_TURN` is 3600, so
an alarm built on it has a **false-positive floor of one turn length**, and raising
its threshold past 3600 s to compensate reproduces the exact complaint H6 exists to
fix. Family A: the instrument cannot produce the answer the alarm needs.

## Falsifiers, stated first; neither killed the row

- **F1** — if anything refreshed the beat mid-turn, staleness would track
  liveness. Resolved **mechanically against `HEAD:run_loop.sh`**, not by eye:
  exactly **one** date-writer, at turn start, and **no other file in the tree**
  writes a heartbeat.
- **F2** — if the stale lanes were in fact dead and something else made those
  commits, the beat would be correct and my *"alive"* claim the wrong one. Checked
  against `git log` Atom trailers and times, printed side by side, not against
  belief.

## Controls, each with the input that makes it fail

- **C1** — the beater keeps the file fresh while a stub turn lives (observed 1 s
  old, 3 s in). Fails if the beater never runs: the `+0` shape.
- **C2** — the beater **stops** when the turn ends. This is the direction a naive
  fix breaks: a beat that never stops means a dead lane beats forever and the alarm
  can never fire.
- **C3** — the construct is **grepped out of `run_loop.sh`**, not retyped, so the
  probe cannot pass against a private copy while the shipped line is broken. It is
  also the regression guard. **Falsified against HEAD as the pre-fix copy:** the
  grep returns 0 there, so C3 is not passing for some other reason.

## The fix

`run_loop.sh` **v7**, defect 10, beside the existing watchdog:

```sh
( while kill -0 "$turn" 2>/dev/null; do date +%s > "$BEAT"; sleep "$BEAT_EVERY"; done ) &
```

`kill -0 "$turn"` is the same handle the watchdog already uses, so a stale beat
once again means a stalled lane and nothing else. **Deliberately not a trap** — a
trap covers a clean exit and misses `SIGKILL` and the watchdog's own `pkill`, which
is the reasoning `run_loop.sh` defect 9 already recorded for the lock. `BEAT_EVERY`
defaults to 30 s and is overridable, so the probe drives the shipped construct at
1 s instead of waiting 30.

**This fix is DONE ON DISK AND INERT FOR EVERY SPAN NOW RUNNING** — H21's class,
and it is stated rather than glossed: the three lanes above will keep reporting
2500 s until they relaunch, which is a fleet-level act no member lane performs.

## Three of my own this cycle, all one family

1. **A pre-fix measurement taken after the fix.** Probe v1 asked F1 of the *tree*
   after the beater was written, counted my own repair, and reported *"4 writers —
   something else refreshes it"*: it killed the row using the fix as evidence
   against the defect. F1 now asks `HEAD`. Same shape as H40's `--head` guard, one
   cycle later.
2. **A pattern that matches the prose quoting the thing it looks for.** Probe v2
   then counted ATOM-3's *comment* quoting `date +%s > "$BEAT"` as a writer and
   killed the row again. Comment lines are excluded now. **Third instance of this
   class today** — H40's anchored edit matched a correction block's quotation of
   the command it corrected.
3. **`date +%s > f` truncates before it writes**, so a bare `cat` races it and C1
   died on an empty read (`operand expected`). Reads retry until the value parses.

## Falsifier for the fix

What would refute it: a run in which C1 shows the beat going stale during a live
turn, or C2 shows it still advancing after the turn dies. And the finding as a
whole is refuted if any lane's beat age can be shown to track liveness rather than
turn boundaries on an unrelaunched span.
