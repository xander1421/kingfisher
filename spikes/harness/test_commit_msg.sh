#!/bin/sh
# Constructs the FAILING cases, not only the passing one — ATOM-3's point, and
# the reason their 15-check suite passed over the defect it was written to catch.
# Every REFUSE case below is a real value taken from this repo's own history.
H=.git/hooks/commit-msg; pass=0; fail=0
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
echo "commit-msg gate: $pass passed, $fail failed"
[ "$fail" = 0 ]
