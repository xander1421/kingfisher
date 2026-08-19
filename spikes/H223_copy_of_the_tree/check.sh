#!/bin/sh
# H223 check. Fails if constcheck v3's stated denominator breaks, in either
# direction, in any of the SHAPES it has to distinguish (error 41: a two-sided
# control in ONE shape is a one-sided control).
set -e
cd "$(dirname "$0")/../.."
fail=0
ck() { if [ "$2" = "$3" ]; then echo "  ok   $1"; else echo "  FAIL $1 -- want [$2] got [$3]"; fail=1; fi; }

# CONSTCHECK lets the mutation driver point every arm at a COPY of the module.
# Mutating `spikes/harness/constcheck.py` IN PLACE would break the shared module
# for four live lanes for the length of three check runs -- which is the class
# this very row reported to livechat an hour ago, and doing it inside the
# certification would be the joke writing itself.
: "${CONSTCHECK:=spikes/harness/constcheck.py}"

echo "--- constcheck --selfcheck (unchanged by v3) ---"
if python3 "$CONSTCHECK" --selfcheck >/dev/null 2>&1; then r=0; else r=$?; fi
ck "selfcheck green" 0 "$r"

echo "--- H201's runnable check still passes (v3 did not widen scan()'s tuple) ---"
if sh spikes/H201_literal_verdicts/check.sh >/dev/null 2>&1; then r=0; else r=$?; fi
ck "H201 check.sh PASS" 0 "$r"

echo "--- the denominator, four shapes ---"
out=$(python3 - <<'PY'
import os, sys
sys.path.insert(0, 'spikes/harness')
import importlib.util, os
spec = importlib.util.spec_from_file_location('cc', os.environ.get('CONSTCHECK', 'spikes/harness/constcheck.py'))
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)
R = os.path.abspath('.')

# A: a tracked file is NOT reported as absent from the repository.
print('A', len(cc.untracked_scanned(R, ['spikes/harness/constcheck.py'])))

# B: an untracked file IS, and only it.
b = cc.untracked_scanned(R, ['spikes/harness/constcheck.py',
                             'fixtures/verifier/grok_check.py'])
print('B', b == ['fixtures/verifier/grok_check.py'])

# C: THE SHAPE THAT PRODUCED THIS ROW -- a path INSIDE a materialised copy of
# the tree. Its SUFFIX is a tracked path and the path itself is not tracked, so
# any implementation that matches on the tail scores this file as present.
print('C', cc.untracked_scanned(
    R, ['spikes/H999_copy/fresh/spikes/harness/constcheck.py']) ==
    ['spikes/H999_copy/fresh/spikes/harness/constcheck.py'])

# D: git fails -> REFUSE to answer. A silent empty set here would report
# "all tracked" for exactly the case this exists to catch (error 42).
import subprocess
real = subprocess.run
subprocess.run = lambda *a, **k: type('P', (), {'returncode': 128, 'stdout': ''})()
try:
    print('D', cc.untracked_scanned(R, ['anything']) is None)
finally:
    subprocess.run = real
PY
)
ck "A tracked file is not called absent"            "A 0"    "$(echo "$out" | grep '^A ')"
ck "B untracked file named, and only it"           "B True" "$(echo "$out" | grep '^B ')"
ck "C a path inside a COPY of the tree is caught"  "C True" "$(echo "$out" | grep '^C ')"
ck "D git failure REFUSES, never reports clean"    "D True" "$(echo "$out" | grep '^D ')"

echo "--- the line reaches the report AND is computed, not constant ---"
# WHY THIS ARM IS NOT `grep -c '^  population: '`: that version PASSED a mutant
# that replaced the computation with `ut = []`, because the empty answer prints
# the healthy "all N are in this repository" branch. A check whose healthy
# answer is indistinguishable from a disabled instrument is the very class this
# row reports, and it shipped here first. The oracle is git, not a second copy
# of the rule: plant a file git calls untracked, require the report to NAME it.
PLANT=spikes/H223_copy_of_the_tree/_planted_untracked.py
trap 'rm -f "$PLANT"' EXIT INT TERM
printf 'x = 1\n' > "$PLANT"
if git ls-files --error-unmatch "$PLANT" >/dev/null 2>&1; then r=tracked; else r=untracked; fi
ck "the planted file is genuinely untracked (the oracle is git)" untracked "$r"
n=$(python3 "$CONSTCHECK" --list-untracked 2>&1 | grep -c "not in the repository: $PLANT" || true)
ck "the report NAMES a file git calls untracked" 1 "$n"
rm -f "$PLANT"
n=$(python3 "$CONSTCHECK" --list-untracked 2>&1 | grep -c "not in the repository: $PLANT" || true)
ck "and stops naming it once it is gone" 0 "$n"

echo "--- and the report is not empty (a silent instrument has no verdict) ---"
n=$(python3 "$CONSTCHECK" 2>&1 | wc -l | tr -d ' ')
if [ "$n" -gt 10 ]; then r=big; else r=small; fi
ck "constcheck still speaks" big "$r"

[ "$fail" = 0 ] && echo "check.sh: PASS" || echo "check.sh: FAIL"
exit "$fail"
