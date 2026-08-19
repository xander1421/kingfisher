#!/bin/sh
# check.sh v1 — H187, ATOM-3, 2026-08-19. The §12.3 runnable check for this row.
#
# It does NOT re-run the sweep (31s of git calls, and the counts move under a
# live fleet anyway). It checks the three things that would make the row wrong:
# the checker disagrees with `certify`; the checker's own arms went dead; the
# record on disk is not the one this RESULT.md describes.
set -e
cd "$(git rev-parse --show-toplevel)"
fail=0
ck() { if [ "$2" = "$3" ]; then echo "  ok   $1"; else echo "  FAIL $1 (want $2, got $3)"; fail=1; fi; }

# C1 — the shipped entry point still agrees with a real certify() run, both ways.
# `if`, not a bare call: under `set -e` a failing bare command aborts the script
# BEFORE `ck` prints why, so the one run that matters is the one with no output.
if python3 spikes/harness/stalecheck.py --selfcheck >/dev/null 2>&1; then src=0; else src=$?; fi
ck "stalecheck --selfcheck green" 0 "$src"

# C2 — the arms are not dead. Half the two-clock rule removed must turn it red.
# v1 shipped with this mutation SURVIVING, which is why the arm exists.
MUT=spikes/harness/.check_h187_mutant.py
sed 's|            if src_mt and int(os.path.getmtime(a)) >= src_mt:|            if False:|' \
    spikes/harness/stalecheck.py > "$MUT"
if cmp -s "$MUT" spikes/harness/stalecheck.py; then
  echo "  FAIL mutation anchor absent — a no-op mutation reads as a passing arm"
  fail=1
fi
python3 "$MUT" --selfcheck >/dev/null 2>&1 && mrc=0 || mrc=$?
rm -f "$MUT"
ck "mutant (second opinion removed) is REJECTED" 1 "$mrc"

# C3 — the record this RESULT.md describes is the one on disk.
if [ -f spikes/H187_stale_sweep/sweep.json ]; then jrc=0; else jrc=1; fi
ck "sweep.json present" 0 "$jrc"
ck "certify recorded ok" true \
   "$(python3 -c "import json;print(str(json.load(open('spikes/H187_stale_sweep/provenance.json'))['ok']).lower())")"

# The scan is BOUNDED and a truncated scan is not a clean bill (exit 2, not 0).
python3 spikes/harness/stalecheck.py --max-seconds=0 >/dev/null 2>&1 && prc=0 || prc=$?
ck "zero-second budget refuses as PARTIAL" 2 "$prc"

[ "$fail" = 0 ] && echo "check.sh: PASS" || echo "check.sh: FAIL"
exit "$fail"
