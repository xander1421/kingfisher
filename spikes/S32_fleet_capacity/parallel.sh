#!/bin/bash
# S32 — how many MeTTa jobs can ONE phone actually run at once?
#
# Every number in this workspace so far is single-threaded. fuelrun is one
# thread; the S25 Ultra has 8 cores (2 prime + 6 performance, Oryon). Fleet
# TPS scales with whatever this returns, so it is the single highest-leverage
# unmeasured input in the capacity model.
#
# Method: launch N copies of the identical job concurrently, wait for all,
# take the SLOWEST (that is when the batch is done), and compute aggregate
# steps/s = N * steps / slowest_seconds. Report per-process slowdown so
# thermal/contention effects are visible rather than averaged away.
#
# Hash is checked on every process: parallelism must not change results.
set -u
DEV=/data/local/tmp/kingfisher
ADB=$HOME/Library/Android/sdk/platform-tools/adb
JOB=${1:-job_terminating}
FUEL=${2:-5000000}
STEPS=100082          # fuel_used for job_terminating, verified identical everywhere
EXPECT=c2940ab5fcd507681ff8d3c32f607f236819915a38cda9a5f4f863c681261ab3

echo "job=$JOB steps=$STEPS  binary=fuelrun.v2 (the S30 winner)"
printf "%3s %11s %11s %11s %13s %8s %s\n" \
       N slowest_ms fastest_ms per_proc_ms agg_steps_per_s speedup hashes

for n in 1 2 4 6 8; do
  # start n copies in background on the device, collect every run_ms
  out=$($ADB shell "cd $DEV && for i in \$(seq 1 $n); do
            ./fuelrun.v2 $JOB.metta $FUEL > out_p\$i.txt 2>&1 &
          done; wait;
          grep -h '^run_ms' out_p*.txt | awk '{print \$2}';
          echo ---;
          grep -h '^raw_hash' out_p*.txt | awk '{print \$2}' | sort -u | wc -l;
          grep -h '^raw_hash' out_p*.txt | awk '{print \$2}' | sort -u | head -1;
          rm -f out_p*.txt" 2>/dev/null | tr -d '\r')

  times=$(echo "$out" | sed -n '1,/^---$/p' | grep -E '^[0-9]+$')
  nuniq=$(echo "$out" | sed -n '/^---$/,$p' | sed -n '2p')
  thehash=$(echo "$out" | sed -n '/^---$/,$p' | sed -n '3p')

  slow=$(echo "$times" | sort -n | tail -1)
  fast=$(echo "$times" | sort -n | head -1)
  [ -z "$slow" ] && { echo "  N=$n FAILED"; continue; }

  agg=$(python3 -c "print(int($n*$STEPS/($slow/1000.0)))")
  if [ "$n" -eq 1 ]; then base=$agg; fi
  spd=$(python3 -c "print(f'{$agg/$base:.2f}x')")
  hs="$nuniq distinct"
  [ "$thehash" = "$EXPECT" ] && hs="$hs OK" || hs="$hs MISMATCH!"
  printf "%3d %11s %11s %11s %13s %8s %s\n" \
         "$n" "$slow" "$fast" "$((slow/1))" "$agg" "$spd" "$hs"
  sleep 20   # cool down between points; S30 showed back-to-back runs throttle
done
