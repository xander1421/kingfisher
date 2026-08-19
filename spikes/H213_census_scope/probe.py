#!/usr/bin/env python3
"""H213 — the §10 rail census could not see the one file a cycle is writing.

`scratchcheck.py --scan` seeded from `git ls-files` — TRACKED paths only. A
cycle's own new probe is UNTRACKED BY CONSTRUCTION until that cycle commits, so
the file most likely to carry a fresh violation was the one file the census
could not look at, and absence read as clean.

TWO-SIDED against the PINNED pre-fix module, and the arm that matters is A6:
a file written this second, never committed, containing a real `/tmp` write,
must be FOUND by a bare `--scan`. That is the row's whole claim and it is the
only arm that reproduces the operating conditions of a live cycle.

THE CLASSIFIER IS NOT UNDER TEST AND A5 ASSERTS THAT. Pre-fix and post-fix must
give the SAME verdict on the SAME explicit path — the defect was the census, not
the detector, and an arm that cannot tell those apart proves nothing.
"""
import os, subprocess, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
HARNESS = os.path.join(ROOT, 'spikes', 'harness')
_PIN = '5a4bfae'          # the commit that carries scratchcheck v4 (pre-fix)

checks = []
def ck(name, cond, detail=''):
    checks.append((bool(cond), name, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def prefix_module():
    r = subprocess.run(['git', '-C', ROOT, 'show', f'{_PIN}:spikes/harness/scratchcheck.py'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, f'cannot read {_PIN}: {r.stderr.strip()}'
    text = r.stdout
    if 'v4 — H89' not in text:
        return None, f'{_PIN} does not carry scratchcheck v4 — pre-fix arm VOID'
    if "'-c', '-o', '--exclude-standard'" in text:
        return None, (f'{_PIN} already carries the H213 fix — the pre-fix arm '
                      f'would be a second post-fix arm and the run is VOID')
    return text, ''


def scan_with(source_text, extra_args=()):
    """Run a scratchcheck SOURCE (pinned or live) as `--scan` and return stdout."""
    # THE COPY GOES IN THIS SPIKE, NOT IN `spikes/harness/`. scratchcheck
    # derives ROOT from its own location as `../..`, and this spike sits at the
    # same depth, so the copy resolves to the same repo root. The first draft
    # put it in `spikes/harness/` — a DECLARED DEP SUBTREE for five spikes, so
    # every one of them would have gone red on a dirty tree for the duration of
    # this probe. That is H216's class exactly, and H216 is this lane's own row.
    # DEPTH IS LOAD-BEARING AND MY FIRST TWO DRAFTS BOTH GOT IT WRONG.
    # scratchcheck derives ROOT as `dirname(__file__)/../..`. This spike dir is
    # at the same depth as `spikes/harness`, so a copy placed DIRECTLY in it
    # resolves to the repo root — but a copy inside a TEMPDIR under it is one
    # level deeper and resolves to `spikes/`, which silently re-runs the whole
    # census over a fifth of the tree. That failure is invisible except as a
    # smaller number, so `A0b` asserts the derived root instead of trusting this
    # comment.
    mod = os.path.join(HERE, '.h213_probe_sc.py')
    with open(mod, 'w') as f:
        f.write(source_text)
    try:
        p = subprocess.run([sys.executable, mod, '--scan', *extra_args],
                           capture_output=True, text=True, cwd=ROOT)
        return p.stdout + p.stderr
    finally:
        os.remove(mod)


def main():
    print(__doc__.split('\n')[0])
    print(f"\n[pin] pre-fix arm = {_PIN} (scratchcheck v4)\n")

    pre_src, why = prefix_module()
    live_src = open(os.path.join(HARNESS, 'scratchcheck.py')).read()
    if pre_src is None:
        ck('A0 the PRE-FIX module is loadable and pinned', False, why)
        print('\nH213 probe: VOID')
        return 1
    ck('A0 the PRE-FIX module is loadable and pinned', True, _PIN)

    # A0b — THE ROOT THE COPY DERIVES MUST BE THIS REPO. A copy one level too
    # deep silently censuses `spikes/` instead, and the only symptom is a
    # smaller count. Asserted against a path that exists ONLY at the repo root.
    _probe_root = scan_with(live_src, [os.path.join(ROOT, 'run_all.sh')])
    ck('A0b the relocated copy derives THIS repo as its root, not `spikes/`',
       'NOT SCANNED' in _probe_root or 'write position' in _probe_root,
       _probe_root.strip().splitlines()[-1][:90] if _probe_root.strip() else 'no output')

    # ---- A1: the seeded population -------------------------------------------
    tracked = subprocess.run(['git', 'ls-files', '*.sh', '*.py', '*.hook'],
                             cwd=ROOT, capture_output=True, text=True).stdout.split()
    untracked = subprocess.run(
        ['git', 'ls-files', '-o', '--exclude-standard', '*.sh', '*.py', '*.hook'],
        cwd=ROOT, capture_output=True, text=True).stdout.split()
    ck('A1 the untracked population is not empty — if it were, this fix would be '
       'inert and the row theoretical (its own F3)',
       len(untracked) > 0, f'{len(untracked)} untracked vs {len(tracked)} tracked')

    # ---- A2 (F2): the fix must not drag in noise -----------------------------
    noise = [t for t in untracked
             if t.startswith('.scratch/') or t.startswith('elders/')]
    ck('A2 no `.scratch/` or `elders/` path enters the census — F2, the arm that '
       'could have killed the fix', not noise, f'{len(noise)} noise paths')

    # ---- A5 FIRST: the CLASSIFIER is unchanged --------------------------------
    # Run before A6 because if the classifier moved, A6 proves nothing.
    probe_sh = os.path.join(ROOT, 'spikes', 'H209_carries_toctou', 'probe.sh')
    if os.path.exists(probe_sh):
        a = scan_with(pre_src, [probe_sh])
        b = scan_with(live_src, [probe_sh])
        norm = lambda s: [l for l in s.splitlines() if ': ' in l and 'NOT SCANNED' not in l]
        ck('A5 the CLASSIFIER is untouched: same explicit path, same findings '
           'pre-fix and post-fix — the census was the defect, not the detector',
           norm(a) == norm(b), f'{len(norm(a))} vs {len(norm(b))} findings')
    else:
        ck('A5 fixture path present', False, probe_sh)

    # ---- A6: THE ROW'S CLAIM. A file written now, never committed. ------------
    live_file = os.path.join(ROOT, 'spikes', 'H213_census_scope',
                             '.h213_fresh_probe.sh')
    with open(live_file, 'w') as f:
        f.write('#!/bin/sh\n# a probe a cycle just wrote and has not committed\n'
                'echo hello > /tmp/h213_violation_written_by_a_live_cycle\n')
    try:
        tracked_now = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', live_file],
            cwd=ROOT, capture_output=True, text=True).returncode
        ck('A6a the fixture really is UNTRACKED — the condition the row is about',
           tracked_now != 0, 'git ls-files --error-unmatch: no match')
        pre_out = scan_with(pre_src)
        live_out = scan_with(live_src)
        ck('A6b PRE-FIX: a bare `--scan` does NOT see it (the defect, reproduced)',
           'h213_violation_written_by_a_live_cycle' not in pre_out)
        ck('A6c POST-FIX: a bare `--scan` DOES see it',
           'h213_violation_written_by_a_live_cycle' in live_out,
           [l for l in live_out.splitlines()
            if 'h213_violation' in l][:1])
    finally:
        os.remove(live_file)

    # ---- A3: the four real violations the tracked census never reported -------
    KNOWN = ['fixtures/run_all.sh',
             'fixtures/webgrok-pack/run_all.sh',
             'spikes/H185_launcher_generation/sandbox/bringup.sh',
             'spikes/H236_retirement_undone/sandbox/bringup.sh']
    pre_out = scan_with(pre_src)
    live_out = scan_with(live_src)
    missed_pre = [k for k in KNOWN if k in pre_out]
    found_post = [k for k in KNOWN if k in live_out]
    ck('A3a PRE-FIX reported NONE of the four live untracked violations',
       not missed_pre, f'{len(missed_pre)} reported')
    ck('A3b POST-FIX reports all four', len(found_post) == len(KNOWN),
       f'{len(found_post)} of {len(KNOWN)}')

    # ---- A4: no path is scanned twice ----------------------------------------
    import re
    m = re.search(r'in (\d+) shell file\(s\)', live_out)
    m2 = re.search(r'in (\d+) shell file\(s\)', pre_out)
    ck('A4 the census GREW rather than shifted — `-c -o` deduped, not doubled',
       m and m2 and int(m.group(1)) > int(m2.group(1))
       and int(m.group(1)) <= len(tracked) + len(untracked),
       f'{m2.group(1) if m2 else "?"} -> {m.group(1) if m else "?"} shell files scanned')

    ck('A7 this probe never wrote into `spikes/harness/`, a declared dep '
       'subtree for five spikes (H216\'s class, and its first draft did)',
       not os.path.exists(os.path.join(HARNESS, '.h213_probe_sc.py')))

    bad = [c for c in checks if not c[0]]
    print(f"\nH213 probe: {len(checks) - len(bad)} pass, {len(bad)} fail")
    for _, n, dt in bad:
        print(f"  FAILED  {n}  {dt}")
    import json
    with open(os.path.join(HERE, 'result.json'), 'w') as f:
        json.dump({'row': 'H213', 'pin_prefix': _PIN,
                   'tracked': len(tracked), 'untracked': len(untracked),
                   'checks_pass': len(checks) - len(bad), 'checks_fail': len(bad),
                   'arms': [{'name': n, 'pass': ok, 'detail': str(dt)}
                            for ok, n, dt in checks]},
                  f, indent=2, sort_keys=True)
        f.write('\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
