#!/usr/bin/env bash
# test_h232_falsify.sh v1 — H232, ok-1, 2026-08-19.
#
# The check that has never been red on purpose is a check with a regression
# record and no detection record. Each mutant below removes one property of
# run_loop.sh v11's per-turn lock re-read and requires the probe arm that owns
# that property to go RED while the others stay GREEN -- a mutant that reddens
# everything proves only that the probe notices damage.
#
# Every mutation asserts THAT THE EDIT APPLIED (H217: a silent no-op edit is how
# an inert flag ships) and that the mutant still parses. Two-sided: the control
# run at the end is the shipped launcher and must be all-green.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/run_loop.sh"
SB="$ROOT/.scratch/h232_falsify.$$"
mkdir -p "$SB"
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1";
       else fail=$((fail+1)); printf '  FAIL  %s (want %s, got %s)\n' "$1" "$3" "$2"; fi; }

mutate() {   # mutate <name> <M1|M2|M3>
  local name="$1" which="$2" out="$SB/$1.sh"
  python3 "$ROOT/spikes/harness/h232_mutants.py" "$SRC" "$out" "$which" >/dev/null || {
    echo "  FAIL  $name: the edit did not apply (anchor missing)"; fail=$((fail+1)); return 1; }
  chmod +x "$out"
  cmp -s "$SRC" "$out" && { echo "  FAIL  $name: the edit did not apply (copy is byte-identical)"; fail=$((fail+1)); return 1; }
  bash -n "$out" || { echo "  FAIL  $name: mutant does not parse"; fail=$((fail+1)); return 1; }
  return 0
}

arm() {      # arm <mutant> <check substring> <want PASS|FAIL>
  local out="$1" want="$3" got
  if printf '%s' "$out" | grep -q "FAIL  $2"; then got=FAIL
  elif printf '%s' "$out" | grep -q "PASS  $2"; then got=PASS
  else got=ABSENT; fi
  ck "    arm '$2'" "$got" "$want"
}

echo "H232 falsifier — three mutants of run_loop.sh v11's per-turn lock re-read"

# M1 · the re-read deleted: the exact pre-H232 launcher.
if mutate M1_no_reread M1; then
  o=$(KF_TEST_LAUNCHER="$SB/M1_no_reread.sh" bash "$ROOT/spikes/H232_two_lanes_one_lock/probe.sh" 2>&1)
  echo "  M1 · the lock is never re-read (pre-H232 behaviour)"
  arm "$o" "a launcher that has lost the lock stops producing turns" FAIL
  arm "$o" "a lane whose lock was DELETED keeps running" PASS
fi

# M2 · retire on ANY mismatch: the absent/dead re-acquire branch removed.
if mutate M2_always_retire M2; then
  o=$(KF_TEST_LAUNCHER="$SB/M2_always_retire.sh" bash "$ROOT/spikes/H232_two_lanes_one_lock/probe.sh" 2>&1)
  echo "  M2 · any mismatch retires, so a deleted lock kills the lane"
  arm "$o" "a lane whose lock was DELETED keeps running" FAIL
  arm "$o" "a launcher that has lost the lock stops producing turns" PASS
fi

# M3 · liveness by pid alone, which reports HELD for any reused pid.
if mutate M3_kill0_only M3; then
  o=$(KF_TEST_LAUNCHER="$SB/M3_kill0_only.sh" bash "$ROOT/spikes/H232_two_lanes_one_lock/probe.sh" 2>&1)
  echo "  M3 · liveness by pid alone (a reused pid reads as the holder)"
  arm "$o" "a lock naming a live NON-launcher does not retire the lane" FAIL
  arm "$o" "a launcher that has lost the lock stops producing turns" PASS
fi

# CONTROL. rc=0 is also what a suite that never ran returns, so the count is read.
o=$(bash "$ROOT/spikes/H232_two_lanes_one_lock/probe.sh" 2>&1)
echo "  CONTROL · the shipped launcher"
ck "    probe is all-green on run_loop.sh as shipped" \
   "$(printf '%s' "$o" | sed -n 's/^probe: \([0-9]*\) passed, \([0-9]*\) failed$/\2/p')" "0"
ck "    and it actually ran its arms" \
   "$([ "$(printf '%s' "$o" | sed -n 's/^probe: \([0-9]*\) passed.*/\1/p')" -ge 9 ] && echo ran || echo empty)" "ran"

rm -rf "$SB"
echo
echo "falsifier: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ]
