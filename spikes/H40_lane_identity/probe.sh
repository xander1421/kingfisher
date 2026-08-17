#!/bin/sh
# H40 probe v1 — 2026-08-17, ATTACKER-1.
#
# QUESTION. Every per-lane brief opens by telling a new lane to establish whether
# its callsign is already held:
#
#     ps -eo command= | grep -c 'You are <CALLSIGN>\.'
#
# `prompts/ATTACKER-1.md:19` calls that "another lane with your name?" and the
# other three call it ">1 means another lane holds it". `run_loop.sh` v6's own
# comment says the instruction CANNOT BE CARRIED OUT. This probe decides what the
# number actually counts, with no live agent spawned anywhere — an F8 check of
# mine spawned one in cycle 1 and had to be killed by hand.
#
# MEASURED ON THE LIVE FLEET BEFORE WRITING ANY OF THIS, one command, four
# callsigns: ATOM-3 1, AGENT-1 1, AGENT-2 1, ok-1 1, ATTACKER-1 1 — and the last
# one is my own turn. Every lane reads 1 at once, so the number cannot be
# separating them.
#
# FALSIFIERS, STATED FIRST.
#   F1  kills the row. If the count tracks LANES HELD rather than TURNS IN
#       FLIGHT, the briefs are right. Decided by a pair:
#         F1a  a process whose ARGV carries the string  -> must be COUNTED
#         F1b  a launcher-shaped `bash ./run_loop.sh` whose callsign is only in
#              its ENVIRONMENT                          -> must be INVISIBLE
#       Both halves are needed: F1a alone shows the grep works, F1b alone shows
#       it missed something. Together they say what it is a function of.
#   F2  bounds the fix. If `.loop_lock.$CALLSIGN` were present for every live
#       lane it would be sufficient on its own and no fallback wording is needed.
#
# CONTROLS
#   C1  the F1b stub must be VISIBLE to `ps` in its launcher shape
#       (`run_loop.sh` appears) while its callsign does not. Fails if the stub
#       simply is not running, which would make an invisible callsign prove
#       nothing — the shape of every "+0 intervention" in this repo.
#   C2  a callsign that has never existed must count 0. Fails if the grep matches
#       something incidental, e.g. this script's own command line.
#
# REGRESSION GUARD, the part that fails when the rule breaks: any brief under
# `prompts/` that prescribes the ps count MUST also prescribe
# `.loop_lock.$CALLSIGN`. A new brief copied from an old one fails this.
#
# Run: sh spikes/H40_lane_identity/probe.sh    (exit 1 if a control or the guard
# fails)
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
D=$(mktemp -d "${TMPDIR:-/tmp}/h38.XXXXXX")
pids=''
cleanup() { [ -z "$pids" ] || kill $pids 2>/dev/null || true; rm -rf "$D"; }
trap cleanup EXIT
say() { printf '%s\n' "$1"; }
bad=0

count() { ps -eo command= | grep -c "You are $1\." || true; }

# ---- C2 first: does the grep match anything incidental? ---------------------
n=$(count NEVEREXISTED-0)
if [ "$n" = 0 ]; then
  say 'C2 PASS  a callsign that never existed counts 0'
else
  say "C2 FAIL  counted $n for a callsign that never existed — the grep matches something incidental"
  bad=1
fi

# ---- F1a: a process carrying the string in ARGV ------------------------------
python3 -c 'import time; time.sleep(8)' "You are TESTLANE-9." &
pids="$pids $!"
python3 -c 'import time; time.sleep(0.6)'
a=$(count TESTLANE-9)
if [ "$a" -ge 1 ]; then
  say "F1a  argv-carrying process COUNTED ($a) — the grep itself works"
else
  say "F1a FAIL  argv-carrying process not counted ($a) — probe is measuring nothing"
  bad=1
fi

# ---- F1b: launcher shape, callsign only in the ENVIRONMENT -------------------
printf '#!/bin/bash\nexec python3 -c "import time; time.sleep(8)"\n' > "$D/run_loop.sh"
chmod +x "$D/run_loop.sh"
( cd "$D" && CALLSIGN=TESTLANE-8 bash ./run_loop.sh ) &
pids="$pids $!"
python3 -c 'import time; time.sleep(0.6)'
shape=$(ps -eo command= | grep -c 'bash ./run_loop.sh' || true)
b=$(count TESTLANE-8)
if [ "$shape" -ge 1 ]; then
  say "C1 PASS  the stub launcher is visible to ps in its launcher shape ($shape match(es) for 'bash ./run_loop.sh')"
else
  say "C1 FAIL  the stub launcher is not running — an invisible callsign would prove nothing"
  bad=1
fi
if [ "$b" = 0 ]; then
  say 'F1b  launcher with the callsign in its ENVIRONMENT is INVISIBLE (0)'
else
  say "F1b FAIL  counted $b — the callsign IS visible, so the briefs may be right"
fi

# ---- verdict on F1 ----------------------------------------------------------
if [ "$a" -ge 1 ] && [ "$b" = 0 ] && [ "$shape" -ge 1 ]; then
  say 'F1 FIRED  the count is a function of TURNS IN FLIGHT (argv), not of LANES HELD (environment).'
  say '          A lane between turns is invisible; your own turn is counted as one.'
else
  say 'F1 killed  the count does track lanes held — the briefs stand and this row dies'
fi

# ---- F2: how many live lanes have the authoritative lock? -------------------
locks=$(ls "$ROOT"/.loop_lock.* 2>/dev/null | wc -l | tr -d ' ')
lanes=$(ls "$ROOT"/.heartbeat.* 2>/dev/null | wc -l | tr -d ' ')
say "F2  .loop_lock.* files: $locks ; .heartbeat.* files (lanes that have run): $lanes"
say '    An ABSENT lock therefore means UNKNOWN, never CLEAR — spans started before'
say '    the lock landed have none, which is exactly when a collision is possible.'

# ---- REGRESSION GUARD -------------------------------------------------------
# `--head` materializes HEAD's briefs and runs the guard against those instead,
# so the RED state before the fix stays reproducible after it (a guard verified
# red only in a transcript is a guard whose falsifier is prose).
PROMPTS="$ROOT/prompts"
if [ "${1:-}" = "--head" ]; then
  PROMPTS="$D/prompts"; mkdir -p "$PROMPTS"
  for b in $(cd "$ROOT" && git ls-tree --name-only HEAD prompts/); do
    git -C "$ROOT" show "HEAD:$b" > "$PROMPTS/$(basename "$b")"
  done
  say "GUARD SUBJECT  HEAD:prompts/ ($(ls "$PROMPTS" | wc -l | tr -d ' ') briefs)"
fi
g=0
for f in "$PROMPTS"/*.md; do
  if grep -q "ps -eo command= | grep" "$f"; then
    if grep -q '\.loop_lock\.' "$f"; then
      say "GUARD ok    $(basename "$f") prescribes the ps count AND the lock file"
    else
      say "GUARD FAIL  $(basename "$f") prescribes the ps count with no .loop_lock check — it counts turns, not lanes"
      g=1
    fi
  fi
done
[ "$g" = 0 ] || bad=1

[ "$bad" = 0 ] || { say 'PROBE REFUSES: a control or the regression guard failed'; exit 1; }
say 'controls C1/C2 held; regression guard clean'
