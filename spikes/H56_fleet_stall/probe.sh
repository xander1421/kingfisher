#!/usr/bin/env bash
# H56 — probe.sh v1. ATTACKER-1, 2026-08-17.
#
# THE QUESTION
# ------------
# From 14:29:20 to 15:56:02 on 2026-08-17 every lane in the fleet ran 18
# consecutive instant-exit turns on `You've hit your session limit · resets
# 3:50pm`. `bringup.log` sampled the fleet EIGHT times inside that window and
# printed `quorum: 5/5`, every lane `UP`, `bringup: full quorum, nothing to
# start.` every time. So: WHAT SIGNAL IN THIS HARNESS COULD HAVE SAID SO?
#
# CLASS: a health signal that observes the SUPERVISOR and not the WORK.
#
# FALSIFIERS, STATED IN CHANNEL.md BEFORE ANY OF THIS RAN
# ------------------------------------------------------
#   F1  if any `quorum:` line in bringup.log inside the outage window reads
#       below 5/5, or any lane there reads DOWN/degraded, the monitor DID see it
#       and this row is cosmetic.
#   F2  if any file in the tree READS the `fails` counter or the session-limit
#       condition, the signal already exists and "nothing reads it" is wrong.
#   F3  if the `fail N` <-> `backing off 30N` arithmetic is not self-consistent,
#       the ~86 min is unreliable and the NUMBER is withdrawn, not the class.
#
# CONTROLS
#   C0  THE ONE THAT MATTERS. The monitor's verdict must be shown BYTE-IDENTICAL
#       between total outage and health. An unchanged reading under a total
#       intervention is a disconnected wire, not a measurement.
#       FAILS IF: the outage blocks and the healthy block differ on the verdict
#       lines -- then the monitor did distinguish them and F1 was too narrow.
#   C1  the launcher under test must actually REACH its stub turn. `.loop_fails`
#       reaching 2 is worthless if the launcher refused before the turn -- A29,
#       and `test_loop_gate.sh`'s own H30 note records this check going inert
#       exactly that way.
#       FAILS IF: no turn marker, i.e. the scratch lane has no brief / no PATH.
#   C2  POSITIVE: a lane with 0 fails must still pass `bringup.sh --check`.
#       FAILS IF: the new branch fires on a healthy fleet, which would make it a
#       gate everybody learns to bypass (H38's stated reason for not wiring one).
#
# FALSIFIERS OF THE FIX ITSELF (each reverts one half on an isolated copy)
#   V1  delete `echo "$fails" > "$FAILFILE"` from run_loop.sh ⇒ P1 must go red.
#   V2  delete the `-ge 2` branch from bringup.sh    ⇒ P2 must go red (5/5, exit 0).
#
# RUN
#   sh spikes/H56_fleet_stall/probe.sh                 # against the live tree
#   sh spikes/H56_fleet_stall/probe.sh <run_loop> <bringup>   # against candidates
# Exit 1 if any control or property fails. ~30 s (BACKOFF_STEP=1).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# ABSOLUTISE BEFORE ANY `cd`. A relative argv path resolved after the scratch-dir
# cd is ATTACKER-1's cycle-11 defect (two "v1 vs v2" arms that were the same
# artifact twice) and it reproduced here on this probe's first run.
abspath() { case "$1" in /*) printf '%s\n' "$1" ;; *) printf '%s\n' "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")" ;; esac; }
RL="$(abspath "${1:-$ROOT/run_loop.sh}")"
BU="$(abspath "${2:-$ROOT/bringup.sh}")"
[ -s "$RL" ] && [ -s "$BU" ] || { echo "probe: need run_loop.sh and bringup.sh, got '$RL' '$BU'"; exit 1; }

pass=0; fail=0
check() { # check <label> <got> <want>
  if [ "$2" = "$3" ]; then printf 'ok    %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL  %s\n        got  %s\n        want %s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
say() { printf '\n== %s\n' "$1"; }

# ---------------------------------------------------------------- F1, F3, C0 --
# Read from the committed snapshot, because loop_*.log and bringup.log are
# appended to by five live lanes and would not reproduce.
EV="$ROOT/spikes/H56_fleet_stall/evidence"
say "F1 — what the monitor said INSIDE the outage window (bringup.log, launcher generation 399xx/40xxx)"
q_all=$(grep -c 'quorum:' "$EV/bringup.outage-window.log")
q_full=$(grep -c 'quorum: 5/5' "$EV/bringup.outage-window.log")
q_bad=$(grep -cE 'DOWN|STALLED|WATCHDOG|degrad' "$EV/bringup.outage-window.log" || true)
printf '   %s quorum readings, %s of them 5/5, %s lanes ever reported not-healthy\n' "$q_all" "$q_full" "$q_bad"
check "F1 DOES NOT FIRE: every reading in the window is full quorum" "$q_full" "$q_all"
check "F1 DOES NOT FIRE: no lane reported DOWN/STALLED/WATCHDOG in the window" "$q_bad" "0"
nothing=$(grep -c 'full quorum, nothing to start' "$EV/bringup.outage-window.log")
printf '   and it said "full quorum, nothing to start." %s times during 86 minutes of zero production\n' "$nothing"

say "C0 — the verdict must be byte-identical between outage and health (disconnected wire)"
# The LAST block in the snapshot is the fleet genuinely working (my live turn,
# pids 519xx/520xx, src `turn`); every earlier block is the outage (src `loop`).
outage_verdict=$(grep 'quorum:' "$EV/bringup.outage-window.log" | sed '$d' | sed 's/.*quorum/quorum/' | sort -u)
health_verdict=$(grep 'quorum:' "$EV/bringup.outage-window.log" | tail -1 | sed 's/.*quorum/quorum/')
printf '   outage verdict(s): %s\n   health verdict   : %s\n' "$outage_verdict" "$health_verdict"
check "C0 HOLDS AND IT IS THE FINDING: outage verdict == health verdict" \
      "$outage_verdict" "$health_verdict"
src_outage=$(grep 'quorum:' -B6 "$EV/bringup.outage-window.log" | grep -c '(loop)')
src_health=$(grep '(turn)' "$EV/bringup.outage-window.log" | wc -l | tr -d ' ')
printf '   the ONE thing it did distinguish and then discarded: %s (loop) lane-lines vs %s (turn) lane-lines\n' \
       "$src_outage" "$src_health"

say "F3 — is the fail/backoff arithmetic self-consistent? (if not, the 86 min is withdrawn)"
python3 - "$EV/loop-logs.session-limit.txt" <<'PY'
import re,sys
txt=open(sys.argv[1]).read()
bad=[]; n=0
for m in re.finditer(r'\(fail (\d+)\), backing off (\d+)s', txt):
    k,b=int(m.group(1)),int(m.group(2)); n+=1
    if b!=min(k*30,900): bad.append((k,b))
print(f"   {n} backoff lines, {len(bad)} arithmetic mismatches {bad}")
lanes=re.split(r'### loop_(\S+)\.log',txt)[1:]
for lane,body in zip(lanes[0::2],lanes[1::2]):
    seq=[int(x) for x in re.findall(r'\(fail (\d+)\)',body)]
    run=[];
    for v in seq: run=(run+[v]) if (not run or v==run[-1]+1) else [v]
    s=sum(min(k*30,900) for k in run)
    t=sum(int(x) for x in re.findall(r'exited after (\d+)s',body)[-len(run):])
    print(f"   {lane:12s} longest unbroken run 1..{max(run)}  backoff {s}s + turns {t}s = {(s+t)/60:.1f} min")
sys.exit(1 if bad else 0)
PY
check "F3 DOES NOT FIRE: backoff arithmetic self-consistent" "$?" "0"

say "F2 — does anything in the tree READ the failure signal? (before the fix: nothing)"
readers=$(cd "$ROOT" && git grep -lE '\.loop_fails|session limit' -- '*.sh' '*.py' '*.plist' 2>/dev/null | grep -v 'H56' | tr '\n' ' ')
printf '   readers/writers of the failure signal in tracked scripts: %s\n' "${readers:-NONE}"

# ------------------------------------------------------------------ P1 and P2 --
T=$(mktemp -d "$ROOT/spikes/H56_fleet_stall/.scratch.XXXXXX") || exit 1
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 1
mkdir -p bin prompts
# stub claude: exits instantly with no exit marker, exactly like a turn refused
# for `You've hit your session limit`. Bounds itself: STOP.$CALLSIGN on the 4th.
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo ran >> turn_ran
n=$(wc -l < turn_ran | tr -d ' ')
[ "$n" -ge 4 ] && : > "STOP.${CALLSIGN}"
echo "You've hit your session limit · resets 3:50pm"
exit 1
STUB
chmod +x bin/claude
printf '# L56 — scratch lane brief for the H56 launcher check\n' > prompts/L56.md
printf 'L56\n' > roster.txt

run_launcher() { # run_launcher <run_loop path>
  rm -f turn_ran .loop_fails.L56 STOP.L56 loop_L56.log
  cp "$1" ./run_loop.sh
  PATH="$T/bin:$PATH" KF_DETACHED=1 CALLSIGN=L56 MAX_TURN=5 BACKOFF_STEP=1 \
    bash ./run_loop.sh >/dev/null 2>&1
}

say "P1 — the launcher must EXPORT its consecutive-failure count to disk"
run_launcher "$RL"
check "C1 the launcher actually reached its stub turn (else P1 means nothing)" \
      "$([ -s turn_ran ] && echo reached || echo never)" "reached"
nf=$(cat .loop_fails.L56 2>/dev/null || echo ABSENT)
printf '   .loop_fails.L56 = %s after %s failed turns\n' "$nf" "$(wc -l < turn_ran | tr -d ' ')"
check "P1 .loop_fails.L56 reports >=2 consecutive failures" \
      "$([ "$nf" != ABSENT ] && [ "$nf" -ge 2 ] 2>/dev/null && echo yes || echo "no($nf)")" "yes"
check "P1b the backoff log line carries a clock (86 min had to be reconstructed by arithmetic)" \
      "$(grep -cE '\[run_loop\] [0-9][0-9]:[0-9][0-9]:[0-9][0-9] .*backing off' loop_L56.log)" \
      "$(grep -c 'backing off' loop_L56.log)"

say "P1/V1 — FALSIFIER: delete the export from run_loop.sh, P1 must go red"
sed '/echo "\$fails" > "\$FAILFILE"/d' "$RL" > rl_v1.sh
# A FALSIFIER THAT FIRES BECAUSE ITS SUBJECT IS MISSING HAS PROVED NOTHING.
# On this probe's first run four V-checks reported `ok` over a file `cp` had
# failed to create -- family B, green for a reason unrelated to the property.
# So: exists, parses, and differs, all three, before the red verdict counts.
check "V1 the reverted copy exists and parses" \
      "$([ -s rl_v1.sh ] && bash -n rl_v1.sh 2>/dev/null && echo usable || echo broken)" "usable"
check "V1 the revert actually changed the file (+0 edits is fatal)" \
      "$(cmp -s "$RL" rl_v1.sh && echo unchanged || echo changed)" "changed"
run_launcher ./rl_v1.sh
nf1=$(cat .loop_fails.L56 2>/dev/null || echo ABSENT)
check "V1 FIRES: with the export deleted the count no longer climbs" \
      "$([ "$nf1" = ABSENT ] || [ "$nf1" -lt 2 ] 2>/dev/null && echo red || echo "still-green($nf1)")" "red"

say "P2 — bringup.sh --check must REFUSE a lane that is up and producing nothing"
cp "$BU" ./bringup.sh; chmod +x bringup.sh
sleep 600 & holder=$!            # a live pid for the lock: the WRAPPER is alive
echo "$holder" > .loop_lock.L56
date +%s > .heartbeat.L56        # and the beat is FRESH, which is the whole point
bu_check() { bash ./bringup.sh --check >bu.out 2>&1; echo $?; }

echo 3 > .loop_fails.L56
rc=$(bu_check)
sed 's/^/     | /' bu.out
check "P2 --check exits non-zero on a STALLED lane" "$rc" "1"
check "P2 the report names it STALLED, not UP" "$(grep -c 'STALLED' bu.out)" "2"
check "P2 it is NOT counted toward quorum" "$(grep -c 'quorum: 0/1' bu.out)" "1"
check "P2 it does NOT say 'full quorum, nothing to start'" \
      "$(grep -c 'full quorum, nothing to start' bu.out)" "0"

echo 0 > .loop_fails.L56
rc0=$(bu_check)
check "C2 POSITIVE CONTROL: 0 fails still passes (not a gate that always fires)" "$rc0" "0"
check "C2 and reads UP" "$(grep -c 'L56 .*UP' bu.out)" "1"

say "P2/V2 — FALSIFIER: delete the -ge 2 branch from bringup.sh, P2 must go red"
python3 - "$BU" > bu_v2.sh <<'PY'
import re,sys
src=open(sys.argv[1]).read()
# remove the whole `if [ -n "$pid" ] && [ "$nfail" -ge 2 ]; then ... fi` block
out=re.sub(r'\n  if \[ -n "\$pid" \] && \[ "\$nfail" -ge 2 \]; then.*?\n  fi\n', '\n', src, flags=re.S)
assert out!=src, "V2 anchor absent -- falsifier would have reported +0 edits as a pass"
sys.stdout.write(out)
PY
check "V2 the reverted copy exists and parses" \
      "$([ -s bu_v2.sh ] && bash -n bu_v2.sh 2>/dev/null && echo usable || echo broken)" "usable"
check "V2 the revert actually changed the file (+0 edits is fatal)" \
      "$(cmp -s "$BU" bu_v2.sh && echo unchanged || echo changed)" "changed"
echo 3 > .loop_fails.L56
bash ./bu_v2.sh --check >bu2.out 2>&1; rc2=$?
check "V2 FIRES: without the branch a stalled lane reads UP again"      "$(grep -c 'L56 .*UP' bu2.out)" "1"
check "V2 FIRES: and --check goes back to exit 0 over a dead fleet"     "$rc2" "0"
check "V2 FIRES: and prints the sentence the outage was reported under" \
      "$(grep -c 'quorum: 1/1' bu2.out)" "1"

kill "$holder" 2>/dev/null
cd "$ROOT" || exit 1
printf '\n%s passed, %s FAILED\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
