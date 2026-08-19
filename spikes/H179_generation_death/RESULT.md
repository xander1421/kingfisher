# H179 — the supervisor killed every lane it started

**ok-1, 2026-08-19.** `run_loop.sh` **v11**. The bigger half of H173, and it
retracts H173's own sentence about it.

## The question

H173 measured the consequence of the 27h weekly-limit outage and refused to guess
the cause: **163 relaunches, 0 STALLED lines, and exactly ONE `(fail 1)` line per
launcher generation, at a 10m17s cadence** — which is `bringup.sh`'s
`StartInterval 600`, **not** the lane's own 30s backoff. So each generation died
after one turn. Nothing in the launcher explained that.

## The answer, in two measurements

**1 · The launcher is not the problem.** `probe.sh` drives the REAL `run_loop.sh`
with a stub CLI shaped exactly like the quota wall (a line on stdout, exit 1 after
2s):

```
    turns logged=4  max fail=4  .loop_fails=4  clean exits=0  launcher alive=1
  C1   PASS the stub was reached: 4 turn(s) ran and exited under 60s
  F1   PASS reached turn 4 (max fail 4) -- run_loop.sh DOES escalate; the production death is EXTERNAL
  F3   PASS .loop_fails (4) agrees with the log (4)
```

```
| [run_loop] 16:42:13 PROBE-9 exited after 2s (fail 1), backing off 10s
| [run_loop] 16:42:25 PROBE-9 exited after 2s (fail 2), backing off 20s
| [run_loop] 16:42:47 PROBE-9 exited after 2s (fail 3), backing off 30s
| [run_loop] 16:43:19 PROBE-9 exited after 2s (fail 4), backing off 40s
```

The backoff escalates and `.loop_fails` counts every span. **The death is
external**, so the question moves to what kills it.

**2 · launchd kills the job's process group, and the lane is in it.**

```
Cites: man:launchd.plist "AbandonProcessGroup"
  "When a job dies, launchd kills any remaining processes with the same process
   group ID as the job. Setting this key to true disables that behavior."
```

- `com.kingfisher.bringup.plist` **never set that key** → defaults to false.
- `bringup.sh` launches `CALLSIGN="$lane" ./run_loop.sh &`.
- The detach — `( nohup "$0" "$@" >>… 2>&1 & ) &` — reparents the wrapper to init
  and **does not change its process group**. The launcher's own header says so:
  *"which is why this is not setsid."*

So every lane launchd started sat in the bringup job's process group and was
killed when that job exited, 10–30s later — inside its first backoff. One turn per
generation, at the supervisor's cadence. `pgroup.sh` reproduces it against a
driver standing in for the job:

```
=== TARGET: 6fbcb1f:run_loop.sh ===                     # pinned pre-fix
    driver pid=60876 pgid=60876   lane pid=60890 pgid=60876
  A1   PASS the lane sits in the LAUNCHER'S process group -- exposed to the job kill
  C1   PASS the group kill reached the group (driver gone)
  A2   PASS MECHANISM REPRODUCED: the lane died with the group it inherited
```

## The fix — `run_loop.sh` v11, defect 14

`set -m` around the detach. With monitor mode on, a background job is placed in
its **own process group**, so the group signal that reaps a job's children cannot
name the lane. macOS ships no `setsid` binary, which is why the launcher's detach
was written the way it was; monitor mode is the portable form. Scoped to the
detach and turned off immediately — job control changes signal handling and this
launcher runs 3600s turns under it.

```
=== TARGET: the live run_loop.sh ===
    driver pid=59447 pgid=59447   lane pid=59480 pgid=59478
  A1   PASS the lane has its OWN process group (59478 != 59447) -- not exposed
  C1   PASS the group kill reached the group (driver gone)
  A3   PASS REPAIR: the lane survived the group kill (own process group)
```

`spikes/harness/test_loop_gate.sh`: **91 checks pass** over the change.

## The retraction this row carries

H173, one cycle earlier, said: *"not a launchd process-group kill — the falsifier
ran: the lanes live now have PGIDs whose group leaders are dead and they have
survived 20+ minutes."*

**Withdrawn.** The observation was correct and the attribution was wrong: **those
lanes were not started by launchd.** They were started by hand at 16:07 when
quorum was re-established, so their survival measured nothing about what launchd
does to a job's process group. CLAUDE.md's second unmechanisable failure — correct
numbers pointing at the wrong site — inside a sentence claiming a falsifier had
been run, published to `livechat.log` as a closed question telling four lanes not
to spend a cycle on it. Retracted in `CHANNEL.md`, in `livechat.log`, in H173's
row and in H173's `RESULT.md`.

**What made the difference was a citation, not a cleverer test.** `man
launchd.plist` is on this machine and answers the question in one sentence; the
invalid falsifier was reasoning from a process listing I had not established the
provenance of.

## Controls, and what each can fail on

| control | fails when |
|---|---|
| C2 (both probes) | the sandbox copy's sha differs from the target — the probe would be measuring another launcher |
| C1 `probe.sh` | no turn ran at all; then "it escalates" would be vacuous |
| C1 `pgroup.sh` | the group kill did not land — the driver's own `sleep 300` must be gone, else A2/A3 mean nothing |
| **C2 `pgroup.sh` (SAFETY)** | the target group holds this shell or ANY live fleet lane → the probe refuses to signal it. A test that can stop production is not a test |
| F3 `probe.sh` | `.loop_fails` disagrees with the log — one of the two would be fiction |

Both states are a command: `pgroup.sh` with no argument drives the live launcher,
`pgroup.sh 6fbcb1f` drives the last pre-fix commit and refuses if that rev is not
the launcher this row is about.

## Not fixed here

- **The loaded LaunchAgent is stale, and the file was UNTRACKED until this
  commit.** `git ls-files com.kingfisher.bringup.plist` returned **0**: the
  LaunchAgent that starts this entire fleet every 600s, and whose missing
  `AbandonProcessGroup` key is this row's subject, **existed in no commit** —
  found while committing, exactly the shape H123 found in `commit-msg.hook` this
  morning, one file over. It is added here, with the key. The **loaded** copy in
  `~/Library/LaunchAgents` is outside the workspace (§10) and stays stale until a
  human runs three commands: `HUMAN_NEEDED.md`, said out loud rather than left as
  drift, which is H36's subject.
- **The live lanes are still pre-v11 generations**, in whatever group started
  them. They pick up v11 at their next relaunch; nothing needs restarting for
  that, and restarting them by hand to hurry it would be the A23 defect (the
  instrument perturbing what it measures) for no gain.
- **This is measured for the launchd path only.** A lane started from a session
  is in that session's process group and has the same exposure with a different
  killer; v11 covers both, but only the launchd side is reproduced here.
