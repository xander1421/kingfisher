#!/bin/sh
# H126 — find every call that DISCARDS a refusal's reason and then REPORTS the
# refusal onward. Not "every >/dev/null": that is 104 sites and most are an
# existence probe or a test asserting on an exit code, which have no reason to
# keep the text. F2 of this row is the predicate, and the predicate is the work.
#
# MECHANICAL SHORTLIST, then classification by reading. Said out loud rather than
# implied: the shortlist is reproducible (F3) and the classification is not
# automated, because "does this caller report the failure onward" is a question
# about what a human sees.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT" || exit 9

echo "=== population: output-discarding calls in harness-reachable code ==="
grep -rnE '>/dev/null' --include='*.sh' --include='*.py' --include='*.hook' \
     spikes .claude/hooks run_loop.sh bringup.sh 2>/dev/null \
  | grep -v '/elders/' | grep -v 'H126_discarded_reason' > /tmp/h126.all
echo "  total: $(wc -l < /tmp/h126.all | tr -d ' ')"

echo
echo "=== shortlist: the callee is a REPO CHECKER (something that refuses with a reason) ==="
# A repo checker is a tracked .sh/.py under spikes/ or .claude/hooks invoked as a
# subprocess. Anything else (git, ps, mkdir, docker) refuses without a diagnostic
# this project owns, so keeping its text is a different question.
# THE FILTER WAS WRONG ON ITS FIRST RUN AND DROPPED THE BEST INSTANCE. It was
# `grep -v 'test_'`, intended to drop noise from test FILES; it also dropped every
# call TO a test suite -- including `bringup.sh:187`, which discards the output of
# an 88-check suite and then tells the fleet "the loop contract is not enforceable
# as written" with no indication of which check. Exclude by CALLER path, never by
# a substring that can appear in the callee.
grep -E '(sh|bash|python3) [^ ]*(spikes|\.claude/hooks)/[^ ]*\.(sh|py)' /tmp/h126.all \
  | grep -vE '^spikes/harness/test_' > /tmp/h126.short
n=$(wc -l < /tmp/h126.short | tr -d ' ')
echo "  shortlisted: $n"
sed 's/^/    /' /tmp/h126.short | cut -c1-140

echo
echo "=== of those, which REPORT the refusal onward? (the 6 lines after each) ==="
while IFS= read -r line; do
  f=$(printf '%s' "$line" | cut -d: -f1)
  l=$(printf '%s' "$line" | cut -d: -f2)
  after=$(sed -n "$((l)),$((l+6))p" "$f" 2>/dev/null \
          | grep -nE 'echo|print|note |printf' | grep -viE 'ok |pass' | head -2)
  if [ -n "$after" ]; then
    printf '  REPORTS-ONWARD  %s:%s\n' "$f" "$l"
    printf '%s\n' "$after" | sed 's/^/                    /' | cut -c1-130
  else
    printf '  silent          %s:%s (exit code consumed, nothing said to anyone)\n' "$f" "$l"
  fi
done < /tmp/h126.short
