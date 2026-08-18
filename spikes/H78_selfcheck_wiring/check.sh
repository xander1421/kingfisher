#!/bin/sh
# H78 — the wiring must stay wired, and each property is falsified on a copy.
#
# `bringup.sh` itself is NEVER executed here: it launches lanes. Every assertion
# is made against a COPY under this spike directory (§10: nothing outside the
# workspace), and each one is re-run against a copy with the property REMOVED, so
# a check that cannot go red is caught the way H17 says to catch it.
#
# v2 (H95, ATTACKER-1, 2026-08-18). DEFECT REMOVED: **P2 AND P3 WERE TEXT
# POSITION STANDING IN FOR CONTROL FLOW, AND THEY WERE GREEN THROUGH THE WHOLE
# FAILURE THEY EXIST TO CATCH.** v1's P2 read "the call site is below the launch
# loop" and P3 "no `exit [1-9]` textually after it". Both were true of the file;
# the file also had five `exit` statements ABOVE the block, two of them carrying
# all the traffic, so the sweep ran on NO path the fleet takes -- 26 logged
# reconciles, 0 sweeps, and this suite green for all of them. The v1 header even
# says `bringup.sh` is never executed here, which is precisely why it could not
# see the defect: reachability is not decidable from the text of a file.
#
# THE PROPERTIES ARE KEPT, NOT DROPPED. P2's property is "the sweep cannot delay
# a lane launch" and P3's is "a red sweep cannot stop the reconciler". Both are
# now asserted by RUNNING a byte-identical copy on every termination path in
# spikes/H95_selfcheck_reach/check.sh (A9 output ORDER, A6 controlled-pair exit
# codes, plus a negative control that removes the trap and requires silence).
# Delegated rather than duplicated: two copies of one rule is the class §12.2
# names, and this file would be the second copy.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
D="$ROOT/spikes/H78_selfcheck_wiring"
B="$D/.bringup.copy"
FAIL=0
cp "$ROOT/bringup.sh" "$B"

ck() { # ck <label> <expected 0|1> <actual rc>
  if [ "$2" -eq "$3" ]; then echo "  ok    $1"
  else echo "  FAIL  $1 (expected rc=$2, got rc=$3)"; FAIL=$((FAIL+1)); fi
}

# P1 — the invocation exists in EXECUTABLE position. `grep -c selfcheckall` alone
# would pass on the rationale comment block, which is the whole H78 finding
# (a mention is not an invocation) reproduced inside its own check.
invoked() { grep -nE '^[^#]*python3 spikes/harness/selfcheckall\.py' "$1" >/dev/null; }
invoked "$B"; ck "bringup.sh INVOKES selfcheckall.py outside a comment" 0 $?

# Falsifier for P1: strip the invocation, keep every comment mentioning it.
sed 's|^\( *\)_sca=$(python3 spikes/harness/selfcheckall.py.*|\1_sca=""; _scarc=0|' \
  "$B" > "$D/.bringup.stripped"
invoked "$D/.bringup.stripped"; ck "and P1 goes RED when the call is stripped" 1 $?

# P2+P3 (v2) — the two liveness properties, now decided by execution. See the
# header: as text positions they were green across 26 reconciles that ran no
# sweep at all, and after the H95 repair they INVERT (the handler is defined near
# the top of the file, and `--check`'s contracted `exit 1` sits below it).
sh "$ROOT/spikes/H95_selfcheck_reach/check.sh" >"$D/.h95.out" 2>&1
ck "P2+P3 by EXECUTION: H95 check.sh green (reached on every exit path; delays no launch; exit codes unchanged)" 0 $?
[ -s "$D/.h95.out" ] && grep -q 'assertions, 0 FAILED' "$D/.h95.out"
ck "and that suite actually ran (its own summary line is present, not an empty pass)" 0 $?

# P4 — the module it calls actually distinguishes states. Without this, P1-P3 are
# satisfied by wiring in a script that prints nothing and returns 0.
python3 "$ROOT/spikes/harness/selfcheckall.py" --selfcheck >/dev/null 2>&1
ck "selfcheckall.py --selfcheck is green (8 checks, both exit directions)" 0 $?

rm -f "$B" "$D/.bringup.stripped" "$D/.h95.out"
echo
[ "$FAIL" -eq 0 ] && echo "H78 check: 5 assertions, 0 FAILED — the sweep is wired, reached, late, and ungated" \
                  || echo "H78 check: $FAIL FAILED"
exit "$FAIL"
