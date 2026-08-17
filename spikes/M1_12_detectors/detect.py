#!/usr/bin/env python3
"""Close the measured blind spots in the corpus's fault-expression.

M1.9 mutation-tested the 64-program admitted corpus against the agreement key
`(status, fuel_used, hash)` and found two holes:

    less-is-lesseq   (< a a) returns True        detected by  0/64
    stdlib-init      one extra stdlib rule       detected by  0/64

A replica wrong at every comparison boundary agrees byte-identically with an
honest one and quorum returns UNANIMOUS. That is a property of the WORKLOAD, not
of the quorum: `<` is executed by the corpus, but its fault is never observed,
because `<` and `<=` differ only at equality and no admitted program prints a
comparison of equal values.

These programs are not a bigger corpus. They are four small programs written to
make exactly those faults observable, measured with the same harness and the
same agreement key so the numbers compare directly against 0/64.

    python3 detect.py

Reuses M1_9_mutation/mutate.py rather than copying it: same probe control (a
mutation whose probe does not move is VOID, not 0), same byte-exact backup with
os.utime forward so cargo cannot skip the rebuild, same clean-binary assertion
before the baseline is recorded.
"""
import collections
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
PROGS = os.path.join(HERE, 'progs')

spec = importlib.util.spec_from_file_location(
    'mutate', os.path.join(ROOT, 'spikes', 'M1_9_mutation', 'mutate.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

# Point the borrowed sweep at the detector programs. BANNED is emptied: these
# are ours and none is on the admission ban surface.
M.CORPUS = PROGS
M.BANNED = set()


def main():
    M.build()
    M.assert_clean_binary()
    base = M.sweep()
    print(f'{len(base)} detector programs\n')

    results = {}
    for name, path, old, new, desc, probe in M.MUTATIONS:
        base_probe = M.probe_result(probe)
        bak = path + '.kf-backup'
        shutil.copy2(path, bak)
        try:
            M.apply(path, old, new)
            M.build()
            mut_probe = M.probe_result(probe)
            after = M.sweep()
        finally:
            shutil.move(bak, path)
            os.utime(path, None)     # copy2 preserves mtime; forward or cargo skips
            M.build()

        if mut_probe == base_probe:
            print(f'{name:16s} VOID -- probe did not move; mutant not live')
            results[name] = {'void': True}
            continue

        hits = [n for n, b in base.items() if after.get(n, {}).get('key') != b['key']]
        results[name] = {'detected': len(hits), 'n': len(base), 'by': sorted(hits)}
        print(f'{name:16s} {len(hits)}/{len(base)}   {sorted(hits)}')

    json.dump(results, open(os.path.join(HERE, 'detect.json'), 'w'), indent=1)
    print('\nwrote detect.json')
    return results


if __name__ == '__main__':
    main()
