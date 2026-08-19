#!/usr/bin/env python3
"""H232 mutants of run_loop.sh's per-turn lock re-read, one property each.

Separated from `test_h232_falsify.sh` because the first version built these edits
inside a heredoc inside a shell function: two of the three anchors never matched,
the mutants were never written, and the falsifier reported `mutant does not parse`
for a file that did not exist. The anchor assertion is what said so -- a silent
no-op edit would have reported the arm GREEN, which is the H217 defect this file
is supposed to detect, in the detector.

usage: python3 spikes/harness/h232_mutants.py <src> <dst> M1|M2|M3
"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from edits import anchored_replace

MUTANTS = {
    # the re-read deleted: the exact pre-H232 launcher
    'M1': ('  _lk=$(tr -dc \'0-9\' < "$LOCK" 2>/dev/null)',
           '  _lk=$$   # M1: never look at the lock again'),
    # retire on ANY mismatch: the absent/dead re-acquire branch removed
    'M2': ('    if [ -z "$_lk" ] || ! ps -p "$_lk" -o command= 2>/dev/null | grep -q \'run_loop\\.sh\'; then',
           '    if false; then   # M2: any mismatch retires'),
    # liveness by pid alone: a reused pid reads as the holder
    'M3': ('! ps -p "$_lk" -o command= 2>/dev/null | grep -q \'run_loop\\.sh\'; then',
           '! kill -0 "$_lk" 2>/dev/null; then   # M3: pid alone'),
}

src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]
old, new = MUTANTS[name]
s = open(src).read()
open(dst, 'w').write(anchored_replace(s, old, new))
print(f'{name}: applied')
