#!/usr/bin/env bash
# H173 ATTACK -- ok-1, 2026-08-19, on my own branch shipped 20 minutes earlier.
#
# TARGET CHOSEN BY RULE (§2: instruments before conclusions, self-authored data
# first; §12.8: every fourth attack is the loop itself). FLAPPING is the newest
# code in the fleet's restart path, it is mine, it shipped this cycle, and its
# failure direction is the WORSE one: a false FLAPPING means a dead fleet is
# never relaunched. probe.sh drove `--check`, which NEVER REACHES THE LAUNCH
# PATH -- that is my own H117 FA1 class ("the tested path is not the executed
# path") in the module I wrote one cycle after naming it.
#
# So this drives bringup.sh in its DEFAULT mode, the one launchd runs, against a
# stub `run_loop.sh` that records its invocation and exits.
#
# usage: bash spikes/H173_flapping_lane/attack.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/attack_sandbox"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-5s %-4s %s\n' "$1" "$2" "$3"; }

setup() {
  rm -rf "$SB"; mkdir -p "$SB/prompts"
  cp "$ROOT/bringup.sh" "$SB/bringup.sh"
  # The stub IS the observation: bringup launching a lane means this file runs.
  cat > "$SB/run_loop.sh" <<'STUB'
#!/usr/bin/env bash
echo "$CALLSIGN" >> launched.txt
STUB
  chmod +x "$SB/run_loop.sh"
  printf 'FLAP-1\nGOOD-1\n' > "$SB/roster.txt"
  printf 'synthetic, H173 attack\n' > "$SB/prompts/FLAP-1.md"
  printf 'synthetic, H173 attack\n' > "$SB/prompts/GOOD-1.md"
  printf 'NOTE FLAP-1 synthetic\nNOTE GOOD-1 synthetic\n' > "$SB/CHANNEL.md"
  : > "$SB/launched.txt"
}
stamps() { # stamps <lane> <count> <age>
  local n=$2 now; now=$(date +%s); rm -f "$SB/.loop_launches.$1"
  while [ "$n" -gt 0 ]; do echo $(( now - $3 )) >> "$SB/.loop_launches.$1"; n=$(( n - 1 )); done
}
run_default() { ( cd "$SB" && bash ./bringup.sh 2>&1; echo "EXIT=$?" ); }

echo "=== A1 · THE EXECUTED PATH: bringup's DEFAULT mode, not --check ==="
setup
stamps FLAP-1 3 60          # flapping
rm -f "$SB/.loop_launches.GOOD-1"   # first time down
OUT=$(run_default)
LAUNCHED=$(cat "$SB/launched.txt" | tr '\n' ' ')
# A29 -- if NOTHING launched, every assertion below passes for the wrong reason.
case "$LAUNCHED" in
  *GOOD-1*) ctl A29 PASS "the launch path was REACHED (GOOD-1 ran run_loop.sh)" ;;
  *)        ctl A29 FAIL "nothing launched at all: '$LAUNCHED' -- arms below are vacuous" ;;
esac
case "$LAUNCHED" in
  *FLAP-1*) ctl A1 FAIL "FLAP-1 WAS LAUNCHED in default mode -- the refusal only exists under --check" ;;
  *)        ctl A1 PASS "FLAP-1 not launched; GOOD-1 launched in the same run" ;;
esac
printf '%s\n' "$OUT" | grep -q 'FLAPPING' \
  && ctl A2 PASS "the census names it: FLAPPING printed in default mode" \
  || ctl A2 FAIL "default mode printed no FLAPPING line"

echo "=== A3 · the stamp is written by the LAUNCH, not by the census ==="
# `wc -l` pads with spaces on macOS, so a STRING compare against it reads a
# correct count as wrong -- caught by this arm going red on its first run.
n=$(( $(wc -l < "$SB/.loop_launches.GOOD-1" 2>/dev/null || echo 0) ))
[ "$n" -eq 1 ] && ctl A3 PASS "GOOD-1 has exactly 1 launch stamp after 1 launch" \
             || ctl A3 FAIL "GOOD-1 has $n stamp(s) -- the record is not the launch"
n=$(( $(wc -l < "$SB/.loop_launches.FLAP-1" 2>/dev/null || echo 0) ))
[ "$n" -eq 3 ] && ctl A4 PASS "a REFUSED lane accrues no new stamp (still 3) -- self-clearing holds" \
             || ctl A4 FAIL "FLAP-1 has $n stamps -- a refusal that stamps itself never clears"

echo "=== A5 · DEFAULTS, unset. probe.sh set FLAP_WINDOW/FLAP_MAX; launchd sets neither ==="
setup
stamps FLAP-1 3 60
rm -f "$SB/.loop_launches.GOOD-1"
OUT=$( cd "$SB" && env -u FLAP_WINDOW -u FLAP_MAX bash ./bringup.sh 2>&1 )
printf '%s\n' "$OUT" | grep -q 'FLAPPING' \
  && ctl A5 PASS "fires on built-in defaults with no env at all" \
  || ctl A5 FAIL "no FLAPPING without env -- the probe measured a configuration nobody runs"

echo "=== A6 · THE WORSE DIRECTION: two launches must NOT refuse ==="
setup
stamps FLAP-1 2 60
rm -f "$SB/.loop_launches.GOOD-1"
run_default >/dev/null
grep -q 'FLAP-1' "$SB/launched.txt" \
  && ctl A6 PASS "2 launches in the window still relaunch (boundary is >=3, not >=2)" \
  || ctl A6 FAIL "2 launches refused -- the gate is tighter than stated and stops healthy recovery"

echo "=== A7 · a corrupt stamp file must not decide anything ==="
setup
printf 'not-a-number\n\nNaN\n' > "$SB/.loop_launches.FLAP-1"
rm -f "$SB/.loop_launches.GOOD-1"
OUT=$(run_default)
grep -q 'FLAP-1' "$SB/launched.txt" \
  && ctl A7 PASS "garbage stamps count as 0 launches -- lane still relaunched" \
  || ctl A7 FAIL "garbage stamps refused the lane: '$(printf '%s' "$OUT" | grep FLAP-1 | head -1)'"

rm -rf "$SB"
echo
[ "$fail" = 0 ] && echo "H173 attack: all arms as stated" || echo "H173 attack: FAILED"
exit "$fail"
