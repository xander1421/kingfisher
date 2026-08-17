#!/usr/bin/env bash
# check_live_launcher.sh v1 — A24 applied to a RUNNING PROCESS.
#
# THE DEFECT IT EXISTS FOR (H21, found 2026-08-17 by ATTACK cycle 18):
# `run_loop.sh` was fixed at 11:52 and 12:00. Every live launcher started at
# 11:49. They were still executing the OLD code, and nothing anywhere said so.
#
# MEASURED, not argued -- /tmp probe, a bash script editing itself mid-run:
#   * the loop body kept the PRE-EDIT text for every remaining iteration;
#   * and bash resumed reading AFTER the loop at a stale byte offset, dying with
#     `unexpected EOF while looking for matching '"'`.
# Bash parses a top-level `while ... done` once and runs it from memory, so a
# long-running launcher never sees an edit, and the code after its loop can be
# read as garbage.
#
# THE ASYMMETRY THAT MAKES "FIXED" AMBIGUOUS, and it is why this check is only
# about the launcher:
#   * `loop_gate.sh` is a FRESH PROCESS per turn end -- a hook fix is live at the
#     next stop, no relaunch needed. (Verified: the refusal text now names
#     .loop_signal.$CALLSIGN, which was edited at 11:52 into lanes spawned 11:49.)
#   * `run_loop.sh` is a LONG-RUNNING process -- a launcher fix is live only at
#     the next relaunch. H16 and the v4 callsign whitelist are both in this state
#     right now.
#
# A24 says a digest pins which artifact, not what is in it. This is the same
# sentence about processes: the file on disk is not the code that is running, and
# `git log` cannot tell you which lanes have the fix.
#
# REFUSES, per the harness rule that a gate refuses rather than warns.
# usage: bash spikes/harness/check_live_launcher.sh [--selfcheck]
# exit 0 = every live launcher is at or newer than run_loop.sh.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAUNCHER="$ROOT/run_loop.sh"

# macOS `ps` prints lstart as "Mon Aug 17 11:49:21 2026". Parsed rather than
# regex-sliced so a format change fails loudly instead of comparing nonsense.
start_epoch() { date -j -f "%a %b %d %T %Y" "$1" +%s 2>/dev/null; }

if [ "${1:-}" = "--selfcheck" ]; then
  # §12.3: the check ships a check. Both directions, because a comparison that
  # only ever sees one side is the happy-path coverage that let H1's 15-check
  # suite pass over a live defect.
  now=$(date +%s)
  fail=0
  stale_case=$(( now - 600 )); fresh_case=$(( now + 600 ))
  [ "$stale_case" -lt "$now" ] || { echo "SELFCHECK FAIL: stale not detected"; fail=1; }
  [ "$fresh_case" -ge "$now" ] || { echo "SELFCHECK FAIL: fresh misreported"; fail=1; }
  e=$(start_epoch "$(date '+%a %b %d %T %Y')")
  [ -n "$e" ] || { echo "SELFCHECK FAIL: cannot parse this platform's lstart"; fail=1; }
  [ "$fail" -eq 0 ] && echo "selfcheck: comparison and lstart parsing both work"
  exit "$fail"
fi

[ -f "$LAUNCHER" ] || { echo "REFUSE: no launcher at $LAUNCHER"; exit 1; }
mtime=$(stat -f %m "$LAUNCHER")
stale=0 seen=0

while IFS= read -r line; do
  pid=${line%% *}
  rest=${line#* }
  st=$(start_epoch "$rest")
  [ -n "$st" ] || { echo "REFUSE: cannot parse start time for pid $pid ('$rest')"; exit 1; }
  seen=$((seen + 1))
  if [ "$st" -lt "$mtime" ]; then
    stale=$((stale + 1))
    printf 'STALE  pid %-7s started %s, launcher modified %s -- running PRE-FIX code\n' \
      "$pid" "$(date -r "$st" '+%H:%M:%S')" "$(date -r "$mtime" '+%H:%M:%S')"
  fi
done < <(ps -eo pid,lstart,command | grep '[r]un_loop.sh' | awk '{print $1, $2, $3, $4, $5, $6}')

if [ "$seen" -eq 0 ]; then
  echo "no live launcher: nothing to be stale (this is not a pass, it is an absence)"
  exit 0
fi
if [ "$stale" -gt 0 ]; then
  echo "REFUSE: $stale of $seen live launcher processes predate run_loop.sh."
  echo "        Their fixes are on disk and NOT running. Relaunch is the only cure;"
  echo "        editing the file again changes nothing for them, and can corrupt"
  echo "        the tail they have not read yet."
  exit 1
fi
echo "all $seen live launcher processes are at or newer than run_loop.sh"
exit 0
