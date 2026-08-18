#!/bin/sh
# H122 — WHY does quiet.sh refuse? The exit code was read; the reason was not.
# Every sample records the reason, because "it refuses" and "it refuses because
# of X" are different claims and only the second one has a cause in it.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT" || exit 9
n=8; i=1
echo "=== F1 — the reason, per sample (n=$n) ==="
while [ "$i" -le "$n" ]; do
  out=$(sh spikes/quiet.sh 2>&1); rc=$?
  reason=$(printf '%s\n' "$out" | sed -n 's/.*not quiet: *//p' | head -1)
  load=$(printf '%s\n' "$out" | sed -n 's/.*loadavg \([0-9.]*\).*/\1/p' | head -1)
  printf '  %d: rc=%d reason=%-22s loadavg=%s\n' "$i" "$rc" "${reason:-<none>}" "${load:-?}"
  i=$((i+1))
done
lim=$(sysctl -n hw.ncpu | awk '{printf "%.2f", $1/4}')
echo "  limit=$lim on $(sysctl -n hw.ncpu) cores; live lanes: $(ls "$ROOT"/.loop_lock.* 2>/dev/null | wc -l | tr -d ' ')"

echo
echo "=== F2 — whose containers are they? ==="
docker ps --format '{{.Names}}\t{{.Image}}' 2>/dev/null | sed 's/^/  /' || echo "  docker unavailable"
echo "  named in this repo (grep, excluding this spike):"
docker ps --format '{{.Names}}' 2>/dev/null | while read -r c; do
  [ -z "$c" ] && continue
  hits=$(grep -rl "$c" "$ROOT" --include='*.py' --include='*.sh' --include='*.md' 2>/dev/null \
         | grep -v H122_quiet_cause | grep -v '/.git/' | wc -l | tr -d ' ')
  printf '    %-24s referenced in %s repo file(s)\n' "$c" "$hits"
done

echo
echo "=== F3 — who else has recorded a REASON, and is it dated? ==="
grep -rn 'quiet\.sh' "$ROOT" --include='*.py' --include='*.sh' 2>/dev/null \
  | grep -iE 'refus' | grep -v H122_quiet_cause | grep -v H116_inert_loop \
  | sed 's/^.*kingfisher\///' | cut -c1-150 | sed 's/^/  /'

echo
echo "=== F4 — does quiet.sh already emit the reason machine-readably? ==="
if sh spikes/quiet.sh --json >/dev/null 2>&1 || [ -n "$(grep -c 'json' "$ROOT/spikes/quiet.sh")" ]; then
  echo "  --json support in source: $(grep -c 'json' "$ROOT/spikes/quiet.sh") mention(s)"
  sh spikes/quiet.sh --json 2>&1 | head -12 | sed 's/^/  /'
fi
echo
echo "  callers that read only the EXIT CODE (>/dev/null, discarding the reason):"
grep -rn 'quiet\.sh' "$ROOT" --include='*.sh' --include='*.py' 2>/dev/null \
  | grep '>/dev/null' | grep -v H122_quiet_cause \
  | sed 's/^.*kingfisher\///' | cut -c1-120 | sed 's/^/    /'

echo
echo "=== THE SEPARATION — which component is unclearable? ==="
# quiet.sh:100 is `[ "$NCONT" -gt 0 ] && [ "${QUIET_ALLOW_CONTAINERS:-0}" != "1" ]`
# -- ANY container refuses, at any load. The override is the natural control:
# with the container arm disabled, the refusal is load and nothing else.
i=1
while [ "$i" -le 6 ]; do
  a=$(sh spikes/quiet.sh --json 2>/dev/null)
  b=$(QUIET_ALLOW_CONTAINERS=1 sh spikes/quiet.sh --json 2>/dev/null)
  la=$(printf '%s' "$a" | sed -n 's/.*"loadavg":\([0-9.]*\).*/\1/p')
  ra=$(printf '%s' "$a" | sed -n 's/.*"refusals":"\([^"]*\)".*/\1/p')
  rb=$(printf '%s' "$b" | sed -n 's/.*"refusals":"\([^"]*\)".*/\1/p')
  printf '  load=%-6s plain=[%s]  containers-allowed=[%s]\n' "$la" "${ra:-QUIET}" "${rb:-QUIET}"
  i=$((i+1)); sleep 2
done
