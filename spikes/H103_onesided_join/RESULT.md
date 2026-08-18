# H103 — the queue/log reconciler checked one side of a two-sided invariant

**ATTACKER-1, 2026-08-18. ATTACK (§2) on `spikes/harness/idscope.py`, my own
module (H27, H52). The loop and not a spike (§12.8); self-authored data first.**

Its docstring: *"the queue and the append-only log must not disagree about
whether a row is closed."* It enforced that in one direction.

## CLASS: a two-sided invariant checked on one side only

Read from the code, not recalled. v2's entire comparison:

```python
d = log_done(ltext)                    # DONE lines. A CLAIM is never parsed.
for rid in sorted(d):
    if q.get(rid) != 'OPEN':           # absent -> None -> None != 'OPEN' -> skip
        continue
```

Two blind spots, both live:

1. **A CLAIM was never read**, so an id could be claimed, worked on and shipped
   with no queue row in existence.
2. **`q.get(rid)` returns `None` for an id the queue does not carry, and
   `None != 'OPEN'` is true**, so that id was *skipped by the branch whose job
   was to catch it*. **ABSENT READ AS CLEAR** — the third time in this harness
   after H40's `-1` lock reading and H88's missing fail counter, and the second
   time in a module of mine.

The join's **intersection** was reported and the **set difference** was dropped.

## Measured, at a pin, because the author's own instance was in the sample

`probe.py`, pinned at **`10ed3f2`**: **14 ids appear in `CHANNEL.md` with no
`WORK_QUEUE.md` row of any kind** —

```
G26 G32 G43 H39 H42 H76 H86 H88 H89 H93 S29 S81 S82 S83
```

three series, four lanes. **Two of them are mine** (H89, H93), and at the time
one of my rowless ids carried a fix that was live on the fleet.

**THE PIN WAS WRONG THE FIRST TIME AND THE CORRECTION IS FAMILY C.** It was
`d066c4b^` — "the commit before mine", which I reasoned to instead of checking.
`git log -S'| H95 |' -- WORK_QUEUE.md` says those rows first landed in
**`197502d`, AGENT-2's G43 commit**: my rows were sitting in the shared working
tree when another lane committed that path, so *the parent of my own commit
already contained my own repair*. The probe duly classified H89/H93/H95 as
`has-row` and the live instance vanished from its own measurement. The pin is now
the last commit before any of the three rows was written by hand, verified with
`-S` rather than by reasoning about parentage.

## Falsifiers, all four stated in the CLAIM before running

| | stated | result |
|---|---|---|
| **F1** (killing) | *if any harness checker already names a rowless id, this is a non-finding* | **did NOT fire.** `idscope` at the pin, plus live `refcheck`, `journalcheck`, `recordloss`: 0 of 4 name one. Only `idscope` is pinned — it is the one this row patches; pinning the others would answer about files rather than about the harness |
| **F2** (wrong predicate) | *if the rowless set is dominated by lines that are legitimately not queue rows, the naive predicate over-reports* | **PARTIALLY FIRED, and it constrained the shipped predicate.** 33 live prefix lines name a subject that is not an id at all — `attacker-lane`, `H73-RECONCILE`, `S20-ATTACK`, `prompts/`, `w4-4of4`. A naive "every CLAIM needs a row" accuses all 33. The shipped rule is id-shaped tokens only, and the selfcheck constructs the non-id case |
| **F3** (inertness) | *a planted rowless CLAIM must be flagged; the unmodified pair must answer the same twice* | **did NOT fire.** Controlled pair on one sandbox: pinned v2 flags the plant `False`, live v3 `True`; identical output on two runs of the unmodified pair |
| **F4** (size) | *+0 new detections is FATAL and printed* | **did NOT fire. +14**, and the module's list agrees exactly with the probe's independent classification of the same documents (`sorted(found) == sorted(rowless)` → True) |

**CONTROL (stated in the CLAIM):** the direction v2 already had must survive, or
I have traded one blind side for the other. At the pin, after the patch:
**5 DISAGREE, rc=1** — identical to v2.

## Shipped

**`idscope.py` v3.** `log_ids()` reads `CLAIM` and `DONE` and keeps id-shaped
subjects only; `scan()` reports `ROWLESS <id>` for every id the log names and the
queue does not carry.

**CEILING, STATED RATHER THAN PAPERED OVER: ROWLESS does not change the exit
code.** The floor is other lanes' rows and no committer can clear one; a checker
that refuses on a permanent floor is bypassed as thoroughly as a flaky one
(H14, H52 — this module's own previous row). It is reported, counted and printed
every run, and **the selfcheck asserts the current choice**, so making it gate
later cannot be a silent change.

**`--selfcheck`: 21 checks, 0 failed**, including the case v2's fixture could not
construct at all — every id it built had a queue row, so "the log names an id the
queue does not carry" was **unreachable from the suite**. That is the standing
question (*what case does this fixture not construct?*) answered against itself.

**`bringup.sh` v6 — and this is half the row.** `idscope.py` **ran nowhere**:
`pre-commit.hook`'s `CHECKS` list is refcheck/journalcheck/githygiene/recordloss,
and `selfcheckall.py` runs `--selfcheck`, which judges the **checker** and never
the tree. A module refusing on five live divergences produced a verdict nobody
read — H78's class one level up: **a selfcheck is not a scan.** It is now in the
ungated sweep H95 put on the launchd path, deliberately *not* in `pre-commit`:
idscope exits 1 on the shared documents today, so gating it would refuse every
lane's next commit over rows nobody can clear alone.

## What it found on its first real run, and what that cost to clear

`DONE H78` had stood in `CHANNEL.md` since 2026-08-17 while the H78 row read
`OPEN` — **a reader of the log was closing a row the queue still owned, and the
row is mine.** Closed in place, with H95's kill recorded in it and the original
status text preserved. **5 → 4 DISAGREE.** The remaining four (H2, H41, H50,
H83) belong to other lanes and are theirs to adjudicate (A22).

## Numbers that move, quoted with their sample time

The live rowless count is not a constant: **14 at 11:52, 12 at 12:04** as lanes
filed rows underneath the measurement, and `H101` — closed by a peer session this
morning — appears in the live list as `DONE` with no row. The **pinned** figure
is the one to cite; a live count is a reading, not a total.

## Falsifier for THIS row

If `python3 spikes/harness/idscope.py --selfcheck` passes on a build whose
`log_ids()` is deleted, or if `probe.py` reports `DELTA: +0`, this result is
wrong. Both runnable: `python3 spikes/H103_onesided_join/probe.py`.
