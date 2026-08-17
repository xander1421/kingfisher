#!/usr/bin/env bash
# test_h51_falsify.sh — H51. Does trie_witness's selfcheck go RED when the defect
# returns? A passing suite cannot answer that for itself (H7).
#
# THE DEFECT: `witness_bytes()` dispatched on `pf['kind']`, and a membership
# proof is `{'steps', 'leaf'}` with no `kind` at all — so the one correct
# accounting in the module RAISED KeyError on the commonest proof shape, and four
# spikes (S77, S79, S80, S84) used `steps_bytes` instead, which is the
# authentication path only. For an absence proof the difference is the DIVERGENCE
# CHILD SET, which is what S79's model charges: `spikes/S79_absence_bytes/ATTACK.md`.
#
# NO STALE COPY IS COMMITTED. The broken variant is derived here at run time and
# deleted, because a checked-in copy of a shared instrument is exactly A24 — a
# second artifact that drifts from the source it was cut from.
#
# usage: bash spikes/harness/test_h51_falsify.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/spikes/W2_witnessed_trie/trie_witness.py"
[ -f "$SRC" ] || { echo "FAIL: no trie_witness.py at $SRC"; exit 1; }

WORK="$ROOT/spikes/W2_witnessed_trie/.h51_falsify"
trap 'rm -rf "$WORK"' EXIT
rm -rf "$WORK"; mkdir -p "$WORK"
cp "$SRC" "$WORK/tw.py"

# Restore the defect, and ASSERT THE EDIT TOOK. A patch whose anchor is absent
# leaves the file unchanged and the run then reports the control's result under
# the defect's name — CLAUDE.md's editing rule, and the same shape as the BSD
# `sed -i 's/\bH42\b/'` that silently matched nothing this same hour.
python3 - "$WORK/tw.py" <<'PY' || exit 1
import sys
p = sys.argv[1]
s = open(p).read()
old = """    if 'leaf' in pf:                       # membership: the terminal descriptor
        return n + desc_bytes(pf['leaf'])
    if pf.get('kind') == COVER:            # completeness: the answer set"""
new = """    if pf['kind'] == COVER:                # DEFECT RESTORED (H51)"""
if old not in s:
    sys.exit('FAIL: falsifier anchor absent — the defect was NOT restored, so a '
             'red run below would be about something else')
open(p, 'w').write(s.replace(old, new, 1))
PY

fail=0
if python3 "$WORK/tw.py" --selfcheck >/dev/null 2>&1; then
  echo "  INERT  selfcheck passed with the defect restored — it is documentation, not enforcement (A28)"
  fail=1
else
  echo "  BITES  selfcheck fails when witness_bytes cannot size a membership proof"
fi

# The control: the real module must be green in the same breath, or "it went red"
# says nothing about the defect.
if python3 "$SRC" --selfcheck >/dev/null 2>&1; then
  echo "  GREEN  the unmodified module passes (control)"
else
  echo "  FAIL   the unmodified module does NOT pass — the red above is not about the defect"
  fail=1
fi

[ "$fail" -eq 0 ] && { echo "H51: the check fails when the defect returns"; exit 0; }
echo "H51: a check did not fire — it is documentation, not enforcement (A28)"
exit 1
