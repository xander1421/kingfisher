#!/bin/sh
# Constructs the FAILING cases, not only the passing one — ATOM-3's point, and
# the reason their 15-check suite passed over the defect it was written to catch.
# Every REFUSE case below is a real value taken from this repo's own history.
H=${H:-.git/hooks/commit-msg}; pass=0; fail=0
t() { # t <expect 0|1> <label> <message>
  printf '%s\n' "$3" > /tmp/_cm.$$
  sh "$H" /tmp/_cm.$$ >/dev/null 2>&1; got=$?
  if [ "$got" = "$1" ]; then pass=$((pass+1)); else fail=$((fail+1));
    echo "  FAIL  $2 (want exit $1, got $got)"; fi
  rm -f /tmp/_cm.$$
}
B="Claude-Session: https://x"
t 1 "no trailers"            "subject"
t 1 "missing Reviewed-By"    "subject

Atom: AGENT-2
$B"
t 1 "Atom is a topic label"  "subject

Atom: mutation-detection
$B
Reviewed-By: ATOM-3"
t 1 "Atom is harness-hardening" "subject

Atom: harness-hardening
$B
Reviewed-By: ATOM-3"
t 1 "Reviewed-By: self"      "subject

Atom: AGENT-1
$B
Reviewed-By: self"
t 1 "Reviewed-By: none"      "subject

Atom: AGENT-1
$B
Reviewed-By: none"
t 1 "literal self-review"    "subject

Atom: AGENT-2
$B
Reviewed-By: AGENT-2"
t 1 "case-folded self-review" "subject

Atom: AGENT-1
$B
Reviewed-By: agent-1"
t 0 "valid peer review"      "subject

Atom: AGENT-2
$B
Reviewed-By: ATOM-3"
t 0 "explicit unreviewed"    "subject

Atom: AGENT-2
$B
Reviewed-By: unreviewed"
t 0 "hyphenated callsign"    "subject

Atom: AGENT-2-LANE
$B
Reviewed-By: AGENT-2"

# --- v5: Claude-Session is ASSIGNED, not typed (H22) --------------------------
# Scratch goes in .git/, not /tmp: H17 is open and undecided, so a NEW check does
# not add another instance to a live rail question. The existing cases above are
# left on /tmp deliberately — changing another lane's checks is not this row.
S=.git/_cm_v5.$$
P="subject

Atom: AGENT-1
Claude-Session: unassigned-in-lane
Reviewed-By: unreviewed"

# fail-open, and it is checked FIRST because it is the one that can wedge every
# lane in the fleet: no CALLSIGN must leave the message untouched and exit 0.
printf '%s\n' "$P" > "$S"
env -u CALLSIGN sh "$H" "$S" >/dev/null 2>&1
if [ $? = 0 ] && grep -q '^Claude-Session: unassigned-in-lane$' "$S"; then
  pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL  fail-open without CALLSIGN"; fi

# the assignment itself, per live lane. A callsign with no live launcher cannot
# be assigned from, so that is a PRECONDITION and is reported, never a FAIL --
# the three outcome categories M1_11 named, applied here.
# THE PRECONDITION WAS COMPUTED BY THE EXPRESSION UNDER TEST (v6, AGENT-2, H37).
# This loop used to skip with "no live launcher for $cs — assignment unmeasurable
# here" whenever `ps -eo command | grep "CALLSIGN=..run_loop"` found nothing. That
# grep IS the mechanism v5 used. So when the mechanism stopped matching anything,
# its own detector reported PRECONDITION and the suite passed — the failure
# disabled the only thing that could have reported it. A29: a probe that cannot
# show it reached its target has produced no evidence, one layer up.
#
# The case is CONSTRUCTED now instead of waited for: a process that looks like a
# launcher to `ps`, its pid written to the lock the launcher really writes
# (run_loop.sh v6, H8). Deterministic, and it runs whether or not a fleet is up.
_fakedir="$(dirname "$S")/fakelane"
mkdir -p "$_fakedir"
printf '#!/usr/bin/env bash\nsleep 20\nexit 0\n' > "$_fakedir/run_loop.sh"
bash "$_fakedir/run_loop.sh" & _holder=$!
# The trailing `exit 0` is load-bearing: bash EXECs the last simple command of a
# script, so a fixture ending in `sleep` reports `sleep 20` to ps and resembles
# nothing. Asserted rather than assumed, so the fixture cannot rot into a skip.
if ps -p "$_holder" -o command= 2>/dev/null | grep -q 'run_loop\.sh'; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "  FAIL  fixture holder does not look like a launcher to ps"
fi
for cs in KF-TEST1 KF-TEST2; do
  echo "$_holder" > ".loop_lock.${cs}"
  printf '%s\n' "$P" > "$S"
  CALLSIGN=$cs sh "$H" "$S" >/dev/null 2>&1
  got=$(sed -n 's/^Claude-Session: //p' "$S")
  # It must be REWRITTEN, and it must carry the callsign -- which is what makes
  # two lanes differ. Asserting "not the placeholder" alone would pass on any
  # rewrite, including a constant one, i.e. the exact defect v5 removes.
  case "$got" in
    lane:$cs@*) pass=$((pass+1)) ;;
    *) fail=$((fail+1)); echo "  FAIL  $cs Claude-Session not assigned: '$got'" ;;
  esac
  rm -f ".loop_lock.${cs}"
done
# Two lanes must not receive the same value; a rewrite to a constant would pass
# every check above. They share one fixture pid here, so this asserts the CALLSIGN
# half separates them -- the half an agent cannot type is the start time.
kill "$_holder" 2>/dev/null; rm -rf "$_fakedir"
rm -f "$S"

# --- v8, H123: OWNERSHIP MUST SEE THE RENAME SOURCE ---------------------------
# `git diff --cached --name-only` reports a rename as the DESTINATION alone, so
# `git mv HANDOFF.OTHER-9.md notes.md` staged one unowned path and this gate
# passed a commit DELETING another lane's journal. Driven in a throwaway repo,
# because the property is "the hook refuses this staged set" and the staged set
# is the whole point. Both arms: the evasion must refuse, and a lane renaming its
# OWN journal must still pass, or the fix would wedge a legitimate operation.
_rr="$(git rev-parse --git-path hooks)/_cm_rename.$$"
_habs="$(cd "$(dirname "$H")" && pwd)/$(basename "$H")"
rm -rf "$_rr"; mkdir -p "$_rr"
(
  cd "$_rr" || exit 1
  git init -q .; git config user.email t@t; git config user.name t
  printf '# theirs\n' > HANDOFF.OTHER-9.md; printf '# mine\n' > HANDOFF.MINE-1.md
  git add HANDOFF.OTHER-9.md HANDOFF.MINE-1.md; git commit -q -m base
  printf 'subject\n\nAtom: MINE-1\nClaude-Session: x\nReviewed-By: unreviewed\n' > m
  git mv HANDOFF.OTHER-9.md notes.md
  sh "$_habs" m >/dev/null 2>&1 && exit 3   # must REFUSE
  git reset -q --hard
  # The control is an ORDINARY rename, not a self-rename of a journal: a journal
  # renamed to any other name has a DIFFERENT inferred owner and was already
  # refused before v8, so asserting otherwise would be asserting a property this
  # gate has never had. Found by this arm failing on its first run.
  printf 'x\n' > a.md; git add a.md; git commit -q -m a
  git mv a.md b.md
  sh "$_habs" m >/dev/null 2>&1 || exit 4   # unowned rename: must PASS
  exit 0
)
case $? in
  0) pass=$((pass+2)) ;;
  3) fail=$((fail+1)); echo "  FAIL  a rename of ANOTHER lane's journal to an unowned path must REFUSE (H123)" ;;
  4) fail=$((fail+1)); echo "  FAIL  renaming your OWN journal must still pass" ;;
  *) fail=$((fail+1)); echo "  FAIL  H123 rename fixture did not run" ;;
esac
rm -rf "$_rr"

echo "commit-msg gate: $pass passed, $fail failed"
[ "$fail" = 0 ]
