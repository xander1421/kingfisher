#!/usr/bin/env bash
# H123 class sweep (§12.2) — CLASS: a gate that walks `git diff --cached
# --name-only` cannot see the SOURCE path of a rename.
#
# Sites, from `grep -rn 'name-only' spikes/harness/`:
#   commit-msg.hook:264   FIXED here (v8, --name-status -M, both ends walked)
#   recordloss.py         already fixed (v2, H117 FA2c)
#   githygiene.py:240     reasoned, see RESULT.md — subject is what the commit ADDS
#   statuscheck.py:179    reasoned, see RESULT.md — scope is journal/prompt space
#   pre-commit.hook:192   MEASURED HERE: unsound_paths() intersects the staged
#                         names with the DIRTY names, so a rename that hides the
#                         source could hide an unsound path.
#
# usage: bash spikes/H123_rename_evasion/sweep.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
T="$ROOT/spikes/H123_rename_evasion/.sweep"
rm -rf "$T"; mkdir -p "$T"; cd "$T"
git init -q .; git config user.email t@t; git config user.name t
cp "$ROOT/spikes/harness/pre-commit.hook" hook.sh; chmod +x hook.sh
grep -q 'unsound_paths' hook.sh || { echo "REFUSING: hook.sh has no unsound_paths"; exit 2; }
printf 'base\n' > a.md; git add a.md; git commit -q -m base

arm() { printf '  %-46s pre-commit rc=%s%s\n' "$1" "$2" "$3"; }

# CONTROL — no rename, staged content differs from the tree copy: must REFUSE.
printf 'staged\n' > a.md; git add a.md; printf 'tree\n' > a.md
out=$(./hook.sh 2>&1); rc=$?
arm "CONTROL: no rename, staged != tree" "$rc" "  (expect 1)"
git checkout -q -- a.md 2>/dev/null; git reset -q --hard

# ARM — rename, then dirty the DESTINATION without staging it.
git mv a.md b.md; printf 'tree-only\n' > b.md
echo "  staged (--name-only):   $(git diff --cached --name-only | tr '\n' ' ')"
echo "  dirty  (--name-only):   $(git diff --name-only | tr '\n' ' ')"
out=$(./hook.sh 2>&1); rc=$?
arm "ARM: rename + dirty destination" "$rc" "  (expect 1 — dest is named on both sides)"
git reset -q --hard

# ARM — clean rename, nothing dirty: must PASS (this is the false-red control).
git mv a.md b.md
out=$(./hook.sh 2>&1); rc=$?
arm "ARM: clean rename, tree matches index" "$rc" "  (expect 0)"
cd "$ROOT"; rm -rf "$T"
