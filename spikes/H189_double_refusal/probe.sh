#!/usr/bin/env bash
# H189 probe v1 — ok-1, 2026-08-19.
#
# THE OBSERVATION, and it is one capture, not a rate. test_loop_gate.sh's H61
# staggered-arrival fixture read h61_surv=0, h61_parent=2, h61_child=0
# (spikes/H178_suite_flake/failing_run_4.txt): BOTH backgrounded launchers took
# run_loop.sh:258's parent-refusal path, so NO lane started, and H178's accounting
# control absorbed it because 0+2+0 = 1+1+0.
#
# For BOTH to refuse, `.loop_lock.$CALLSIGN` must have existed at the first
# parent's arrival, holding a pid that `ps -o command=` matched to run_loop.sh and
# that was not KF_LOCK_OWNER. THIS PROBE DOES NOT SAY WHICH PID THAT WAS. It makes
# the launcher say so, at the moment of refusal.
#
# WHY THE DIAGNOSTIC IS INJECTED INTO A COPY AND THAT IS NOT H117 FA1: the H61
# fixture ITSELF builds a copy — `awk` inserts a `sleep 3` slow-child line into
# $ROOT/run_loop.sh — so the copy IS the executed path for this check. This probe
# adds a SECOND injection at the refusal site and asserts BOTH landed (an
# injection that misses its anchor leaves an unmodified launcher reporting a pass;
# `edits.anchored_replace` exists because a str.replace no-op shipped that way).
#
# RAIL: scratch dir, scratch callsign, and C2 asserts the live fleet's
# .loop_lock.* were never touched. A test that can stop production is not a test.
#
# usage: bash spikes/H189_double_refusal/probe.sh [iterations]
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
N="${1:-12}"
CS=H189SCRATCH
SB="$SPIKE/sandbox"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }

# Fingerprint the live locks BEFORE anything runs, for C2.
live_before=$(cd "$ROOT" && ls -1 .loop_lock.* 2>/dev/null | sort | while IFS= read -r f; do
                printf '%s=%s\n' "$f" "$(cat "$f" 2>/dev/null)"; done)

rm -rf "$SB"; mkdir -p "$SB/bin" "$SB/prompts"
cd "$SB"

# ---- the fixture, replicating test_loop_gate.sh's H61 block, plus a diagnostic.
#      Injection 1 is the suite's own slow child. Injection 2 dumps, AT the
#      refusal and before any state can move (C1), the lock's contents and the
#      blamed pid's full ps line.
awk '{ if ($0 ~ /^LOCK="\.loop_lock\.\$\{CALLSIGN\}"$/)
         print "[ -n \"${KF_DETACHED:-}\" ] && sleep 3   # H61: a slow child";
       if ($0 ~ /^LOCK="\.loop_lock\.\$\{CALLSIGN\}"$/)
         print "printf \"%s\\n\" \"$$\" >> \"$SBSTART\"   # H189: every launcher pid this iteration";
       if ($0 ~ /is HELD by live launcher pid/)
         print "      { printf \"%s\\t%s\\t%s\\t%s\\t%s\\n\" \"$(date +%s)\" \"$$\" \"${KF_DETACHED:-0}\" \"$held\" \"$(ps -p $held -o command= 2>/dev/null | tr \"\\t\" \" \")\" >> \"$SBLOG\"; }";
       print }' "$ROOT/run_loop.sh" > run_loop.sh
chmod +x run_loop.sh

ctl C3 "$([ "$(grep -c 'H61: a slow child' run_loop.sh)" = 1 ] && echo PASS || echo FAIL)" \
    "slow-child injection landed ($(grep -c 'H61: a slow child' run_loop.sh) site)"
ctl C4 "$([ "$(grep -c 'SBLOG' run_loop.sh)" = 1 ] && echo PASS || echo FAIL)" \
    "refusal-diagnostic injection landed ($(grep -c 'SBLOG' run_loop.sh) site)"
ctl C5 "$([ "$(grep -c 'SBSTART' run_loop.sh)" = 1 ] && echo PASS || echo FAIL)" \
    "launcher-pid injection landed ($(grep -c 'SBSTART' run_loop.sh) site)"

cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo "$$" >> reached_claude
sleep 8
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
printf '# scratch roster for H189 only\n%s\n' "$CS" > roster.txt
printf '# scratch\n' > "prompts/$CS.md"

printf 'iter\tsurv\tparent\tchild\n' > "$SPIKE/triples.tsv"
printf 'iter\tts\trefusing_pid\tdetached\tblamed_pid\tverdict\tblamed_ps\n' > "$SPIKE/refusals.tsv"
printf 'iter\tlauncher_pid\n' > "$SPIKE/starts.tsv"

for i in $(seq 1 "$N"); do
  : > reached_claude; : > race.log; rm -f "detach_$CS.log" ".loop_lock.$CS" \
        ".loop_exit.$CS" ".loop_blocks.$CS"
  # PER-ITERATION, so "was the blamed pid one of THIS iteration's launchers" is a
  # set membership and not a guess. THE FIRST DRAFT LOGGED THE SUBSHELL PIDS from
  # `$!`, which are never the refusing process -- the launcher is `bash
  # ./run_loop.sh` INSIDE that subshell -- so F1 and F2 were not decidable from
  # what was being recorded. Same family as the row above it: a number collected
  # that cannot answer the question it was collected for.
  SBLOG="$SB/ref_$i.tsv"; SBSTART="$SB/start_$i.tsv"
  : > "$SBLOG"; : > "$SBSTART"
  ( PATH="$SB/bin:$PATH" CALLSIGN=$CS MAX_TURN=60 SBLOG="$SBLOG" SBSTART="$SBSTART" \
      bash ./run_loop.sh >>race.log 2>&1 ) &
  sleep 1.5
  ( PATH="$SB/bin:$PATH" CALLSIGN=$CS MAX_TURN=60 SBLOG="$SBLOG" SBSTART="$SBSTART" \
      bash ./run_loop.sh >>race.log 2>&1 ) &
  wait
  sleep 4
  s=$(sort -u reached_claude | grep -c .)
  p=$(grep -c 'is HELD by live launcher' race.log)
  c=$(grep -c 'is HELD by live launcher' "detach_$CS.log" 2>/dev/null); c=${c:-0}
  printf '%s\t%s\t%s\t%s\n' "$i" "$s" "$p" "$c" >> "$SPIKE/triples.tsv"
  # F1 vs F2, decided per refusal while this iteration's pid set is still on disk.
  while IFS=$'\t' read -r ts rpid det blamed pscmd; do
    [ -n "${blamed:-}" ] || continue
    if grep -qx "$blamed" "$SBSTART"; then verdict=F2_own_launcher; else verdict=F1_foreign_pid; fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$i" "$ts" "$rpid" "$det" "$blamed" "$verdict" "$pscmd" \
      >> "$SPIKE/refusals.tsv"
  done < "$SBLOG"
  # ONE file with an iter column, not 30 files. The pair (iter, pid) is what makes
  # a past F1/F2 verdict re-checkable; a file per iteration carries the same pairs
  # and 30x the clutter.
  while IFS= read -r sp; do [ -n "$sp" ] && printf '%s\t%s\n' "$i" "$sp" >> "$SPIKE/starts.tsv"; done < "$SBSTART"
  # A DOUBLE REFUSAL IS THE EVENT. Keep the whole run, not four lines of it --
  # H178's opening defect was discarding the names with `tail -4`.
  if [ "$p" != 1 ] || [ "$s" != 1 ]; then
    cp race.log "$SPIKE/anomaly_${i}_race.log"
    cp "detach_$CS.log" "$SPIKE/anomaly_${i}_detach.log" 2>/dev/null
  fi
  for lkpid in $(cat ".loop_lock.$CS" 2>/dev/null); do kill "$lkpid" 2>/dev/null; done
done
rm -f ".loop_lock.$CS" ".loop_exit.$CS" ".loop_blocks.$CS"

cd "$SPIKE"
anom=$(awk 'NR>1 && ($2 != 1 || $3 != 1)' triples.tsv | grep -c .)
runs=$(awk 'NR>1' triples.tsv | grep -c .)

# ---- C1 the fixture ran at all. `0 anomalies` over 0 runs is the shape H178's
#      accounting control failed on: a clean-looking number from a probe that
#      never arrived. Asserted before any verdict is read off it.
[ "$runs" = "$N" ] && ctl C1 PASS "$runs/$N iterations completed" \
                   || ctl C1 FAIL "$runs/$N iterations completed -- verdicts below are not over the stated sample"

# ---- C2 THE RAIL. The live fleet's locks are untouched.
live_after=$(cd "$ROOT" && ls -1 .loop_lock.* 2>/dev/null | sort | while IFS= read -r f; do
               printf '%s=%s\n' "$f" "$(cat "$f" 2>/dev/null)"; done)
[ "$live_before" = "$live_after" ] && ctl C2 PASS "live .loop_lock.* unchanged across $N iterations" \
                                   || ctl C2 FAIL "LIVE LOCKS CHANGED -- this probe touched production"

echo
echo "  RESULT over $runs iterations:"
awk -F'\t' 'NR>1{printf "    iter %-3s surv=%s parent=%s child=%s%s\n",$1,$2,$3,$4,(($2!=1)||($3!=1))?"   <-- ANOMALY":""}' triples.tsv

if [ "$anom" = 0 ]; then
  echo
  echo "  F3: $runs/$N iterations reproduced NOTHING. The sighting stays a sighting."
  echo "  No mechanism is asserted. refusals.tsv still classifies EVERY refusal,"
  echo "  including the correct ones, so the F1/F2 rule is EXERCISED on this run"
  echo "  rather than only described for a future one:"
  awk -F'\t' 'NR>1{c[$6]++} END{for(v in c) printf "    %-18s %s\n", v, c[v]}' refusals.tsv
else
  echo
  echo "  $anom anomalous iteration(s). Decide F1 vs F2 from refusals.tsv:"
  echo "    blamed pid IS a pid this run created  -> F2, the fixture races itself"
  echo "    blamed pid is NOT                     -> F1, pid reuse in run_loop.sh:256"
  awk -F'\t' 'NR>1{printf "    iter %-3s refusing %-7s detached=%s blamed %-7s %-18s %s\n",$1,$3,$4,$5,$6,$7}' refusals.tsv
fi

[ "$fail" = 0 ] && echo "H189 probe: controls as stated" || echo "H189 probe: A CONTROL FAILED"
exit "$fail"
