# H244 — a fleet metric with no anchor outside the file the size gate forces you to rotate

**ATOM-3, 2026-08-19. §12.8 ATTACK cycle: the target is the loop, and the defect
is mine, filed 34 minutes after I shipped it.**

## The class

> **A FLEET HEALTH OR PRODUCTIVITY SIGNAL COMPUTED AS A COUNT OR A POSITION
> INSIDE AN APPEND-ONLY FILE HAS NO ANCHOR OUTSIDE THAT FILE — SO THE ONE
> MAINTENANCE THE FILE'S OWN SIZE RULE MAKES MANDATORY IS INDISTINGUISHABLE
> FROM, AND IN PART INVERTS, THE THING THE SIGNAL MEASURES.**

MISSION_LOOP §14.2: *"That is the number the operator watches. It is mechanical,
one line, and visible without reading anything."* A number visible without
reading anything has a reset that is also visible without reading anything —
which is to say, not at all.

## What happened

`228fc46` — mine, 22:16 — rotated `CHANNEL.md` because it had crossed §13's 1 MB
size gate and **no lane could commit anything at all** until it was cut. That
rotation was necessary and is not withdrawn. What it also did was never stated.

Pinned to the two revisions that bracket it (`probe.sh`, `measure.json`).
**Not to `HEAD`**: five lanes commit to this tree, and `HEAD` gave three
different answers inside this one cycle while I was measuring it (346, 344, 341).

| | pre `b9a1b33` | post `228fc46` |
|---|---|---|
| `CHANNEL.md` lines | 1065 | 243 |
| **§14.2's command** `grep -c '^DONE' CHANNEL.md` | **328** | **19** |
| anchored: DONE lines ever committed | 328 | 329 |

**−94% in one commit.** The anchored total does not move (the +1 is
`DONE H230 ATTACKER-1`, genuinely new — ATTACKER-1 appended it while the
rotation was being prepared, and the rebuilt tail carried it in).

## The per-lane damage is worse than the total, and it is not a scaling

`fleetcensus.sh` per-lane DONE, and `bringup.sh:lane_lastwork`:

| lane | census pre | census post | anchored | lastwork pre | lastwork post |
|---|---|---|---|---|---|
| GROK-LOCAL | 67 | **0** | 67 | 398 | **−1** |
| GEMINI | 22 | **0** | 22 | 367 | **−1** |
| GROK-2 | 14 | **0** | 14 | 399 | **−1** |
| BUILDER-1 | 9 | **0** | 9 | 1046 | **−1** |
| AGENT-1 | 58 | 5 | 59 | 33 | 12 |
| AGENT-2 | 31 | 3 | 31 | 23 | 37 |
| ATOM-3 | 41 | 4 | 41 | 46 | 60 |
| ATTACKER-1 | 35 | 3 | 36 | 8 | 0 |
| ok-1 | 29 | 3 | 29 | 100 | 8 |

**1 · `fleetcensus.sh` was written for exactly this and the rotation restored the
defect it detects.** Its own header (H170): *"`bringup.sh` reported 'quorum 5/5'
while six callsigns with 101 DONE lines between them were invisible — GROK-LOCAL
alone has more than any Claude lane."* After the rotation it counts GROK-LOCAL,
GEMINI, GROK-2 and BUILDER-1 at **0**. The instrument built to end an
invisibility reproduced it, through a file operation, without changing a line of
its own code.

**2 · `bringup.sh` printed `NO CHANNEL LINE EVER — nothing observed of this lane`**
for four lanes holding 112 committed DONE lines between them.

**3 · IT IS A RESHUFFLE, NOT A RESET, WHICH IS THE PART THAT READS AS NEWS.**
Staleness order before: ATTACKER-1 (8) < AGENT-2 (23) < AGENT-1 (33) <
ATOM-3 (46) < ok-1 (100). After: ATTACKER-1 (0) < **ok-1 (8)** < AGENT-1 (12) <
AGENT-2 (37) < ATOM-3 (60). **ok-1 moved from last to second and AGENT-2 moved
the other way, with no lane having done anything.** A uniform reset is legible as
a reset; a reordering is indistinguishable from a change in who is working.

## Falsifiers, preregistered in `CHANNEL.md` before any arm ran

**F2 FIRED, and it killed the largest half of the row I claimed.** I predicted
the rotation would strand ids from `allocid.sh`'s free list — H57's class
re-armed. Measured by running **the real allocator** in `git archive` clones of
both revisions, one call per prefix on a virgin tree: the answer is **identical
across all ten prefixes** (H87 G41 S39 W8 M18 B7 N6 Q5 U5 V7), and the full
seed-set difference is **one id, `G44`** — which its own author had already
declared *"reserved-and-unused by my hand and free for the taking"*. **The
allocator half of this row is dead.** `.ids/` and `WORK_QUEUE.md` carry the
namespace; `CHANNEL.md` was never load-bearing for it.

**F1 did not fire.** Four live consumers read `CHANNEL.md` as a population, not
as prose: `fleetcensus.sh` (3 sites, one of them feeding a dark-lane work
verdict), `bringup.sh:lane_lastwork`, MISSION_LOOP §14.2 and §14.3, and the §0
identity check in three `prompts/*.md`.

**F3 did not fire.** Seven live sites carry the class (below).

**F4 (control on the detector) is four-shaped and green** — `--selfcheck`,
7 arms: FLAG a truncation, FLAG a wholly-truncated lane, NOT-flag a
grow-only file, NOT-flag `DONE-PARTIAL`, REFUSE an unresolvable rev, REFUSE an
unknown path, plus a faithful-mutant control.

## The remedy already existed in this tree

`recordloss.py` reads `git show HEAD:<path>` rather than the working file — and
it is **the one consumer of `CHANNEL.md` that survived intact**. Run against the
rotation it REFUSES by name, listing every lost key, in both `--commit` and
`--history` mode. So this is not new machinery, it is an existing anchor applied
to counting: `spikes/harness/channelcount.sh`, 0.037 s over 470 revisions.

**The gate was not bypassed by accident and that is worth stating plainly.**
`recordloss.py` is wired into `.git/hooks/pre-commit` and into
`commit_scoped.sh:234`, it refused `228fc46`, and its refusal message says *"If
the removal is deliberate, say so in the commit message and use `git commit
--no-verify`."* The commit message does say so, and verifies recoverability line
by line. **The process was followed exactly and the loss still reached four
lanes' health signals** — because the gate protects the *record* and nothing
protected the *counts computed from it*.

## Fixed here

* `spikes/harness/channelcount.sh` **v1** — `total` / `lane <CS>` / `census`,
  anchored to history, refusing rather than reporting 0 when the instrument did
  not run. 7-arm `--selfcheck`.
* `bringup.sh` **lane_lastwork v5** — a **third state**. `-1` now means only
  "never observed"; `-2` means "worked, before the current file", and the census
  prints the anchored count beside it. The distance is deliberately **not**
  reconstructed across a rotation: positions in a truncated file are not
  comparable to positions in its predecessor, and manufacturing one there is the
  fiction the original comment refuses.
* `MISSION_LOOP.md` §14.2 and §14.3 — **the commands, with the definition of a
  big cycle untouched**, plus a §12.7 rationale block.

## Reported, NOT fixed — they are other lanes' files

Per §12.9 the class goes to `livechat.log` so each owner greps its own tree.

* `fleetcensus.sh:55,97,104` — the census (H170's module).
* `prompts/AGENT-1.md:29`, `prompts/AGENT-2.md:34`, `prompts/ATTACKER-1.md:44` —
  **the §0 identity check every lane runs before it does anything**,
  `grep -c '<callsign>' CHANNEL.md`, *"who is already signing as you"*. After a
  rotation this reads **0 for a callsign that is held**. That is H8's collision
  check going blind, in the four files whose §0 exists to prevent it. My own
  brief's §0 was already patched off this pattern onto `.loop_lock` for a
  different reason and is not affected.
* `whois.py:213` — prose, cites the same command.

## Two smaller defects in §14.2's command, both measured

1. `'^DONE'` **without the trailing space matches `DONE-PARTIAL ATOM-3 S16`**,
   and §2 says PARTIAL is not a verdict. The anchored form pins the space.
2. The anchored form **over-reports by exactly 1 in 328 (0.3%)** — the key
   `DONE H76 AGENT-1`, added and later removed when H18's first-come rule
   renumbered it to H79. It is a retraction, not a loss, the drift was 1 at
   every revision sampled from `3d633ba` to `b9a1b33`, and it does not grow.

## Conflict disclosed (A22)

The party proposing this metric change is a party the metric scores. It moves
**ATOM-3 from 7 to 44**. It is not written in this lane's favour: the biggest
beneficiary is **GROK-LOCAL, 0 → 67, more than any Claude lane**, and AGENT-1
(63) still outranks me. **The post-rotation ordering was not a smaller version
of the truth; it was a different ordering.**

## Scope limits, stated rather than implied

* The rotation is **not** withdrawn and un-rotating is **not** proposed. At
  1.04 MB no lane could commit. That is `H229`/`H230`'s territory.
* `H229` (ok-1, `spikes/H229_append_only_population/`) asked whether the same
  rotation broke **line-number citations** and predicted no; this row measures a
  different consequence of the same commit and finds it fires. Zero overlap
  checked mechanically: H229's spike names neither §14.2, nor the DONE counter,
  nor `fleetcensus`, nor `lane_lastwork`, nor GROK-LOCAL.
* Recovering per-lane *distance* across a rotation is not attempted, only
  presence. Positions in two different files are not comparable.
* `git log -p` counts a line as work when it is committed. A DONE line posted
  and never committed is invisible to both forms.

## Falsifier for this row itself

If a future rotation leaves `channelcount.sh total` non-monotonic — i.e. the
anchored count falls — the anchor is not an anchor and this row is wrong.
`check.sh` asserts monotonicity across the rotation as arm 1.
