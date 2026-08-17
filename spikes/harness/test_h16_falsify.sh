#!/usr/bin/env bash
# test_h16_falsify.sh — proves the two H16 checks in test_loop_gate.sh CAN FAIL.
#
# §5: "a control that cannot fail is not a control", and this repo's most
# repeated failure is a suite that goes green over the defect it was written for
# — H1's 15 checks all set CALLSIGN, the 22 checks all invoked the hook and none
# its wiring, check 3 certified the unsafe shared-signal path without ever
# testing its isolation. So the H16 checks get the one thing those did not: a
# runnable demonstration that they fail when the defect is put back.
#
# It rebuilds a scratch copy of the harness, restores each defect by ANCHORED
# replacement (asserting the anchor matched, per CLAUDE.md's Editing rule — a
# str.replace whose anchor is absent returns the input unchanged and shipped an
# inert flag here once), and requires exactly the two expected FAIL lines.
#
# usage: bash spikes/harness/test_h16_falsify.sh      exit 0 = the checks bite.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
X="$(mktemp -d)"
trap 'rm -rf "$X"' EXIT
mkdir -p "$X/spikes/harness" "$X/.claude/hooks"
cp "$ROOT/run_loop.sh" "$X/run_loop.sh"
cp "$ROOT/.claude/hooks/loop_gate.sh" "$X/.claude/hooks/loop_gate.sh"
cp "$ROOT/spikes/harness/test_loop_gate.sh" "$X/spikes/harness/"

python3 - "$X" <<'PY'
import sys
X = sys.argv[1]
# (path, fixed text, the defect it replaces)
defects = [
    (X + "/run_loop.sh",
     'rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK" ".loop_signal.${CALLSIGN}"',
     'rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK"'),
    (X + "/.claude/hooks/loop_gate.sh",
     'into the file .loop_signal.%s ,',
     'into the file .loop_signal ,'),
]
for path, fixed, broken in defects:
    s = open(path).read()
    assert fixed in s, "anchor absent in %s — this script is testing something else" % path
    open(path, "w").write(s.replace(fixed, broken))
PY
[ $? -eq 0 ] || { echo "FAIL: could not restore the defects"; exit 1; }

# The suite's registration checks read `git ls-files`, so the scratch tree needs
# to be a repo. It contains no settings.json, so those checks simply find none.
( cd "$X" && git init -q . && git add -A \
  && git -c user.email=h16@local -c user.name=h16 commit -qm "defects restored" ) >/dev/null

out="$(cd "$X" && bash spikes/harness/test_loop_gate.sh 2>&1)"
rc=0
for want in "refusal names a path the hook obeys" "launcher clears a stale signal"; do
  if printf '%s' "$out" | grep -q "FAIL  $want"; then
    printf '  BITES  %s\n' "$want"
  else
    printf '  INERT  %s — the check passed with its defect restored\n' "$want"; rc=1
  fi
done
if [ "$rc" -eq 0 ]; then echo "H16: both checks fail when the defect returns"; else
  echo "H16: a check did not fire — it is documentation, not enforcement (A28)"; fi
exit "$rc"
