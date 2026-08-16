#!/bin/bash
# S32b — sustained 8-way throughput and power, the two inputs the fleet model
# actually needs.
#
# S30 showed a single thread loses 40% when run back-to-back (thermal). S32a
# showed 8-way burst scales 5.87x. Neither answers the fleet question, which
# is: what does this phone hold for HOURS, and what does it cost in watts?
#
# Runs 8 concurrent copies of the 2M-step job in rounds, back to back, no
# cooldown, and samples battery current/voltage/temperature between rounds.
set -u
DEV=/data/local/tmp/kingfisher
ADB=$HOME/Library/Android/sdk/platform-tools/adb
ROUNDS=${1:-6}
NPROC=${2:-8}
STEPS=2000000

echo "sustained: ${NPROC}-way x ${ROUNDS} rounds of job_kb (${STEPS} steps each), no cooldown"
printf "%6s %11s %15s %8s %9s %9s\n" round slowest_ms agg_steps_per_s temp_C curr_uA volt_uV

for r in $(seq 1 "$ROUNDS"); do
  out=$($ADB shell "cd $DEV && for i in \$(seq 1 $NPROC); do
            ./fuelrun.v2 job_kb.metta $STEPS > out_s\$i.txt 2>&1 &
          done; wait
          grep -h '^run_ms' out_s*.txt | awk '{print \$2}' | sort -n | tail -1
          grep -h '^raw_hash' out_s*.txt | awk '{print \$2}' | sort -u | wc -l
          cat /sys/class/power_supply/battery/temp 2>/dev/null || echo NA
          cat /sys/class/power_supply/battery/current_now 2>/dev/null || echo NA
          cat /sys/class/power_supply/battery/voltage_now 2>/dev/null || echo NA
          rm -f out_s*.txt" 2>/dev/null | tr -d '\r')

  slow=$(echo "$out" | sed -n 1p)
  nuniq=$(echo "$out" | sed -n 2p)
  temp=$(echo "$out" | sed -n 3p)
  curr=$(echo "$out" | sed -n 4p)
  volt=$(echo "$out" | sed -n 5p)
  [ -z "$slow" ] && { echo "round $r FAILED"; continue; }
  agg=$(python3 -c "print(int($NPROC*$STEPS/($slow/1000.0)))")
  printf "%6s %11s %15s %8s %9s %9s  (%s distinct hash)\n" \
         "$r" "$slow" "$agg" "$temp" "$curr" "$volt" "$nuniq"
done
