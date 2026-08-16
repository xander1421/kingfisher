#!/bin/bash
# S35 — MORK vs hyperon, identical semantic work, on the phone and the host.
#
# Reports: wall clock each, and whether the two engines produce the same set of
# derived facts, checked against a third-party ground truth computed in gen.py.
#
# Semantic note found while building this: MORK's space is a SET (it dedupes on
# write), hyperon's match returns a BAG (380 results, 365 distinct). Agreement
# is therefore compared on the deduplicated set, and the bag/set difference is
# itself a protocol finding -- two engines cannot be byte-compared directly,
# only their canonicalised result sets can.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DEV=/data/local/tmp/kingfisher/s35
ADB=$HOME/Library/Android/sdk/platform-tools/adb
MORK_HOST=$HOME/kingfisher/elders/MORK/target/release/mork
FUEL_HOST=$HOME/kingfisher/spikes/S15_android_device/fuelrun/target/release/fuelrun
REPS=${1:-3}

canon () { grep -o '(TwoHop [^)]*)' "$1" | sort -u; }

$ADB shell "mkdir -p $DEV" >/dev/null 2>&1
$ADB push "$HERE/job.mm2" "$HERE/job.metta" "$DEV/" >/dev/null 2>&1

echo "expected unique TwoHop: $(wc -l < "$HERE/expected.txt" | tr -d ' ')"
echo
printf "%-8s %-9s %10s %10s %12s %s\n" where engine best_ms results digest agrees

for where in host phone; do
  # ---- MORK ----
  best=999999
  for r in $(seq 1 "$REPS"); do
    if [ "$where" = host ]; then
      t=$( { /usr/bin/time -p "$MORK_HOST" run "$HERE/job.mm2" "$HERE/out_mork.txt" --steps 1 >/dev/null; } 2>&1 | awk '/real/{print $2*1000}')
    else
      t=$($ADB shell "cd $DEV && LD_PRELOAD=/data/local/tmp/kingfisher/libnotag.so \
            /data/local/tmp/kingfisher/mork run job.mm2 out_mork.txt --steps 1 --timing" 2>&1 \
          | sed -n 's/.*steps took \([0-9]*\) ms.*/\1/p' | tr -d '\r')
    fi
    t=${t%.*}; [ -n "$t" ] && [ "$t" -lt "$best" ] 2>/dev/null && best=$t
  done
  if [ "$where" = phone ]; then
    $ADB pull "$DEV/out_mork.txt" "$HERE/out_mork_phone.txt" >/dev/null 2>&1
    f="$HERE/out_mork_phone.txt"
  else f="$HERE/out_mork.txt"; fi
  n=$(canon "$f" | wc -l | tr -d ' ')
  d=$(canon "$f" | shasum -a 256 | cut -c1-12)
  a=$(diff <(canon "$f") "$HERE/expected.txt" >/dev/null && echo MATCHES-TRUTH || echo DIFFERS)
  printf "%-8s %-9s %10s %10s %12s %s\n" "$where" MORK "$best" "$n" "$d" "$a"

  # ---- hyperon ----
  best=999999
  for r in $(seq 1 "$REPS"); do
    if [ "$where" = host ]; then
      out=$("$FUEL_HOST" "$HERE/job.metta" 50000000 2>/dev/null)
    else
      out=$($ADB shell "cd $DEV && /data/local/tmp/kingfisher/fuelrun.v2 job.metta 50000000" 2>/dev/null | tr -d '\r')
    fi
    t=$(echo "$out" | sed -n 's/^run_ms *//p')
    [ -n "$t" ] && [ "$t" -lt "$best" ] 2>/dev/null && best=$t
  done
  echo "$out" > "$HERE/out_hyperon_$where.txt"
  n=$(canon "$HERE/out_hyperon_$where.txt" | wc -l | tr -d ' ')
  d=$(canon "$HERE/out_hyperon_$where.txt" | shasum -a 256 | cut -c1-12)
  a=$(diff <(canon "$HERE/out_hyperon_$where.txt") "$HERE/expected.txt" >/dev/null && echo MATCHES-TRUTH || echo DIFFERS)
  printf "%-8s %-9s %10s %10s %12s %s\n" "$where" hyperon "$best" "$n" "$d" "$a"
done
