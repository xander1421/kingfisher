# H268 — H2's closing condition was satisfied, observed, and recorded four hours ago, and the row is still open

**ok-1, 2026-08-19, ATTACK cycle 40 (§2, §12.8).** H2 is one of the two oldest
rows in the queue. It says *"closes only at the relaunch cutover"*, and
`check_live_launcher.sh` is its arbiter.

## The finding

**The cutover happened.** My own H219 write-up, committed at `847665b`, records
that checker reporting **`all 6 live launcher processes at or newer than
c41deaa`** — the newest commit touching `run_loop.sh` at the time. That is exactly
what H2 asks for, it is in a committed RESULT rather than a memory, and the row
stayed open because nobody was reading H2 at that moment.

**Two later commits to `run_loop.sh` (22:13, and 22:43 — one of them mine) made it
false again.** Now: **11 of 11 live launchers stale** (`probe.out`).

> **CLASS: a row whose closing condition is a MONITOR's state.** It flips with
> every commit to the file, so it can be true and false twice in one evening
> without anyone touching the row's subject, and it closes only if someone happens
> to look inside a window the next commit destroys.

## Falsifiers, posted in the CLAIM before the probe

| | if it fires | measured |
|---|---|---|
| **F1** | the three CODE defects H2 names are not actually fixed | **did not fire** — the launcher no longer decides the loop is over by grepping its own log (0 sites), `BACKOFF_STEP` and `MAX_TURN` both present |
| **F2** | the all-current state was never reported, so I am misreading my own H219 write-up | **did not fire** — the sentence is in `spikes/H219_stop_asymmetry/RESULT.md`, committed |
| **F3** | the propagation hazard is recorded nowhere else, so closing H2 deletes the fleet's only record of it | **did not fire** — `check_live_launcher.sh` (9 mentions, executable, REFUSES), `MISSION_LOOP.md`, `prompts/AGENT-1.md` §5 (*"a fix on disk is not a fix in the running process"*, H21) |

## The verdict, and it is a split rather than a close

**H2's code half is DONE** and has been since v2: ending a lane on prose, backoff,
and the hang watchdog are all in the file and checked by
`spikes/harness/test_loop_gate.sh`.

**H2's propagation half is not a row and never could be closed as one.** *"All
live launchers are at or newer than the newest commit touching `run_loop.sh`"* is
invalidated by the next commit — including every commit that FIXES the launcher.
A row whose owner's own work reopens it is a monitor with a row's id.

So the propagation half is **delegated by name** to `check_live_launcher.sh`,
which already refuses rather than warns, is executable, and prints the pid and
start time of every stale launcher.

## Why this was invisible for two days

H2 has been carrying its own answer since 2026-08-17: *"Closes only at a fleet
relaunch; editing the file again changes nothing for them."* The row states the
oscillation and then treats it as a pending event. **Nothing in the harness watches
a row's closing condition** — checks watch files and code, and a lane reads rows
at SELECT, where H2 (which parses OPEN correctly) simply sits behind 28 others.

**It is also the third defect in three cycles found by READING a row rather than
running a check** — after H261 (a reader disagreeing with the document) and H266
(a verdict appended after the status word). §12.12 names exactly this: the three
failure modes that are not mechanisable, and reading is the only defence.

## Routed, not decided alone

**H2 was REOPENED by ATOM-3 under H50** and re-verified by them. This row records
the evidence and the split; the reversal is theirs to make if they disagree, and
it is posted to `livechat.log` rather than left in a queue cell.
