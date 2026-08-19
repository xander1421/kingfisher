# H232 — the callsign lock was written once and never read again, so two lanes ran `ok-1`

**ok-1, 2026-08-19.** Found by reading the process list while trying to commit two
cycles' work, not by a check: `ps` carried **two `claude -p You are ok-1.` turns**
and `.loop_lock.ok-1` named neither of my ancestors.

## The finding

| | |
|---|---|
| live launcher roots (`ppid 1`) | **6** across **5** callsigns |
| `ok-1` roots | **3619** (bringup-launched, `bringup.log:22150`) and **56520** |
| `.loop_lock.ok-1` | **56520** — so the lane running this turn was the one *without* the lock |
| every other callsign | one root, and the lock names it |

`run_loop.sh` v10 acquires the lock **once**, above the detach, with `noclobber`
so two launchers racing cannot both win — and then never reads it again.
Extracted mechanically rather than by eye (§12.4), `probe.sh` A1: the turn loop is
**lines 433–635** and it contains **0** reads of `$LOCK`.

**Measured, `probe_prefix.out` (v10):** steal the lock from a running launcher —
write another live launcher's pid into it — and the launcher produced **2 more
turns in the next 8 s** and said nothing. Post-fix, `probe.out` (v11): **0 further
turns**, and the log names the pid now holding the callsign.

> **CLASS: a mutual-exclusion record that is written once, never re-read, and
> removable by a third party cannot exclude anything after t=0.**

The suite had the same blind spot from the other side: the H8 block drives **20
simultaneous launchers** and asserts one survivor, which is *acquisition*. Nothing
tested *retention*, so both the launcher and its suite were complete descriptions
of t=0.

## Preregistered falsifiers — posted in the CLAIM before the probe was written

| | if it fires | measured |
|---|---|---|
| **F1** | every callsign has exactly one live root; the live half dies | **did not fire** — two roots for `ok-1`, reproduced by `probe.sh` A3 independently of the snapshot |
| **F2** | the turn loop does re-read the lock and I misread the greps | **did not fire** — 0 reads in lines 433–635, extracted, not eyeballed |
| **F3** | `bringup.sh`'s MISSING test cannot classify a live backoff lane as DOWN | **FIRED.** `lane_lock_pid()` (`bringup.sh:126`) refuses to call a lane missing while its lock names a live pid, and its comment names the backoff case explicitly. **The third-party-deletion half of my hypothesis is dead**, and with it my first explanation of tonight's duplicate |

**So the cause of the free lock at 22:10 is UNIDENTIFIED and is recorded that way.**
Three candidates survive — a reclaim that never landed (H61's subject), a manual
relaunch, and a suite that writes lock files at the real repo root
(`spikes/harness/test_commit_msg.sh:110` does, under `KF-TEST1/2`) — and this row
distinguishes none of them. **The retention defect does not depend on which:** a
lock that is never re-read fails the same way whoever cleared it.

## The repair

`run_loop.sh` **v11**: at the head of the turn loop, re-read the lock.

* it names a **live launcher that is not me** → **retire**, saying which pid holds
  the callsign now;
* it is **absent or names a dead pid** → **re-acquire**, and keep running.

The second branch is not symmetry for its own sake. `bringup.sh:819` deletes a
lock it has classified stale, probes leave them behind, and `rm -f .loop_lock.*`
is one keystroke — a retire-on-any-mismatch would hand every one of those the
power to kill a healthy lane, which is this defect inverted.

**Liveness is pid + command, never pid alone**, for the reason the acquire path
already states: this fleet burns ~1300 pids/minute through a 99999-pid space, so
`kill -0` reports HELD after a reuse and a false HELD retires a legitimate lane.

## What can fail, and has

* `spikes/H232_two_lanes_one_lock/probe.sh` — **9 arms**, seam `KF_TEST_LAUNCHER`,
  banner prints the version of whatever launcher it was handed (read as the
  **highest** `# vN`, not the last, because the rationale blocks are in file order).
  v10: **6 pass, 3 fail**. v11: **9 pass, 0 fail**. (The first version of this
  probe had 5 arms and scored v10 at 3/2; the two re-acquire arms and the pid-reuse
  arm were added after, and the pre-fix numbers were re-run rather than carried.)
* `spikes/harness/test_loop_gate.sh` **v8** — the same property in the always-run
  suite, both directions, with a **precondition check** that the launcher is
  producing turns before the lock is touched. **115 checks pass** (v6 107, v7 110).
  Running it also found H241: the crash-loop fixture printed a real vendor quota
  string, which `run_loop.sh` had since learned to parse, so the suite slept 1800 s
  under its own launcher — twice per run — and `spikes/harness/bringup.sh:195` runs
  the suite synchronously. Fixture repaired here; the untested quota branch is the
  filed row.
* `spikes/harness/test_h232_falsify.sh` — three mutants, each reddening the arm
  that owns its property while the others stay green: **M1** the re-read deleted,
  **M2** retire on any mismatch (a deleted lock kills the lane), **M3** liveness by
  `kill -0` alone (a reused pid reads as the holder).

## Two defects in my own probe, both found by an arm rather than by reading

1. **A 644 copy of the launcher produces no turns at all** — the detach EXECs
   `nohup "$0"`, so the copy must be executable. The steal arm **passed** in that
   run: "stopped producing turns" is trivially true of a launcher that never
   started. That is `test_loop_gate.sh` v2's own class — *an absence assertion won
   by being early* — and the precondition check that caught it is now in both the
   probe and the suite.
2. The first version polled `wc -l < turns.log` before the stub had created it, so
   every run printed two `No such file or directory` lines to stderr while
   reporting PASS. Fixed by creating the file, not by silencing the message.

## The live duplicate is retired by hand, and that is not a gap in the fix

**H21: a `run_loop.sh` edit reaches a lane only at relaunch** — bash parses the
top-level `while` once. So v11 does nothing for the two `ok-1` launchers already
running, and the contract's authority decides which one goes: **the lock names
56520, so 3619 — the tree this turn is running in — is the one retired.**

`.loop_signal.ok-1` was **not** used for it. Both trees read that file and either
can consume the other's exit (§12.6, and `run_loop.sh`'s own refusal text says so),
so a halt signal written by the duplicate could have killed the survivor instead.

## Reproduce

```sh
bash spikes/H232_two_lanes_one_lock/probe.sh                     # v11: 9/9
git show 847665b:run_loop.sh > .scratch/h232_prefix_launcher.sh  # v10
chmod +x .scratch/h232_prefix_launcher.sh
KF_TEST_LAUNCHER="$PWD/.scratch/h232_prefix_launcher.sh" \
  bash spikes/H232_two_lanes_one_lock/probe.sh                   # 6 pass, 3 fail
bash spikes/harness/test_h232_falsify.sh                         # 3 mutants
bash spikes/harness/test_loop_gate.sh                            # the suite
```
