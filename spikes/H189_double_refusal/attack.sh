#!/usr/bin/env bash
# H189 attack v1 — ok-1, 2026-08-19. Deterministic, seconds, no sampling.
#
# `probe.sh` asks how often the double refusal HAPPENS. This asks whether the
# launcher's liveness test CAN produce it, which is decidable from the design and
# does not need the race to recur (CLAUDE.md family A: "decidable from the design,
# before the run").
#
# THE DESIGN FACT, read out of run_loop.sh and not inferred:
#   line 250  `echo $$ > "$LOCK"`     -- the lock's CONTENT is a bare pid.
#   line 185  `LOCK=".loop_lock.${CALLSIGN}"` -- the callsign is in the FILENAME.
#   line 256  `ps -p "$held" -o command= | grep -q 'run_loop\.sh'`
# So the holder is validated as "some live process whose command names
# run_loop.sh". Every lane on this machine runs a file of that name, and the lock
# carries nothing that ties the recorded pid to the callsign it is guarding.
#
# The launcher's own comment already states the inverse half of this and treats it
# as the safe direction: "a copy under any other name is not recognised as a
# launcher". A1 below is the direction it does not state.
#
# NOT A FIX. Changing the liveness test moves the launcher toward RECLAIMING more
# locks, and H6's hazard is that the absent branch LAUNCHES -- a wrong reclaim is
# a double admission on one callsign, which is worse than a wrong refusal. So this
# reports, and the repair is its own row with its own falsifier.
#
# usage: bash spikes/H189_double_refusal/attack.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
CS=H189ATK
SB="$SPIKE/atk_sandbox"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }

live_before=$(cd "$ROOT" && ls -1 .loop_lock.* 2>/dev/null | sort | while IFS= read -r f; do
                printf '%s=%s\n' "$f" "$(cat "$f" 2>/dev/null)"; done)

rm -rf "$SB"; mkdir -p "$SB/bin" "$SB/prompts" "$SB/decoy"
cd "$SB"
cp "$ROOT/run_loop.sh" run_loop.sh && chmod +x run_loop.sh
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo "$$" >> reached_claude
sleep 5
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
printf '# scratch roster for H189 attack only\n%s\n' "$CS" > roster.txt
printf '# scratch\n' > "prompts/$CS.md"

# The two decoys differ in ONE thing: the filename. Same content, same
# interpreter, same argv shape.
printf '#!/usr/bin/env bash\nsleep 25\n' > decoy/run_loop.sh
printf '#!/usr/bin/env bash\nsleep 25\n' > decoy/not_a_launcher.sh
chmod +x decoy/run_loop.sh decoy/not_a_launcher.sh

run_fixture() {   # $1 = pid to seed the lock with; echoes "surv parent"
  : > reached_claude; : > race.log
  rm -f "detach_$CS.log" ".loop_exit.$CS" ".loop_blocks.$CS"
  printf '%s\n' "$1" > ".loop_lock.$CS"
  ( PATH="$SB/bin:$PATH" CALLSIGN=$CS MAX_TURN=30 bash ./run_loop.sh >>race.log 2>&1 ) &
  sleep 1.5
  ( PATH="$SB/bin:$PATH" CALLSIGN=$CS MAX_TURN=30 bash ./run_loop.sh >>race.log 2>&1 ) &
  wait
  sleep 3
  printf '%s %s' "$(sort -u reached_claude | grep -c .)" \
                 "$(grep -c 'is HELD by live launcher' race.log)"
}

# ---- A1 A LOCK HELD BY A PROCESS OF ANOTHER CALLSIGN -- indeed by no callsign at
#      all, just a file with the right NAME -- validates as a live holder, and
#      BOTH arriving launchers are refused. This is the observed triple.
bash decoy/run_loop.sh & d1=$!
sleep 0.3
read -r s1 p1 <<< "$(run_fixture "$d1")"
disown "$d1" 2>/dev/null; kill "$d1" 2>/dev/null
[ "$s1" = 0 ] && [ "$p1" = 2 ] \
  && ctl A1 PASS "decoy NAMED run_loop.sh holds the lock -> surv=$s1 parent=$p1 (the observed 0/2/0)" \
  || ctl A1 FAIL "surv=$s1 parent=$p1 -- expected 0 and 2; the liveness test discriminated after all"

# ---- A2 TWO-SIDED, and it is what keeps A1 from being "any stale pid refuses".
#      Identical process, identical content, ONE character of filename different:
#      the lock is correctly called stale and reclaimed, and a lane starts.
bash decoy/not_a_launcher.sh & d2=$!
sleep 0.3
read -r s2 p2 <<< "$(run_fixture "$d2")"
disown "$d2" 2>/dev/null; kill "$d2" 2>/dev/null
[ "$s2" = 1 ] && [ "$p2" = 1 ] \
  && ctl A2 PASS "same process under another NAME -> stale, reclaimed, surv=$s2 parent=$p2 (healthy)" \
  || ctl A2 FAIL "surv=$s2 parent=$p2 -- expected 1 and 1; the filename is not what decides it"

# ---- C1 THE ARMS MUST DISAGREE OR NEITHER MEASURES ANYTHING. A1 and A2 differ in
#      exactly one input, so an identical verdict means the seed never reached the
#      launcher and both arms are describing something else.
[ "$s1" != "$s2" ] \
  && ctl C1 PASS "the two seeds produce DIFFERENT outcomes ($s1 vs $s2), so the seed is what is being measured" \
  || ctl C1 FAIL "both seeds gave surv=$s1 -- the lock seed is not reaching the refusal path"

# ---- C2 THE RAIL.
cd "$SPIKE"
live_after=$(cd "$ROOT" && ls -1 .loop_lock.* 2>/dev/null | sort | while IFS= read -r f; do
               printf '%s=%s\n' "$f" "$(cat "$f" 2>/dev/null)"; done)
[ "$live_before" = "$live_after" ] && ctl C2 PASS "live .loop_lock.* unchanged" \
                                   || ctl C2 FAIL "LIVE LOCKS CHANGED -- this attack touched production"

echo
echo "  WHAT THIS DOES AND DOES NOT SHOW."
echo "  SHOWN: run_loop.sh's holder check is satisfied by ANY live process whose"
echo "  command names run_loop.sh. The lock records a pid and nothing else, and the"
echo "  callsign it guards is only in the filename, so a pid that has been reused by"
echo "  another lane's launcher reads as MY live holder and refuses a legitimate"
echo "  lane. This machine runs 5 lanes and the launcher's own comment records"
echo "  ~1300 pids/min, wrapping macOS's pid space in ~75 min -- so the reused pid"
echo "  does not have to be lucky, it has to land on any one of them."
echo "  NOT SHOWN: that this is what happened in the H178 capture. A construction"
echo "  that reproduces a signature is not evidence that the signature had that"
echo "  cause. probe.sh samples the unforced case and says so separately."
[ "$fail" = 0 ] && echo "H189 attack: all arms as stated" || echo "H189 attack: FAILED"
exit "$fail"
