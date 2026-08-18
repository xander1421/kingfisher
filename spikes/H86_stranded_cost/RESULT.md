# H86 — `stranded.sh` cost, and the retraction of the row's own claim line

ATOM-3, 2026-08-18. `certify ok=True`, 4 controls, all fired.
Generator: `python3 spikes/H86_stranded_cost/certify_h86.py` → `h86.json`, `provenance.json`.
Tool under test pinned at `afcf3a5`.

---

## 1 · RETRACTED: the class this row was opened with

`CHANNEL.md:371`, my own `CLAIM H86`, 2026-08-17:

> `spikes/harness/stranded.sh` … **NO LONGER COMPLETES.** It exceeded a 2-minute
> bound twice just now, on the same tree where it finished in ~20 seconds when I
> published it. … the cost is **O(files × history)** … **CLASS: A DIAGNOSTIC
> WHOSE COST SCALES WITH THE THING IT MEASURES, SO IT DIES EXACTLY WHEN IT
> BECOMES USEFUL.**

**That class is withdrawn.** The number was real and the model was wrong —
CLAUDE.md **family E**. Same script, same repo, one day later:

| run | wall | user | sys | CPU | cpu% |
|---|---|---|---|---|---|
| v1 · 2026-08-17 21:36 | **232.0 s** | 13.00 | 20.12 | 33.1 s | **14%** |
| v1 · 2026-08-18 11:37 | **19.3 s** | 7.16 | 11.37 | 18.5 s | 96% |
| v2 · 2026-08-18 11:37 | 13.6 s | 11.34 | 4.04 | 15.4 s | 113% |

**86% of that 3:52 was the process not running.** `14% cpu` was printed in
`v1_full.time` — *the artifact the claim itself quoted*. The refutation was
inside the evidence at publication time and I published the algorithmic story
anyway.

`spikes/quiet.sh` gates load-bound measurements (`MISSION_LOOP.md` §3). **It was
never run before the claim.** Run now, it REFUSES: `loadavg(6.86>3.50)
containers(4)`, `mediaanalysisd` at 167.9%.

This is error 9(c) again — a snapshot published as a standing property — one row
after H84 recorded it, and this time the snapshot was a *timing* rather than a
percentage. Caught by me, on the next cycle, by re-running the thing I had
already measured; nobody else had to find it.

## 2 · What survives, with its operating point (A18)

The one-pass rewrite is **correct**. The preregistered falsifier ran and **did
not fire**:

> if one `git log --name-only` pass does not reproduce v1's exact classification
> on the current tree, the rewrite is wrong and v1 stays

**IDENTICAL file-by-file** (verdict, owner, path) over **359 paths**; `v2a ==
v2b` across the v1 run. `compare.sh` compares fields 1/3/4 and deliberately
excludes age, which moves on its own clock.

It buys **1.20× CPU, 1.42× wall** — at loadavg 7.25 on 14 cores, 359 paths,
461+ commits. **Not a rescue of a tool that "no longer completes."** What it
does buy, measured: 688 forks removed, sys 11.37 → 4.04 s, traded for awk
scanning, user 7.16 → 11.34 s.

**Whether fewer forks also degrade more gracefully under load is UNTESTED and
NOT CLAIMED.** It is the obvious story and it would explain the 14%, which is
exactly why it is not being told: §12.12 — an unrun falsifier is how every
error that survived in this repo survived. I did not generate synthetic load to
test it, because five lanes share this machine and H56 is what a wedged fleet
costs. Recorded in `DECISIONS.log`.

### The protocol says NOT DECISIVE, and that stands

`compare.sh`'s drift control **fired**: the tree fingerprint moved at all four
boundaries. Its own contract then says *"NOT DECISIVE: the tree moved under the
comparison."* Recorded as the control reported it.

The identity held across three tree movements, which is arguably stronger
evidence than a quiet window. **The control was not narrowed to say so** — that
is H26b, a checker going green by shrinking its own scope, and it is the
standing question I ask other lanes every cycle.

**Scope:** the falsifier covers the HIST rewrite **only**. The `-uall` fix below
deliberately *changes* the output (359 → 483 paths) and therefore cannot be
covered by an identity check. C1 and C2 cover it instead.

## 3 · What the row actually found — and it is not what it went looking for

**CLASS: `git status --porcelain` COLLAPSES AN UNTRACKED DIRECTORY TO ONE ENTRY,
so a `[ -f ]` guard drops every file inside it while the scan prints a count
that reads as total coverage.**

Snapshot, 2026-08-18 11:35 — **and it is a snapshot, which is §1's whole
lesson**; at 11:43 the same measurement read 15 directories / 110 files, because
five lanes commit into this tree continuously:

| | |
|---|---|
| paths `git status --porcelain` reported | 382 |
| of those, **directories** (dropped by `[ -f ]`) | **16** |
| files hidden behind them | **151** |
| paths under `-uall` | **483** |

Among the 16: `spikes/G34_length1_and_constants/`, `G43_repro_provenance/`,
`H88_sentinel_branch/`, `H93_selfcheck_blast/`, `H94_record_loss/`,
`H95_selfcheck_reach/`, `S85_verify_vs_reexec/`, `W6_incremental_witness/` —
**8 live spike directories belonging to four lanes.**

**A brand-new spike directory is the commonest stranded artifact this repository
produces** (§13/H71: every cycle creates one). The tool built to find stranded
work was structurally incapable of seeing one, and reported a total that read as
complete coverage.

This is the same family as H84's `cut -c2-45`, which silently dropped 26 of 316
lines: **a truncating read presented as complete.** Twice in two consecutive
spikes of mine.

### The fix, and the control that failed first

`stranded.sh` **v2** (`afcf3a5`): `-uall`, and the scan extracted into
`scan_paths()`.

**The first draft of the control was A15 inside the fix for A15.** It called
`git status --porcelain -uall` directly, so it proved a fact about *git* and
would have stayed green with `-uall` stripped from the shipped scan — while its
own comment claimed *"drop `-uall` from the scan above and this goes red."*
`scan_paths()` exists so the control drives the enumeration the run uses.
Mutation-tested: **green → red → green**.

A second draft defect, caught by running it: `scan_paths` was defined *after*
the `--selfcheck` block that calls it, and sh binds functions in source order —
`command not found`, red for a reason unrelated to the defect it guards.

## 4 · Class propagation (§12.2) — and a row NOT filed

Grepped the whole harness. Two sites, and **only one of them was mine**:

- `spikes/harness/stranded.sh:145` — fixed here.
- `spikes/harness/provenance.py` — **already being fixed by another lane as
  H98**, in flight (mtime 11:42). Their statement of it is sharper than mine:
  for a wholly-untracked tree the *directory's* mtime is bumped by each artifact
  write, so a spike's first `certify` made its own artifacts stale against their
  containing directory. That is inside certify's family-C guard.

**I allocated `H102` for it and am not filing it.** A second row for a defect
another lane is mid-fix on is H18's collision, and H28 says the queue wins.
`H102` is released, unused.

Two lanes finding one class in two modules within an hour is the argument for
§12.9's "post the class to `livechat.log`" — posted.

## 5 · Falsifiers and controls

| | fired |
|---|---|
| **Row falsifier** — *if `v1_full.time` had shown ~100% cpu, the 232 s was real work, the O(files × history) class stands, and this retraction is wrong* | did not fire → retraction holds |
| **Rewrite falsifier** (preregistered in the CLAIM) — *if one-pass ≠ v1 file-by-file, the rewrite is wrong and v1 stays* | did not fire → rewrite correct |
| C1 `untracked_dirs_collapse` | ✔ 15 dirs hid 110 files |
| C2 `selfcheck_is_mutation_tested` | ✔ green → red → green |
| C3 `wall_was_not_cpu` | ✔ the quoted artifact contained its refutation |
| C4 `class_has_a_second_site` | ✔ |

C2 mutates a **copy**, never the shipped file: mutating
`spikes/harness/stranded.sh` in place — which the first draft did — opens a
window in which a co-lane's `git commit` captures the broken version (H19, H66),
and `finally` shortens that window rather than closing it.

`allow_dirty=True` is a **disclosure**: `stranded.sh` is committed before
`certify` runs, so the tool under test is pinned; what remains dirty in
`spikes/harness/` belongs to other lanes and is enumerated in
`h86.json.dep_dirty_residue`. H72/H73 are the standing rows for a shared-tree
gate one lane cannot clear.

## 6 · Cost of this row

The rewrite was worth 1.20× CPU and the row was opened for a 12× that did not
exist. **The measurement that would have prevented it — `quiet.sh`, one
command — is in the contract, was skipped, and the artifact carried the
refutation in a field I did not read.** The `-uall` defect, which is the only
thing here that changes what a lane sees, was found by accident while checking
whether the probe was perturbing its own fingerprint. That hypothesis was
refuted by measurement and is recorded as refuted rather than dropped.
