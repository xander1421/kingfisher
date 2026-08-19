#!/usr/bin/env bash
# H123 — can a RENAME carry another lane's journal past the H19 foreign-file gate?
#
# `commit-msg.hook`'s H19 block infers ownership from per-lane FILENAMES over
# `git diff --cached --name-only`, and that command reports a rename as the
# DESTINATION path only. So the source — another lane's file — may never be
# named in the set the gate walks. Same class as H117 FA2c, one gate over.
#
# Throwaway repo under the workspace (§10). Three arms, the first two are the
# controls that make the third mean anything.
#
# usage: bash spikes/H123_rename_evasion/probe.sh            # worktree hook (v8+)
#        bash spikes/H123_rename_evasion/probe.sh 7c3822e    # the hook as of that rev
#
# BOTH STATES ARE A COMMAND, not a stored .out. `probe.out` is the v7 record and
# is never overwritten (CORRECTED M17: a certify that overwrites the historical
# record it was written to diagnose). 7c3822e is the last commit carrying the v7
# H19 block -- `git show 7c3822e:spikes/harness/commit-msg.hook | grep -c
# name-status` is 0, which is the defect.
set -u
REV="${1:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
T="$ROOT/spikes/H123_rename_evasion/.repo"
rm -rf "$T"; mkdir -p "$T"
cd "$T"
git init -q .; git config user.email t@t; git config user.name t
# An empty or wrong hook.sh EXITS 0 on every arm, which reads as "the defect
# reproduced" for arm B and as "the controls hold" for the rest. A29: an
# unreached fixture must never read as a pass.
validate_hook() {
  grep -q "committing another lane's files" hook.sh \
    || { echo "REFUSING: hook.sh (rev='${REV:-worktree}') carries no H19 block"; exit 2; }
}
# The missing-file half of that guard is observable from history (`probe.sh
# 24e23a4` exits 2, git show refusing the path). The present-but-wrong half is
# NOT: every rev of this file in this history carries the H19 block, so a
# control that cannot fire is made to fire here rather than asserted in prose.
if [ "$REV" = "--guardcheck" ]; then
  printf 'echo not-a-hook\n' > hook.sh
  ( validate_hook ); rc=$?
  cd "$ROOT"; rm -rf "$T"
  [ "$rc" = 2 ] && { echo "guardcheck: a hook with no H19 block is refused (rc=2)"; exit 0; }
  echo "GUARDCHECK FAILED: a junk hook was accepted (rc=$rc)"; exit 1
fi
if [ -n "$REV" ]; then
  git -C "$ROOT" show "$REV:spikes/harness/commit-msg.hook" > hook.sh || exit 2
else
  cp "$ROOT/spikes/harness/commit-msg.hook" hook.sh
fi
validate_hook
chmod +x hook.sh
cp "$ROOT/spikes/harness/recordloss.py" .
printf '# other lane\n\n## Cycle 1 — theirs\n' > HANDOFF.OTHER-9.md
printf '# my lane\n\n## Cycle 1 — mine\n' > HANDOFF.MINE-1.md
git add HANDOFF.OTHER-9.md HANDOFF.MINE-1.md
git commit -q -m base
msg() { printf 'subject line\n\nAtom: MINE-1\nClaude-Session: x\nReviewed-By: unreviewed\n' > msg; }
msg

arm() {  # $1 label, $2 expected-hook-rc
  out=$(./hook.sh msg 2>&1); rc=$?
  rl=$(python3 recordloss.py 2>&1); rlrc=$?
  printf '  %-52s commit-msg rc=%s  recordloss rc=%s\n' "$1" "$rc" "$rlrc"
  [ "$rc" = "$2" ] || printf '        (expected commit-msg rc=%s)\n' "$2"
  printf '%s\n' "$out" | grep -E 'REFUSED|foreign' | head -2 | sed 's/^/        /'
  git reset -q
}

# CONTROL 1 — plainly staging another lane's journal must REFUSE (the gate works).
git add HANDOFF.OTHER-9.md 2>/dev/null; echo x >> HANDOFF.OTHER-9.md; git add HANDOFF.OTHER-9.md
arm "CONTROL: staging another lane's journal directly" 1
git checkout -q -- HANDOFF.OTHER-9.md

# CONTROL 2 — staging only my own journal must PASS.
echo y >> HANDOFF.MINE-1.md; git add HANDOFF.MINE-1.md
arm "CONTROL: staging only my own journal" 0
git checkout -q -- HANDOFF.MINE-1.md; git reset -q

# ARM A — rename their journal ONTO mine. Git records this as D + M, not a
# rename, because the destination already existed: both paths are listed and the
# gate sees theirs. Kept because it is the arm I ran first and it FAILED to
# evade; without it the successful arm below looks like "renames are unchecked",
# which is not what is true.
git mv -f HANDOFF.OTHER-9.md HANDOFF.MINE-1.md
echo "  staged (--name-only):   $(git diff --cached --name-only | tr '\n' ' ')"
echo "  staged (--name-status): $(git diff --cached --name-status -M | tr '\n' ' ' | tr '\t' ' ')"
arm "ARM A: git mv their journal ONTO mine (dest exists)" 1
git reset -q --hard

# ARM B — rename their journal to a path with NO per-lane pattern. The
# destination is new, so git collapses it to a rename and `--name-only` lists
# the DESTINATION alone; `notes.md` matches no ownership case, so the gate's
# `*) continue` infers no owner and the source is never considered.
git mv HANDOFF.OTHER-9.md notes.md
echo "  staged (--name-only):   $(git diff --cached --name-only | tr '\n' ' ')"
echo "  staged (--name-status): $(git diff --cached --name-status -M | tr '\n' ' ' | tr '\t' ' ')"
arm "ARM B: git mv their journal to an UNOWNED path" 1
cd "$ROOT"; rm -rf "$T"
