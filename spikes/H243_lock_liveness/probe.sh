#!/usr/bin/env bash
# H243 — `.loop_lock.<CS>` is read by six instruments and only one of them asks
# whether the pid it names is a LAUNCHER. ok-1, 2026-08-19, ATTACK cycle 32.
#
# run_loop.sh's acquire path states the rule in its own comment: "LIVENESS IS pid
# + COMMAND, never pid alone. `kill -0` on its own reports HELD after any pid
# reuse, and pid reuse here is not theoretical: this fleet burned ~1300
# pids/minute while three lanes ran, so macOS's 99999-pid space wraps in about 75
# minutes." Every other reader of the same file uses pid alone.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SB="$ROOT/.scratch/h243_sb.$$"
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1";
       else fail=$((fail+1)); printf '  FAIL  %s (want %s, got %s)\n' "$1" "$3" "$2"; fi; }

echo "H243 probe — who asks whether the lock's pid is a launcher"

# ------------------------------------------------------------------ A1 · SITES
# Printed with their text, never as a bare count: a count of 6 says nothing about
# which one gates a decision, and this row is entirely about that difference.
echo "A1 · every liveness test applied to a lock pid"
python3 "$(dirname "$0")/sites.py" "$ROOT"

# -------------------------------------------------------------- A2 · DECISION
# The supervisor, driven end to end in a sandbox. `--check` starts nothing.
mkdir -p "$SB/prompts" "$SB/fake"
cp "$ROOT/bringup.sh" "$SB/bringup.sh"
printf 'PROBE-1\n' > "$SB/roster.txt"
printf '# scratch brief\n' > "$SB/prompts/PROBE-1.md"
printf '#!/usr/bin/env bash\nsleep 60\nexit 0\n' > "$SB/fake/run_loop.sh"
cd "$SB" || exit 1
# BSD sed has no \| alternation in a basic regex -- the first version of this
# line returned EMPTY for every arm and all three checks went red at once, which
# is what a broken instrument looks like when it is honest about it.
status() { bash bringup.sh --check 2>&1 | sed -nE 's/^ *PROBE-1 +(UP|DOWN|STALLED).*/\1/p' | head -1; }

sleep 60 & impostor=$!            # a live process that is NOT a launcher
echo "$impostor" > .loop_lock.PROBE-1
got_impostor=$(status)
bash fake/run_loop.sh & real=$!   # a live process that IS launcher-shaped to ps
echo "$real" > .loop_lock.PROBE-1
got_real=$(status)
sleep 0.2 & dead=$!; wait "$dead" 2>/dev/null
echo "$dead" > .loop_lock.PROBE-1
got_dead=$(status)
kill "$impostor" "$real" 2>/dev/null
echo "A2 · bringup.sh --check, one callsign, three locks: impostor=$got_impostor launcher=$got_real dead=$got_dead"
ck "a DEAD holder reads DOWN"                     "$got_dead"     "DOWN"
ck "a LAUNCHER holder reads UP"                   "$got_real"     "UP"
ck "a live NON-launcher holder does not read UP"  "$got_impostor" "DOWN"

# --------------------------------------------------------------- A3 · CENSUS
# fleetcensus reads CHANNEL.md and roster.txt from its cwd; without the first it
# enumerates nothing and every verdict below it is a zero from a census that
# never ran. The precondition check is what said so.
# fleetcensus pins its cwd to the repo root by resolving `dirname $0/../..`
# (line 26), exactly as the Stop hook pins ROOT -- so a copy run from a sandbox
# measures the LIVE fleet and reports a clean zero for the fixture. Rather than
# rewriting that line, the copy is placed where its OWN resolution lands in the
# sandbox: the real code path runs, unedited.
mkdir -p "$SB/spikes/harness"
cp "$ROOT/spikes/harness/fleetcensus.sh" "$SB/spikes/harness/fleetcensus.sh"
printf 'DONE X1 PROBE-1 fixture\n' > CHANNEL.md
sleep 60 & impostor2=$!
echo "$impostor2" > .loop_lock.PROBE-1
cenout=$(bash "$SB/spikes/harness/fleetcensus.sh" 2>&1)
cen=$(printf '%s' "$cenout" | grep -c 'PROBE-1.*CONSTITUTED')
saw=$(printf '%s' "$cenout" | grep -c 'PROBE-1')
kill "$impostor2" 2>/dev/null
echo "A3 · fleetcensus.sh: lines naming PROBE-1 = $saw, of them CONSTITUTED = $cen"
# A ZERO FROM A CENSUS THAT NEVER SAW THE LANE IS NOT A PASS (H178's shape), so
# the precondition is asserted before the verdict is read.
ck "the census actually saw the fixture lane"        "$([ "$saw" -ge 1 ] && echo yes || echo no)" "yes"
ck "the census does not call an impostor lock CONSTITUTED" "$cen" "0"

cd "$ROOT" || exit 1
rm -rf "$SB"
echo
echo "probe: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ]
