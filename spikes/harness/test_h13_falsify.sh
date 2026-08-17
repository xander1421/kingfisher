#!/usr/bin/env bash
# test_h13_falsify.sh — proves the H13 concurrency check in test_loop_gate.sh
# CAN FAIL, and that it is not passing for some other reason.
#
# The check it guards spent its whole life as a `KNOWN` line: it printed the
# undercount and passed the suite either way, so the suite's exit code could not
# tell a fixed fuse from a broken one. Promoting it to an assertion is worth
# nothing unless a red run is reachable (H7's question), so:
#
#   BITES   — restore the unlocked read-modify-write on an isolated copy and
#             `fuse counts 20/20 under concurrency` must go FAIL.
#   CONTROL — the same tree, unmodified, must show that check PASS. Without this
#             half a scratch tree that is broken for an unrelated reason (a
#             missing brief, an absent git repo) produces the FAIL line for free
#             and the falsifier certifies itself.
#
# usage: bash spikes/harness/test_h13_falsify.sh     exit 0 = the check bites.
set -u
CHECK="fuse counts 20/20 under concurrency"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
X="$(mktemp -d)"
trap 'rm -rf "$X"' EXIT

build() {   # build <dir> ; leaves a committed scratch repo holding the harness
  mkdir -p "$1/spikes/harness" "$1/.claude/hooks"
  cp "$ROOT/run_loop.sh" "$1/run_loop.sh"
  cp "$ROOT/.claude/hooks/loop_gate.sh" "$1/.claude/hooks/loop_gate.sh"
  cp "$ROOT/spikes/harness/test_loop_gate.sh" "$1/spikes/harness/"
  ( cd "$1" && git init -q . && git add -A \
    && git -c user.email=h13@local -c user.name=h13 commit -qm scratch ) >/dev/null
}
verdict() {  # verdict <dir> -> PASS | FAIL | ABSENT
  local out; out="$(cd "$1" && bash spikes/harness/test_loop_gate.sh 2>&1)"
  if   printf '%s' "$out" | grep -q "PASS  $CHECK"; then echo PASS
  elif printf '%s' "$out" | grep -q "FAIL  $CHECK"; then echo FAIL
  else echo ABSENT; fi
}

build "$X/control"
build "$X/broken"

# Restore the v6 defect: drop the lock, leaving the bare read-modify-write.
# ANCHORED, and the anchor is asserted — a replacement whose anchor is absent
# returns the input unchanged (CLAUDE.md, Editing), which here would leave the
# fix in place and report the check INERT for a reason that is not true.
python3 - "$X/broken/.claude/hooks/loop_gate.sh" <<'PY'
import sys
p = sys.argv[1]
fixed = '''LOCK="${BLOCKS}.lock"
held=no
i=0
while [ "$i" -lt 50 ]; do
  if mkdir "$LOCK" 2>/dev/null; then held=yes; break; fi
  i=$((i+1)); sleep 0.02
done
[ "$held" = no ] && rm -rf "$LOCK"
N=$(cat "$BLOCKS" 2>/dev/null || echo 0)
case "$N" in (''|*[!0-9]*) N=0 ;; esac
N=$((N+1))
echo "$N" > "$BLOCKS"
[ "$held" = yes ] && rmdir "$LOCK" 2>/dev/null'''
broken = '''N=$(cat "$BLOCKS" 2>/dev/null || echo 0)
case "$N" in (''|*[!0-9]*) N=0 ;; esac
N=$((N+1))
echo "$N" > "$BLOCKS"'''
s = open(p).read()
assert fixed in s, "anchor absent — v7's lock is not where this script thinks it is"
open(p, "w").write(s.replace(fixed, broken))
PY
[ $? -eq 0 ] || { echo "FAIL: could not restore the defect"; exit 1; }
( cd "$X/broken" && git add -A \
  && git -c user.email=h13@local -c user.name=h13 commit -qm "defect restored" ) >/dev/null

c="$(verdict "$X/control")"
b="$(verdict "$X/broken")"
printf '  CONTROL  %s: %s\n' "$CHECK" "$c"
printf '  BROKEN   %s: %s\n' "$CHECK" "$b"

if [ "$c" = PASS ] && [ "$b" = FAIL ]; then
  echo "H13: the check bites — locked fuse passes, unlocked fuse fails"
  exit 0
fi
echo "H13: NOT falsified — want control=PASS broken=FAIL, got control=$c broken=$b"
[ "$c" != PASS ] && echo "  the control is not green, so the FAIL above proves nothing"
[ "$b" != FAIL ] && echo "  the check passed with its defect restored: documentation, not enforcement (A28)"
exit 1
