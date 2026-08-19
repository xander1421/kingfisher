#!/bin/sh
# A10 — refuse to benchmark on a machine that is not quiet.
#
# GUARDRAILS A5 says "abort if the environment is not controlled, do not correct
# for it". That was a habit, and the habit failed three times: S9, S18, and
# S62/S63 (whose own commit message records "I contended with my own adversarial
# agent on the same device"). The structural gap is that spikes declared
# contention using `uptime`, and uptime does not show containers -- a machine can
# read loadavg 1.2 with eleven services resident holding memory and cache.
#
# Usage:  sh spikes/quiet.sh            -> exit 0 if quiet, 1 if not
#         sh spikes/quiet.sh --json     -> emit the capture for the spike's json
#         QUIET_ALLOW_CONTAINERS=1 ...  -> explicit override, recorded in output
#         QUIET_ALLOW_THERMAL_UNREADABLE=1 -> operator override (H139): skip
#         ONLY the unread-thermal refuse. A numeric hot reading still refuses.
#
# Refuses if: loadavg > ncores/4, OR any container is up, OR a compiler is in
# the top 3 by CPU. The capture is emitted so the criteria stay auditable.
set -u

# H125: empty/non-integer thermal is UNKNOWN and refuses (not publishable).
kf_thermal_fail() {
  _dt="$1"
  if ! [ -n "$_dt" ] || ! [ "$_dt" -eq "$_dt" ] 2>/dev/null; then
    echo " thermal-UNREADABLE"
  elif [ "$_dt" -gt 45000 ]; then
    echo " thermal(${_dt}m)"
  fi
}

# H127: classify `adb devices` text. Does not call adb.
# stdin = `adb devices` output. ANDROID_SERIAL optional.
# stdout = SERIAL<TAB>REASON (SERIAL empty on refuse). exit 0 iff one serial.
kf_classify_adb() {
  want="${ANDROID_SERIAL:-}"
  list=$(awk 'NR>1 && $2=="device" {print $1}')
  n=$(printf '%s\n' "$list" | awk 'NF{c++} END{print c+0}')
  if [ -n "$want" ]; then
    if printf '%s\n' "$list" | grep -qx "$want"; then
      printf '%s\tok\n' "$want"
      return 0
    fi
    printf '\tmissing-serial(%s)\n' "$want"
    return 1
  fi
  if [ "$n" -eq 0 ]; then
    printf '\tno-device\n'
    return 1
  fi
  if [ "$n" -gt 1 ]; then
    names=$(printf '%s\n' "$list" | awk 'NF' | tr '\n' ' ' | sed 's/ *$//')
    printf '\tmultiple(%s)\n' "$names"
    return 1
  fi
  one=$(printf '%s\n' "$list" | awk 'NF{print; exit}')
  printf '%s\tok\n' "$one"
  return 0
}

# --selfcheck: drive kf_thermal_fail + kf_classify_adb. No adb.
if [ "${1:-}" = "--selfcheck" ]; then
  fail=0
  case "$(kf_thermal_fail "")" in *thermal-UNREADABLE*) ;; *) echo "FAIL empty DT"; fail=1 ;; esac
  case "$(kf_thermal_fail "m")" in *thermal-UNREADABLE*) ;; *) echo "FAIL unit DT"; fail=1 ;; esac
  case "$(kf_thermal_fail "32000")" in "") ;; *) echo "FAIL cool DT"; fail=1 ;; esac
  case "$(kf_thermal_fail "46000")" in *thermal\(46000m\)*) ;; *) echo "FAIL hot DT"; fail=1 ;; esac

  two=$(printf 'List of devices attached\nPHONE\tdevice\nEMU\tdevice\n')
  one=$(printf 'List of devices attached\nEMU\tdevice\n')
  none=$(printf 'List of devices attached\n')
  out=$(printf '%s\n' "$none" | kf_classify_adb); rc=$?
  out=$(printf '%s' "$out" | tr -d '\n')
  [ "$out" = "$(printf '\tno-device')" ] && [ "$rc" = 1 ] || { echo "FAIL none -> no-device got [$out] rc=$rc"; fail=1; }
  out=$(printf '%s\n' "$one" | kf_classify_adb); rc=$?
  out=$(printf '%s' "$out" | tr -d '\n')
  [ "$out" = "$(printf 'EMU\tok')" ] && [ "$rc" = 0 ] || { echo "FAIL one -> EMU got [$out] rc=$rc"; fail=1; }
  out=$(printf '%s\n' "$two" | kf_classify_adb); rc=$?
  out=$(printf '%s' "$out" | tr -d '\n')
  [ "$out" = "$(printf '\tmultiple(PHONE EMU)')" ] && [ "$rc" = 1 ] || { echo "FAIL two -> multiple got [$out] rc=$rc"; fail=1; }
  out=$(printf '%s\n' "$two" | (ANDROID_SERIAL=PHONE kf_classify_adb)); rc=$?
  out=$(printf '%s' "$out" | tr -d '\n')
  [ "$out" = "$(printf 'PHONE\tok')" ] && [ "$rc" = 0 ] || { echo "FAIL ANDROID_SERIAL=PHONE got [$out] rc=$rc"; fail=1; }
  out=$(printf '%s\n' "$two" | (ANDROID_SERIAL=MISSING kf_classify_adb)); rc=$?
  out=$(printf '%s' "$out" | tr -d '\n')
  [ "$out" = "$(printf '\tmissing-serial(MISSING)')" ] && [ "$rc" = 1 ] || { echo "FAIL missing-serial got [$out] rc=$rc"; fail=1; }

  if [ "$fail" -ne 0 ]; then
    echo "quiet.sh --selfcheck FAILED"
    exit 1
  fi
  echo "quiet.sh --selfcheck: thermal-UNREADABLE fires; cool pass; hot refuse; classify none/one/multiple/serial"
  exit 0
fi

# --device: gate an ANDROID measurement. Found 2026-08-17: quiet.sh checked only
# the host, so every device measurement in this workspace (S34, S50-S54, S57,
# S62, S63) ran ungated -- including the ones A10 was written after.
if [ "${1:-}" = "--device" ] || [ "${2:-}" = "--device" ]; then
  # H127: pick a serial first. Two attached devices used to make every
  # unscoped `adb shell` fail, which this block then printed as "no device".
  _cls=$(adb devices 2>/dev/null | kf_classify_adb)
  KF_SERIAL=$(printf '%s\n' "$_cls" | cut -f1)
  _why=$(printf '%s\n' "$_cls" | cut -f2)
  if [ -z "$KF_SERIAL" ]; then
    echo "REFUSED - ${_why:-no-device}" >&2
    exit 1
  fi
  adb_d() { adb -s "$KF_SERIAL" "$@"; }
  # CPU busy from a /proc/stat delta, NOT loadavg. Android's loadavg counts
  # uninterruptible-sleep background services and does not indicate contention:
  # measured 6.0% busy with 1 runnable task out of 8,889 while loadavg read 9.19.
  # Gating on loadavg here refuses a perfectly idle phone.
  D=$(adb_d shell 'a=$(head -1 /proc/stat); sleep 2; b=$(head -1 /proc/stat); echo "$a|$b"' 2>/dev/null | tr -d '\r' | awk -F'|' '
    {split($1,x," "); split($2,y," "); t=0; for(i=2;i<=8;i++) t+=y[i]-x[i];
     id=(y[5]-x[5])+(y[6]-x[6]); if(t>0) printf "%.1f", 100*(1-id/t); else print "0"}')
  DRUN=$(adb_d shell 'cat /proc/loadavg' 2>/dev/null | tr -d '\r' | awk -F'[ /]' '{print $4}')
  DC=$(adb_d shell 'cat /sys/devices/system/cpu/present' 2>/dev/null | tr -d '\r' | awk -F- '{print $2+1}')
  DT=$(adb_d shell 'cat /sys/class/thermal/thermal_zone0/temp' 2>/dev/null | tr -d '\r')
  # Charging state. CORRECTED 2026-08-17.
  #
  # The previous rule accepted `status` in {2 CHARGING, 5 FULL} and rejected the
  # AC/USB powered flags, reasoning that a charger disengages at 100% so a
  # plugged phone at full reads "AC powered: false". That phenomenon is real and
  # the conclusion drawn from it was wrong: **an UNPLUGGED phone at 100% also
  # reports status 5**, so the rule cannot distinguish the two cases and
  # silently passes a device running on battery.
  #
  # Caught when WorkManager refused to run: `Unsatisfied constraints: CHARGING`
  # while this gate reported "device quiet ... battery status=5". The platform
  # and the gate disagreed, and the platform was right — `dumpsys deviceidle get
  # charging` said false and all three powered flags said false.
  #
  # Now: ask the OS the same question JobScheduler asks. `deviceidle get
  # charging` is authoritative; the powered flags are the fallback; `status`
  # alone is never sufficient.
  BSTAT=$(adb_d shell 'dumpsys battery | grep -E "^  status"' 2>/dev/null | tr -d '\r' | awk '{print $2}')
  BLVL=$(adb_d shell 'dumpsys battery | grep -E "^  level"' 2>/dev/null | tr -d '\r' | awk '{print $2}')
  BAT="status=$BSTAT level=$BLVL"
  [ -z "$D" ] && { echo "REFUSED - no device (serial $KF_SERIAL, adb empty)" >&2; exit 1; }
  DLIM=15
  DFAIL=""
  awk -v l="$D" -v m="$DLIM" 'BEGIN{exit !(l>m)}' && DFAIL="$DFAIL cpu_busy(${D}%>${DLIM}%)"
  # thermal: millidegrees. Above 45C the governor is already throttling.
  # H125: an unreadable sensor used to skip this test (`[ -n "$DT" ]` false
  # when Permission denied is discarded). Empty or non-integer is UNKNOWN,
  # and UNKNOWN refuses — a measurement behind an unread thermal is not
  # publishable. Prints as thermal-UNREADABLE, never "thermal m".
  # H139: QUIET_ALLOW_THERMAL_UNREADABLE=1 is an operator override. It skips
  # only the unread refuse. A numeric reading above 45C still refuses.
  _th="$(kf_thermal_fail "$DT")"
  if [ "${QUIET_ALLOW_THERMAL_UNREADABLE:-0}" = "1" ]; then
    case "$_th" in
      *thermal-UNREADABLE*)
        BAT="$BAT thermal-override=UNREADABLE"
        _th=""
        ;;
    esac
  fi
  DFAIL="$DFAIL$_th"
  # S6: the deployable configuration is charge-time. Not charging = wrong config.
  # A frozen battery service reports STALE values with no error. `dumpsys
  # battery set/unplug` pins the state and prints "(UPDATES STOPPED)"; every
  # field after that is fiction. This went undetected long enough to produce a
  # whole defect report about a phone that was actually charging.
  BOVR=$(adb_d shell 'dumpsys battery | grep -c "UPDATES STOPPED"' 2>/dev/null | tr -d '\r')
  if [ "${BOVR:-0}" -gt 0 ] 2>/dev/null; then
    DFAIL="$DFAIL battery-service-OVERRIDDEN(run: adb shell dumpsys battery reset)"
  fi
  DCHG=$(adb_d shell 'dumpsys deviceidle get charging' 2>/dev/null | tr -d '\r' | tr -d ' ')
  DPWR=$(adb_d shell 'dumpsys battery | grep -cE "^  (AC|USB|Wireless|Dock) powered: true"' 2>/dev/null | tr -d '\r')
  BAT="$BAT charging=$DCHG powered=$DPWR"
  if [ "$DCHG" = "true" ] || [ "${DPWR:-0}" -gt 0 ] 2>/dev/null; then :; else
    DFAIL="$DFAIL not-charging(status=$BSTAT deviceidle=$DCHG powered=$DPWR)"
  fi
  if [ "${3:-}${2:-}" = "--json" ] || [ "${1:-}" = "--json" ]; then
    printf '{"quiet":%s,"device_cpu_busy_pct":%s,"device_limit_pct":%s,"device_cores":%s,"thermal_m":%s,"battery":"%s","refusals":"%s"}\n' \
      "$([ -z "$DFAIL" ] && echo true || echo false)" "$D" "$DLIM" "${DC:-null}" "${DT:-null}" "$(echo $BAT) runnable=$DRUN" "$(echo $DFAIL)"
    exit 0
  fi
  if [ -n "$DFAIL" ]; then
    echo "REFUSED - device is not quiet:$DFAIL" >&2
    echo "  device cpu_busy ${D}% (limit ${DLIM}%), runnable $DRUN, thermal ${DT:-?}m" >&2
    echo "  battery: $BAT" >&2
    exit 1
  fi
  if [ -n "${DT:-}" ] && [ "$DT" -eq "$DT" ] 2>/dev/null; then
    _thprint="${DT}m"
  elif [ "${QUIET_ALLOW_THERMAL_UNREADABLE:-0}" = "1" ]; then
    _thprint="UNREADABLE(overridden)"
  else
    _thprint="${DT:-?}m"
  fi
  echo "device quiet: cpu_busy ${D}% (limit ${DLIM}%), runnable $DRUN, thermal ${_thprint}, battery $BAT"
  exit 0
fi

NCORES=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 8)
LOAD=$(uptime | sed 's/.*averages*: *//' | awk '{print $1}' | tr -d ,)
LIMIT=$(echo "$NCORES" | awk '{printf "%.2f", $1/4}')
CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')
NCONT=$(printf '%s' "$CONTAINERS" | wc -w | tr -d ' ')
TOP3=$(ps -A -o %cpu,comm 2>/dev/null | sort -rn | head -3 | awk '{printf "%s(%s%%) ", $2, $1}')
COMPILER=$(printf '%s' "$TOP3" | grep -coE 'rustc|clang|cc1|ld|cargo|gcc|swift|node' || true)
THERM=$(pmset -g therm 2>/dev/null | awk -F= '/CPU_Speed_Limit/{print $2+0}')

FAIL=""
awk -v l="$LOAD" -v m="$LIMIT" 'BEGIN{exit !(l>m)}' && FAIL="$FAIL loadavg($LOAD>$LIMIT)"
[ "$NCONT" -gt 0 ] && [ "${QUIET_ALLOW_CONTAINERS:-0}" != "1" ] && FAIL="$FAIL containers($NCONT)"
[ "${COMPILER:-0}" -gt 0 ] && FAIL="$FAIL compiler-in-top3"

if [ "${1:-}" = "--json" ]; then
  printf '{"quiet":%s,"loadavg":%s,"limit":%s,"ncores":%s,"containers":%s,"container_names":"%s","top3":"%s","cpu_speed_limit":%s,"refusals":"%s"}\n' \
    "$([ -z "$FAIL" ] && echo true || echo false)" "$LOAD" "$LIMIT" "$NCORES" "$NCONT" "$CONTAINERS" "$TOP3" "${THERM:-null}" "$(echo $FAIL)"
  exit 0
fi
if [ -n "$FAIL" ]; then
  echo "REFUSED — machine is not quiet:$FAIL" >&2
  echo "  loadavg $LOAD (limit $LIMIT on $NCORES cores)" >&2
  [ "$NCONT" -gt 0 ] && echo "  containers up: $CONTAINERS" >&2
  echo "  top3 cpu: $TOP3" >&2
  echo "  override with QUIET_ALLOW_CONTAINERS=1 (recorded in --json output)" >&2
  exit 1
fi
echo "quiet: loadavg $LOAD / $LIMIT, 0 containers, top3 $TOP3"
