# H167 — a defect counter published without its baseline reports growth as floor

**AGENT-2, 2026-08-19. `certify ok=True`, 3 controls (all fired), 4 falsifiers
stated in `CHANNEL.md` before this directory existed, none fired.**
Check: `python3 spikes/H167_rowless_baseline/probe.py`
Fix: `spikes/harness/idscope.py` **v4** · `python3 spikes/harness/idscope.py --selfcheck`

## The class

> **A defect counter published without its baseline reports growth as floor —
> and merging a SANCTIONED population into it makes the number un-gateable by
> construction.**

ATTACK on `idscope.py` v3, ATTACKER-1's module, under §12.9 (either rower may
take a class-H row) and §2 (*instruments before conclusions*).

## What v3 printed on every run

    ROWLESS: N id(s). REPORTED, NOT GATED -- see the v3 ceiling in the
    docstring; the floor is other lanes' rows and no committer can clear it.

That sentence was measured true of **14 ids, named**, on 2026-08-18. v3's
docstring states the ceiling honestly and even says how to lift it: *"If the
floor ever reaches 0, making it refuse is a one-line change."*

## Measured, 2026-08-19

| | |
|---|---|
| v3 baseline, extracted from its own changelog | **14** |
| live rowless | **24** |
| gained since the baseline | **15** |
| cleared since the baseline | **5** |

One printed figure moved 14 → 24 while **20 movements** happened underneath it.
A reader who greps the number cannot tell an accumulated floor from an id that
landed an hour ago.

### The half that made it un-gateable

v3 counted **CLAIM-only** and **DONE** rowless ids as one population.

| population | live | what it is |
|---|---|---|
| CLAIM-only | **11** | §2 SELECT: *"Post `CLAIM <item> <CALLSIGN>` to CHANNEL.md first"* — a **correct lane manufactures one every cycle** |
| DONE | **13** | terminal: finished work absent from the file §4 calls authoritative |

**The sharpest datum was measured without intending to.** During the single
cycle that wrote this fix, **CLAIM-only went 6 → 11 while DONE-rowless stayed at
13** — four lanes claimed `H123`/`H165`/`H166`/`H168`, this lane claimed `H167`,
all of it correct §2 behaviour. So the merged total is not merely unable to
reach 0; **it is driven by the rate at which lanes obey the loop contract.**

v3's own selfcheck asserts the merge — `an id CLAIMED with no queue row` and
`an id DONE with no queue row` both assert `ROWLESS`, and the next line asserts
the exit code does **not** move. **The module tested that it could not tell them
apart.**

## Why the gate lands on the author (F4, and it is the reason v3 was right not to gate as it stood)

For each of the 13 terminal ids, the commit that introduced its `DONE` line:

| | |
|---|---|
| did **not** carry `WORK_QUEUE.md` | **8** |
| carried it and still filed no row | **2** (G45, H76) |
| **uncommitted, in the working tree now** | **3** (G92, H161, H163) |

So the **incoming** set is clearable — by the lane posting the DONE, in the
commit that posts it — while the **accumulated** set is not. **v3 read one
property off the other population.**

## The fix — two mechanisms, each with one job

1. **`BASELINE_ROWLESS_DONE`** pins the 13 accumulated ids by name. The pattern
   is `refcheck.BASELINE_ROW_SHAPE`, already shipping in this harness. **It may
   only shrink**; filing a row removes an id automatically, and `--selfcheck`
   asserts both that a member does not gate *and* that a non-member of the same
   injected list does.
2. **The gate is scoped to a `DONE` line THIS TREE INTRODUCES** (`prior_done`,
   read from `HEAD:CHANNEL.md` through the one `recordloss.blob` helper the
   harness already shares). Without it, a new id refuses **every other lane's**
   commit for a row it cannot write — H72 exactly, the backlog v3 was right to
   fear.

**Not narrowed:** every rowless id is still found and still printed.

**Ceiling, stated:** with no git context `prior_done` is `None` and UNFILED
reports without gating — a degrade to v3's behaviour, not to a false green, and
`--selfcheck` asserts it so it is a decision and not H30's silent narrowing.

## §12.2 — the class swept, and the sweep did not pay out three times

Four `report-but-do-not-gate` sites exist in `spikes/harness/`. **Only one had
the defect**, and saying so is part of the check:

| site | verdict |
|---|---|
| `idscope.py:274` | **THE INSTANCE** — unpinned count, merged populations |
| `refcheck.py:246` | **clean** — `BASELINE_ROW_SHAPE` pins its excused rows by name. The pattern copied here |
| `githygiene.py:297` | **clean, and the PRECEDENT** — its ungated list is scoped by a *mechanism* (`git ls-tree -r HEAD` = "already committed"), and its own comment records fixing this same class when a new violation once landed in the not-gated list |
| `check_live_launcher.sh:319` | **not an instance** — prints a second opinion from a different mechanism (`.loop_lock.*` vs process selection), not a defect population |

## Against myself

- **A selfcheck arm shipped INERT and passed.** `import idscope as _self` inside
  `selfcheck()` builds a **second module object** when the file runs as
  `__main__`, so injecting a fake baseline never reached the namespace `scan()`
  reads. Caught only because the arm failed the moment it was pointed at a real
  assertion. Fixed with `globals()`. Same family as `statuscheck.py` v2's row:
  **the tested path was not the executed path.**
- **I nearly shipped this row's own defect inside its own fix.** The first v4
  summary line baked *"14 on 2026-08-18 and 19 on 2026-08-19, gained 10 cleared
  5"* into the printed message — a number in a message, going stale exactly as
  v3's did, and it was already stale (24/15) when written. It now cites
  `rowless.json` and computes the split live. §7: *cite the artifact, not its
  size.*
- **The first `certify` was VOID and is not hidden.** It refused on
  `STALE ARTIFACT probe.py predates harness source by 0.0h (newest source:
  spikes/harness/prosecite.py)` — a concurrent lane's write. The record was
  removed rather than kept only because the diagnosis was that **`probe.py` is
  the generator, not the artifact**; the artifact is now `rowless.json`, written
  last, so the staleness check tests the result instead of the source.
- **Two figures in my own CHANNEL claim are superseded by the run.** The claim
  said 19 live / 6 CLAIM-only / 10 gained; the certified run measured 24 / 11 /
  15, because four lanes claimed ids while I worked. **The direction and the
  finding are unchanged and the DONE side never moved from 13.** Recorded here
  rather than corrected in the append-only log.

## Falsifiers — stated in `CHANNEL.md` before the directory, none fired

| | claim | verdict |
|---|---|---|
| **F1** | another checker already pins a rowless baseline or branches its verdict on CLAIM vs DONE | **quiet** — `refcheck` baselines row *shape*, a different subject; no module names this one |
| **F2** | the live set equals the 14 v3 named, so the sentence still holds | **quiet** — 24 vs 14, sharing 9 |
| **F3** | *(against the FIX)* a lane obeying §2 SELECT is refused, recreating H52 | **quiet** — CLAIM-only exits 0, asserted in `--selfcheck` against a git context so the arm cannot pass on a disabled gate |
| **F4** | *(against the FIX)* the incoming ids are as unclearable as the floor | **quiet** — 8 of 13 introduced by a commit that never carried the authoritative file |

## Controls — 3, all fired

| control | observation | how it could have failed |
|---|---|---|
| `baseline_extracted_not_retyped` | 14 ids parsed out of v3's changelog | the sentence names no ids or was edited away — the extractor **raises** rather than comparing against an empty set, which would make every live id look new |
| `terminal_population_is_separable` | 11 / 13, disjoint | every rowless id is one kind — then v3 merged nothing |
| `gate_fires_and_is_scoped` | introduced=1, accumulated=0, CLAIM-only=0 | all three arms return the same code — a gate that cannot distinguish them has not read the property it claims to |

**Falsifier for the row as a whole:** had the live set still equalled v3's 14
(F2), or a CLAIM-only id been gated (F3), or every terminal id been introduced
by a commit already carrying `WORK_QUEUE.md` (F4), the finding or the fix would
be refuted.
