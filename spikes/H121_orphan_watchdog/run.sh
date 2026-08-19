#!/usr/bin/env bash
# H121 two-sided: sandbox pattern + shipped run_loop.sh contains the same shape.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd ../.. && pwd)"
fail=0
say() { printf '%s\n' "$*"; }

say "=== pattern probe ==="
bash ./probe.sh || fail=1

say ""
say "=== run_loop.sh source ==="
src="$ROOT/run_loop.sh"
if grep -q 'loop_turn_gen' "$src"; then
  say "  PASS  writes .loop_turn_gen.\$CALLSIGN"
else
  say "  FAIL  no generation file"; fail=1
fi
if grep -E '^[[:space:]]*if kill -0 "\$turn"' "$src" >/dev/null; then
  say "  FAIL  still gates watchdog on kill -0 \$turn"; fail=1
else
  say "  PASS  watchdog does not gate on pipeline pid"
fi
if grep -q 'disown' "$src"; then
  say "  PASS  dog is disowned"
else
  say "  FAIL  dog is still a job of the wrapper"; fail=1
fi
if grep -q 'ended-' "$src"; then
  say "  PASS  gen invalidated on clean turn end"
else
  say "  FAIL  gen not invalidated"; fail=1
fi

if [ "$fail" = 0 ]; then
  say "H121 CONFIRMED then FIXED. Pipeline-dead dog skipped; gen-bound dog reaps; run_loop.sh matches."
  exit 0
fi
say "H121 NOT CLOSED"
exit 1
