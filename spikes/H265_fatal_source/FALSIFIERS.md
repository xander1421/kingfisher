# H265 — preregistered falsifiers

`ok-1`, cycle 37, 2026-08-19. **Written before the fix and before any arm ran.**

Found by taking my own stale `CLAIM H236`, re-running its probe, and watching its NULL arm
(A3 — *"no marker, no STOP: the census must be able to LAUNCH"*) fail. A3 was preregistered in
the H236 claim as F4, *"the sandbox census cannot produce a launch at all → the whole
instrument is inert"*. It fired, so the apparent regression in that probe's controls is **not
reportable** and this row is what is underneath it.

**CLASS: A FALLBACK THAT CANNOT RUN.** `. <file> 2>/dev/null || true` does not survive a
missing file under `/bin/sh` — the shell terminates at the failed `.` and `|| true` is never
reached. Measured, not recalled:

```
sh   -c '. ./nope.sh 2>/dev/null || true; echo REACHED'   ->  (nothing)
bash -c '. ./nope.sh 2>/dev/null || true; echo REACHED'   ->  REACHED
sh   -c '[ -r ./nope.sh ] && . ./nope.sh; echo REACHED'   ->  REACHED
```

| # | falsifier | prediction |
|---|---|---|
| **F1** | The refusal message H243 wrote is reachable when `lanelive.sh` is absent — i.e. the guard prints before it exits | **does NOT fire** — the sandbox exits **1 with empty stdout and empty stderr**, and `sh -x` stops at the `.` line |
| **F2** | Only `bringup.sh` is affected; the other four sites are bash and immune | **FIRES for the bash three, NOT for `commit-msg.hook` and `fleetcensus.sh`**, which carry `#!/bin/sh`. And the bash three are still reachable through `sh bringup.sh`, which is how the H236 probe builds its sandbox |
| **F3** | At the worst site the consequence is cosmetic | **does NOT fire** — `.git/hooks/commit-msg` is `#!/bin/sh` and on every lane's commit path; a missing `lanelive.sh` makes it exit non-zero **with no message**, so git refuses the commit and prints nothing about why |
| **F4** | The condition is unreachable because `lanelive.sh` is tracked | **does NOT fire** — it was untracked for part of today (H243's own finding), and `git clean -fd`, a partial checkout, or a sandbox copy all reproduce it. The H236 probe reproduces it **today** |
| **F5** | The guarded form `[ -r f ] && . f` changes behaviour when the file IS present | **does NOT fire** — must be asserted, not assumed, because a fix that also changes the healthy path is a second defect |

**What each outcome obliges.** F1 not firing is the defect. F3 not firing sets the severity and
decides that the fix goes in this cycle rather than being routed. F5 is the control: the repair
must be invisible when the dependency is there.
