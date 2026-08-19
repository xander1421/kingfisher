#!/bin/bash
# H121: dog is disowned and bound to a generation file. It does NOT gate on
# the pipeline pid. A later generation is not reaped.
set -u
MAX="${1:-2}"
GENFILE="${2:-.loop_turn_gen.PROBE-H121}"
gen=$(date +%s)
printf '%s\n' "$gen" > "$GENFILE"
nohup bash -c 'exec -a h121stubproc sleep 30' >/dev/null 2>&1 &
stub=$!
sleep 100 &
turn=$!
echo "TURN=$turn STUB=$stub GEN=$gen"
(
  sleep "$MAX"
  now=$(cat "$GENFILE" 2>/dev/null || true)
  if [ "$now" = "$gen" ]; then
    echo DOG_FIRED
    pkill -f '^h121stubproc' 2>/dev/null
    kill -TERM "$turn" 2>/dev/null
  else
    echo DOG_SKIP_GEN now="$now" mine="$gen"
  fi
) &
disown
echo "DOG=$!"
kill -TERM "$turn" 2>/dev/null
exit 0
