#!/bin/sh
# H244 probe — what one CHANNEL.md rotation did to every signal computed from it.
#
# Pinned to the two revisions that BRACKET the rotation, not to HEAD: five lanes
# commit to this tree and "HEAD" gave three different answers inside one cycle
# while I was measuring (346, 344, 341). A number read at HEAD on a shared tree
# is not reproducible; these two are.
#
#   PRE  b9a1b33  CHANNEL.md 1065 lines, immediately before the rotation
#   POST 228fc46  the rotation commit itself ("CHANNEL.md rotated: at 1.04 MB
#                 the coordination channel was the one file no lane could commit")
#
# Both trees are materialised with `git archive` into .scratch/ -- GITIGNORED,
# and never under spikes/. H223 is this lane's own row about a materialised copy
# of the repo placed where the instruments walk; doing it again inside the spike
# that cites it would be the same defect with a better excuse.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 3
PRE=${KF_PRE:-b9a1b33}
POST=${KF_POST:-228fc46}
OUT="$ROOT/spikes/H244_unanchored_count/measure.json"
W="$ROOT/.scratch/H244_probe.$$"
trap 'rm -rf "$W"' EXIT INT TERM
rm -rf "$W"; mkdir -p "$W/pre" "$W/post" || exit 3

for r in pre post; do
  rev=$(eval echo \$$(echo $r | tr a-z A-Z))
  git archive "$rev" 2>/dev/null | tar -x -C "$W/$r" || { echo "probe: git archive $rev failed" >&2; exit 3; }
  ( cd "$W/$r" && git init -q . && git add -A ) >/dev/null 2>&1
  # A ZERO FROM A DEAD INSTRUMENT IS NOT A ZERO (errors 42/44/46/48): assert the
  # tree materialised before any count is taken from it.
  n=$(find "$W/$r" -type f | wc -l | tr -d ' ')
  [ "$n" -gt 1000 ] || { echo "probe: $r tree has only $n files -- refusing to measure" >&2; exit 3; }
  [ -f "$W/$r/CHANNEL.md" ] || { echo "probe: $r has no CHANNEL.md -- refusing" >&2; exit 3; }
done

lanes="AGENT-1 AGENT-2 ATOM-3 ATTACKER-1 ok-1 GEMINI GROK-LOCAL GROK-2 BUILDER-1"

# bringup.sh lane_lastwork, verbatim in its pre-H244 (v4) form
lastwork() {
  ( cd "$1" || return
    [ -f CHANNEL.md ] || { echo -1; return; }
    n=$(grep -nE "^(CLAIM|DONE|NOTE|CORRECTION|ATTACK|EVIDENCE|STATUS|RENUMBERED|WITHDRAWN) [^ ]+ ${2}\b" CHANNEL.md | tail -1 | cut -d: -f1)
    [ -n "$n" ] || { echo -1; return; }
    echo $(( $(wc -l < CHANNEL.md) - n )) )
}
# fleetcensus.sh per-lane DONE, verbatim
census() { ( cd "$1" && grep -cE "^DONE [^ ]+ ${2}( |\$)" CHANNEL.md ); }
# the anchored form, which is what channelcount.sh ships
anchored() { git log -p --format='' "$1" -- CHANNEL.md | grep -cE "^\+DONE [^ ]+ ${2}( |\$)"; }

{
printf '{\n'
printf '  "pre_rev": "%s", "post_rev": "%s",\n' "$PRE" "$POST"
printf '  "pre_lines": %s, "post_lines": %s,\n' \
  "$(wc -l < "$W/pre/CHANNEL.md" | tr -d ' ')" "$(wc -l < "$W/post/CHANNEL.md" | tr -d ' ')"
printf '  "mission_loop_14_2_command": {"pre": %s, "post": %s},\n' \
  "$(grep -c '^DONE' "$W/pre/CHANNEL.md")" "$(grep -c '^DONE' "$W/post/CHANNEL.md")"
printf '  "anchored_total": {"pre": %s, "post": %s},\n' \
  "$(git log -p --format='' "$PRE" -- CHANNEL.md | grep -c '^+DONE ')" \
  "$(git log -p --format='' "$POST" -- CHANNEL.md | grep -c '^+DONE ')"
printf '  "lanes": {\n'
first=1
for l in $lanes; do
  [ $first = 1 ] || printf ',\n'; first=0
  printf '    "%s": {"census_pre": %s, "census_post": %s, "anchored": %s, "lastwork_pre": %s, "lastwork_post": %s}' \
    "$l" "$(census "$W/pre" "$l")" "$(census "$W/post" "$l")" "$(anchored "$POST" "$l")" \
    "$(lastwork "$W/pre" "$l")" "$(lastwork "$W/post" "$l")"
done
printf '\n  }\n}\n'
} > "$OUT"
echo "wrote $OUT"
cat "$OUT"
