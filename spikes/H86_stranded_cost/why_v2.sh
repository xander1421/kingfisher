#!/bin/sh
# H86 why_v2.sh — ATOM-3. MEASURE why v2 is slower than the v1 it replaced,
# rather than guess. Runs v2's EXACT per-file body (copied, not imitated) over
# the first N uncommitted paths and prints cumulative wall seconds every 20, so
# the shape of the cost is visible instead of a single total.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
N=${1:-60}
HIST=$(git log --format='C%x09%at%x09%(trailers:key=Atom,valueonly)' --name-only 2>/dev/null | awk -F'\t' '
  /^C\t/ { t = $2; a = $3; gsub(/[ \r\n]/, "", a); next }
  NF && $0 !~ /^C\t/ { if (!($0 in seen)) { seen[$0] = 1; printf "P\t%s\t%s\n", $0, a } }
  { if (a != "" && (!(a in newest) || t+0 > newest[a])) newest[a] = t+0 }
  END { for (k in newest) printf "A\t%s\t%d\n", k, newest[k] }')
echo "HIST lines: $(printf '%s\n' "$HIST" | wc -l | tr -d ' ')  bytes: $(printf '%s' "$HIST" | wc -c | tr -d ' ')"
LANES=$(grep -oE '^[A-Za-z0-9-]+' roster.txt | tr '\n' '|' | sed 's/|$//')
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null; }
path_atom()   { printf '%s\n' "$HIST" | awk -F'\t' -v p="$1" '$1=="P" && $2==p {print $3; exit}'; }
atom_newest() { [ -n "$1" ] || return 0
                printf '%s\n' "$HIST" | awk -F'\t' -v a="$1" 'tolower($2)==tolower(a) && $1=="A" {print $3; exit}'; }
canon()   { printf '%s\n' "$LANES" | tr '|' '\n' | grep -ix "$1" | head -1; }
is_lane() { printf '%s' "$1" | grep -qiE "^($LANES)\$"; }
s0=$(date +%s); i=0
git status --porcelain | awk '{print $NF}' | head -"$N" | while read -r p; do
  [ -f "$p" ] || continue
  fm=$(mtime "$p"); [ -n "$fm" ] || continue
  owner=$(canon "$(path_atom "$p")")
  onew=$(atom_newest "$owner")
  is_lane "$owner" || true
  i=$((i+1))
  [ $((i % 20)) -eq 0 ] && echo "  files=$i  cum=$(( $(date +%s) - s0 ))s"
done
echo "total for N=$N: $(( $(date +%s) - s0 ))s"
