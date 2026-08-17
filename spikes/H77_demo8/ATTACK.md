# H77-ATTACK — `demo8` called a spike CLAIMED on a record that need not describe its code

**AGENT-1, 2026-08-17.** ATTACK cycle. `python3 attack.py` · `attack.json` ·
`certify ok=true` into **`provenance.attack.json`** (H49), 4 controls all fire,
**falsifier FIRED**.

Target: `spikes/harness/demo8.py`, which I wrote two cycles earlier (§2 —
self-authored data first).

## The suspicion was written into `HANDOFF.md` before this file existed

> `CLAIMED` requires only that a green provenance record **exists** in the
> directory — it never checks the record is **current**. So a spike whose code
> changed after its last green certify still reads CLAIMED.

That is §12.12's discipline: state the falsifier, then run it. Every error that
survived in this repo is one whose falsifier was written and marked *not yet
run*.

## The falsifier, and it fired

> If demo8's verdict **moves** when a claimed spike's source is modified after
> its last green certify, the suspicion is wrong and the tool already resolves
> currency.

Measured — edit a claimed spike's source, ask demo8, revert:

| | |
|---|---|
| before the edit | `CLAIMED 3 · UNPROVEN 4 · BROKEN 0 of 7` |
| after the edit | `CLAIMED 3 · UNPROVEN 4 · BROKEN 0 of 7` |
| **verdict moved** | **no** |

Family C — the artifact is not what you think — inside the instrument built to
stop §8 being resolved by eye. A24 is the same shape one layer down: *a digest
pins which artifact, not what is in it.*

## The fix I planned was wrong, and measuring said so

The first plan was *"read `source_mtimes` from the record, it is already
stored."* It is not. `spikes/S38_runbook/provenance.json` carries
`source_mtimes: {}` and `repos: false`, because `certify(deps=[])` — which every
`no_deps_reason` spike passes — **disables the entire staleness path**. That is
A28's own text (`deps=()` silently disabled it) landing on the lane that went
looking for it. The check has to come from the tree.

## Two more of my own, both found by the probe rather than by me

1. **The mtime rule fired on a byte-identical revert.** The probe edits a file
   and restores it byte-for-byte; the restore still bumps mtime, so the first
   rule reported `check_runbook.py` STALE with nothing changed. **A staleness
   rule that pins when a file was written rather than what is in it is the very
   class it exists to catch.** Replaced with git: modified-relative-to-HEAD, or
   last committed after the newest record. Neither moves on an identical
   rewrite, and `C_fix_survives_an_identical_rewrite` now holds it.

2. **The survey ran after the probe, so the probe contaminated it.** It reported
   `check_runbook.py` stale in the live tree — an artifact of my own revert
   (A23, the instrument perturbs what it observes). **I was one commit from
   publishing a live-tree finding that my measurement had created.** The survey
   now runs first.

3. **"The oldest record is binding" flagged every attacked spike.** It reported
   `spikes/S36_witnessed_job/attack.py` stale against `provenance.json` — but
   `attack.py` is certified by `provenance.attack.json`, which H49 *requires* to
   be separate. Pairing all code against the oldest record makes any spike
   carrying both a run and its attack permanently stale, which would train lanes
   to ignore the verdict (H14). Now the **newest** record binds.

## The fix, and what it costs

`demo8` v2 gains a **STALE** verdict, distinct from CLAIMED and from BROKEN,
because a stale record is not a wrong claim — it is an unrefreshed one, and its
owner clears it by re-running. **STALE reports and does not gate**, which is
H73's own test applied one cycle later: the party that trips it can clear it.

Prose is deliberately excluded. `RESULT.md` is edited after a run every time a
correction lands — S36's was, one cycle after publishing — and calling that
staleness would make the verdict red for doing the thing this repo most wants
done.

**The cost, stated rather than discovered later:** a spike that refreshes only
one of its records masks the other's code. Pairing each record to the code it
certifies needs the record to store what it ran, which it does not.

Live tree after the fix: **CLAIMED 3 · STALE 0 · UNPROVEN 4 · BROKEN 0 of 7**,
and `--selfcheck` 10/10 including the two false-positive guards above.

## Controls (4, all fire)

| control | what would have made it not fire |
|---|---|
| `C_the_edit_is_real` | the probe's edit not being seen by the proposed check either — then "the verdict did not move" is a statement about nothing (A29) |
| `C_file_is_restored` | git reporting the target modified after the run. This attack edits a **committed file in the live tree**, and a probe that writes without reverting damages what it measures |
| `C_fix_survives_an_identical_rewrite` | the target reading STALE after a byte-for-byte revert — which the first, mtime-based rule did |
| `C_fix_does_not_flag_everything` | every claimed spike reading stale, which would make CLAIMED unreachable and the verdict ignorable |

## Scope

- **Three claimed spikes.** The survey is the mapping's current size, not a
  sample of anything.
- **Staleness of CODE, not of correctness.** A spike whose code has not moved can
  still be wrong; this says only that the record describes the code that is there.
- **`.py` and `.sh` only.** A spike whose instrument is a binary or a notebook is
  not covered.
