# proposed/mork-license — NOT APPLIED

The two-file change that would settle `trueagi-io/MORK`'s licence, prepared so
that opening the PR is mechanical. **Nothing here has been applied to
`elders/MORK`, and nothing has been pushed anywhere.** The operator filed the
ask on issue #2; publishing is theirs, not this workspace's (mission §11).

## Context
Adam-Vandervorst answered issue #2 on 2025-05-21: *"Yes! It's now under MIT."*
The file never landed. At `main` HEAD `0653b50` and on `server` `2d6730b` there
is no LICENSE/COPYING/NOTICE, no `license` key in any of the 10 manifests, and
`gh api repos/trueagi-io/MORK --jq .license` returns `null`.

## The change
1. `LICENSE` — `LICENSE.proposed` here is a verbatim copy of **PathMap's own**
   MIT file (`Copyright (c) 2025 Adam Vandervorst`), same author, so the text
   and the holder line are already his. **The year and holder are the
   maintainer's call, not ours** — if MORK's copyright should read differently
   (TrueAGI, a range of years, multiple holders), that is for him to set and
   the PR should follow whatever he says.
2. `Cargo.toml` — add `license = "MIT"` to `[workspace.package]`, which
   propagates to all 10 member crates. Diff in `Cargo.toml.patch`.

Optionally also `kernel/Cargo.toml` etc. if any member overrides the workspace
inheritance — checked: none do, so the one line is sufficient.

## Do not pre-empt the gate
Until a licence file exists **at HEAD**, MORK stays UNKNOWN = all rights
reserved in `analysis/LICENSE_LEDGER.md`. A maintainer comment, a merged PR in
someone's fork, or this directory existing are all insufficient. The check is:

    gh api repos/trueagi-io/MORK --jq .license
    git -C elders/MORK fetch --depth 1 origin main && \
      git -C elders/MORK show origin/main:LICENSE | head -3

## What flips when it lands
Mechanical, so nobody has to re-derive it:

| file | change |
|---|---|
| `analysis/LICENSE_LEDGER.md` | MORK row UNKNOWN ⛔ → MIT ✅ PORT; add Adam Vandervorst / MORK to the NOTICE block |
| `analysis/GAP_MATRIX.md` row 7 | exact engine: SPEC → **PORT** (hyperon stays the phone engine on the S45 library-surface ground, which the licence does not change) |
| `analysis/GAP_MATRIX.md` row 8 | fuel metering: MORK's step counter becomes liftable, not just describable |
| `analysis/GAP_MATRIX.md` row 11 | rung-1 verification: the differential harness becomes PORT instead of clean-room SPEC |
| `out/PORT_PLAN.md` M0.1 | close it |
| `out/PORT_PLAN.md` M4.3 | ARM NEON kernels for `linalg` unblock — currently "blocked on MORK having no licence" |
| `reports/REPORT_MORK.md` §1 | licence line, and drop the "read for ideas, copy nothing" framing |
| `out/STATE_OF_THE_UNION.md` | the Layer-2 paragraph on MORK |

****[2026-08-16] The paragraph below is now wrong on its first point.** S55 linked `mork = { path = "kernel" }` and ran `Space::new` / `add_all_sexpr` / `metta_calculus` / `dump_all_sexpr` in-process on an Android phone. MORK **does** have a library surface. The rest of the paragraph stands.

Two things do NOT flip.** MORK still has no library surface, so it cannot be
the phone's per-query stage-2 engine (S45: 5.66 ms (corrected; the 13 ms figure timed a SIGABRT tombstone, see `out/RETRACTIONS.md`) of `exec()` per invocation
against ~0.5 ms of work). And it is still nightly-only with a hardcoded
`/dev/shm` on `main`. The licence was never the only blocker, just the
absolute one.
