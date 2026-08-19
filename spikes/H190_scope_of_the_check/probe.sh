#!/bin/sh
# H190 F1 — WHAT DOES `git commit --only <path>` ACTUALLY COMMIT?
#
# Decided in a scratch repo on THIS git, not read off a man page. F1 was the
# withdrawal condition: if `--only` commits the INDEX for the named paths, then
# `carriescheck`'s index mode was the right object and H190 dies.
#
# Two-sided by construction: the fixture stages one foreign line, leaves a
# second unstaged, and stages an unrelated sibling file. A single assertion
# would not separate "takes the worktree" from "takes everything".
set -e
# H89/§10: scratch goes inside the workspace. `mktemp -d` defaults to /tmp, which
# is outside it -- the shape scratchcheck.py refuses, and H17's open row about
# two harness tests already doing it. -p keeps the sandbox and moves the location.
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$ROOT/.scratch"
D=$(mktemp -d -p "$ROOT/.scratch")
trap 'rm -rf "$D"' EXIT
cd "$D"
git init -q .
git config user.email t@t; git config user.name t
printf 'base\n' > CHANNEL.md
git add CHANNEL.md; git commit -qm base

printf 'DONE X1 AGENT-2 foreign STAGED line\n' >> CHANNEL.md
git add CHANNEL.md
printf 'DONE X2 AGENT-2 foreign UNSTAGED line\n' >> CHANNEL.md
printf 'other\n' > other.txt
git add other.txt

git commit -q --only CHANNEL.md -m "only test"

echo "--- files in the commit ---"
git show --format= --name-only HEAD
echo "--- CHANNEL.md as committed ---"
git show HEAD:CHANNEL.md

n=$(git show HEAD:CHANNEL.md | grep -c 'AGENT-2')
files=$(git show --format= --name-only HEAD | tr -d ' ')

[ "$n" = "2" ] || { echo "F1 FIRED: --only committed $n foreign line(s), not 2 -- it is NOT the working tree" >&2; exit 1; }
[ "$files" = "CHANNEL.md" ] || { echo "F1 FIRED: commit carried '$files', not CHANNEL.md alone" >&2; exit 1; }
echo
echo "F1 DOES NOT FIRE: --only committed the WORKING TREE (both foreign lines,"
echo "including the UNSTAGED one) and left the staged sibling other.txt OUT."
echo "So a check reading 'git diff --cached' misses exactly the lines --only takes."
