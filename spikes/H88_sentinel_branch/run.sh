#!/usr/bin/env bash
# H88 -- THE RUNNABLE CHECK (§12.3). One command, two-sided, and it FAILS WHEN
# THE FIX IS REVERTED.
#
# probe.sh v2 answers a question about ONE FILE ("does this census distinguish
# an absent .loop_fails from 0"). The ROW's verdict needs both sides, and this
# is the only thing that holds both:
#
#   PRE-FIX  spikes/H88_sentinel_branch/bringup.before_h88.sh  must be DEFECT_PRESENT
#   LIVE     bringup.sh                                        must be DEFECT_ABSENT
#
# The pre-fix arm is the NEGATIVE CONTROL and it is the half that matters:
# M1_10_patchlive recorded 2 of 4 probes scoring clean against a build with the
# bug fully present, and a passing check and an inert check are the same
# observation. If the pre-fix arm ever reads DEFECT_ABSENT, this probe stopped
# being able to see the defect and the live arm's green means nothing.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd ../.. && pwd)"
rc=0
run() { # run <label> <target> <expected-verdict>
  local out v
  out=$(KF_H88_TARGET="$2" bash ./probe.sh 2>&1)
  v=$(printf '%s\n' "$out" | sed -n 's/.*verdict=\([A-Z_]*\).*/\1/p' | tail -1)
  local c
  c=$(printf '%s\n' "$out" | sed -n 's/.*controls_ok=\([a-z]*\).*/\1/p' | tail -1)
  if [ "$v" = "$3" ] && [ "$c" = true ]; then
    printf '  %-8s PASS  %s -> %s (controls_ok=true)\n' "$1" "$(basename "$2")" "$v"
  else
    printf '  %-8s FAIL  %s -> verdict=%s controls_ok=%s, expected %s with all controls PASS\n' \
      "$1" "$(basename "$2")" "${v:-<none>}" "${c:-<none>}" "$3"
    printf '%s\n' "$out" | sed 's/^/          | /'
    rc=1
  fi
}
echo "=== H88 two-sided check ==="
run PRE-FIX "$PWD/bringup.before_h88.sh" DEFECT_PRESENT
run LIVE    "$ROOT/bringup.sh"           DEFECT_ABSENT
echo "h88_check=$([ $rc = 0 ] && echo PASS || echo FAIL)"
exit $rc
