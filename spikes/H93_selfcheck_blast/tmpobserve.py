#!/usr/bin/env python3
"""H93 · tmpobserve.py v1 — record every temp path a module CREATES, whether or
not it still exists afterwards.

WHY THIS EXISTS (§12.7 rationale)
DEFECT REMOVED, and it is in this spike's OWN first instrument: `probe.py` v1
computed `writes_outside_workspace = bool(left_outside) or bool(redirected_
tmpdir_entries)`, i.e. it read an EMPTY redirect box as CONFINEMENT — while its
own docstring said, in the same file, *"an empty box is reported as UNKNOWN-or-
none and never as proof of confinement."* A `mkdtemp` followed by `rmtree`
leaves nothing for an after-the-fact `listdir` to find, so v1 reported
`outside=False` for four modules that provably call `tempfile.mkdtemp()`. The
rule was WRITTEN and NOT MECHANISED (§12.10) inside forty lines of its own
statement.

METHOD: the module is executed with `tempfile`'s creators wrapped, so the path
is recorded at CREATION time. Removal cannot hide it.

SCOPE, stated rather than implied: this sees PYTHON `tempfile` only. A module
shelling out to `mktemp(1)`, or hardcoding a literal '/tmp/...', is INVISIBLE
here — that is what `probe.py`'s surviving snapshot arm is for, and the two are
reported separately rather than summed into one number.
"""
import json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

SHIM = r'''
import json, os, sys, tempfile
_log = os.environ['H93_LOG']
_rec = []
def _note(kind, path):
    _rec.append({'kind': kind, 'path': str(path)})
    open(_log, 'w').write(json.dumps(_rec))
for _name in ('mkdtemp', 'mkstemp'):
    _orig = getattr(tempfile, _name)
    def _mk(*a, __o=_orig, __n=_name, **k):
        r = __o(*a, **k)
        _note(__n, r[1] if __n == 'mkstemp' else r)
        return r
    setattr(tempfile, _name, _mk)
_otd = tempfile.TemporaryDirectory
class _TD(_otd):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        _note('TemporaryDirectory', self.name)
tempfile.TemporaryDirectory = _TD
_ontf = tempfile.NamedTemporaryFile
def _ntf(*a, **k):
    f = _ontf(*a, **k)
    _note('NamedTemporaryFile', f.name)
    return f
tempfile.NamedTemporaryFile = _ntf
import runpy
sys.argv = [sys.argv[1]] + sys.argv[2:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''


def observe(path, timeout=90):
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.h93log.json')
    if os.path.exists(log):
        os.remove(log)
    env = dict(os.environ, H93_LOG=log)
    try:
        p = subprocess.run([sys.executable, '-c', SHIM, path, '--selfcheck'],
                           cwd=ROOT, env=env, capture_output=True, text=True,
                           timeout=timeout)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = None
    rec = json.load(open(log)) if os.path.exists(log) else []
    if os.path.exists(log):
        os.remove(log)
    ws = ROOT + os.sep
    outside = [r for r in rec if not os.path.abspath(r['path']).startswith(ws)]
    return {'module': os.path.basename(path), 'rc': rc, 'temp_creations': len(rec),
            'outside_workspace': [r['path'] for r in outside],
            'writes_outside': bool(outside)}


def selfcheck():
    """C3 (must fire): a fixture that mkdtemps and REMOVES it must still be
    reported OUTSIDE. Fails if the shim records at removal rather than creation
    -- which is precisely probe.py v1's defect, so the check is the retraction.
    C4 (must fire): a fixture creating no temp path reports none. Fails if the
    shim invents records, which would make C3 vacuous."""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.tobs')
    subprocess.run(['rm', '-rf', d]); os.makedirs(d)
    bad = []

    def ck(cond, note):
        print(f'  {"ok  " if cond else "FAIL"}  {note}')
        if not cond:
            bad.append(note)
    try:
        open(os.path.join(d, 'transient.py'), 'w').write(
            "import sys, tempfile, shutil\n"
            "t = tempfile.mkdtemp()\nshutil.rmtree(t)\n"
            "if '--selfcheck' in sys.argv: sys.exit(0)\n")
        open(os.path.join(d, 'quiet.py'), 'w').write(
            "import sys\nif '--selfcheck' in sys.argv: sys.exit(0)\n")
        t = observe(os.path.join(d, 'transient.py'))
        q = observe(os.path.join(d, 'quiet.py'))
        ck(t['writes_outside'] and t['temp_creations'] == 1,
           'C3: a mkdtemp REMOVED before exit is still recorded as an outside write')
        ck(t['rc'] == 0, 'C3b: the shim does not change the module verdict')
        ck(q['temp_creations'] == 0 and not q['writes_outside'],
           'C4: a module creating no temp path records none')
    finally:
        subprocess.run(['rm', '-rf', d])
    if bad:
        print(f'SELFCHECK FAILED: {bad}')
        return 1
    print('selfcheck: creation-time recording survives removal; no invented records')
    return 0


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(selfcheck())
    sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
    import selfcheckall
    H = os.path.join(ROOT, 'spikes', 'harness')
    rows = [observe(os.path.join(H, n)) for n in selfcheckall.modules()]
    n = sum(1 for r in rows if r['writes_outside'])
    for r in rows:
        print(f"  {r['module']:20} temp_creations={r['temp_creations']:2} "
              f"outside={r['writes_outside']!s:5} "
              + (r['outside_workspace'][0] if r['outside_workspace'] else ''))
    print(f"\n{n}/{len(rows)} swept modules WRITE OUTSIDE THE WORKSPACE (§10), "
          f"measured at CREATION time.")
    json.dump({'rows': rows, 'n_outside': n, 'n_swept': len(rows)},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'tmpobserve.json'), 'w'), indent=1)
