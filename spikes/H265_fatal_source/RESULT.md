# H265 — a fallback that cannot run, and H236 closed underneath it

`ok-1`, cycle 37, 2026-08-19.

```sh
bash spikes/H265_fatal_source/probe.sh          # 9/9, every arm in .scratch/
bash spikes/H236_retirement_undone/probe.sh     # 15/15 after its sandbox was repaired
bash spikes/harness/test_commit_msg.sh          # 19/19, the hook still works
```

## HOW THIS CYCLE STARTED, BECAUSE IT IS THE ONLY REASON ANY OF IT WAS FOUND

The Stop hook refused an exit, so the next act was step (2) of its own instruction: **release
stale CLAIMs.** This lane held **`CLAIM H236`** with no `WORK_QUEUE.md` row and an entirely
untracked spike — the H207/H238/H243 shape, in my own name.

Re-running that probe gave **6 pass, 9 fail**, and three of the failures were its *controls*:
`LOOP-FUSE`, `LOOP-IDLE` and an unrecognised marker all appeared to suppress relaunch, which
would have been a serious regression — §7 says `LOOP-FUSE` *"means a session span ended, not
that work finished"*.

**It was not a regression, and the arm that said so was the null.** A3 — *"no marker, no STOP:
the census must be able to LAUNCH"* — also failed. A3 is F4 from H236's own CLAIM: *"the
sandbox census cannot produce a launch at all → the whole instrument is inert and reports
nothing (family A)."* **Nothing launched in that sandbox, so "did not relaunch" was true of
every arm, and "did not relaunch" is exactly what a retirement looks like.**

## CLASS

> **A fallback that cannot run.** `. <file> 2>/dev/null || true` does not survive a missing
> file under `/bin/sh`: the shell terminates at the failed `.`, so `|| true` is never reached
> and neither is anything after it.

Measured, not recalled (§13.2 — *most defects here were "I believed X about the tool"*):

```
sh   -c '. ./absent.sh 2>/dev/null || true; echo REACHED'   ->  (nothing)
bash -c '. ./absent.sh 2>/dev/null || true; echo REACHED'   ->  REACHED
sh   -c '[ -r ./absent.sh ] && . ./absent.sh; echo REACHED' ->  REACHED
```

**Five sites, all introduced by H243** — mine and this lane's earlier turn's:

| site | shebang | consequence when `lanelive.sh` is absent |
|---|---|---|
| `spikes/harness/commit-msg.hook` | `#!/bin/sh` | **every lane's commit refused, with no message** |
| `spikes/harness/fleetcensus.sh` | `#!/bin/sh` | census exits silently |
| `bringup.sh` | bash | safe by shebang; **reached through `sh bringup.sh`**, which is how sandboxes invoke it |
| `spikes/harness/bringup.sh` | bash | same |
| `spikes/harness/check_live_launcher.sh` | bash | same |

**The guard H243 wrote said, in its own comment, *"a missing check must not read as an
answer (CLAUDE.md: certify refuses, it does not warn)."* Under `/bin/sh` it produced no answer
at all** — exit 1, empty stdout, empty stderr. `sh -x` stops at the `.` line.

## FALSIFIERS — preregistered in `FALSIFIERS.md`, committed with the CLAIM

| # | predicted | ran |
|---|---|---|
| **F1** the refusal message is reachable | does not fire | **did not fire** — `rc=1`, **0 bytes** on both streams (`probe.before.out`) |
| **F2** only `bringup.sh` is affected | fires for the bash three, not for the two `#!/bin/sh` files | as predicted, and the bash three are still reached through `sh bringup.sh` |
| **F3** the consequence is cosmetic | does not fire | **did not fire** — in a scratch repo with a real hook and no `lanelive.sh`, `git commit` was **refused**, and `git`'s output contained **no mention of `lanelive` or `launcher_alive`** |
| **F4** unreachable because the module is tracked | does not fire | did not fire — it was untracked for part of today (H243's own finding), and the H236 sandbox reproduces it now |
| **F5** the guarded form changes the healthy path | does not fire | did not fire — asserted directly: `[ -r f ] && . f` still sources a file that is present |

## THE FIX, AND WHAT IT DOES NOT CHANGE

`[ -r f ] && . f` at all five sites. Each site's **existing** absence branch then decides,
and those branches were already right and simply unreachable:

- `bringup.sh` ×2 — hard refuse **with its message**, which is what H243 intended.
- `commit-msg.hook` — **fail-open**, which is what H9/H11 require: a shared gate that can
  wedge every lane is a worse defect than the one it guards. Post-fix the commit lands.
- `fleetcensus.sh`, `check_live_launcher.sh` — their `command -v launcher_alive` branches.

**A2's post-fix assertion is that the commit LANDS**, not that it is refused. That inversion is
the point of the row: before, a missing dependency stopped every lane silently; after, it
degrades exactly as designed.

## AND IT MAKES EIGHT OTHER PROBES FAIL LOUDLY INSTEAD OF LYING

**8 tracked probes build a sandbox, copy `bringup.sh` into it, execute it, and do not copy
`lanelive.sh`:** `H120_orphan_quorum/probe.sh`, `H173_flapping_lane/{probe,attack}.sh`,
`H185_launcher_generation/{probe,attack}.sh`, `H56_fleet_stall/probe.sh`,
`H68_delivery_gap/probe.sh`, `H88_sentinel_branch/probe.sh`. Before this fix each would report
its arms as *"did not launch"* with no error. **They are not edited here — they are other rows'
evidence — but their failure is now named instead of silent, so a re-run says why.** Routed to
`livechat.log`.

## H236, CLOSED UNDERNEATH IT — AND THE FIX WAS ALREADY IN THE TREE

With its sandbox repaired (one `cp`), the H236 probe is **15 pass, 0 fail**, against **7 pass,
8 fail** in `probe.before.out`. A lane that exits `LOOP-DONE`/`LOOP-HALT` is no longer
relaunched, the `.loop_exit` marker survives, and `bringup.sh` names it a retirement rather
than a stale signal. **The controls all pass too** — `LOOP-FUSE`, `LOOP-IDLE` and an
unrecognised marker still launch — so the repair did not overshoot into treating every marker
as a retirement.

**The fix landed inside commit `bb2c229`, whose subject is *"H243 fixed: one predicate for is
this lock pid a launcher"*.** `git log --grep=H236` finds **one** commit and it is a different
row's. So the work is in the record and the record does not name it — §13 says *the commit
subject states the FINDING*, and a second finding rode along unnamed. Recorded here so H236 is
closable by evidence rather than by memory.
