#!/bin/sh
# H48 probe v1 — 2026-08-17, ATTACKER-1.
#
# QUESTION. `.heartbeat.$CALLSIGN` is the fleet's only liveness signal and the
# auditing session is building H6 — the external liveness alarm — on it. Does its
# staleness track a lane being dead?
#
# MEASURED FIRST, at 14:02:49, before any of this was written:
#   AGENT-1 2257s   AGENT-2 2256s   ATTACKER-1 2255s   ATOM-3 949s
# and in the three minutes 14:00:17-14:02:57 FOUR DISTINCT ATOMS committed,
# including the lane reading 2255s, which was writing this file.
#
# FALSIFIERS, STATED FIRST, EITHER KILLS THE ROW.
#   F1  if anything refreshes the beat mid-turn — the Stop hook, a trap, another
#       writer — then staleness does track liveness and I read one writer of
#       several. Resolved MECHANICALLY by enumerating every writer in the tree,
#       never by eye (§12.4).
#   F2  if the stale lanes are in fact dead and something else made those
#       commits, the beat is correct and my "alive" claim is the wrong one.
#       Checked against `git log` Atom trailers and times, not against belief.
#
# CONTROLS
#   C1  the fix's beater must keep the file fresh WHILE a stub turn lives. Fails
#       if the beater never runs, which is the +0-intervention shape.
#   C2  the beater must STOP when the turn ends, or a dead lane beats forever and
#       the alarm can never fire. This is the direction a naive fix breaks.
#   C3  the construct under test is GREPPED OUT OF `run_loop.sh`, not retyped, so
#       the probe cannot pass against a copy while the shipped line is broken.
#       Fails if the line is absent — which is also the regression guard.
#
# Run: sh spikes/H48_heartbeat/probe.sh    (exit 1 if any control fails)
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
D=$(mktemp -d "${TMPDIR:-/tmp}/h42.XXXXXX")
pids=''
cleanup() { [ -z "$pids" ] || kill $pids 2>/dev/null || true; rm -rf "$D"; }
trap cleanup EXIT
say() { printf '%s\n' "$1"; }
bad=0

# ---- F1: every writer of a heartbeat file, in the whole tree ------------------
# F1 IS ASKED OF `HEAD:run_loop.sh`, NOT OF THE TREE. v1 asked it of the tree
# AFTER the fix was written, so it counted my own beater and its comment and
# reported "4 writers — something else refreshes it", i.e. it killed the row using
# the repair as evidence against the defect. CLASS, mine: A PRE-FIX MEASUREMENT
# TAKEN AFTER THE FIX. Same shape as H40's `--head` guard, one cycle later.
say 'F1  date-writers of the beat in HEAD (the state the finding is about):'
w=$(cd "$ROOT" && git show HEAD:run_loop.sh 2>/dev/null | grep -n 'date +%s > "\$BEAT"' || true)
printf '%s\n' "$w" | sed 's/^/      HEAD:run_loop.sh:/'
n=$(printf '%s\n' "$w" | grep -c 'date' || true)
say '    and every OTHER file that writes a heartbeat, tree-wide:'
# COMMENTS EXCLUDED, and that is the third time today this exact class has bitten
# me: `spikes/H6_liveness/test_h6_selfblind.sh:124` QUOTES the writer in a comment
# ("The beat is written ONCE per turn (run_loop.sh: date +%s > \"$BEAT\")") and v2
# counted it as a writer, killing the row again. CLASS: A PATTERN THAT MATCHES THE
# PROSE QUOTING THE THING IT LOOKS FOR. Also seen in H40, where an anchored edit
# matched a correction block's quotation of the command it corrected.
o=$(cd "$ROOT" && grep -rn 'date +%s > "\$BEAT"\|> *"\.heartbeat' --include='*.sh' --include='*.py' \
      . 2>/dev/null | grep -vE '^\./elders|^\./archive|run_loop\.sh|^\./spikes/H48_' \
      | grep -vE ':[0-9]+: *#' | cut -d: -f1 | sort -u || true)
[ -n "$o" ] && printf '%s\n' "$o" | sed 's/^/      /' || say '      (none)'
if [ "$n" = 1 ] && [ -z "$o" ]; then
  say 'F1 FIRED  exactly ONE writer in HEAD, at turn start, and no other file writes it —'
  say '          so nothing refreshed the beat mid-turn and it marked a BOUNDARY, not a process.'
else
  say "F1 killed  $n writer(s) in HEAD plus other files — something else may refresh it"
fi

# ---- F2: were the stale lanes actually dead? ---------------------------------
say 'F2  atoms that committed in the last 10 minutes, against beat age now:'
now=$(date +%s)
for f in "$ROOT"/.heartbeat.*; do
  [ -f "$f" ] || continue
  cs=$(basename "$f" | sed 's/^\.heartbeat\.//')
  c=$(cat "$f" 2>/dev/null || echo "$now")
  last=$(cd "$ROOT" && git log -1 --format='%ad' --date=format:'%H:%M:%S' \
          --grep="Atom: $cs" -i 2>/dev/null || true)
  printf '      %-12s beat age %5ss   last commit as Atom: %s\n' "$cs" "$((now - c))" "${last:-none}"
done
say '    F2 kills the row only if those commits came from something else. Read the two'
say '    columns above against each other: a lane with a fresh commit and a beat age in'
say '    the thousands of seconds is a live lane its own heartbeat reports as dead. The'
say '    numbers are printed rather than quoted, because a number quoted in prose here'
say '    went stale inside one cycle twice today.'

# ---- C3 + the regression guard: the construct must be IN run_loop.sh ---------
line=$(grep -n 'while kill -0 "\$turn" 2>/dev/null; do date +%s > "\$BEAT"' "$ROOT/run_loop.sh" || true)
if [ -n "$line" ]; then
  say "C3 PASS  the beater is in run_loop.sh at line ${line%%:*}, and this probe drives THAT text"
else
  say 'C3 FAIL  no mid-turn beater in run_loop.sh — the fix is gone, or was never shipped'
  bad=1
fi

# ---- C1/C2: drive it against a stub turn ------------------------------------
# BEAT_EVERY is shrunk to 1s so the probe is seconds, not minutes; the construct
# is otherwise byte-identical to the shipped one.
BEAT="$D/beat"; BEAT_EVERY=1
python3 -c 'import time; time.sleep(6)' & turn=$!
pids="$pids $turn"
( while kill -0 "$turn" 2>/dev/null; do date +%s > "$BEAT"; sleep "$BEAT_EVERY"; done ) &
beater=$!
pids="$pids $beater"
python3 -c 'import time; time.sleep(3)'
readbeat() {                 # `date +%s > f` truncates first, so a bare cat races it
  i=0
  while [ $i -lt 20 ]; do
    v=$(cat "$BEAT" 2>/dev/null || true)
    case $v in [0-9]*) printf '%s' "$v"; return 0 ;; esac
    python3 -c 'import time; time.sleep(0.1)'; i=$((i+1))
  done
  printf '0'
}
if [ -f "$BEAT" ]; then
  age=$(( $(date +%s) - $(readbeat) ))
  if [ "$age" -le 2 ]; then
    say "C1 PASS  beat is ${age}s old three seconds into a live stub turn"
  else
    say "C1 FAIL  beat already ${age}s stale during a live turn — the beater is not running"
    bad=1
  fi
else
  say 'C1 FAIL  no beat file written at all — +0 intervention'
  bad=1
fi
kill -TERM "$turn" 2>/dev/null || true
python3 -c 'import time; time.sleep(3)'
before=$(readbeat)
python3 -c 'import time; time.sleep(2)'
after=$(readbeat)
if [ "$before" = "$after" ]; then
  say 'C2 PASS  the beat STOPPED when the turn ended — a dead lane goes stale, so the alarm can fire'
else
  say 'C2 FAIL  the beat kept advancing after the turn died — a dead lane would beat forever'
  bad=1
fi

[ "$bad" = 0 ] || { say 'PROBE REFUSES: a control failed'; exit 1; }
say 'controls C1/C2/C3 held'
