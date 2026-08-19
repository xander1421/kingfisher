#!/bin/sh
# H199 arm B — ATTACK (§2, instruments before conclusions) on the OTHER remedy
# for this class: `carries_repair()`, AGENT-1's H209, uncommitted in the tree at
# the time of writing.
#
# ITS PREMISE: "it scores HEAD AFTER the commit lands. A commit object is
# IMMUTABLE, so the window is not shrunk from 8s to 8ms -- it is ELIMINATED,
# because the object scored and the object recorded are the same object by
# construction."
#
# THE OBJECT IS IMMUTABLE. `HEAD` IS NOT. Nothing in the function pins the sha
# it just created, and the whole premise of the row is that a co-lane commits
# inside seconds. So this measures what happens when one does.
#
# TWO-SIDED: B1 is the healthy case (no interleave -- the amend must land on my
# own commit and the function must work), B2 is the interleaved case. Without B1
# a red B2 could just mean the function never fired.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$ROOT/.scratch"
D=$(mktemp -d -p "$ROOT/.scratch")
trap 'rm -rf "$D"' EXIT
. "$ROOT/spikes/harness/carries_repair.sh"      # THE SHIPPED FILE, not a copy
fail=0
ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1 (want '$3', got '$2')"; fail=$((fail+1)); fi; }

cd "$D"
git init -q .; git config user.email t@t; git config user.name t
printf 'base\n' > CHANNEL.md; git add CHANNEL.md
git commit -qm "base

Atom: AGENT-1
Reviewed-By: unreviewed"

# ------------------------------------------------------------------ B1 healthy
printf 'DONE X1 ATTACKER-1 a co-lane line swept in by --only\n' >> CHANNEL.md
git commit -q --only CHANNEL.md -m "mine

Atom: AGENT-1
Reviewed-By: unreviewed"
mine=$(git rev-parse HEAD)
carries_repair AGENT-1 "$ROOT" >/dev/null 2>&1
# CORRECTED before the first green run: this expectation was written as
# "ATTACKER-1 ok-1" by copying B2e's value. At B1 the fixture contains ONE
# foreign line and `ok-1` has not written yet, so the tool was right and the
# probe was wrong. Recorded rather than quietly edited (§5).
ck "B1 no interleave: my own commit gains the trailer" \
   "$(git log -1 --format=%B | sed -n 's/^Carries: //p')" "ATTACKER-1"
ck "B1b and it is still MY commit that is HEAD" \
   "$(git log -1 --format=%B | sed -n 's/^Atom: //p')" AGENT-1

# --------------------------------------------------------------- B2 interleave
# Lane A commits. Lane B commits before lane A's repair step runs -- the eight
# seconds ATTACKER-1 measured, which is the reason this row exists.
printf 'DONE X2 ATTACKER-1 second co-lane line\n' >> CHANNEL.md
git commit -q --only CHANNEL.md -m "lane A subject

Atom: AGENT-1
Reviewed-By: unreviewed"
a_sha=$(git rev-parse HEAD)

printf 'DONE X3 ok-1 lane B own line\n' >> CHANNEL.md
printf 'DONE X4 ATTACKER-1 a line lane B swept in\n' >> CHANNEL.md
git commit -q --only CHANNEL.md -m "lane B subject

Atom: ok-1
Reviewed-By: unreviewed"
b_sha=$(git rev-parse HEAD)
b_msg=$(git log -1 --format=%B)
b_tree=$(git rev-parse HEAD^{tree})

carries_repair AGENT-1 "$ROOT" >/dev/null 2>&1        # lane A's repair, late

now=$(git rev-parse HEAD)
ck "B2 lane A's OWN commit is untouched (it is not HEAD)" \
   "$(git rev-parse $a_sha^{commit})" "$a_sha"
ck "B2b lane A's commit still lacks the trailer it was owed" \
   "$(git show -s --format=%B $a_sha | grep -c '^Carries:')" 0
ck "B2c HEAD -- lane B's commit -- WAS REWRITTEN by lane A" \
   "$( [ "$now" = "$b_sha" ] && echo unchanged || echo rewritten )" rewritten
ck "B2d the rewritten commit still declares Atom: ok-1" \
   "$(git log -1 --format=%B | sed -n 's/^Atom: //p')" ok-1
ck "B2e ...and carries a trailer scored for AGENT-1, which NAMES LANE B ITSELF" \
   "$(git log -1 --format=%B | sed -n 's/^Carries: //p')" "ATTACKER-1 ok-1"
ck "B2f the trailer names lanes scored against the WRONG commit's lines" \
   "$( git show -s --format=%B $b_sha | grep -c '^Carries:' )" 0
ck "B2g lane B's tree is unchanged, so only the MESSAGE and the sha moved" \
   "$(git rev-parse HEAD^{tree})" "$b_tree"

echo "--- lane A committed $a_sha, lane B committed $b_sha, HEAD is now $now ---"
echo "checks failed: $fail"
[ "$fail" -eq 0 ] || exit 1
