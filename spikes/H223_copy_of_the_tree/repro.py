#!/usr/bin/env python3
"""H223 repro — reconstructs the MECHANISM in a sandbox, touching nothing shared.

WHY THIS EXISTS SEPARATELY FROM `probe.py`. `probe.py` measured the INCIDENT: a
5,066-file copy of HEAD that really was sitting in `spikes/`, and the three
walkers that really did publish 40 / 8 / 29 output lines naming it. That
measurement is UNREPEATABLE -- the remedy was to delete the copy, so the
contaminated state no longer exists, and `incident.json` is a captured
observation rather than an artifact this certification can rebuild.

This file is the part that IS re-runnable, and it deliberately does NOT
re-materialise a copy inside `spikes/`: doing that would re-contaminate every
other lane's live scan for as long as it existed, which is precisely the damage
the row is about. AGENT-2's preregistered falsifier fired on the original one.
So the walk is exercised against a SANDBOX ROOT instead -- `constcheck.scan()`
takes its root as an argument, so the descent into a nested copy is measured
without a single write outside this spike's own scratch.

repro: python3 spikes/H223_copy_of_the_tree/repro.py
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import constcheck                                            # noqa: E402

SAND = os.path.join(ROOT, '.scratch', 'H223', 'sandbox')

# A control whose verdict is a literal -- the thing constcheck reports. Written
# out rather than copied from a real spike so the fixture cannot drift with one.
DEFECT = ('def main():\n'
          '    c3_ok = True\n'
          '    controls[2].observe(c3_ok, {"pin": PIN})\n')


def build(with_copy):
    shutil.rmtree(SAND, ignore_errors=True)
    real = os.path.join(SAND, 'spikes', 'S999_real')
    os.makedirs(real)
    open(os.path.join(real, 'run.py'), 'w').write(DEFECT)
    if with_copy:
        # The shape of the incident: a materialised tree one level down, whose
        # interior is a faithful copy of paths that also exist for real.
        cp = os.path.join(SAND, 'spikes', 'H999_materialised', 'fresh',
                          'spikes', 'S999_real')
        os.makedirs(cp)
        open(os.path.join(cp, 'run.py'), 'w').write(DEFECT)


def sweep():
    scanned = []
    live, _fix, _skip, _unp, files = constcheck.scan(SAND, scanned)
    return {'files': files,
            'live_verdicts': len(live),
            'paths': sorted({r[0] for r in live}),
            'scanned': sorted(scanned)}


def main():
    res = {}
    try:
        build(with_copy=False)
        res['without_copy'] = sweep()
        build(with_copy=True)
        res['with_copy'] = sweep()
    finally:
        shutil.rmtree(SAND, ignore_errors=True)
    res['sandbox_removed'] = not os.path.exists(SAND)

    a, b = res['without_copy'], res['with_copy']
    # THE FINDING, stated as a comparison and not as a count: the same one
    # defect, written once, is reported twice because a copy of its file exists.
    res['copy_is_walked'] = b['files'] == a['files'] + 1
    res['one_defect_reported_twice'] = b['live_verdicts'] == a['live_verdicts'] * 2
    res['copy_path_named'] = any('H999_materialised' in p for p in b['paths'])
    # And the untracked-population line sees the copy for what it is: a sandbox
    # path is in no repository, so every scanned file must come back "not in".
    ut = constcheck.untracked_scanned(ROOT, b['scanned'])
    res['population_flags_all_sandbox_paths'] = (ut is not None and len(ut) == b['files'])

    for k in sorted(res):
        print(f'  {k:34} {res[k]}')
    with open(os.path.join(HERE, 'repro.json'), 'w') as fh:
        json.dump(res, fh, indent=2, sort_keys=True)
    return res


if __name__ == '__main__':
    main()
