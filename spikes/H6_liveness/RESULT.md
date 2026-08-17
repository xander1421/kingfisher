# H6 — the fleet census could not see the lane running it

**ATOM-3, 2026-08-17.** Detector half of H6. The cure is split out as H43.

## CLASS

**A census that cannot see its own observer.**

`man pgrep`, flag `-a`: *"Include process ancestors in the match list. By
default, the current pgrep or pkill process and all of its ancestors are
excluded (unless -v is used)."*

Every fleet census in this repo was `pgrep -f "You are <lane>."`. A lane running
a census is **always** that census's ancestor — `claude -p` → `bash` →
`bringup.sh` → `pgrep`. So the one lane guaranteed to be alive was the one lane
the census could not see, and it was invisible unless the observer stood inside
the fleet it was counting.

This is not a defect in `pgrep`. The ancestor rule exists so that `pkill sshd`
run over ssh does not kill the session running it. The defect is using a
**self-protecting tool as a census**.

## FALSIFIER, stated before the run

If `pgrep -f` returns an ancestor pid on this machine, the finding is wrong.
If `ps` *also* fails to return it, the probe never planted a target and the
result is vacuous rather than confirming.

Run: `sh spikes/H6_liveness/test_h6_selfblind.sh`

## The probe failed twice before it worked, and both failures looked clean

Recorded because neither was visible without a positive control, and because
this is the same family as the defect under test.

1. **The marker sat late in a long argv, past macOS `ps` line truncation.**
   Both arms read empty — including the `ps` arm that was supposed to be the
   control. A29: a probe that cannot show it reached its target has produced no
   evidence.
2. **The search was `grep -v grep`, and the target's own argv contained the
   string `grep`.** The filter deleted the target. One-sided, so it read as a
   confirmation of the hypothesis.

`C2`/`C2b` are the positive controls that would have caught both. They run
first, before the finding they qualify.

## Measured

Two arms. Same pattern, same binary, same machine. The only difference is
whether the marker process is an **ancestor** or a **descendant** of the searcher.

| arm | `ps -eww \| grep` | `pgrep -f` |
|---|---|---|
| marker is an ANCESTOR of the searcher | 3 pids | **nothing** |
| marker is a DESCENDANT of the searcher | 4 pids | the target |

End to end, from inside `ATOM-3`, before the fix:

```
=== QUORUM ===
  AGENT-1      UP   pid 3543    beat 1749s ago
  AGENT-2      UP   pid 3597    beat 1748s ago
  ATTACKER-1   UP   pid 3663    beat 1747s ago
  ATOM-3       DOWN
  quorum: 3/4
```
exit 1, while `ps -eww` showed pid 44527 carrying `You are ATOM-3.` and
`.loop_lock.ATOM-3` held live wrapper 44512. After the fix: `quorum: 4/4`, exit 0.

## Sites — the whole harness grepped, per §12.2

| site | what it does | state |
|---|---|---|
| `bringup.sh:40` | `lane_pid()` — the roster census | **fixed** |
| `spikes/harness/bringup.sh:155` | launch decision: absent ⇒ `CALLSIGN=$l ./run_loop.sh` | **fixed** |
| `spikes/harness/bringup.sh:190` | post-launch VERIFY | **fixed** |
| `spikes/harness/bringup.sh:204` | the **undeclared-lane audit** | **fixed** |
| `spikes/harness/whois.py:74` | `sh("pgrep","-f","claude")` | **OPEN, AGENT-2's, reported** |
| `run_loop.sh:343` | watchdog `pkill -f "You are $CALLSIGN."` | **not a census — out of scope, see below** |

Two of those are worse than a wrong number:

- **`spikes/harness/bringup.sh:155` LAUNCHES on the absent branch.** So a lane
  running its own bring-up starts a second launcher on its own held callsign —
  H8, which is the defect that same section's header says it exists to prevent.
  `.loop_lock` only covers lanes started by `run_loop.sh` v6+; the four lanes
  live during this cycle predate it and hold no lock.
- **`spikes/harness/bringup.sh:204` is the audit for UNDECLARED lanes**, written
  because `ok-1` ran for hours with no role. A lane that was itself off-roster
  would audit the fleet and report itself absent.

**The watchdog's `pkill` is deliberately untouched and is not the same defect.**
Its target is the `claude -p` child of a *sibling* subshell, never an ancestor of
the watchdog, and `kill -TERM "$turn"` backs it up. Stated rather than assumed
because it is the highest-stakes `pkill` in the tree.

**`whois.py` is left RED, not whitelisted.** The suite reports `8 passed, 1
failed` and names the file and line. It is another lane's file and another
lane's row (H37); narrowing C4b to route around it would be the H26b move — a
checker going green by shrinking its own scope. Measured from inside ATOM-3, the
unmodified script prints `CENSUS: 11 claude processes (total printed; nothing
truncated)`, lists **4** lanes, omits pid 44527 — and its own `LOCK FILES`
section eight lines below lists `ATOM-3`. The contradiction is on one screen and
nothing flags it. Reported to AGENT-2 with the one-line `ps` substitution.

## The second half: the heartbeat could never have been the alarm

H6's row said *"`.heartbeat.$CALLSIGN` now exists to watch."* It cannot be
watched for lane death at any threshold:

- The beat is written **once per turn, at turn start** (`run_loop.sh:263`).
- A turn is legal until `MAX_TURN=3600`.
- So every threshold **below** 3600 fires on a healthy long turn, and no
  threshold above it beats the watchdog that already kills at 3600.

The old `STALE_SECS=2100` was 35 minutes — the number from the *post-mortem* of a
dead fleet, not a threshold anything can act on. Live confirmation while this was
being written: `AGENT-1` read `turn age 2071s` and was healthy; under the old
threshold it would have alarmed 29 seconds later.

Three changes, all in `bringup.sh` v2:

1. **Liveness needs no threshold.** Two sources, and the report says which:
   a turn in flight (`ps`), or the recorded holder `.loop_lock.$CALLSIGN`
   (`run_loop.sh` v6 / H8), which is the only signal that survives *between*
   turns and through a backoff that reaches 900 s. A lane held only by its lock
   has not been observed doing anything, and printing that as plain `UP` is the
   empty-input floor.
2. **The beat's honest job is watchdog-failure detection.** A beat older than
   `MAX_TURN` means the turn outlived the only mechanism that bounds it. There is
   no healthy reading of that. `MAX_TURN_SECS` is asserted against
   `run_loop.sh`'s `MAX_TURN` by `C5`, so the two files cannot drift silently.
3. **Absent is not stale, and only one of them has a timestamp** (ok-1's phrasing,
   via AGENT-2). `run_loop.sh:337` removes the beat on a clean exit, so absence
   means retired, *or* never started, *or* — observed on `ok-1`, alive and
   mid-turn with no beat file at all — a wrapper still running a launcher
   generation that predates the beat (H21). Four states, one observation; the
   report now names all four instead of printing `no heartbeat file yet`.

## Checks

`sh spikes/H6_liveness/test_h6_selfblind.sh` — 9 checks.

| id | asserts | fails when |
|---|---|---|
| C1 | `pgrep -f` returns nothing for its own ancestor | macOS changes the ancestor rule; the whole rationale block above is then wrong |
| C2 | `ps` DOES see the ancestor | the probe planted nothing — makes C1 vacuous. This is the control the first two attempts lacked |
| C2b | the descendant arm is found by BOTH tools | the pattern does not match a live target |
| C3 | the real `lane_pid()`, read out of each `bringup.sh`, finds a lane that is its own ancestor | either file is reverted to `pgrep` |
| C4 | no `*.sh`/`*.hook` census uses `pgrep -f` | a new shell census is written anywhere in the harness, including in files that do not exist yet |
| C4b | the one Python census either does not use `pgrep` or declares its self-blindness in the file | a second Python census appears, or whois.py's caveat is deleted without fixing the call. **RED now, by design** |
| C5 | `bringup.sh`'s `MAX_TURN_SECS` tracks `run_loop.sh`'s `MAX_TURN` | either number moves without the other |
| C6 | restoring the `pgrep` form on an inline copy makes C3's assertion fail | C3 is passing for some reason other than the fix |

`C6` is the §12.10 requirement: a check never seen red is not known to be a check.

No `mktemp`. H17 — whether §10's *"nothing outside the workspace is written"*
has an exception for `/tmp` scratch — is an OPEN, undecided row, and a suite that
takes a side on it merely by running is deciding it by default.

## Regression

`sh spikes/harness/test_loop_gate.sh` → **62 checks pass**, rc=0, after the edits.

## Not done, split out rather than folded in

- **H43 — the cure.** This row is the DETECTOR. What to do about a wedged lane is
  a separate decision, and the obvious answer (kill the child) is wrong: H31
  records that the detached wrapper respawns it, so killing the child is not
  killing the lane. §2: PARTIAL is not a verdict; split and finish the half that
  is finishable.
- **H44 — two `bringup.sh`.** `./bringup.sh` (what `prompts/ATOM-3.md` and the
  LOADED `com.kingfisher.bringup` LaunchAgent invoke) and
  `spikes/harness/bringup.sh` (what `CHANNEL.md:182`'s `DONE H6b` names, and what
  `spikes/harness/net.kingfisher.fleet.plist` — PROPOSED, never installed —
  invokes). They differ from line 2. Both had this defect; I fixed both rather
  than pick a winner mid-cycle, because a second census that disagrees is the H6
  hazard in its own right.

  > **CORRECTED 2026-08-17, ATOM-3.** This paragraph said `./bringup.sh` was
  > "163 lines" and `spikes/harness/bringup.sh` "untracked, 228 lines". The
  > second copy had been TRACKED since `600d138` (13:56), and the counts were
  > 230 and 273 at HEAD. Measured once, early, then restated unchanged in four
  > documents — this file, the H44 queue row, `HANDOFF.ATOM-3.md:79`, and
  > `./bringup.sh`'s own header. Claim decay across documents (`CLAUDE.md`,
  > "three things no tool will catch"), inside the row whose subject is these
  > two files. The counts are struck rather than updated: a line count of a file
  > in the same repo is stale on the next edit. `C10`/`C12` of
  > `test_h44_check_is_readonly.sh` now refuse both forms.
