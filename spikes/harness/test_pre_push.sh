#!/bin/sh
# test_pre_push.sh v1 — H115. The §12.3 runnable check for `pre-push.hook`.
#
# It performs REAL `git push` commands, and every one of them goes into a BARE
# REPOSITORY CREATED UNDER THIS SPIKE DIRECTORY (§10: nothing is written outside
# the workspace, and H89 is the open row about that rail). No network, no
# `origin`, nothing leaves this machine — asserted at the end by requiring the
# sandbox's only remote to be a path inside the workspace.
#
# THE QUESTION THIS SUITE IS BUILT AROUND: what case does it not construct? The
# gate has one refusing direction, so the arms that matter are the ones that must
# STAY QUIET — an inert `.md` in the same directory, a lock outside it, a branch
# deletion — because a gate that refuses everything is bypassed exactly as fast
# as one that refuses nothing (H14, H52).
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HOOK="$ROOT/spikes/harness/pre-push.hook"
D="$ROOT/spikes/H115_push_rail/.sandbox"
FAIL=0

ck() { # ck <label> <expected rc> <actual rc>
  if [ "$2" -eq "$3" ]; then echo "  ok    $1"
  else echo "  FAIL  $1 (expected rc=$2, got rc=$3)"; FAIL=$((FAIL + 1)); fi
}

setup() {
  rm -rf "$D"; mkdir -p "$D/origin.git" "$D/work"
  git init --quiet --bare "$D/origin.git"
  git init --quiet "$D/work"
  cd "$D/work" || exit 9
  git config user.email h115@local; git config user.name H115
  git remote add origin "$D/origin.git"
  cp "$HOOK" .git/hooks/pre-push; chmod +x .git/hooks/pre-push
  mkdir -p .github/workflows
  echo one > a.txt; git add a.txt; git commit --quiet -m 'base'
}

push() { git push --quiet origin HEAD:refs/heads/"$1" >"$D/out" 2>&1; }

# A1 — the CONTROL, and it is first on purpose: an ordinary push must succeed.
# Without it every arm below is satisfied by a hook that refuses unconditionally.
setup
push main; ck "A1 an ordinary push is ACCEPTED (the gate is not always-red)" 0 $?

# A2 — the refusing direction.
echo 'on: push' > .github/workflows/x.yml
git add .github/workflows/x.yml; git commit --quiet -m 'add a workflow'
push main; ck "A2 a pushed tree containing .github/workflows/x.yml is REFUSED" 1 $?
grep -q 'pre-push REFUSED' "$D/out"; ck "A2 and it says so in its own words" 0 $?
grep -q 'x.yml' "$D/out"; ck "A2 and names the file, so the refusal is diagnosable" 0 $?

# A3 — THE TREE, NOT THE DIFF. The workflow arrived in the PREVIOUS commit; a
# push of an unrelated change still delivers it to the remote.
echo two >> a.txt; git add a.txt; git commit --quiet -m 'unrelated change'
push main; ck "A3 an unrelated push still REFUSES while the tree carries a workflow" 1 $?

# A4 — and it must let go once the tree no longer carries one, or it is a
# one-way latch that every lane learns to bypass.
git rm --quiet .github/workflows/x.yml; git commit --quiet -m 'remove the workflow'
push main; ck "A4 ACCEPTED again once the workflow leaves the tree" 0 $?

# A5 — .yaml is executable too. Extension, not filename: `autoloop.lock.yml` is
# what the compiler emits today, and a check keyed to that name is a proxy for
# the behaviour rather than the behaviour.
# mkdir again: `git rm` of the last file in .github/workflows/ removes the
# directory, and the first run of this arm wrote into a path that no longer
# existed -- the shell said so, git found nothing to add, and the arm reported
# ACCEPTED. A setup failure that reads as a passing verdict is the same shape as
# the fixture in H111 that printed a finding while running no gate at all.
mkdir -p .github/workflows
echo 'on: push' > .github/workflows/y.yaml
git add .github/workflows/y.yaml; git commit --quiet -m 'yaml spelling'
push main; ck "A5 the .yaml spelling is REFUSED as well" 1 $?
git rm --quiet .github/workflows/y.yaml; git commit --quiet -m 'drop it'

# A6 — QUIET: an .md in .github/workflows/ is the gh-aw SOURCE and Actions does
# not execute it. This repo's whole disable rests on that distinction, so a hook
# that refuses the directory rather than the extension would break the fleet's
# working arrangement while looking stricter.
mkdir -p .github/workflows; echo '# source' > .github/workflows/autoloop.md
git add .github/workflows/autoloop.md; git commit --quiet -m 'md source only'
push main; ck "A6 QUIET on an .md source in the same directory" 0 $?

# A7 — QUIET but REPORTED: a compiled lock outside .github/workflows/ is inert on
# the remote and is already in this repo's history.
mkdir -p .autoloop; echo 'jobs: {}' > .autoloop/autoloop.lock.yml.disabled
git add .autoloop; git commit --quiet -m 'a disabled lock outside the workflows dir'
push main; ck "A7 ACCEPTED with a lock outside .github/workflows/" 0 $?
grep -q 'pre-push NOTE' "$D/out"; ck "A7 and it is REPORTED rather than passed in silence" 0 $?

# A8 — a branch DELETION pushes the zero sha and has no tree to inspect. Reading
# it as a commit is how a hook crashes on the one operation that removes work.
git push --quiet origin HEAD:refs/heads/tmpbranch >/dev/null 2>&1
git push --quiet origin :refs/heads/tmpbranch >"$D/out" 2>&1
ck "A8 a branch deletion (zero sha) is handled, not crashed on" 0 $?

# A9 — §10: the test itself must not have reached outside the workspace.
remote=$(git remote get-url origin)
case "$remote" in "$ROOT"/*) rc=0 ;; *) rc=1 ;; esac
ck "A9 the sandbox pushed only into a path inside the workspace ($remote)" 0 "$rc"

cd "$ROOT" || exit 9
rm -rf "$D"
echo
if [ "$FAIL" -eq 0 ]; then
  echo "test_pre_push: 12 assertions, 0 FAILED — refuses an executable workflow in"
  echo "               the pushed TREE, stays quiet on the source, the lock and a"
  echo "               deletion, and lets go when the workflow does."
else
  echo "test_pre_push: $FAIL FAILED"
fi
exit "$FAIL"
