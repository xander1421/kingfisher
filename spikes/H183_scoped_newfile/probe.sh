#!/usr/bin/env bash
# H183 -- ok-1, 2026-08-19. The escape hatch cannot commit a new file.
#
# CLASS: H71 living inside the escape hatch built for H72. commit_scoped.sh ends
# in `git commit --no-verify --only "$@"` with no `git add -N`, and §13 records
# that `--only` REFUSES a path git has never seen. Every cycle here creates a new
# spike directory, so the documented route for a lane blocked by another lane's
# tree-wide refusal cannot commit the commonest operation in this repo.
#
# Measured twice in one hour on my own H173/H179 commits: every gate passed, the
# script printed `== committing ==`, and the commit did NOT land. That order is
# the dangerous part -- a lane reading "all gates passed" walks away.
#
# The arms drive `git commit --only` DIRECTLY rather than the whole script,
# because the script's gates need a full harness tree, its own installed
# `.git/hooks/commit-msg`, and four other lanes' files to judge -- a sandbox
# carrying all of that would be a copy of the repo, not a test.
#
# THE EXECUTED-PATH ARM IS THE COMMIT OF THIS ROW ITSELF. H183's own commit
# carries new files and goes THROUGH commit_scoped.sh v7; if the fix does not
# work, the row does not land. That is deliberate, and it is H108's lesson from
# the other side -- the commit that shipped a gate went round it.
#
# usage: bash spikes/H183_scoped_newfile/probe.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }

fresh() {
  rm -rf "$SB"; mkdir -p "$SB"; cd "$SB"
  git init -q .; git config user.email t@t; git config user.name t
  printf 'base\n' > tracked.md; git add tracked.md; git commit -q -m base
  printf 'new spike\n' > new.md          # untracked, as every cycle's spike dir is
}

echo "  git $(git --version | awk '{print $3}')"

# ---- C2 the fixture's new file really is untracked, or nothing below is evidence
fresh
n=$(git ls-files new.md | wc -l | tr -d ' ')
[ "$n" = 0 ] && ctl C2 PASS "new.md is untracked (git ls-files = 0)" \
              || ctl C2 FAIL "new.md is already tracked -- the fixture proves nothing"

# ---- F1 --only refuses an untracked path on THIS git
out=$(git commit --only new.md -m x 2>&1); rc=$?
case "$out" in
  *"did not match any file"*) ctl F1 PASS "--only REFUSES an untracked path (rc=$rc)" ;;
  *) [ "$rc" = 0 ] && ctl F1 FAIL "--only ACCEPTED an untracked path on git $(git --version | awk '{print $3}') -- row withdrawn" \
                   || ctl F1 FAIL "refused for another reason: $(printf '%s' "$out" | head -1)" ;;
esac

# ---- C3 an already-tracked path still commits by the same route
printf 'edit\n' >> tracked.md
git commit -q --only tracked.md -m y 2>/dev/null \
  && ctl C3 PASS "a tracked path commits with --only, so the refusal is about NEWNESS" \
  || ctl C3 FAIL "tracked path refused too -- the diagnosis is wrong"

# ---- F2 `add -N` fixes it AND stages no content: a co-lane's bare commit in the
#         window must capture an EMPTY file, which is why §13 chose -N over add.
fresh
git add -N new.md
staged=$(git diff --cached --numstat -- new.md | awk '{print $1}')
[ -z "$staged" ] || [ "$staged" = 0 ] \
  && ctl F2 PASS "add -N stages NO content (numstat added='${staged:-none}')" \
  || ctl F2 FAIL "add -N staged $staged line(s) -- blast radius is a whole spike, not an empty file"
git commit -q --only new.md -m z 2>/dev/null \
  && ctl F2b PASS "after add -N, --only commits the new path" \
  || ctl F2b FAIL "still refused after add -N -- the proposed fix does not work"
git show --stat --format= HEAD | grep -q 'new.md' \
  && ctl F2c PASS "the committed tree really contains new.md" \
  || ctl F2c FAIL "commit landed without the file"

# ---- F3 a path that does not exist must refuse loudly, not be created or skipped
fresh
out=$(git add -N absent.md 2>&1); rc=$?
[ "$rc" != 0 ] && [ ! -e "$SB/absent.md" ] \
  && ctl F3 PASS "add -N on a missing path refuses (rc=$rc) and creates nothing" \
  || ctl F3 FAIL "add -N on a missing path rc=$rc, exists=$([ -e "$SB/absent.md" ] && echo yes || echo no)"

cd "$SPIKE"; rm -rf "$SB"
echo
[ "$fail" = 0 ] && echo "H183 probe: all arms as stated" || echo "H183 probe: FAILED"
exit "$fail"
