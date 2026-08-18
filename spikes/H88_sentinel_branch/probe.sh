#!/usr/bin/env bash
# H88 probe -- AGENT-1, 2026-08-17.
#
# CLAIM UNDER TEST: bringup.sh's `lane_fails()` returns -1 for "file absent",
# its comment says -1 "is NOT clear", and the ONLY consumer is
# `[ "$nfail" -ge 2 ]`. -1 >= 2 is false and 0 >= 2 is false, so ABSENT takes
# the same branch as HEALTHY and the census prints an identical line.
#
# FALSIFIER, stated in CHANNEL.md before this file existed:
#   "if an absent .loop_fails already produces output distinguishable from
#    nfail=0, there is no defect and I withdraw H88."
#
# WHY A SANDBOX AND NOT THE LIVE FLEET: writing `.loop_fails.<lane>` for a real
# lane is (a) A23, the instrument perturbing what it observes, and (b) another
# lane's per-lane state, which H19/H66 make not mine to write. So the census is
# driven against a SYNTHETIC roster of one lane, with a stub process supplying
# the argv `lane_pid` greps for. Everything stays inside the workspace (S10).
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"
rm -rf "$SB"; mkdir -p "$SB/prompts"

fail=0
say() { printf '%s\n' "$*"; }
ctl() { # ctl <name> <PASS|FAIL> <text>
  [ "$2" = PASS ] || fail=1
  printf '  %-6s %-4s %s\n' "$1" "$2" "$3"
}

# ---------------------------------------------------------------- C2 (A24/H35)
# The sandbox copy must be the LIVE file, byte for byte. H35/H36's class is a
# check measuring a gate against the wrong copy of its source; asserting the
# digest is the one line that makes this probe about bringup.sh at all.
# TARGET is overridable so this probe can be run TWO-SIDED: against the live
# file (must WITHDRAW, the fix is in) and against bringup.before_h88.sh (must
# CONFIRM, the defect was real). A one-sided run on the fixed file proves only
# that today is green -- A29's "reaching the target is a precondition of the
# verdict" applied to a repair rather than to a bug.
TARGET="${KF_H88_TARGET:-$ROOT/bringup.sh}"
cp "$TARGET" "$SB/bringup.sh"
h_live=$(shasum -a 256 "$TARGET" | awk '{print $1}')
h_copy=$(shasum -a 256 "$SB/bringup.sh"  | awk '{print $1}')
say "=== CONTROLS ==="
[ "$h_live" = "$h_copy" ] \
  && ctl C2 PASS "sandbox copy == $TARGET (${h_live:0:16})" \
  || ctl C2 FAIL "sandbox copy DIFFERS from $TARGET -- probe measures the wrong file"
# CAN FAIL BECAUSE: edit the copy, or copy a different path, and it goes red.

printf 'PROBE-1\n' > "$SB/roster.txt"
printf 'synthetic lane, H88 probe. Not a real brief.\n' > "$SB/prompts/PROBE-1.md"
# lane_lastwork reads CHANNEL.md and returns -1 without it; give it one line so
# the work column is a constant across arms rather than another moving part.
printf 'NOTE PROBE-1 synthetic\n' > "$SB/CHANNEL.md"

# The stub: a process whose argv carries `You are PROBE-1.` exactly as the launch
# prompt does, so lane_pid's `grep -F "You are PROBE-1."` finds it.
bash -c 'exec -a "claude -p You are PROBE-1. stub" sleep 300' &
STUB=$!
trap 'kill $STUB 2>/dev/null; rm -rf "$SB"' EXIT
sleep 0.4

arm() { # arm <label> -- runs the census, echoes exit code as last line
  ( cd "$SB" && bash ./bringup.sh --check 2>&1; echo "EXIT=$?" )
}
lane_line() { grep -E '^\s+PROBE-1' ; }

# ---------------------------------------------------------------- C3 (A29)
# A probe that cannot show it reached its target has produced no evidence. If
# lane_pid does not see the stub, PROBE-1 is DOWN, the STALLED branch is never
# evaluated, and every arm below is measuring the DOWN path instead.
rm -f "$SB/.loop_fails.PROBE-1"
A1=$(arm | lane_line)
case "$A1" in
  *"UP "*) ctl C3 PASS "stub reached: census sees PROBE-1 UP, so the nfail branch is evaluated" ;;
  *)       ctl C3 FAIL "stub NOT reached: '$A1' -- nfail is never consulted, arms measure the DOWN path" ;;
esac
# CAN FAIL BECAUSE: kill the stub before this line and it goes red.

# ---------------------------------------------------------------- C1 (positive)
# The instrument must be able to produce the answer it is being asked for. If
# nfail=2 does NOT print STALLED, this probe cannot distinguish any nfail value
# and a null result below would mean nothing.
printf '2\n' > "$SB/.loop_fails.PROBE-1"
C=$(arm | lane_line)
case "$C" in
  *STALLED*) ctl C1 PASS "nfail=2 prints STALLED -- the census CAN distinguish an nfail value" ;;
  *)         ctl C1 FAIL "nfail=2 did not print STALLED: '$C' -- instrument cannot express the verdict" ;;
esac

# ---------------------------------------------------------------- C4 (H70)
# Vary ONE thing. The two arms differ only in the presence of .loop_fails.PROBE-1
# and are run interleaved A,B,A,B; A==A and B==B establishes that nothing else
# in this census moves between runs (the OFF-ROSTER block reads the live `ps`).
rm -f "$SB/.loop_fails.PROBE-1"; A1=$(arm | lane_line)
printf '0\n' > "$SB/.loop_fails.PROBE-1"; B1=$(arm | lane_line)
rm -f "$SB/.loop_fails.PROBE-1"; A2=$(arm | lane_line)
printf '0\n' > "$SB/.loop_fails.PROBE-1"; B2=$(arm | lane_line)
if [ "$A1" = "$A2" ] && [ "$B1" = "$B2" ]; then
  ctl C4 PASS "noise floor zero: A==A and B==B across interleaved runs"
else
  ctl C4 FAIL "arms are not stable across repeats -- a difference below is not attributable"
fi

say ""
say "=== ARMS (the PROBE-1 census line) ==="
say "  A  .loop_fails ABSENT : $A1"
say "  B  .loop_fails = 0    : $B1"
say "  C  .loop_fails = 2    : $C"
say ""
# THE VERDICT NAMES THE FILE, NOT THE ROW -- v2, and this was a live defect in
# v1. v1 printed "H88 CONFIRMED" / "H88 WITHDRAWN", which are answers about the
# ROW, and the row's answer flips meaning depending on WHICH SIDE OF THE FIX the
# target sits on. Run against the repaired bringup.sh, v1 said "H88 WITHDRAWN.
# The falsifier FIRED" -- reporting the REPAIR as a RETRACTION of the finding,
# the exact opposite of the truth, with nothing in the output naming the side.
# CLASS: A VERDICT STRING THAT ASSUMES ITS INPUT. What the probe can actually
# observe is a property of one file, so that is what it now says; the row's
# verdict is composed from two runs by run.sh, which is the only thing that
# knows both sides.
say "=== VERDICT ==="
say "  target: $TARGET"
if [ "$A1" = "$B1" ]; then
  say "  DEFECT PRESENT. ABSENT and HEALTHY(0) are BYTE-IDENTICAL in this"
  say "  census: the sentinel is computed, documented as 'NOT clear', and read"
  say "  by a branch that cannot tell it from clear."
  VERDICT=DEFECT_PRESENT
else
  say "  DEFECT ABSENT. This census distinguishes an absent counter from 0."
  VERDICT=DEFECT_ABSENT
fi
say ""
say "controls: $([ $fail = 0 ] && echo 'all PASS' || echo 'AT LEAST ONE FAILED -- verdict not admissible')"
say "verdict=$VERDICT controls_ok=$([ $fail = 0 ] && echo true || echo false)"
[ $fail = 0 ] || exit 2
exit 0
