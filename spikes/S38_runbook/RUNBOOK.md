# M1-DEMO run-book — what a stranger can reproduce from a clean checkout

**AGENT-1, 2026-08-17.** MISSION_LOOP §8's last item. Checked by
`python3 check_runbook.py`, which **refuses** — see *How this page is checked*.

> **Read this first.** This is not a demo script and it does not claim M1-DEMO
> passes. `python3 spikes/harness/demo8.py` is the authority on that and today it
> says **CLAIMED 2 · UNPROVEN 5 · BROKEN 0** of seven. This page tells a stranger
> which parts they can run themselves, what each one should print, and — the part
> a run-book usually omits — **which parts they cannot run and why.**

## 0 · What you need

Python 3 and git. Nothing else, for everything in §2 and §3. No network, no
keys, no wallets, no devices. The corpus and key files are committed.

```sh
git clone <this repo> kingfisher && cd kingfisher   # CHECK: paths-only, a clone URL is not resolvable from inside the repo
sh spikes/harness/install_hooks.sh                  # CHECK: paths-only, it writes into .git/hooks of the live tree
```

**Do not skip the second line.** `.git/hooks/` is untracked and cannot be
tracked, so the two enforcing gates do not arrive by pulling. A fresh clone has
no commit gate at all.

## 1 · Is the tree honest right now?

These are the checks the project runs on itself. Run them before believing
anything else on this page.

```sh
python3 spikes/harness/refcheck.py          # CHECK: paths-only, its verdict is FLEET STATE and flips minute to minute (H73)
python3 spikes/harness/journalcheck.py      # CHECK: run
python3 spikes/harness/githygiene.py        # CHECK: run
python3 spikes/harness/demo8.py             # CHECK: run
```

`refcheck.py` is deliberately **not** expected to exit 0. It judges the shared
worktree, so any lane's unfinished edit turns it red — measured in
`spikes/H73_gate_scope/`, where that condition held this lane's finished work for
twenty minutes. A stranger with a clean checkout and no co-lanes should see it
green; **if you see it red on a clean checkout, that is a finding, not your
mistake.**

## 2 · The verification chain, which is the part that actually works

This is the asset: a result you can check without re-running it. Each command
prints its own numbers and ends with `certify ok=True`.

```sh
python3 spikes/S27_verify_floor/verify_floor.py       # CHECK: run
python3 spikes/S36_witnessed_job/witnessed_job.py     # CHECK: run
python3 spikes/S36_witnessed_job/attack.py            # CHECK: run
```

What you should see, in order:

1. **`verify_floor.py`** — the completeness verifier's floor. `slack +0.000%` on
   all three key sets: it hashes exactly what recomputing the root requires, so
   the 2–4× constant is the commitment format and not the implementation.
2. **`witnessed_job.py`** — witnessed verification driven as a job, 37 jobs.
   The row that matters is `two_non_independent_liars`: **replication 0/37,
   witnessed 37/37.** Two workers running the same wrong computation agree with
   each other, so byte-compare reads consensus; one verifier holding the root
   rejects every one.
3. **`attack.py`** — and then the attack on the line above, which you should run
   *because* step 2 looks like good news. The committed verifier **accepts 37/37**
   deeper-prefix replays, omitting **96.7%** of the answers, and the liar forges
   nothing. Step 2's claim holds only with the q-bound verifier in `attack.py`.

**Run all three.** Stopping after step 2 is how you would leave with a wrong
belief, and this project's most useful documents are the ones that killed a
result it had already published (`out/RETRACTIONS.md`).

## 3 · The harness, checked against itself

```sh
python3 spikes/harness/githygiene.py --selfcheck    # CHECK: run
python3 spikes/harness/demo8.py --selfcheck         # CHECK: run
python3 spikes/H73_gate_scope/probe.py              # CHECK: run
sh spikes/H73_gate_scope/reconcile_h72.sh           # CHECK: run
```

`H73_gate_scope/probe.py` builds a throwaway repo inside the workspace, runs this
repo's real commit gate against it, and removes it. It is the reason the claim
"one lane's unfinished edit freezes every other lane's commits" is a measurement
and not a complaint.

## 4 · What you CANNOT run, and why

A run-book that lists only what works is a sales page. These are §8 items that
`demo8.py` reports UNPROVEN, with the reason each one is out of your reach:

| §8 item | why you cannot reproduce it |
|---|---|
| 3 physical devices + 1 coordinator, real transport | the recorded chain ran **3 hosts and 1 phone**, not 3 devices. You would need the hardware, and the phone leg needs the device charging, idle and on an unmetered network — the gate **refuses**, it does not warn |
| Real corpus (ConceptNet slice) via content-addressed shards | 64 CIDs exist and are committed; that the corpus *is* the named slice is asserted by no spike I can cite you |
| Jobs admitted under the versioned ban surface, build-enforced | `spikes/harness/admission.py` is recorded **REFUTED as a gate** and kept as a linter, so "build-enforced" is not established |
| Quorum-3 with stake-weighted seat draw | the recorded run is **quorum-4**, and `specs/D3_economics.md` deliberately publishes no stake floor, so the draw does not exist to be run |

`spikes/M1_8_quorum3/` holds the recorded run and its `RESULT.md`. **Do not
re-run it from this page**: at the time of writing it carries 256 modified files
from another lane's live run, and a stranger re-running it would be measuring
that lane's work rather than a committed artifact.

## 5 · If something fails

- **A commit is refused over a path you did not touch.** Expected, and not your
  fault: the gate judges the shared worktree. Use
  `sh spikes/harness/commit_scoped.sh <msgfile> <path>...`, which runs *more*
  checks than `--no-verify` and scopes only the tree-wide verdict.
- **`git commit --only` says `did not match any file(s) known to git`.** The path
  is untracked. `git add -N <your paths>` first — §13 carries the reason it is
  that and not plain `git add`.
- **A spike refuses with `DIRTY TREE`.** That is `certify` working. It means a
  dependency has uncommitted changes and the numbers would describe code that
  exists in no commit. Do not pass `allow_dirty`; find out whose edit it is.

## How this page is checked

`python3 check_runbook.py` extracts **every** command from the fenced blocks
above and refuses unless each one is either

- **executed**, and exits 0 (`# CHECK: run`), or
- **explicitly excused** with a stated reason (`# CHECK: paths-only <why>`), in
  which case every path it names must still exist.

**A command that is neither is a refusal**, which is what stops this page from
decaying into prose that mentions files nobody can run. The falsifier stated
before it was written: *if the checker passes while a listed command cannot
actually be run, it is testing spelling rather than followability.*

**Two gaps in that, stated rather than left for a reader to trip over:**

1. **Only fenced ` ```sh ` blocks are checked.** §5's commands are inline, in
   prose, because they are conditional remedies rather than steps — so they are
   **not** executed or path-checked by `check_runbook.py`. Their paths were
   resolved by hand at the time of writing: `spikes/harness/commit_scoped.sh` is
   tracked in git, so a fresh clone has it.
2. **The commands run in THIS tree, not in a clean checkout.** A command
   depending on state this workspace happens to hold would pass here and fail for
   you. A clean-clone harness would close that and **is not built** — that is the
   honest scope, not a plan being implied.
