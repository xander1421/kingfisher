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
for cs in AGENT-1 ATTACKER-1; do
  if ! ps -eo command 2>/dev/null | grep -q "CALLSIGN=${cs}[ =]*[^ ]*run_loop"; then
    echo "  PRECONDITION  no live launcher for $cs — assignment unmeasurable here"
    continue
  fi
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
done
rm -f "$S"

echo "commit-msg gate: $pass passed, $fail failed"
[ "$fail" = 0 ]
