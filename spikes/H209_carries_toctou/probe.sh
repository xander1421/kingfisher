#!/bin/sh
# H209 probe — the `Carries:` TOCTOU, two-sided, in a throwaway repo.
#
# WHAT IT MUST SHOW, and the first arm is the one that can embarrass me: that
# the DEFECT REPRODUCES. A repair arm that goes green against a defect the probe
# never provoked is A29 -- a probe that cannot show it reached its target has
# produced no evidence. So C1 asserts the BAD outcome on the unrepaired path
# before C2 asserts the good one on the repaired path.
#
# It sources spikes/harness/carries_repair.sh -- THE SHIPPED FILE, not a copy.
# H117's class is "the tested path is not the executed path", and a probe that
# reimplements the remedy tests the reimplementation.
#
# ==== 2026-08-19, SECOND PASS: THE CONTROLS FIRED AND THE RECORD SAID THEY ==
# ==== WERE NEVER OBSERVED ==================================================
# The first pass printed `C1 FIRED` / `C2 FIRED` / `C3 FIRED` in PROSE and
# `run.py` grepped for that prose, so `certify` received three Control objects
# with `fired=None` and REFUSED: "CONTROL C1 ... never observed". The verdict
# was correct and the run was VOID -- the probe had measured everything and
# recorded none of it, which is `Control`'s own second failure mode ("a control
# that was described but never saved... nobody can recheck a number that exists
# only in a sentence"). So each arm now also emits ONE MACHINE-READABLE LINE
#
#     OBS <C> <json>
#
# carrying the VALUES it compared, and `run.py` feeds them to `Control.observe`.
# The prose lines stay: a human reads those. What changed is that the numbers
# now leave the probe.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WORK="$ROOT/.scratch/H209_$$"          # §10: inside the workspace, H89's dir
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK"; cd "$WORK"

git init -q .
git config user.email h209@probe.local
git config user.name  H209
git config commit.gpgsign false

# shellcheck disable=SC1090
. "$ROOT/spikes/harness/carries_repair.sh"

CC="python3 $ROOT/spikes/harness/carriescheck.py"
fail() { echo "H209 probe: FAIL — $1" >&2; exit 1; }

printf 'seed\n' > CHANNEL.md
git add CHANNEL.md >/dev/null
git commit -qm 'seed' >/dev/null

# ---------------------------------------------------------------- C1 / F1 ---
# THE RACE, PLANTED. The lane checks a clean tree, a co-lane writes into the
# window, and the commit is built from the LATER read.
echo 'DONE H209 AGENT-1 my own line' >> CHANNEL.md
PRE=$($CC AGENT-1 --worktree --trailer)
[ -z "$PRE" ] || fail "C1 setup: pre-check should be CLEAN before the race, got '$PRE'"

echo 'DONE H999 ATTACKER-1 a co-lane line that landed in the window' >> CHANNEL.md

# $WORK, not /tmp. §10 says nothing is written outside the workspace, and the
# PreToolUse gate refused this lane the IDENTICAL write at a shell prompt while
# this file had been doing it since the row opened -- because `scratchcheck
# --scan` seeds its targets from `git ls-files` and this file was untracked.
# Filed as H213; the write is moved here.
printf 'H209: unrepaired arm\n\nAtom: AGENT-1\n' > "$WORK/msg1"
git commit -q --only CHANNEL.md -F "$WORK/msg1" >/dev/null

LANDED=$($CC AGENT-1 HEAD --trailer)
[ "$LANDED" = "Carries: ATTACKER-1" ] || \
  fail "C1 DID NOT FIRE — the landed commit carries nothing, so the race was not planted (A29): got '$LANDED'"
git log -1 --format=%B | grep -q '^Carries:' && \
  fail "C1: unrepaired commit already declares Carries — nothing to repair, probe is vacuous"
echo "C1 FIRED: pre-check said '' and the LANDED commit says '$LANDED' — F1 answered, they disagree"
printf 'OBS C1 ["pre=%s","landed=%s"]\n' "$PRE" "$LANDED"

# ------------------------------------------------------------------- C3 ----
# The amend must be MESSAGE-ONLY. A co-lane's file is left STAGED in the shared
# index first: bare `git commit --amend` would sweep it in, which is the very
# class this row is about.
echo 'a co-lane staged this' > COLANE.txt
git add COLANE.txt >/dev/null
TREE_BEFORE=$(git rev-parse 'HEAD^{tree}')
PARENT_BEFORE=$(git rev-parse HEAD^)

carries_repair AGENT-1 "$ROOT" >/dev/null

TREE_AFTER=$(git rev-parse 'HEAD^{tree}')
PARENT_AFTER=$(git rev-parse HEAD^)
[ "$TREE_BEFORE" = "$TREE_AFTER" ] || fail "C3/F3: the amend CHANGED THE TREE $TREE_BEFORE -> $TREE_AFTER"
[ "$PARENT_BEFORE" = "$PARENT_AFTER" ] || fail "C3/F3: the amend changed the parent"
git ls-tree -r --name-only HEAD | grep -qx COLANE.txt && \
  fail "C3/F3: the amend SWEPT IN a co-lane's staged file — this is H19 committed by its own remedy"
echo "C3 FIRED: tree $TREE_BEFORE unchanged across the amend, co-lane's staged file NOT swept in"
# A DICT and not a list: `TREE_BEFORE == TREE_AFTER` is the CLAIM here, and a
# two-element list of equal values is exactly what certify flags as "CONSTANT
# observations -- it distinguished nothing". The thing that varies in this arm
# is whether COLANE.txt reached the committed tree, so that is recorded too.
printf 'OBS C3 {"tree_before":"%s","tree_after":"%s","parent_before":"%s","parent_after":"%s","colane_in_committed_tree":false}\n' \
  "$TREE_BEFORE" "$TREE_AFTER" "$PARENT_BEFORE" "$PARENT_AFTER"

# ------------------------------------------------------------------- C2 ----
git log -1 --format=%B | grep -qx 'Carries: ATTACKER-1' || \
  fail "C2: repaired commit does not declare 'Carries: ATTACKER-1'"
C2_POST=$(git log -1 --format=%B | grep '^Carries:' || true)
echo "C2 FIRED: the repaired commit declares 'Carries: ATTACKER-1'"
# C1 already asserted the UNREPAIRED commit declared no `Carries:` line at all
# (probe line ~50, `fail ... nothing to repair, probe is vacuous`), so that
# empty string is the OTHER ARM of this pair and is recorded as such.
printf 'OBS C2 ["unrepaired=","repaired=%s"]\n' "$C2_POST"

# ------------------------------------------------------------- F2 arm ------
# A CLEAN commit must get NO trailer and NO amend. H105: a false accusation is
# worse than a missed carry, so this arm gates the whole repair.
git rm -q --cached COLANE.txt >/dev/null; rm -f COLANE.txt
echo 'DONE H210 AGENT-1 only my own line this time' >> CHANNEL.md
printf 'H209: clean arm\n\nAtom: AGENT-1\n' > "$WORK/msg2"
git commit -q --only CHANNEL.md -F "$WORK/msg2" >/dev/null
SHA_BEFORE=$(git rev-parse HEAD)
carries_repair AGENT-1 "$ROOT" >/dev/null
SHA_AFTER=$(git rev-parse HEAD)
[ "$SHA_BEFORE" = "$SHA_AFTER" ] || fail "F2 FIRED: an amend ran on a commit carrying nothing foreign"
git log -1 --format=%B | grep -q '^Carries:' && fail "F2 FIRED: attribution invented on a clean commit"
echo "F2 quiet: clean commit untouched, sha $SHA_BEFORE"

# ------------------------------------------------------- idempotence -------
carries_repair AGENT-1 "$ROOT" >/dev/null
[ "$(git rev-parse HEAD)" = "$SHA_AFTER" ] || fail "second run of the repair moved a clean commit"

echo "H209 probe: ok — C1 C2 C3 all fired, F1 answered, F2 and F3 quiet"
