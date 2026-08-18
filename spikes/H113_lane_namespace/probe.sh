#!/usr/bin/env bash
# H113 -- does the `P` row namespace prompts/AGENT-1.md assigns to this lane exist?
#
# THE FALSIFIER, stated in CHANNEL.md before this file existed:
#   "if a P row is found in WORK_QUEUE.md, or if any file in this tree defines
#    P0-P5 as a row-id namespace rather than a priority tier, the brief is right
#    and I withdraw H113."
#
# This is the runnable check for the repaired brief too: it FAILS if the brief
# ever again claims a row prefix that WORK_QUEUE.md does not carry. That is the
# property, not the wording -- A30's remedy, since the wording is what drifted.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-6s %-4s %s\n' "$1" "$2" "$3"; }

# The row prefixes WORK_QUEUE.md actually carries, from the table column itself.
PREFIXES=$(grep -oE '^\| *[A-Z]+[0-9]+' WORK_QUEUE.md | tr -d '| ' | sed 's/[0-9]*$//' | sort -u)

echo "=== CONTROLS ==="
# C1 (A15). The extractor must find SOMETHING, or every absence below is the
# extractor failing rather than a namespace missing -- a null from a probe that
# read nothing looks identical to a null from a probe that read everything.
n=$(printf '%s\n' "$PREFIXES" | grep -c '[A-Z]')
[ "$n" -ge 5 ] \
  && ctl C1 PASS "extractor found $n row prefixes: $(echo $PREFIXES | tr '\n' ' ')" \
  || ctl C1 FAIL "extractor found only $n prefixes -- it is broken, not the queue"
# CAN FAIL BECAUSE: break the regex or point it at an empty file and it goes red.

# C2 (A15, the other direction). A prefix the queue DOES carry must be reported
# present, or "P is absent" is a statement about the test and not about P.
printf '%s\n' "$PREFIXES" | grep -qx 'H' \
  && ctl C2 PASS "a known-present prefix (H) is reported present" \
  || ctl C2 FAIL "H is not reported present -- the membership test cannot say YES"

echo
echo "=== THE CLAIM: every row prefix prompts/AGENT-1.md assigns to this lane ==="
# READ THE ONE MACHINE-READABLE LINE, not the prose. v1 scanned the whole file
# for bolded row ids and therefore could not tell a LIVE claim from a QUOTATION
# of a withdrawn one -- it went red on the repair, because the repair quotes
# `P0-P4` in order to retract it. That is refcheck v5's trap ("a rationale block
# naming an absent path is indistinguishable from a broken citation of it") and
# A30's remedy is what is applied: the claim lives where prose cannot collide
# with it. The list is still not retyped here -- it is read from the brief.
CLAIMED=$(sed -n 's/^ *LANE-ROWS: *//p' prompts/AGENT-1.md | head -1)
if [ -z "$CLAIMED" ]; then
  ctl C3 FAIL "no LANE-ROWS line in prompts/AGENT-1.md -- the claim is unreadable, which is not the same as correct"
  CLAIMED=''
else
  ctl C3 PASS "LANE-ROWS line found: $CLAIMED"
fi
for p in $CLAIMED; do
  if printf '%s\n' "$PREFIXES" | grep -qx "$p"; then
    ctl "$p" PASS "brief claims prefix $p and WORK_QUEUE.md carries $p rows"
  else
    ctl "$p" FAIL "brief claims prefix $p and WORK_QUEUE.md carries NO $p row"
  fi
done

echo
echo "=== what P actually is, where it appears ==="
grep -hoE '.{0,44}\bP[0-5]\b.{0,44}' specs/D2_canonical_result.md HUMAN_NEEDED.md 2>/dev/null \
  | head -3 | sed 's/^/  /'
echo
echo "verdict=$([ $fail = 0 ] && echo BRIEF_MATCHES_QUEUE || echo BRIEF_CLAIMS_ABSENT_NAMESPACE)"
exit $fail
