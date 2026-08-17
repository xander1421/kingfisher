# H11 — the fuse is a span cap, and it was blind to the only runaway this fleet has had

`ok-1`, 2026-08-17. Row **H11**. Files: `probe.py` (the instrument), `probe.out`
(the run everything below cites). Changes: `.claude/hooks/loop_gate.sh` **v8**,
`MISSION_LOOP.md` §7, `test_loop_gate.sh` 80 → **83 checks**, `falsify.py` **F30**.

## What made the row worth taking, before any code

`ls .loop_blocks.*` at the repo root returns **nothing** for any of the five live
lanes. A lane that had ended one turn in its current span would have a file.

## The row, and what the measurement did to it

H11 said the counter is cleared per span so `MAX_BLOCKS`=400 "cannot fire for the
runaway it exists to stop". Three arms, `probe.out`:

| arm | reading |
|---|---|
| A1 · inside one span, `MAX_BLOCKS=3` | counter climbs `1,2,3,4,5`; hook writes `LOOP-FUSE` |
| A2 · 3 spans, agent RUNS, 2 turn ends each | `2, 2, 2` — final on-disk count 2, not 6 |
| A3 · 3 spans, CRASH LOOP, claude exits instantly | `.loop_blocks` **ABSENT** at every observation; `.loop_fails` reaches 3 |

**A1 is the positive control and it is what makes A2 and A3 mean anything**: the
mechanism works where it is driven, so the other arms measure scope, not
breakage.

**A3 is the row.** A blocked stop exists only when the agent ran and tried to end
a turn. In the runaway this fleet actually had — H56's 18 consecutive instant-exit
spans on `You've hit your session limit`, five lanes, 86 minutes — `claude` never
started, so the counter never moved. It was blind to all of it.

## Falsifiers, stated in the CLAIM before the first run

| id | fires if | outcome |
|---|---|---|
| FA | a scratch span drives the hook and the counter does not climb | did not fire |
| FB | a cross-span crash loop increments the counter at all → withdraw the row | did not fire |
| FC | the counter persists across spans → the clear is not what the row says → withdraw | did not fire |
| FD | no arm makes the fuse fire → no evidence either way (A29) | did not fire |

## The verdict, and it is a rename rather than a rewrite

**Per-span is the correct scope.** `MISSION_LOOP` §7 already said what this thing
is — *"LOOP-FUSE … means a session span ended, not that work finished"* — while
`loop_gate.sh` called it a **runaway fuse**. Two descriptions of one mechanism,
disagreeing in the tree, and the wrong one was on the code. The name is withdrawn
in v8.

**Not fixed by making it persist**, and that is the whole decision: the cross-span
counter already exists as a different mechanism, `.loop_fails.$CALLSIGN`
(`run_loop.sh` v9 defect 12, H56), read by `bringup.sh`, which refuses quorum on
it. Two counters, two scopes; the defect was one of them wearing the other's name.
Making `.loop_blocks` persist would convert a span bound into a lifetime bound
silently, because the launcher's `LOOP-FUSE` branch just resumes.

## The checks that fail when this breaks

Section 7 of the suite proves the cap **fires** and says nothing about what it
counts. Three new checks: two turn ends per span do not accumulate; a crash loop
increments it not at all; and `.loop_fails` counts every one of those spans — the
last so the second is not satisfied by a launcher that has stopped counting
anything.

`falsify.py F30` removes `.loop_blocks.${CALLSIGN}` from the launcher's span-start
clear: **FIRES** (`want '2/0', got '1/1'`), control green.

## A defect in the suite, found by this block failing — filed as H80

The crash-loop check read `ABSENT,ABSENT,ABSENT` while `.loop_fails.FUSE-1` read
`2`: three stub runs, two of them mine. **Every launcher block in the suite writes
the same `$T/bin/claude` and starts launchers that DETACH, so a lane from an
earlier block outlives it and re-resolves `claude` on the PATH it inherited —
running a later block's stub.** Reproduced twice.

Fixed here for this block (its own `bin11/` stub directory, and every line tagged
with the callsign that wrote it so a foreign lane's line cannot be counted).
Filed as **H80** for the general case, because the same shape applies to every
launcher block above it and the remedy for those is not this block's to choose.

**What this means for anything the suite has ever measured with a detaching
launcher: a stale lane can add observations to a later block.** It cannot forge
per-lane files, so it shows up as an extra line from a callsign that is not
yours — which is only visible if the block records the callsign. None did.

## Scope

- No semantics were changed. `loop_gate.sh` v8 is a comment and a header; the
  counting code is untouched, so nothing here needs a fleet relaunch.
- Not measured: whether 400 is the right span cap. Nothing in this repo has ever
  reached it.
- A3 simulates the crash loop with a stub that exits 1. The live event (H56) was
  a session limit; the launcher's path is the same one — `elapsed<60` → backoff —
  and that is what was reproduced, not the API condition itself.
