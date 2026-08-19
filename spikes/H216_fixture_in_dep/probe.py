#!/usr/bin/env python3
"""H216 — a self-check fixture created INSIDE a declared dependency subtree.

`recordloss.py:275` and `statuscheck.py:332` both ran
`tempfile.mkdtemp(prefix=..., dir=HERE)` with `HERE == spikes/harness` — a tree
that ten spikes name in `deps=[...]`. Cleanup is `shutil.rmtree` in a `finally`,
and a KILLED process never runs its `finally`, so one such directory sat in that
subtree for hours and every spike declaring the dep read as a dirty tree on a
condition none of them caused.

BOTH COMMENTS ABOVE THOSE LINES CITED §10 AND WERE RIGHT ABOUT THE RAIL: the
fixture belongs under the workspace, not in `/tmp`. They were wrong about the
LOCATION — "under the workspace" and "outside every dep subtree" are two
requirements and only the first was being met. `.scratch/` meets both: it is in
the workspace for §10 and gitignored (`.gitignore:111`) so it is invisible to
`git status` as well as outside the declared trees.

A6 IS THE ARM THAT MATTERS: run both self-checks for real and require that
`spikes/harness` gains nothing. Everything else is a proxy for that.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
HARNESS = os.path.join(ROOT, 'spikes', 'harness')
_PIN = 'eef507d'      # carries both pre-fix sites

checks = []
def ck(name, cond, detail=''):
    checks.append((bool(cond), name, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def dirty(path):
    return subprocess.run(['git', 'status', '--porcelain', path], cwd=ROOT,
                          capture_output=True, text=True).stdout.splitlines()


def main():
    print(__doc__.split('\n')[0])
    print()

    # ---- A1: the class, not the site. No harness module may seed a fixture
    #          root in its own directory.
    offenders = []
    for fn in sorted(os.listdir(HARNESS)):
        if not fn.endswith('.py'):
            continue
        txt = open(os.path.join(HARNESS, fn), errors='replace').read()
        for m in re.finditer(r'(mkdtemp|TemporaryDirectory)\([^)]*dir\s*=\s*HERE',
                             txt, re.S):
            offenders.append(f'{fn}:{txt[:m.start()].count(chr(10)) + 1}')
    ck('A1 no harness module seeds a fixture root with `dir=HERE` — the CLASS, '
       'checked over the whole directory rather than the two sites I knew about',
       not offenders, str(offenders))

    # ---- A2: the pre-fix arm. Both sites really did do it. -------------------
    pre_hits = []
    for fn in ('recordloss.py', 'statuscheck.py'):
        r = subprocess.run(['git', '-C', ROOT, 'show', f'{_PIN}:spikes/harness/{fn}'],
                           capture_output=True, text=True)
        if r.returncode == 0 and re.search(r'mkdtemp\([^)]*dir=HERE', r.stdout, re.S):
            pre_hits.append(fn)
    ck('A2 PRE-FIX both modules DID seed inside the dep subtree — if this arm '
       'ever goes quiet the pin is wrong, not the tree', len(pre_hits) == 2,
       f'{pre_hits} at {_PIN}')

    # ---- A3: the dep is really declared, or none of this matters -------------
    # COUNTED FROM THE RECORDS, NOT FROM A GREP. A `git grep` for the path
    # string matched 57 files — imports, prose and `sys.path.insert` alike — and
    # 57 is not the blast radius of anything. What matters is which spikes
    # RECORDED that tree as a dependency, and their own provenance says so.
    import glob, json as _json
    decl = []
    for p in glob.glob(os.path.join(ROOT, 'spikes', '*', 'provenance.json')):
        try:
            r = _json.load(open(p))
        except Exception:
            continue
        keys = list((r.get('manifests') or {}).keys()) + [
            d.get('path', '') if isinstance(d, dict) else str(d)
            for d in (r.get('repos') or [])]
        if any('spikes/harness' in str(k) or str(k).endswith('/harness')
               for k in keys):
            decl.append(os.path.basename(os.path.dirname(p)))
    ck('A3 spikes DO record `spikes/harness` as a dependency — the blast radius '
       'is not zero (the row\'s own F1), counted from the RECORDS and not from '
       'a path grep that reads 57', len(decl) > 0, f'{len(decl)} spike(s)')

    # ---- A4: .scratch is gitignored, so debris cannot dirty git either -------
    ig = subprocess.run(['git', 'check-ignore', '-v', '.scratch/x'], cwd=ROOT,
                        capture_output=True, text=True)
    ck('A4 `.scratch/` is gitignored, so a fixture that outlives its process is '
       'invisible to `git status` as well as outside the dep subtree',
       ig.returncode == 0, ig.stdout.strip()[:60])

    # ---- A5: the debris that WAS in the subtree is gone ----------------------
    left = [p for p in os.listdir(HARNESS)
            if p.startswith('.recordloss_selfcheck.')
            or p.startswith('.statuscheck_selfcheck.')]
    ck('A5 no self-check debris remains in `spikes/harness`', not left, str(left))

    # ---- A6: THE ARM THAT MATTERS. Run them for real. -----------------------
    before = set(dirty('spikes/harness'))
    for mod in ('recordloss.py', 'statuscheck.py'):
        subprocess.run([sys.executable, os.path.join(HARNESS, mod), '--selfcheck'],
                       cwd=ROOT, capture_output=True, text=True)
    after = set(dirty('spikes/harness'))
    ck('A6 running BOTH self-checks for real adds nothing to `spikes/harness` — '
       'the proxy arms above are only evidence for this one',
       after == before, f'{len(after - before)} new entr(ies): {sorted(after - before)[:3]}')

    # ---- A7: and the fixtures clean up after themselves in .scratch too ------
    scratch = os.path.join(ROOT, '.scratch')
    leftover = [p for p in os.listdir(scratch) if 'selfcheck.' in p] \
        if os.path.isdir(scratch) else []
    ck('A7 ...and they clean up after themselves in `.scratch/` on a normal exit '
       '(a KILLED one still cannot, which is why the LOCATION is the fix and not '
       'better cleanup)', not leftover, str(leftover[:3]))

    bad = [c for c in checks if not c[0]]
    print(f"\nH216 probe: {len(checks) - len(bad)} pass, {len(bad)} fail")
    for _, n, d in bad:
        print(f"  FAILED  {n}  {d}")
    import json
    with open(os.path.join(HERE, 'result.json'), 'w') as f:
        json.dump({'row': 'H216', 'pin_prefix': _PIN,
                   'spikes_declaring_dep': len(decl),
                   'checks_pass': len(checks) - len(bad), 'checks_fail': len(bad),
                   'arms': [{'name': n, 'pass': ok, 'detail': str(d)}
                            for ok, n, d in checks]}, f, indent=2, sort_keys=True)
        f.write('\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
