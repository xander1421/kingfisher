#!/usr/bin/env bash
# H120 two-sided run. Probe names a property of ONE file.
# This script is the only thing that knows both sides.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd ../.. && pwd)"
BEFORE="$PWD/bringup.before_h120.sh"
AFTER="$ROOT/bringup.sh"

fail=0
say() { printf '%s\n' "$*"; }

say "=== BEFORE (HEAD census: turn first) ==="
OUT_B=$(KF_H120_TARGET="$BEFORE" bash ./probe.sh) || fail=1
printf '%s\n' "$OUT_B"
V_B=$(printf '%s\n' "$OUT_B" | awk -F= '/^verdict=/{print $2}' | awk '{print $1}')
say ""
say "=== AFTER (live bringup.sh) ==="
OUT_A=$(KF_H120_TARGET="$AFTER" bash ./probe.sh) || fail=1
printf '%s\n' "$OUT_A"
V_A=$(printf '%s\n' "$OUT_A" | awk -F= '/^verdict=/{print $2}' | awk '{print $1}')

say ""
say "=== ROW ==="
if [ "$V_B" = DEFECT_PRESENT ] && [ "$V_A" = DEFECT_ABSENT ]; then
  say "H120 CONFIRMED then FIXED. Before: turn-only UP quorum 1/1. After: ORPHAN quorum 0/1."
  [ $fail = 0 ] || exit 2
  exit 0
fi
say "H120 NOT CLOSED. before=$V_B after=$V_A"
exit 1
