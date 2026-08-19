#!/bin/sh
# H229 · every number in RESULT.md, re-derivable in one command. ok-1, 2026-08-19.
# No seed: each arm is a git query over this repository's own history.
set -u
cd "$(dirname "$0")/../.." || exit 1

echo "== F1 · line-number citations of the fleet's append-only logs (tracked files only) =="
git ls-files -z | xargs -0 grep -ohE '(CHANNEL\.md|livechat\.log|DECISIONS\.log|HANDOFF\.md):[0-9]+' 2>/dev/null \
  | sed 's/:[0-9]*$//' | sort | uniq -c

echo
echo "== F2 · CHANNEL.md line count now, and citations pointing PAST it =="
NOW=$(wc -l < CHANNEL.md)
echo "CHANNEL.md is $NOW lines"
git ls-files -z | xargs -0 grep -ohE 'CHANNEL\.md:[0-9]+' 2>/dev/null \
  | sed 's/.*://' | awk -v n="$NOW" '$1>n' | wc -l | sed 's/^/citations past EOF: /'
echo "the rotation: $(git log --oneline -1 228fc46 | cut -c1-60)"
echo "  before: $(git show 228fc46^:CHANNEL.md | wc -l) lines   after: $(git show 228fc46:CHANNEL.md | wc -l) lines"

echo
echo "== F3 · commits to CHANNEL.md that REMOVED lines (append-only as a property) =="
git log --format='%h' -- CHANNEL.md | while read -r c; do
  git show --numstat --format='' "$c" -- CHANNEL.md | awk -v c="$c" '$2>0 {print "  "c" del="$2" add="$1}'
done

echo
echo "== the property that does NOT separate: deletions per addition, whole history =="
printf "  %-30s %8s %8s %7s\n" file add del del/add
for f in CHANNEL.md livechat.log DECISIONS.log HANDOFF.md HANDOFF.ok-1.md \
         WORK_QUEUE.md MISSION_LOOP.md spikes/harness/githygiene.py run_loop.sh out/LEDGER.md; do
  git log --numstat --format='' -- "$f" \
    | awk -v f="$f" '{a+=$1; d+=$2} END {printf "  %-30s %8d %8d %7.3f\n", f, a, d, (a?d/a:0)}'
done

echo
echo "== F4 · any other size decision in the commit path =="
grep -rn --include='*.py' --include='*.sh' --include='*.hook' -E 'MAX_ADD|1_048_576|1048576|cat-file -s' \
  spikes/harness .git/hooks 2>/dev/null | grep -vc githygiene.py | sed 's/^/  non-githygiene hits: /'

echo
echo "== F5 · what the gate reads vs what the sanctioned path commits =="
for pair in \
  "gate reads:|spikes/harness/githygiene.py|git\", \"diff\", \"--cached\"" \
  "script commits:|spikes/harness/commit_scoped.sh|^git commit --no-verify --only" \
  "the label:|spikes/harness/commit_scoped.sh|index-scoped, already correct"
do
  lbl=${pair%%|*}; rest=${pair#*|}; f=${rest%%|*}; pat=${rest#*|}
  hit=$(grep -nE "$pat" "$f" | grep -vE '^[0-9]+:#' | head -1)
  if [ -z "$hit" ]; then
    echo "  $lbl ARM DID NOT FIND ITS LINE — the evidence is absent, not clean"
  else
    echo "  $lbl $hit"
  fi
done

echo
echo "== the mechanism, both directions =="
python3 spikes/harness/githygiene.py --selfcheck 2>&1 | grep 'H229'
