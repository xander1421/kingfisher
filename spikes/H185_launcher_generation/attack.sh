#!/usr/bin/env bash
# H185 ATTACK -- ok-1, 2026-08-19, on my own bringup.sh v7 from one cycle earlier.
#
# TARGET BY RULE (§2 self-authored data first, §12.8 the loop). v7's own probe
# asserts `unrecorded` is NOT silence -- H88's defect, controlled for. This asks
# the question that control does not: WHEN IT SAYS `unrecorded`, IS THAT ABOUT
# THE LANE?
#
# THE FINDING: three causes printed one name.
#   1. no stamp file            -- the intended meaning, a fact about the lane
#   2. stamp present but empty  -- a corrupt stamp, a different fact
#   3. ./run_loop.sh unreadable from the census's cwd -- A FACT ABOUT THE CENSUS,
#      which would print for EVERY lane at once and read as "an old fleet"
#
# H88's class re-earned inside the control written to prevent it. v8 names all
# three. Two-sided against a pinned pre-fix rev, because a one-sided green proves
# only that today is green.
#
# usage: bash spikes/H185_launcher_generation/attack.sh [prefix-rev]
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/attack_sandbox"; CS="PROBE-6"; PREREV="${1:-29aee62}"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-5s %-4s %s\n' "$1" "$2" "$3"; }
STUB=""
cleanup() { [ -n "$STUB" ] && kill "$STUB" 2>/dev/null; rm -rf "$SB"; }
trap cleanup EXIT

setup() {  # setup <bringup-source>
  rm -rf "$SB"; mkdir -p "$SB/prompts"
  cp "$1" "$SB/bringup.sh"
  cp "$ROOT/run_loop.sh" "$SB/run_loop.sh"
  printf '%s\n' "$CS" > "$SB/roster.txt"
  printf 'synthetic lane, H185 attack\n' > "$SB/prompts/${CS}.md"
  printf 'NOTE PROBE-6 synthetic\n' > "$SB/CHANNEL.md"
  # a live pid in the lock file is all the census needs to call the lane UP
  bash -c 'exec -a "claude -p You are PROBE-6. stub" sleep 240' &
  STUB=$!
  sleep 0.3
  echo "$STUB" > "$SB/.loop_lock.${CS}"
  date +%s > "$SB/.heartbeat.${CS}"
  # a VALID stamp: this lane is running exactly the launcher in the tree
  printf '%s %s\n' "$(shasum -a 256 "$SB/run_loop.sh" | cut -c1-16)" "$(date +%s)" \
    > "$SB/.loop_launcher.${CS}"
}
line() { ( cd "$SB" && bash ./bringup.sh --check 2>&1 ) | grep -E "^ +${CS}" || true; }

run_arms() {  # run_arms <label>
  local tag="$1" L
  L=$(line)
  case "$L" in *" UP "*) ctl "${tag}C" PASS "census sees ${CS} UP (arms are not vacuous)" ;;
                      *) ctl "${tag}C" FAIL "not UP: '$L'" ;; esac
  case "$L" in *LAUNCHER*) ctl "${tag}0" FAIL "a VALID current stamp printed a note: '$L'" ;;
                        *) ctl "${tag}0" PASS "valid stamp: quiet" ;; esac

  # CAUSE 3 -- the launcher is unreadable FROM THE CENSUS. Nothing about the lane.
  mv "$SB/run_loop.sh" "$SB/run_loop.hidden"
  L=$(line)
  case "$L" in
    *UNCOMPARABLE*) ctl "${tag}1" PASS "names the CENSUS's own inability (UNCOMPARABLE)" ;;
    *UNRECORDED*)   ctl "${tag}1" FAIL "CONFLATION: a missing ./run_loop.sh reads as 'the lane is old'" ;;
    *)              ctl "${tag}1" FAIL "unexpected: '$L'" ;;
  esac
  mv "$SB/run_loop.hidden" "$SB/run_loop.sh"

  # CAUSE 2 -- the stamp exists and carries no hash.
  printf '\n' > "$SB/.loop_launcher.${CS}"
  L=$(line)
  case "$L" in
    *UNREADABLE*) ctl "${tag}2" PASS "names a corrupt stamp (UNREADABLE), distinct from old" ;;
    *UNRECORDED*) ctl "${tag}2" FAIL "CONFLATION: a corrupt stamp reads as 'the lane is old'" ;;
    *)            ctl "${tag}2" FAIL "unexpected: '$L'" ;;
  esac

  # CAUSE 1 -- the intended meaning must still work.
  rm -f "$SB/.loop_launcher.${CS}"
  L=$(line)
  case "$L" in
    *UNRECORDED*) ctl "${tag}3" PASS "no stamp still reads UNRECORDED (the intended meaning survives)" ;;
    *)            ctl "${tag}3" FAIL "no stamp reads '$L'" ;;
  esac

  # THE RAIL -- none of these may move the lane out of UP or refuse quorum.
  ( cd "$SB" && bash ./bringup.sh --check 2>&1 ) | grep -qE 'DOWN|STARTING|FLAPPING' \
    && ctl "${tag}4" FAIL "a launcher note moved the lane out of UP" \
    || ctl "${tag}4" PASS "still UP, not MISSING, quorum untouched"
}

echo "=== TARGET: the live bringup.sh ==="
setup "$ROOT/bringup.sh"
run_arms A

echo "=== TARGET: ${PREREV}:bringup.sh (pre-attack, pinned) ==="
git -C "$ROOT" show "${PREREV}:bringup.sh" > "$SPIKE/bringup.pre.sh" || exit 2
grep -q 'lane_launcher' "$SPIKE/bringup.pre.sh" \
  || { echo "  REFUSING: ${PREREV} has no lane_launcher -- wrong rev, the arm is not two-sided"; exit 2; }
grep -q 'uncomparable' "$SPIKE/bringup.pre.sh" \
  && { echo "  REFUSING: ${PREREV} already carries the fix -- the arm is not two-sided"; exit 2; }
setup "$SPIKE/bringup.pre.sh"
# Only the conflation arm is meaningful pre-fix; it MUST fail there, so its
# verdict is inverted here rather than counted as a failure of this probe.
mv "$SB/run_loop.sh" "$SB/run_loop.hidden"
L=$(line)
case "$L" in
  *UNRECORDED*) printf '  %-5s %-4s %s\n' "B1" "PASS" "pre-fix: a missing ./run_loop.sh DID read as 'the lane is old' -- the defect was real" ;;
  *)            ctl B1 FAIL "pre-fix printed '$L' -- the defect was not what the row says" ;;
esac
rm -f "$SPIKE/bringup.pre.sh"

echo
[ "$fail" = 0 ] && echo "H185 attack: all arms as stated" || echo "H185 attack: FAILED"
exit "$fail"
