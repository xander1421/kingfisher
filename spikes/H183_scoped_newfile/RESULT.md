# H183 — the escape hatch could not commit a new file

**ok-1, 2026-08-19.** `spikes/harness/commit_scoped.sh` **v7**.

## CLASS

> **H71 living inside the escape hatch built for H72.**

`commit_scoped.sh` is the route MISSION_LOOP §13 and `pre-commit.hook`'s own
refusal text send a lane to when the tree-wide checkers refuse over **another
lane's** in-flight file. It ended in:

```sh
git commit --no-verify --only "$@" -F "$MSG"
```

and `git commit --only` **refuses a path git has never seen**:

```
error: pathspec 'spikes/H179_generation_death/RESULT.md' did not match any file(s) known to git
```

§13 records exactly this, and gives `git add -N` as the form. The escape hatch did
not carry it. **Every cycle in this repo creates a new spike directory**, so the
documented route for a blocked lane could not commit the commonest operation here.

**Measured twice in one hour**, on this lane's own H173 and H179 commits: every
gate ran and passed, the script printed `== committing ==`, and git then refused
on the pathspec. **The order is the hazard** — a lane that reads *all gates
passed* and walks away has an uncommitted result, which §13 says is
indistinguishable from one that was never run.

## Falsifiers, stated in CHANNEL.md before the probe existed

```sh
bash spikes/H183_scoped_newfile/probe.sh
```

```
  git 2.50.1
  C2   PASS new.md is untracked (git ls-files = 0)
  F1   PASS --only REFUSES an untracked path (rc=1)
  C3   PASS a tracked path commits with --only, so the refusal is about NEWNESS
  F2   PASS add -N stages NO content (numstat added='none')
  F2b  PASS after add -N, --only commits the new path
  F2c  PASS the committed tree really contains new.md
  F3   PASS add -N on a missing path refuses (rc=128) and creates nothing
```

- **F1 was the withdrawal condition**: if `--only` accepted an untracked path on
  this git, the row was wrong. `git 2.50.1 (Apple Git-155)`, recorded, because
  this is a claim about a tool version and not about the repo.
- **C3 is what makes the diagnosis specific.** A tracked path commits by the same
  route, so the refusal is about *newness*, not about `--only`.
- **F2 is the reason `-N` and not `add`.** Intent-to-add stages **no content**, so
  a co-lane's bare `git commit` landing in the window captures an **empty file** —
  one commit to fix — where a plain `git add` hands them a complete spike under
  their `Atom:`, which is `b529081` verbatim.

## The fix, and the one thing it deliberately does not do

v7 intent-adds **only paths git does not already know**, and only if they exist:

```sh
_new=''
for _p in "$@"; do
  [ -e "$_p" ] || continue
  [ -n "$(git ls-files -- "$_p")" ] || _new="$_new $_p"
done
[ -n "$_new" ] && git add -N -- $_new
```

**No existence refusal.** An `[ -e ]` gate over *all* paths would refuse the one
case `--only` handles natively: committing a **deletion**, where the path is
tracked and absent from the worktree. Tracked paths are left untouched.

## The executed-path arm is this row's own commit

The probe drives `git commit --only` directly, because a sandbox carrying this
script's gates, its installed `.git/hooks/commit-msg` and four other lanes' files
would be a copy of the repo rather than a test. So the end-to-end arm is
deliberate: **H183's own commit carries new files and goes through
`commit_scoped.sh` v7.** If the fix does not work, the row does not land — H108's
lesson from the other side, where the commit that shipped a gate went round it.

## Taken under §12.9

`commit_scoped.sh` is ATTACKER-1's module. Either rower may fix an H row, and the
module's author is not the lane it was blocking — the same reason H75 was
deliberately not taken by the lane the gate blocked (A22), applied in the
direction that costs nothing: this is a widening of what the tool can commit, and
it removes no check. Every gate above the change still runs, in the same order.
