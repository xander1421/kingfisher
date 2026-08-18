#!/usr/bin/env bash
# H113 FALSIFIER. A check nobody has broken on purpose is a check nobody tested.
# Every mutation is applied to an ISOLATED COPY of the tree; prompts/AGENT-1.md
# is never written to.
#
# F1  reinstate the withdrawn claim (LANE-ROWS gains P)      -> must go RED
# F2  delete the LANE-ROWS line entirely                     -> must go RED,
#     because an unreadable claim is not the same as a correct one, and "no
#     claim found" silently passing is the empty-input floor this repo keeps
#     paying for (A15/H30).
# F3  quote `**P0-P4**` in the PROSE while LANE-ROWS stays clean -> must stay
#     GREEN. This is the regression that motivated probe v2: the repair itself
#     quotes the withdrawn claim in order to retract it, and v1 went red on it.
# CONTROL: the untouched copy must be GREEN.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROOT="$PWD"
rc=0
arm() { # arm <label> <sed-program|-> <want-rc>
  local d out got
  d=$(mktemp -d "$ROOT/spikes/H113_lane_namespace/.fals.XXXXXX")
  mkdir -p "$d/prompts" "$d/spikes/H113_lane_namespace" "$d/specs"
  cp "$ROOT/WORK_QUEUE.md" "$d/" ; cp "$ROOT/HUMAN_NEEDED.md" "$d/" 2>/dev/null
  cp "$ROOT/specs/D2_canonical_result.md" "$d/specs/" 2>/dev/null
  cp "$ROOT/spikes/H113_lane_namespace/probe.sh" "$d/spikes/H113_lane_namespace/"
  if [ "$2" = '-' ]; then cp "$ROOT/prompts/AGENT-1.md" "$d/prompts/"
  else sed "$2" "$ROOT/prompts/AGENT-1.md" > "$d/prompts/AGENT-1.md"; fi
  if [ "$2" != '-' ] && cmp -s "$ROOT/prompts/AGENT-1.md" "$d/prompts/AGENT-1.md"; then
    printf '  %-8s FAIL  mutation was a NO-OP -- sed matched nothing\n' "$1"; rc=1
    rm -rf "$d"; return
  fi
  out=$(cd "$d" && bash spikes/H113_lane_namespace/probe.sh 2>&1); got=$?
  if [ "$got" = "$3" ]; then printf '  %-8s PASS  rc=%s as required\n' "$1" "$got"
  else printf '  %-8s FAIL  rc=%s, wanted %s\n' "$1" "$got" "$3"
       printf '%s\n' "$out" | sed 's/^/          | /'; rc=1; fi
  rm -rf "$d"
}
echo "=== H113 falsifiers (isolated copies; prompts/AGENT-1.md untouched) ==="
arm CONTROL '-'                                        0
arm F1      's/^    LANE-ROWS: S H M W D/    LANE-ROWS: S H M W D P/' 1
arm F2      '/^    LANE-ROWS:/d'                       1
arm F3      's/^\*\*THE CLAIM IS THE LINE BELOW/**P0-P4** and **P5** quoted in prose. THE CLAIM IS THE LINE BELOW/' 0
echo "h113_falsify=$([ $rc = 0 ] && echo PASS || echo FAIL)"
exit $rc
