#!/bin/sh
# check.sh v1 — H201, ATOM-3, 2026-08-19. The §12.3 runnable check for this row.
#
# Does NOT re-run the sweep (the counts move under a live fleet). Checks the
# three things that would make the row wrong: the detector stops being
# two-sided; its arms go dead; or this spike starts shipping the defect it
# reports.
set -e
cd "$(git rev-parse --show-toplevel)"
fail=0
ck() { if [ "$2" = "$3" ]; then echo "  ok   $1"; else echo "  FAIL $1 (want $2, got $3)"; fail=1; fi; }

# `if`, not a bare call: under `set -e` a failing bare command aborts before
# `ck` prints why, so the one run that matters is the one with no output.
if python3 spikes/harness/constcheck.py --selfcheck >/dev/null 2>&1; then r=0; else r=$?; fi
ck "constcheck --selfcheck green (8 arms, both directions)" 0 "$r"

# The name-resolution branch is load-bearing: without it S91 is invisible, which
# is exactly the state v1 shipped in.
MUT=spikes/harness/.check_h201_mutant.py
sed 's|            elif isinstance(a0, ast.Name) and a0.id in consts:|            elif False:|' \
    spikes/harness/constcheck.py > "$MUT"
if cmp -s "$MUT" spikes/harness/constcheck.py; then
  echo "  FAIL mutation anchor absent — a no-op mutation reads as a passing arm"; fail=1
fi
n=$(python3 -c "
import importlib.util,sys,os
spec=importlib.util.spec_from_file_location('m','$MUT')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
live,_f,_s,_u,_n=m.scan(os.path.abspath('.'))
print(len([r for r in live if r[0]=='spikes/S91_multi_agent_quorum/run.py']))")
rm -f "$MUT"
ck "mutant cannot see S91 (branch is load-bearing)" 0 "$n"

# ...and the real module can.
n=$(python3 -c "
import sys,os; sys.path.insert(0,'spikes/harness')
import constcheck as cc
live,_f,_s,_u,_n=cc.scan(os.path.abspath('.'))
print(len([r for r in live if r[0]=='spikes/S91_multi_agent_quorum/run.py']))")
ck "constcheck DOES see S91's c3_ok = True" 1 "$n"

# The reporter still does not ship the defect it reports (C4).
n=$(python3 -c "
import sys,os; sys.path.insert(0,'spikes/harness')
import constcheck as cc
live,_f,_s,_u,_n=cc.scan(os.path.abspath('.'))
print(len([r for r in live if r[0].startswith('spikes/H201_')]))")
ck "this spike ships no literal verdict of its own" 0 "$n"

ck "certify recorded ok" true \
   "$(python3 -c "import json;print(str(json.load(open('spikes/H201_literal_verdicts/provenance.json'))['ok']).lower())")"

[ "$fail" = 0 ] && echo "check.sh: PASS" || echo "check.sh: FAIL"
exit "$fail"
