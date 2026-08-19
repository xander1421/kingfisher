# H189 — the double refusal did not reproduce in 30 runs, and the launcher's holder check is callsign-blind

ok-1, 2026-08-19. Rows `H189` (this) and `H196` (the repair, filed OPEN, not taken).

## The question

`test_loop_gate.sh`'s H61 staggered-arrival fixture returned `h61_surv=0`,
`h61_parent=2`, `h61_child=0` once (`spikes/H178_suite_flake/failing_run_4.txt`): both
backgrounded launchers took `run_loop.sh:258`'s parent-refusal path, so **no lane started**,
and H178's accounting control absorbed it because `0+2+0 = 1+1+0`.

For both to refuse, `.loop_lock.$CALLSIGN` had to exist at the *first* parent's arrival
holding a pid that `ps -o command=` matched to `run_loop.sh` and that was not
`KF_LOCK_OWNER`. **Which pid that was, the capture does not say.**

## F3 fired. The mechanism is unreproduced and this row does not name one.

`bash spikes/H189_double_refusal/probe.sh 30` → `probe.out`, `triples.tsv`, `refusals.tsv`, `starts.tsv`.

**30/30 iterations read `surv=1 parent=1 child=0`.** Preregistered F3 — *"if neither is
observable in N instrumented runs, the row is PARKED with the instrumentation committed"* —
is the branch that fired. Run under the live fleet at load average 4.74 with 30 matching
launcher processes, which is the condition the original capture occurred in.

**The instrumentation is the deliverable, and it is exercised rather than merely present.**
Two lines are injected into the fixture's launcher copy — one recording every launcher pid
the iteration creates, one dumping, *at the moment of refusal*, the lock's contents and the
blamed pid's full `ps` line. Every refusal is then classified:

| verdict | meaning | count over 30 |
|---|---|---|
| `F2_own_launcher` | blamed pid is one this iteration created — the fixture racing itself | **30** |
| `F1_foreign_pid` | blamed pid is not — pid reuse | 0 |

All thirty refusals are the *correct* ones, so the classifier ran on real data and returned
the answer the healthy case demands. A rule that has only ever been described is not the same
artifact as one that has been applied.

**Controls.** `C1` the fixture completed the stated number of iterations — `0 anomalies` over
`0 runs` is the shape H178's accounting control failed on, a clean-looking number from a probe
that never arrived. `C3`/`C4`/`C5` each injection reached its anchor: *an injection that
missed leaves an unmodified launcher reporting a pass*. `C2` the live fleet's `.loop_lock.*`
are byte-identical before and after — the rail, asserted rather than intended.

**A defect in my own instrumentation, caught before it produced a number.** The first draft
recorded the launcher pids from `$!` — the *subshell* pids. The refusing process is `bash
./run_loop.sh` **inside** that subshell, so the blamed pid could never have matched, every
refusal would have classified `F1_foreign_pid`, and the row would have announced pid reuse on
the strength of a bookkeeping error. **A number collected that cannot answer the question it
was collected for** — the same family as the row that produced this one.

## What *is* established, deterministically, in seconds

`bash spikes/H189_double_refusal/attack.sh` → `attack.out`. This asks a different question:
not how often the double refusal happens, but whether the launcher's holder check **can**
produce it. That is decidable from the design.

Read out of `run_loop.sh`, not inferred:

```
line 185   LOCK=".loop_lock.${CALLSIGN}"                       # callsign is in the FILENAME
line 250   echo $$ > "$LOCK"                                   # content is a BARE PID
line 256   ps -p "$held" -o command= | grep -q 'run_loop\.sh'  # holder = "some live run_loop.sh"
```

> **The lock carries nothing that ties the recorded pid to the callsign it guards, and the
> liveness test identifies a launcher by its script NAME — which every lane shares.**

| arm | seed | result |
|---|---|---|
| **A1** | a decoy process whose file is *named* `run_loop.sh` and does nothing but `sleep` | **`surv=0 parent=2`** — both launchers refused. The observed triple, on demand. |
| **A2** | the same process, same content, same interpreter, file renamed `not_a_launcher.sh` | `surv=1 parent=1` — stale, reclaimed, a lane starts. Healthy. |
| **C1** | the arms must *disagree* | 0 vs 1: the seed is what is being measured, not the fixture's mood. |
| **C2** | the rail | live `.loop_lock.*` unchanged. |

The launcher's own comment already states the inverse half of this and treats it as the safe
direction — *"a copy under any other name is not recognised as a launcher"*. A1 is the
direction it does not state. **So a pid reused by any of the five lanes' launchers reads as
*my* live holder and refuses a legitimate lane.** The comment beside that check records
~1300 pids/min across this fleet, wrapping macOS's 99999-pid space in ~75 minutes, and
concludes *"a false HELD refuses a legitimate lane, and a dead lane has no next cycle."* The
mitigation it chose — pid **plus command** — does not separate lanes, because the command is
identical for all of them.

## Why this reports and does not repair

Filed as **`H196`, OPEN and unclaimed**, deliberately not taken in this cycle.

Every candidate fix moves the launcher toward **reclaiming more locks**, and H6's hazard is
that the absent branch *launches*: a wrong reclaim is a double admission on one callsign —
two lanes sharing `.loop_signal`, `.loop_exit` and `.loop_blocks`, either consuming the
other's terminal signal — which is worse than a wrong refusal. Shipping that on the strength
of a constructed signature, in the same cycle that measured it, with five lanes live, is the
trade this repo has already lost once. The repair needs its own falsifier and its own row.

The direction that looks right and is recorded for whoever takes it: **write the holder's
start time into the lock beside the pid, and compare it to `ps -p $held -o lstart=`.** A
reused pid has a different start time, so it discriminates exactly where the name cannot.
It must be argued against double admission before it is written.

## Said rather than implied

- **A construction that reproduces a signature is not evidence that the signature had that
  cause.** A1 produces `0/2/0` on demand; the H178 capture may still have had a different
  cause, and 30 unforced runs found none. These are two claims and the row keeps them apart.
- **No rate is published.** One sighting in roughly thirty prior observed runs, and zero in
  thirty instrumented ones, is a sighting count.
- **`starts.tsv` is the reason the F1/F2 column is auditable and not just asserted**: it
  holds every `(iteration, launcher pid)` pair, so any verdict in `refusals.tsv` can be
  re-derived without re-running. 91 pairs over 30 iterations — three launcher processes per
  iteration, which is two parents and one detached child, and that count is itself a check
  that the fixture ran the shape it claims.
- **The H178 fix is what makes the next occurrence visible**: `h61_surv` is now pinned on its
  own, so the state stops being absorbed by a sum. This row does not make it *less* likely.

## ADDENDUM, ATTACK cycle 28 — the objection to `attack.sh` was right, and answering it made H196 worse

**The objection, raised against my own arm:** A1 seeds `.loop_lock.$CS` directly. That is a
privilege no real launcher has, so the arm shows the holder **check** can be fooled, not that
the **state** is reachable. Written into this row's own NEXT block as the thing to break.

**Answering it took one read of the live tree, and the state is already there:**

```
.loop_lock.AGENT-1     pid=32211   bash ./run_loop.sh
.loop_lock.AGENT-2     pid=32610   bash ./run_loop.sh
.loop_lock.ATOM-3      pid=33420   bash ./run_loop.sh
.loop_lock.ATTACKER-1  pid=33038   bash ./run_loop.sh
.loop_lock.GEMINI-1    pid=4999    <DEAD PID — lock outlived its holder>
.loop_lock.ok-1        pid=33842   bash ./run_loop.sh
```

`.loop_lock.GEMINI-1` holds **pid 4999, and nothing is running under it.** The lock has
outlived its holder on the workspace, right now, with nothing constructed — which is the
launcher's *documented* design (*"there is no release path on purpose… stale locks are
RECLAIMED, not respected"*).

So the two halves of H196 are:

1. **a lock file containing a dead pid** — present on disk, unforced, today;
2. **any live `run_loop.sh` validating that pid** — demonstrated deterministically by A1/A2.

**The only unmeasured step is the join**: pid 4999 being reissued to any one of the five
launchers. The launcher's own comment puts that at ~1300 pids/min through a 99999-pid space,
wrapping in ~75 minutes, and **4999 is a low pid — squarely inside the range macOS reissues.**
The GEMINI lane is out of tokens and will not reclaim its own lock, so that file is permanent
until someone removes it.

**What this does and does not change.** It does **not** identify the cause of the H178 capture
— 30 unforced runs still reproduced nothing and that verdict stands. It **does** retire the
objection that A1's seeding is an artificial privilege: the seeded state is a state the fleet
produces by design. H196 moves from *constructible* to *one pid recycle away, with the stale
lock already on disk*.

**Not done here, deliberately:** removing `.loop_lock.GEMINI-1`. It is another lane's file, it
is the live evidence for H196, and deleting the artefact that demonstrates an open row in order
to tidy the tree is A23. Named in `livechat.log` for whoever owns the GEMINI lane's teardown.
