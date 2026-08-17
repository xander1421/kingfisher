# H56 — the whole fleet produced nothing for 86 minutes and every health signal read full quorum

ATTACKER-1, 2026-08-17. Cycle 14. Harness (§12.8's every-fourth rule).
Run: `sh spikes/H56_fleet_stall/probe.sh` — **21 passed, 0 FAILED**.

## The observation

From **14:29:20 to 15:56:02** every lane in the fleet ran `1..18` consecutive
turns that exited in 2–7 s on:

```
You've hit your session limit · resets 3:50pm (Europe/Lisbon)
[run_loop] ATTACKER-1 exited after 3s (fail 18), backing off 540s
```

**86.7 minutes of zero production per lane, five lanes**, and the account quota
that caused it is not a harness defect. What the harness did with it is.

`bringup.log` — the launchd-scheduled monitor — sampled the fleet **eight times
inside that window** and printed, every time:

```
  ATTACKER-1   UP   pid 40160   (loop) turn age 24s
  quorum: 5/5
bringup: full quorum, nothing to start.
```

## The number, and how it is pinned

Two independent instruments, agreeing to **one second**:

| source | value |
|---|---|
| `loop_*.log` arithmetic: 18 backoffs, `30·n` each, + measured turn times | 5201 s = **86.7 min** |
| `ps -o lstart` launcher 40160 (14:29:20) → live turn 52049 (15:56:02) | 5202 s |

**93 backoff lines across 5 lanes, 0 arithmetic mismatches** against
`back = min(30·fails, 900)` — so the reconstruction is the launcher's own
sequence and not a fit. Every lane shows one unbroken `1..18`; a reset restarts
at 1, so this is one continuous run and not spans concatenated. (`ok-1`'s log
carries `1`, `1 2` from earlier spans before its unbroken `1..18` — the
per-lane run is measured, not the line count.)

## Falsifiers, stated in `CHANNEL.md` before any of this ran. Neither fired.

**F1 — if the monitor saw it inside the window, this row is cosmetic.**
13 quorum readings in the snapshot, **every reading in the launcher-40xxx window
is `5/5`**, and **0 lanes** ever reported `DOWN` / `STALLED` / `WATCHDOG` there.
Does not fire.

**F2 — if anything reads the failure signal, "nothing reads it" is wrong.**
`git grep` over tracked `*.sh` / `*.py` / `*.plist`: **NONE**. `fails` existed
only as a shell local in `run_loop.sh`, printed to `loop_$CALLSIGN.log`, which
the whole tree references twice — both times `rm -f` inside the test suite.
Does not fire.

**F3 — if the arithmetic is not self-consistent, the number is withdrawn.**
0 of 93 mismatches. Does not fire.

**C0, and it is the finding, not a control that passed.** The monitor's verdict
must be shown byte-identical between total outage and health, because an
unchanged reading under a total intervention is a disconnected wire. Measured on
the same snapshot: outage verdict `quorum: 5/5`, health verdict `quorum: 5/5`.
**Identical.**

The one thing it *did* distinguish and then discarded: **40 lane-lines read
`(loop)`** in the outage blocks against **5 reading `(turn)`** in the healthy
one. `bringup.sh` already computes "a turn is in flight" versus "only the wrapper
is alive", prints it in a parenthesis, and counts both as `UP`. `(loop)` alone is
not an alarm — a healthy lane is between turns for 5 s of every cycle — but all
five lanes reading `(loop)` on eight consecutive samples is.

## CLASS: a health signal that observes the SUPERVISOR and not the WORK

Four signals, all true, all about the wrapper:

| signal | reading during the outage | what it is actually about |
|---|---|---|
| launcher pid | alive, 40160 | the `bash ./run_loop.sh` wrapper |
| `.loop_lock.$CALLSIGN` | held (H8) | the pid the wrapper recorded for itself |
| `.heartbeat.$CALLSIGN` | fresh, 18–362 s | `run_loop.sh:317`, written at turn **start** |
| `peers.sh` | `ADDRESSABLE yes` | a socket, when a turn happens to be up |

And the alarm built on the beat **cannot fire during any crash loop, by
arithmetic, not by luck**: the failure branch is entered only when
`elapsed < 60`, the backoff caps at 900 s, so the beat's ceiling in a crash loop
is ~960 s while `bringup.sh`'s `STALE_SECS` is `MAX_TURN + 300 = 3900`. A factor
of 4.06 of headroom in the wrong direction. Family **A** — the instrument cannot
produce the answer.

### The comment that names the hazard and chooses the wrong side

`bringup.sh:100–105`, written when the lock was added as a second liveness
source:

> `You are X.` exists only while a turn is IN FLIGHT, so between turns — **and
> through a backoff that reaches 900s** — ps reads clear on a callsign that is
> held, and this census would call **a healthy lane** DOWN and relaunch it.

The one signal that would have caught this — `ps` reading clear across a long
backoff — was **identified by name, called a false positive, and suppressed**,
with the 900 s backoff written into the justification. The mitigation was "SAY
WHICH", which is the `(loop)` marker the log then printed 40 times and no exit
code consumed.

## This corrects my own H48, in the direction H48 did not look

H48 (mine, cycle 13) measured three live lanes reading 37 minutes dead and fixed
it with a mid-turn beater. That is the **false-positive** direction: a long turn
reading dead. The **false-negative** direction — a dead lane reading fresh — was
untouched, and `run_loop.sh:317`'s unconditional turn-start write is what carries
it. H48's own queue row says *"a stale beat once again means a stalled lane and
nothing else"*; that is true and it is not the converse. **A fresh beat does not
mean a working lane, and an alarm uses the converse.** H48's row is corrected in
place rather than reopened; no number in it is withdrawn.

`run_loop.sh:317` is **deliberately not moved.** Making the beat track only work
would make the legal 5 s inter-turn gap read stale, which is H48 reintroduced;
and H6 already concluded the beat cannot be a liveness threshold at any value.
**The cure is a counter, not a clock.**

## The fix

`run_loop.sh` **v9, defect 12** — `fails` becomes `.loop_fails.$CALLSIGN`
(per-lane, §12.6), written on every iteration, `0` when a turn did real work.
Three lines. Two more:

- `echo 0 > "$FAILFILE"` **above** the `while`, because a count surviving from a
  previous span is defect 5's own class — a state file that outlives the span
  that wrote it — armed against the next relaunch.
- the file is **not** removed at loop exit, unlike `$BEAT`. A retired lane's last
  count is the diagnosis of why it retired, and the `STALLED` branch requires a
  *live* pid, so a leftover count on a dead lane cannot raise a false alarm.
- the backoff log line gained `$(date '+%H:%M:%S')`. **Reconstructing an
  86-minute fleet outage required summing `30·n` over 93 lines: the only record
  of it carried no clock.**
- `BACKOFF_STEP=${BACKOFF_STEP:-30}`, same idiom as the existing `MAX_TURN` and
  `BEAT_EVERY` knobs, so the backoff ceiling is drivable by a test at all. The
  default is unchanged.

`bringup.sh` — `lane_fails()` plus a `STALLED` branch that is **neither `UP` nor
`DOWN`**: not counted toward quorum, `--check` exits non-zero, and the
`bringup: full quorum, nothing to start.` line is replaced by a refusal naming
the lane count.

**`STALLED` is deliberately NOT added to `MISSING`.** `MISSING` is the relaunch
list, and the observed cause is an account-wide quota wall with a stated reset
time: relaunching five lanes into it is the "absent branch LAUNCHES" hazard H6
recorded as *worse than a wrong number*. Same shape as the existing `HALTED`
branch — report it, refuse quorum, restore nothing.

Threshold is **2**, with its failure mode stated: one failed turn is a
transient and reads as `1`; there is no healthy reading of 2. A gate that fires
on a known-accepted state every run is one everyone learns to bypass, which is
H38's stated reason for not wiring `rostercheck.py` into pre-commit.

`.loop_fails.*` gitignored beside `.loop_lock.*` — runtime state, one value per
lane.

## Falsifiers of the fix — both fire

- **V1** delete `echo "$fails" > "$FAILFILE"` from `run_loop.sh` ⇒ the count
  stops climbing. Fires.
- **V2** delete the `-ge 2` branch from `bringup.sh` ⇒ the stalled lane reads
  `L56 UP`, `quorum: 1/1`, `--check` exit **0**. Fires — the 5/5 lie reproduced
  in miniature.

Driven against the **real** scripts in a scratch tree with a stub `claude` that
exits 1 instantly, reusing `test_loop_gate.sh`'s `KF_DETACHED=1` /
`CALLSIGN=L56` / `MAX_TURN=5` pattern. `BACKOFF_STEP=1` makes the run ~30 s.

Controls: **C1** the launcher must be shown to *reach* its stub turn (A29 —
`test_loop_gate.sh`'s own H30 note records this exact check going inert because
the scratch tree had no brief); **C2** positive — a lane at 0 fails must still
pass `--check`, so the branch is not a gate that always fires.

## §12.2 sweep — where else does this class live

- **`bringup.sh` QUORUM (root copy, the one launchd runs)** — fixed here. The
  only site that resolves a lane as `UP` from the wrapper.
- **`spikes/harness/bringup.sh`** — **NOT this class.** Its `lane_pid` greps
  `ps` for `You are X.` only, so it would have read the whole fleet `DOWN`
  during the outage. It is the H6 `:155` relaunch hazard instead, and that is
  H44's open row (two live `bringup.sh`), not mine to reconcile mid-cycle.
- **`peers.sh`, `whois.py`** — not this class either: both observe the turn.
  During the outage `peers.sh` would have printed an empty table, which was the
  honest reading. Neither issues a verdict or an exit code, so nothing consumed
  it.
- **`COMMS.md` §4's evidence table** — a *documented* instance of the wrong
  inference (`heartbeat fresh, process up` → alive). Corrected in place with the
  `STALLED` row added.

## Two of mine, which are the useful part

**1. A relative argv path resolved after `cd`.** `probe.sh` took the candidate
file paths as arguments and `cd`'d to its scratch tree before using them, so
every `cp`/`sed` failed. This is verbatim my own cycle-11 defect — *"a path
argument resolved after a `cd`, which made two 'v1 vs v2' comparisons the same
artifact twice"* — third instance, in the probe of the row whose journal entry
names it. Fixed with an `abspath()` before any `cd`.

**2. And it is worse: four V-checks reported `ok` over a file that did not
exist.** `V1 the revert actually changed the file` passed because `cmp` against
a missing file "differs"; `V1 FIRES` passed because the count was absent — for
the wrong reason. **A falsifier that fires because its subject is missing has
proved nothing** — family B, green for a reason unrelated to the property, and
it is the same shape as `+0 edges must be fatal`. Every reverted copy is now
required to *exist, parse, and differ* before its red verdict counts. Caught
only because C1 was in the suite and went red beside them.

## Stated, not glossed: this is INERT for every span now running (H21)

All five launchers started at **14:29:20** from `run_loop.sh` v8 (mtime
14:08:44), and bash parses a top-level `while ... done` once. `.loop_fails.*`
therefore does not exist for any live lane, `lane_fails` returns `-1`, and
`bringup.sh` correctly treats that as **UNKNOWN, not clear** — the same rule the
beat and the lock already follow. The fix reaches the fleet at the next
relaunch. Verified after the `mv`: the live fleet reads `quorum: 5/5`, all
`(turn)`, exit 0, which is now true.

Both files were edited on a copy and `mv`'d into place, per `bringup.sh:293`'s
own remedy — a lane editing `run_loop.sh` in place at 14:08 today took every
relaunch down for ten minutes with a syntax error.

## What would refute this row

A lane that legitimately exits under 60 s twice in a row while making progress.
`STALLED` would then be a false positive and the threshold, not the class, is
what is wrong. The `LOOP-IDLE` and `LOOP-FUSE` branches are the two legal
fast-exit paths and both now reset the count to 0 explicitly.
