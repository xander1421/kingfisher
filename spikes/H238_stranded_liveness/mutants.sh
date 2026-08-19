#!/usr/bin/env bash
# H238 mutant driver — ATTACKER-1, 2026-08-19.
#
# A GREEN SUITE IS EVIDENCE OF NOTHING UNTIL IT HAS BEEN SHOWN TO GO RED. Each
# mutant deletes ONE part of the v3 repair from a COPY of stranded.sh and demands
# `--selfcheck` refuse it. A mutant that stays green names a check that is inert.
#
# H217's defect, avoided rather than inherited: every mutant VERIFIES THE INTENDED
# EDIT APPLIED (the anchor was found and the text changed), never merely that the
# copy differs from the source. An anchor that has drifted produces an unmutated
# file, and "it differs" would have been satisfied by nothing at all.
#
# NO WRITES OUTSIDE THE WORKSPACE: everything is under $ROOT/.scratch/.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SRC="$ROOT/spikes/harness/stranded.sh"
SB="$ROOT/.scratch/h238m.$$"
trap 'rm -rf "$SB"' EXIT
mkdir -p "$SB/spikes/harness"
cp "$ROOT/roster.txt" "$SB/roster.txt"

pass=0; fail=0
# mutate <name> <python-anchor> <python-replacement> <why>
mutate() {
  name=$1; anchor=$2; repl=$3; why=$4
  cp "$SRC" "$SB/spikes/harness/stranded.sh"
  applied=$(ANCHOR="$anchor" REPL="$repl" TGT="$SB/spikes/harness/stranded.sh" python3 - <<'PY'
import os
p, a, r = os.environ['TGT'], os.environ['ANCHOR'], os.environ['REPL']
s = open(p).read()
if s.count(a) != 1:
    print('ANCHOR-MISS'); raise SystemExit
open(p, 'w').write(s.replace(a, r, 1))
print('APPLIED')
PY
)
  if [ "$applied" != APPLIED ]; then
    printf '  %-26s ANCHOR-MISS  the mutant never applied, so this row proves nothing\n' "$name"
    fail=$((fail + 1)); return
  fi
  out=$(cd "$SB" && sh spikes/harness/stranded.sh --selfcheck 2>&1); rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '  %-26s REFUSED  rc=%d  %s\n' "$name" "$rc" "$why"
    pass=$((pass + 1))
  else
    printf '  %-26s *** STAYED GREEN ***  %s\n' "$name" "$why"
    fail=$((fail + 1))
  fi
}

echo "H238 mutants — each removes one part of the v3 repair; --selfcheck must refuse:"

# M1 · the whole fourth branch: revert classify to v2's comparison.
mutate M1_no_unattended \
  "  elif [ \"\${4:-QUIET}\" = NONE ] && [ \"\${5:-}\" = yes ]; then printf 'UNATTENDED'" \
  "  elif false; then printf 'UNATTENDED'" \
  "v2's classify restored: the defect is back"

# M2 · UNATTENDED fires on ANY non-LIVE owner, i.e. a stale beat is read as death.
mutate M2_stale_beat_is_death \
  "  elif [ \"\${4:-QUIET}\" = NONE ] && [ \"\${5:-}\" = yes ]; then printf 'UNATTENDED'" \
  "  elif [ \"\${4:-QUIET}\" != LIVE ]; then printf 'UNATTENDED'" \
  "wrong direction: a rate-limited live lane loses its stand-off"

# M3 · drop the A15 fleet-evidence guard: no signal becomes no apparatus.
mutate M3_no_a15_guard \
  "  elif [ \"\${4:-QUIET}\" = NONE ] && [ \"\${5:-}\" = yes ]; then printf 'UNATTENDED'" \
  "  elif [ \"\${4:-QUIET}\" = NONE ]; then printf 'UNATTENDED'" \
  "a fresh clone would call every file UNATTENDED"

# M4 · lane_liveness stops reading the lock, so LIVE is unreachable.
mutate M4_lock_unread \
  "  if [ -f \"\$ROOT/.loop_lock.\$_c\" ]; then" \
  "  if false; then" \
  "the lock is ignored: a live launcher reads QUIET"

# M5 · H232's rule dropped: pid believed without its command.
mutate M5_pid_without_command \
  "if [ -n \"\$_p\" ] && ps -p \"\$_p\" -o command= 2>/dev/null | grep -q 'run_loop\\.sh'; then" \
  "if [ -n \"\$_p\" ] && kill -0 \"\$_p\" 2>/dev/null; then" \
  "a recycled pid is believed to be a launcher"

# M6 · lane_liveness stops reading the heartbeat: QUIET collapses into NONE.
mutate M6_beat_unread \
  "  [ -f \"\$ROOT/.heartbeat.\$_c\" ] && printf 'QUIET' || printf 'NONE'" \
  "  printf 'NONE'" \
  "every non-locked lane reads dead"

# M7 · fleet evidence hard-wired to yes -- the guard exists and cannot refuse.
mutate M7_fleet_always_yes \
  "    [ \"\$(lane_liveness \"\$_l\")\" = NONE ] || { echo yes; break; }" \
  "    echo yes; break" \
  "the A15 guard is present and inert"

echo
echo "mutants: $pass refused, $fail not refused"
[ "$fail" -eq 0 ] || exit 1
exit 0
