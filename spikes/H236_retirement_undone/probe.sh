#!/usr/bin/env bash
# H236 · Does a lane's LEGAL §7 exit survive the supervisors that watch it?
#
# CLASS UNDER TEST: a lane's §7 terminal exit is invisible to every component
# except the launcher that consumed it. `bringup.sh` classifies HALTED from
# `STOP`/`STOP.$lane` and from nothing else, so "retired on purpose" and "died"
# are the same observation -- and the relaunch path deletes `.loop_exit.$lane`
# as stale debris on the way past, so the record of the retirement dies with it.
#
# PREREGISTERED FALSIFIERS (posted to CHANNEL.md before this file was written):
#   F1 a supervisor reads the CONTENT of .loop_exit.$lane somewhere -> dies.
#   F2 run_loop.sh removes the marker before exiting -> the evidence half dies.
#   F3 something else marks a retired lane that the census DOES respect -> dies.
#   F4 the sandbox census cannot produce a launch at all -> the instrument is
#      inert (family A). Arm A3 is that null and it must FIRE.
#
# ARMS. A1/A4 are the finding. A3/A5/A6/A7 are the controls that keep the fix
# from becoming "any exit marker retires a lane", which would be WRONG: the
# launcher's own `break` set is exactly LOOP-DONE|LOOP-HALT. LOOP-IDLE and
# LOOP-FUSE do NOT end the launcher (`run_loop.sh:559-565`), so a dead lane
# carrying one of those died of something else and must still be started.
#
# NOT PRODUCTION. Everything runs in ./sandbox with a one-lane roster and a stub
# run_loop.sh that only appends its callsign. The live tree is never read for
# state and never written.
set -uo pipefail
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)
SB="$PWD/sandbox"

rm -rf "$SB"; mkdir -p "$SB/prompts" "$SB/spikes/harness"
cp "$ROOT/bringup.sh"                  "$SB/bringup.sh"
cp "$ROOT/spikes/harness/bringup.sh"   "$SB/spikes/harness/bringup.sh"
# H265: both bringup copies REFUSE without `lanelive.sh` (H243), and before H265's
# fix that refusal was a SILENT exit 1 under `sh` -- so every arm below read
# "did not launch", which is what a retirement looks like. The null arm A3 is the
# only reason this was caught: it must be able to LAUNCH, and it could not.
cp "$ROOT/spikes/harness/lanelive.sh"  "$SB/spikes/harness/lanelive.sh"
printf 'L1\n' > "$SB/roster.txt"
: > "$SB/prompts/L1.md"
printf '#!/bin/sh\nprintf "%%s\\n" "$CALLSIGN" >> launched.log\n' > "$SB/run_loop.sh"
chmod +x "$SB/run_loop.sh"

pass=0; fail=0
check() {  # desc got want
  if [ "$2" = "$3" ]; then pass=$((pass+1)); printf 'PASS %s\n' "$1"
  else fail=$((fail+1)); printf 'FAIL %s: got [%s] want [%s]\n' "$1" "$2" "$3"; fi
}

# one census run against a freshly-seeded sandbox state
# $1 marker content ('' = no marker)   $2 stop file ('' = none)
run_arm() {
  ( cd "$SB"
    rm -f .loop_exit.* .loop_launches.* launched.log STOP STOP.L1 out.txt
    [ -n "$1" ] && printf '%s\n' "$1" > .loop_exit.L1
    [ -n "$2" ] && : > "$2"
    bash ./bringup.sh > out.txt 2>&1 )
}
launched()  { [ -s "$SB/launched.log" ] && echo yes || echo no; }
marker()    { tr -d '[:space:]' < "$SB/.loop_exit.L1" 2>/dev/null || echo GONE; }
verdict()   { grep -oE 'L1 +(UP|DOWN|HALTED|RETIRED|FLAPPING|STALLED)' "$SB/out.txt" | awk '{print $2}' | head -1; }

echo "== A3 · NULL: no marker, no STOP -- the census must be able to LAUNCH (F4) =="
run_arm '' ''
check "  A3 launched"            "$(launched)"  "yes"
check "  A3 classified"          "$(verdict)"   "DOWN"

echo "== A2 · CONTROL: STOP.L1 -- the census must be able to SUPPRESS a launch =="
run_arm 'LOOP-DONE' 'STOP.L1'
check "  A2 not launched"        "$(launched)"  "no"
check "  A2 classified"          "$(verdict)"   "HALTED"

echo "== A1 · THE FINDING: a lane that exited LOOP-DONE =="
run_arm 'LOOP-DONE' ''
check "  A1 not relaunched"      "$(launched)"  "no"
check "  A1 marker survives"     "$(marker)"    "LOOP-DONE"
check "  A1 classified"          "$(verdict)"   "RETIRED"

echo "== A4 · THE VOCABULARY, not one member of it: LOOP-HALT =="
run_arm 'LOOP-HALT' ''
check "  A4 not relaunched"      "$(launched)"  "no"
check "  A4 marker survives"     "$(marker)"    "LOOP-HALT"
check "  A4 classified"          "$(verdict)"   "RETIRED"

echo "== A5 · CONTROL: LOOP-FUSE is a span cap, NOT a retirement -- must launch =="
run_arm 'LOOP-FUSE' ''
check "  A5 relaunched"          "$(launched)"  "yes"

echo "== A6 · CONTROL: LOOP-IDLE does not end the launcher either -- must launch =="
run_arm 'LOOP-IDLE' ''
check "  A6 relaunched"          "$(launched)"  "yes"

echo "== A7 · CONTROL: an unrecognised marker is not a retirement -- must launch =="
run_arm 'banana' ''
check "  A7 relaunched"          "$(launched)"  "yes"

echo "== A8 · THE SECOND SITE: the PRE-FLIGHT sweeper, under --check (writes nothing) =="
( cd "$SB"
  rm -f .loop_exit.* .loop_launches.* launched.log STOP STOP.L1
  printf 'LOOP-DONE\n' > .loop_exit.L1
  sh spikes/harness/bringup.sh --check > preflight.txt 2>&1 )
check "  A8 does not call the retirement record stale" \
      "$(grep -c 'stale .loop_exit.L1\|\.loop_exit\.L1 (LOOP-DONE) -- would clear' "$SB/preflight.txt")" "0"
check "  A8 names it as a retirement record" \
      "$(grep -c 'retire' "$SB/preflight.txt")" "1"

printf '\n%s pass, %s fail\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
