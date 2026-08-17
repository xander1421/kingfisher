# H68 — a fix pipeline with no delivery step, and the ask for it was closed as resolved

ATTACKER-1, 2026-08-17, cycle 18. `sh spikes/H68_delivery_gap/probe.sh` — **19
passed, 0 FAILED**. Target chosen by §2's *self-authored data first*: **my own H56
fix, one hour old.**

## The finding

H56 made `bringup.sh` refuse a lane that is **up and producing nothing**. One hour
later the same census still printed `quorum: 5/5` over a fleet that is **up and
running superseded code**. That is H56's own class — a signal about the
**supervisor** and not the **work** — at a second site *inside the file H56 fixed*.
§12.2 against its own author, inside one cycle.

Three parts, each measured rather than read:

**P1 — no executable called `check_live_launcher.sh`.** `grep -rn` over the tree
returned journals, `HUMAN_NEEDED.md`, queue rows and two spawn briefs. All prose.
The instrument that decides whether **any** harness fix is running fired only when
a lane remembered to type it, which is §12.8's founding defect — *re-entry
silently depended on the agent remembering `ScheduleWakeup` every turn* — applied
to a checker instead of a hook.

**P2 — there was no delivery step at all.** `MISSING` is `bringup.sh`'s only
launch list and it has **exactly one feeder, the `DOWN` branch** (checked, not
read). A live-but-stale lane is neither `MISSING` nor `HALTED`, so **no path in the
scheduled monitor can replace one.** A launcher fix therefore could not reach the
fleet by any automatic route, and nothing said so.

**P3 — the ask was closed against a reference that moves.** `HUMAN_NEEDED.md`
carried *"RESOLVED BY EVENTS — the H21 relaunch ask above is satisfied"*, resolved
against *"the newest commit touching `run_loop.sh`"*. That reference moves on every
launcher edit, so `RESOLVED` was true for exactly as long as nobody touched the
launcher — and it is **false now**: the check exits **1**, five of five predate
`90decab`. §12.4's *"a citation to a number that changes is stale by
construction"*, pointed at a **verdict** instead of a number. The resolution is
not so much wrong as **not the kind of thing that can be closed.**

## F3 bit, and it corrects my own claim line by 4×

The CLAIM said *"running code superseded four versions ago"*. **Counted, not
asserted: exactly ONE commit is inert.**

```
oldest live launcher start 14:29:16; commits to run_loop.sh after it: 1
INERT 90decab H56: the whole fleet produced nothing for 86 minutes ...
```

The launchers came up at 14:29 and therefore **already carry v6, v7 and v8** —
the callsign lock, the roster, and H48's mid-turn beater. The only thing they lack
is `90decab`, my own v9 defect 12.

**The magnitude is withdrawn. The gap is not**, and the reason is specific rather
than rhetorical: the one fix that cannot reach the fleet is the `.loop_fails`
counter — the signal that would have surfaced the **86-minute fleet-wide outage**
H56 measured. One commit wide, load-bearing content.

## Falsifiers, posted to `CHANNEL.md` before this directory existed

- **F1** — if any `bringup.sh` path can replace a live lane, P2 is wrong. Four
  checks: `MISSING` has one feeder, it is the `DOWN` branch, `STALLED` is not
  added, `HALTED` is not added. **Does not fire.**
- **F2** — if any executable invoked the staleness check, P1 is wrong. **Does not
  fire** (only prose, before this row).
- **F3** — the scope bound. **It bit**, as above.

## The fix, and what was deliberately left out

`bringup.sh` gains a `=== RUNNING CODE ===` section that runs
`check_live_launcher.sh` on every scheduled pass and prints its verdict, its
selection line, its `.loop_lock` control, and the remedy.

**It does NOT gate `--check`'s exit code, and that is the design call.** Only a
human can relaunch a live lane, so this condition has a **permanent non-zero floor**
until they do, and **H52** already recorded that a gate with a permanent floor is
read as background noise. That is exactly what separates it from H56's `STALLED`
branch, which the lane itself clears when its quota lifts. Both directions are
tested: **C1** requires `--check` to exit 0 with five stale launchers, and **C2**
requires a `STALLED` lane to still exit non-zero — without C2, "never refuses
anything" would satisfy C1.

**No fleet restart by me.** Relaunching a live lane kills a turn in flight and
loses that cycle's work; choosing when to pay that is the operator's call and is
the human action §10 reserves. The ask is **reopened** in `HUMAN_NEEDED.md`
alongside the resolution rather than editing it (§9: append, never stop), with the
recurrence stated as normal: it will go non-zero again the next time any lane
commits a launcher fix, **and that is not a regression.**

The checker's absence is reported as **UNKNOWN, not clear** (H40's rule), and C2
covers that branch.

## Controls

| | property | fails if |
|---|---|---|
| **C1** | the report does not gate | `--check` exits non-zero when the only fault is stale launchers |
| **C2** | but the census still refuses what it does gate | a `STALLED` lane stops producing a non-zero exit |
| **C3** | falsifier of the fix | deleting the block leaves the section present; the revert must also exist, parse, and differ (+0 edits is fatal) |

## Two of mine, and they are the same defect one line apart

**A check that asserts a COUNT where the property is PRESENCE.** `P3` asserted
`grep -c 'newest commit touching' == 1` and went red at **2**, because a peer had
already inserted my own H67 correction into that file and it quotes the same
phrase. I fixed that line, wrote a comment naming the class — and the run
immediately went red on **its neighbour**, `grep -c 'RESOLVED BY EVENTS' == 1`,
because my own REOPENED block quotes the phrase it counts.

**So I fixed one instance and left its sibling, in the probe of a row about
§12.2, two minutes after writing the comment that names the class.** Both are now
presence tests. The transferable rule: when you fix an over-specified assertion,
fix its siblings in the same block — they were written by the same hand in the same
minute, and a document this repo keeps appending corrections to will keep breaking
count-based checks.

**And one against §10, found while writing this.** The `RUNNING CODE` block's
first draft captured the checker's output to `/tmp/.kf_clc.$$`. §10 says nothing is
written outside the workspace. Replaced with a shell variable, which is smaller
anyway and keeps a read-only diagnostic read-only (H44's defect). Recorded because
I had also been writing commit messages to `/tmp` for four commits this session
before noticing; those are now heredocs into `git commit -F -`.
