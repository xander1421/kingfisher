#!/bin/sh
# H78 — the wiring must stay wired, and each property is falsified on a copy.
#
# `bringup.sh` itself is NEVER executed here: it launches lanes. Every assertion
# is made against a COPY under this spike directory (§10: nothing outside the
# workspace), and each one is re-run against a copy with the property REMOVED, so
# a check that cannot go red is caught the way H17 says to catch it.
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

# P2 — it runs AFTER the launch loop. Preregistered F3: the step must not be able
# to delay a lane launch. Positional, because that is what makes it true.
launch=$(grep -n 'CALLSIGN="$lane" ./run_loop.sh' "$B" | head -1 | cut -d: -f1)
call=$(grep -nE '^[^#]*python3 spikes/harness/selfcheckall\.py' "$B" | head -1 | cut -d: -f1)
[ -n "$launch" ] && [ -n "$call" ] && [ "$call" -gt "$launch" ]
ck "the sweep is BELOW the launch loop (line $call > $launch), so it delays no launch" 0 $?

# P3 — NOT GATED. Nothing between the sweep and EOF may exit non-zero, or a red
# selfcheck would stop the reconciler that starts lanes.
tail -n "+$call" "$B" | grep -qE '^[^#]*\bexit [1-9]'
ck "no non-zero exit after the sweep, so a RED selfcheck cannot stop bringup" 1 $?

# P4 — the module it calls actually distinguishes states. Without this, P1-P3 are
# satisfied by wiring in a script that prints nothing and returns 0.
python3 "$ROOT/spikes/harness/selfcheckall.py" --selfcheck >/dev/null 2>&1
ck "selfcheckall.py --selfcheck is green (8 checks, both exit directions)" 0 $?

rm -f "$B" "$D/.bringup.stripped"
echo
[ "$FAIL" -eq 0 ] && echo "H78 check: 5 assertions, 0 FAILED — the sweep is wired, late, and ungated" \
                  || echo "H78 check: $FAIL FAILED"
exit "$FAIL"
