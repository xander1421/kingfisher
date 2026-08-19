#!/bin/bash
# Shipped shape: $turn is the pipeline handle; the claude grandchild is
# independent. Supervisor death kills the pipeline pid; the dog gates pkill
# on kill -0 $turn, so it skips while the grandchild lives.
set -u
MAX="${1:-2}"
nohup bash -c 'exec -a h121stubproc sleep 30' >/dev/null 2>&1 &
stub=$!
sleep 100 &
turn=$!
echo "TURN=$turn STUB=$stub"
( sleep "$MAX"
  if kill -0 "$turn" 2>/dev/null; then
    echo DOG_FIRED_ON_PIPELINE
    pkill -f '^h121stubproc' 2>/dev/null
    kill -TERM "$turn" 2>/dev/null
  else
    echo DOG_SKIP_PIPELINE_DEAD
  fi
) &
echo "DOG=$!"
# supervisor death: pipeline handle gone, grandchild left
kill -TERM "$turn" 2>/dev/null
exit 0
