#!/usr/bin/env bash
# H120 probe — GROK-LOCAL, 2026-08-18.
#
# CLAIM UNDER TEST: bringup.sh takes lane_pid (the turn) FIRST and falls
# back to the lock. An orphaned turn — `You are X.` with no live supervisor —
# therefore counts as UP and toward quorum.
#
# FALSIFIER, stated in CHANNEL.md before this file existed:
#   if a turn-only sandbox already prints ORPHAN and quorum 0/1, withdraw.
#
# WHY A SANDBOX: writing a real lane's lock or grepping a live turn is A23.
# The census is driven against a SYNTHETIC roster of one lane. Workspace only.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"
rm -rf "$SB"; mkdir -p "$SB/prompts"

fail=0
say() { printf '%s\n' "$*"; }
ctl() {
  [ "$2" = PASS ] || fail=1
  printf '  %-6s %-4s %s\n' "$1" "$2" "$3"
}

TARGET="${KF_H120_TARGET:-$ROOT/bringup.sh}"
cp "$TARGET" "$SB/bringup.sh"
h_live=$(shasum -a 256 "$TARGET" | awk '{print $1}')
h_copy=$(shasum -a 256 "$SB/bringup.sh"  | awk '{print $1}')
say "=== CONTROLS ==="
[ "$h_live" = "$h_copy" ] \
  && ctl C2 PASS "sandbox copy == $TARGET (${h_live:0:16})" \
  || ctl C2 FAIL "sandbox copy DIFFERS from $TARGET -- probe measures the wrong file"

printf 'PROBE-1\n' > "$SB/roster.txt"
printf 'synthetic lane, H120 probe. Not a real brief.\n' > "$SB/prompts/PROBE-1.md"
printf 'NOTE PROBE-1 synthetic\n' > "$SB/CHANNEL.md"

# Turn stub: argv carries `You are PROBE-1.` so lane_pid finds it.
bash -c 'exec -a "claude -p You are PROBE-1. stub" sleep 300' &
TURN=$!
# Supervisor stub: live pid, argv does NOT match lane_pid.
sleep 300 &
LOOP=$!
trap 'kill $TURN $LOOP 2>/dev/null; rm -rf "$SB"' EXIT
sleep 0.4

arm() {
  ( cd "$SB" && bash ./bringup.sh --check 2>&1; echo "EXIT=$?" )
}
lane_line() { grep -E '^\s+PROBE-1[[:space:]]+(UP|ORPHAN|DOWN|STALLED|HALTED)' ; }
q_line() { grep -E '^\s+quorum:' ; }

# C3: the stub must be visible, otherwise every arm measures DOWN.
rm -f "$SB/.loop_lock.PROBE-1" "$SB/.loop_fails.PROBE-1"
T1=$(arm | lane_line)
case "$T1" in
  *UP*|*ORPHAN*) ctl C3 PASS "turn stub reached: census sees PROBE-1 ($T1)" ;;
  *)             ctl C3 FAIL "turn stub NOT reached: '$T1' -- arms measure DOWN" ;;
esac

# C1: lock-only must be expressible as UP. If the census cannot say UP
# for a live supervisor, ORPHAN vs UP is not a real distinction.
rm -f "$SB/.loop_fails.PROBE-1"
printf '%s\n' "$LOOP" > "$SB/.loop_lock.PROBE-1"
# Hide the turn from lane_pid for this arm by killing its distinctive argv:
# we keep TURN alive later; for lock-only we rely on LOOP only, so stop TURN
# temporarily... no: lane_pid would still see TURN. Kill TURN for this arm
# and respawn after.
kill "$TURN" 2>/dev/null || true
wait "$TURN" 2>/dev/null || true
L1=$(arm | lane_line)
Q_LOCK=$(arm | q_line)
case "$L1" in
  *"UP "*) ctl C1 PASS "lock-only prints UP -- census can express a live supervisor" ;;
  *)       ctl C1 FAIL "lock-only did not print UP: '$L1' -- instrument cannot express the verdict" ;;
esac

# Respawn the turn stub for the orphan arm.
bash -c 'exec -a "claude -p You are PROBE-1. stub" sleep 300' &
TURN=$!
sleep 0.4
trap 'kill $TURN $LOOP 2>/dev/null; rm -rf "$SB"' EXIT

# THE ROW: turn present, lock absent.
rm -f "$SB/.loop_lock.PROBE-1" "$SB/.loop_fails.PROBE-1"
O1=$(arm | lane_line)
Q_ORPH=$(arm | q_line)

# Both present: supervisor wins, still UP (not ORPHAN).
printf '%s\n' "$LOOP" > "$SB/.loop_lock.PROBE-1"
B1=$(arm | lane_line)

say ""
say "=== ARMS (the PROBE-1 census line) ==="
say "  LOCK-ONLY : $L1"
say "  TURN-ONLY : $O1"
say "  BOTH      : $B1"
say "  q lock    : $Q_LOCK"
say "  q orphan  : $Q_ORPH"
say ""
say "=== VERDICT ==="
say "  target: $TARGET"
# Defect: turn-only is counted UP (quorum 1/1).
if printf '%s\n' "$O1" | grep -q 'UP ' && printf '%s\n' "$Q_ORPH" | grep -q '1/1'; then
  say "  DEFECT PRESENT. Turn-only is UP and quorum 1/1 — an orphan counts as healthy."
  VERDICT=DEFECT_PRESENT
elif printf '%s\n' "$O1" | grep -q ORPHAN && printf '%s\n' "$Q_ORPH" | grep -q '0/1'; then
  say "  DEFECT ABSENT. Turn-only is ORPHAN and not counted toward quorum."
  VERDICT=DEFECT_ABSENT
else
  say "  DEFECT UNDECIDED. Unexpected census: line='$O1' quorum='$Q_ORPH'"
  VERDICT=DEFECT_UNDECIDED
  fail=1
fi
say ""
say "controls: $([ $fail = 0 ] && echo 'all PASS' || echo 'AT LEAST ONE FAILED -- verdict not admissible')"
say "verdict=$VERDICT controls_ok=$([ $fail = 0 ] && echo true || echo false)"
[ $fail = 0 ] || exit 2
exit 0
