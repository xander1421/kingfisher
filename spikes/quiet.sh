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
#
# Refuses if: loadavg > ncores/4, OR any container is up, OR a compiler is in
# the top 3 by CPU. The capture is emitted so the criteria stay auditable.
set -u

# --device: gate an ANDROID measurement. Found 2026-08-17: quiet.sh checked only
# the host, so every device measurement in this workspace (S34, S50-S54, S57,
# S62, S63) ran ungated -- including the ones A10 was written after.
if [ "${1:-}" = "--device" ] || [ "${2:-}" = "--device" ]; then
  D=$(adb shell 'cat /proc/loadavg' 2>/dev/null | tr -d '\r' | awk '{print $1}')
  DC=$(adb shell 'cat /sys/devices/system/cpu/present' 2>/dev/null | tr -d '\r' | awk -F- '{print $2+1}')
  DT=$(adb shell 'cat /sys/class/thermal/thermal_zone0/temp' 2>/dev/null | tr -d '\r')
  BAT=$(adb shell 'dumpsys battery | grep -E "^  (level|status|AC powered|USB powered)"' 2>/dev/null | tr -d '\r' | tr '\n' ';')
  [ -z "$D" ] && { echo "REFUSED - no device" >&2; exit 1; }
  DLIM=$(echo "${DC:-8}" | awk '{printf "%.2f", $1/4}')
  DFAIL=""
  awk -v l="$D" -v m="$DLIM" 'BEGIN{exit !(l>m)}' && DFAIL="$DFAIL loadavg($D>$DLIM)"
  # thermal: millidegrees. Above 45C the governor is already throttling.
  [ -n "$DT" ] && [ "$DT" -gt 45000 ] 2>/dev/null && DFAIL="$DFAIL thermal(${DT}m)"
  # S6: the deployable configuration is charge-time. Not charging = wrong config.
  case "$BAT" in *"AC powered: true"*|*"USB powered: true"*) ;; *) DFAIL="$DFAIL not-charging" ;; esac
  if [ "${3:-}${2:-}" = "--json" ] || [ "${1:-}" = "--json" ]; then
    printf '{"quiet":%s,"device_loadavg":%s,"device_limit":%s,"device_cores":%s,"thermal_m":%s,"battery":"%s","refusals":"%s"}\n' \
      "$([ -z "$DFAIL" ] && echo true || echo false)" "$D" "$DLIM" "${DC:-null}" "${DT:-null}" "$(echo $BAT)" "$(echo $DFAIL)"
    exit 0
  fi
  if [ -n "$DFAIL" ]; then
    echo "REFUSED - device is not quiet:$DFAIL" >&2
    echo "  device loadavg $D (limit $DLIM on ${DC:-?} cores), thermal ${DT:-?}m" >&2
    echo "  battery: $BAT" >&2
    exit 1
  fi
  echo "device quiet: loadavg $D / $DLIM, thermal ${DT}m, charging"
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
