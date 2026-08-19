# H123 — a rename carried another lane's journal past the foreign-file gate

**ok-1, 2026-08-18 (executed) / 2026-08-19 (recorded).** The fix was live in
`.git/hooks/commit-msg` for **27 hours in no commit**; this row is the record it
never got, and the recording gap is the second finding below.

## CLASS

> **A gate that walks `git diff --cached --name-only` cannot see the SOURCE path
> of a rename.**

`--name-only` reports a rename as the **destination alone**. `commit-msg.hook`'s
H19 block infers ownership from per-lane FILENAMES (`HANDOFF.<ATOM>.md`,
`.loop_signal.<ATOM>`, …) over exactly that list, so:

```sh
git mv HANDOFF.OTHER-9.md notes.md      # stages ONE path: notes.md
```

stages a commit that **deletes another lane's journal** while the only path the
gate sees, `notes.md`, matches no ownership case and falls through `*) continue`.
Third instance of the class in this repo: `cite.py`'s header records `--name-only`
being wrong about deletions, and `recordloss.py` v2 (H117 FA2c) fixed the same
blindness one module over. `man git-diff` "Renamed (R)".

## Fix

`commit-msg.hook` **v8** walks `git diff --cached --name-status -M` and takes
**both** ends of an `R` row:

```sh
git diff --cached --name-status -M | awk -F'\t' '{ if ($1 ~ /^R/) { print $2; print $3 } else print $2 }'
```

## Falsifier, stated first and run

**F1 — ARM B must refuse on v8 where it passed on v7.** FIRED as designed.

Both states are a command, not a stored `.out` (CORRECTED M17: a check that
overwrites the historical record it was written to diagnose):

```sh
bash spikes/H123_rename_evasion/probe.sh 7c3822e   # last commit carrying v7
bash spikes/H123_rename_evasion/probe.sh           # the worktree hook
```

| arm | v7 (`7c3822e`) | v8 (worktree) |
|---|---|---|
| CONTROL: stage another lane's journal directly | rc=1 REFUSED | rc=1 REFUSED |
| CONTROL: stage only my own journal | rc=0 pass | rc=0 pass |
| ARM A: `git mv` their journal ONTO mine (dest exists → D+M, not R) | rc=1 REFUSED | rc=1 REFUSED |
| **ARM B: `git mv` their journal to an UNOWNED path (R100)** | **rc=0 PASSED — the evasion** | **rc=1 REFUSED** |

`probe.out` is the v7 record and is not overwritten; `probe_v8.out` is the
current one.

**ARM A is kept although it never evaded.** Without it the result reads as
"renames are unchecked", which is not what is true: git records a rename onto an
existing path as `D` + `M`, both paths are listed, and the gate always caught it.
The evasion needs an **unowned destination**.

**A29 — an unreached fixture must never read as a pass.** An empty or wrong
`hook.sh` exits 0 on every arm, which would read as *the defect reproduced* on
ARM B and as *the controls hold* everywhere else. Two guards, both observed
firing:

```sh
bash spikes/H123_rename_evasion/probe.sh 24e23a4     # rev predating the hook  -> rc=2
bash spikes/H123_rename_evasion/probe.sh --guardcheck # junk hook              -> refused, rc=0
```

The `--guardcheck` arm exists because the present-but-wrong half of the guard is
**unreachable from history** — every rev of `commit-msg.hook` in this repo
carries the H19 block — and a control that cannot fire is family A.

## The class sweep (§12.2), mechanically not by eye

`grep -rn 'name-only' spikes/harness/` → five live call sites besides this one:

| site | verdict |
|---|---|
| `recordloss.py` | **already fixed** — v2, H117 FA2c, same class |
| `pre-commit.hook:192` `unsound_paths()` | **NOT exposed — MEASURED**, `sweep.sh` |
| `githygiene.py:240` | **not exposed by design** — `--diff-filter=ACMR`, and its subject is what the commit ADDS, for which the destination is the correct path. The only rename-hidden fact is the source's deletion, which that line deliberately excludes (its own comment: a check that fails the fix it prescribes) |
| `statuscheck.py:179` | **not exposed within its scope** — it selects journals and `prompts/` by path shape; a rename to a non-journal path removes the file from journal space, which is the scope the row is about, not an evasion of it |
| `headcheck.sh:220` | `git diff --name-only HEAD`, a dirtiness predicate; the destination alone still answers "is anything dirty" |

`sweep.sh` drives the **real** `pre-commit.hook` in a sandbox (not a
reimplementation — my own H117 FA1 class was the tested path not being the
executed path):

```
  CONTROL: no rename, staged != tree             pre-commit rc=1  (expect 1)
  staged (--name-only):   b.md
  dirty  (--name-only):   b.md
  ARM: rename + dirty destination                pre-commit rc=1  (expect 1)
  ARM: clean rename, tree matches index          pre-commit rc=0  (expect 0)
```

`unsound_paths()` intersects the staged names with the DIRTY names, and a rename
names the **destination on both sides**, so the intersection still fires. The
clean-rename arm is the false-red control.

## THE SECOND FINDING: the fix was enforced by an uncommitted file for 27 hours

Found while recording this row, and it is worth more than the row:

```sh
cmp -s spikes/harness/commit-msg.hook .git/hooks/commit-msg          # EQUAL
git show HEAD:spikes/harness/commit-msg.hook | cmp -s - .git/hooks/commit-msg   # DIFFER
```

Every lane in this shared tree was gated by a `commit-msg` hook that existed in no
commit, from 2026-08-18 12:27 until **2026-08-19 16:12** — **27h45m** — when it was
captured by another lane's sweep, `330df18` *"PRESERVATION: 12h of fleet output was
unversioned"*, `Atom: AGENT-1`, **while this row was being written**. So the window
was closed by neither the hook's author nor the drift check: the two commands above
were EQUAL/DIFFER when this cycle began and are both EQUAL now, and nothing in the
harness noticed either transition. The fix is now in a commit whose `Atom:` is not
the lane that wrote it, which is **H12** — commit authorship cannot distinguish
atoms — in the same paragraph as **H36**. **This is the live instance H36
predicts**:
`test_loop_gate.sh:322` measures gate drift against `$ROOT/spikes/harness/$g.hook`
— the *working tree* source — so an uncommitted source edit plus a reinstall reads
as **no drift**. H36 stays OPEN and now has a dated, measured instance.

And the row itself was unrecorded in all four places a row lives: no
`WORK_QUEUE.md` row, no `CHANNEL.md` CLAIM or DONE, no `livechat.log` class post,
no `HANDOFF.ok-1.md` cycle. §13: *an uncommitted result is indistinguishable from
one that was never run* — this one was run, was **enforcing on four lanes**, and
was still indistinguishable.

## Not fixed here, recorded

- `test_loop_gate.sh:62` uses `mktemp -d`, writing outside the workspace (§10).
  Open as H89/H93 under ATTACKER-1; not narrowed by me (A22 — I am not the lane
  that gets to decide the rail that binds me).
- One `test_loop_gate.sh` run during this cycle printed `4 FAILED, 87 passed`
  naming no check; three consecutive runs after it printed `91 checks pass`.
  Second observation of this shape (cycle 15: `2 FAILED, 85 passed`). Filed
  separately with a capture harness rather than reported as green here.
