#!/usr/bin/env python3
"""H98 falsifier: does provenance.py's new demo() actually go RED without v3?

A check nobody has broken on purpose is a check nobody has tested. Two mutations
on an ISOLATED COPY -- the live module is never touched:

  F1  restore v2's dirty loop verbatim (porcelain path used AS A FILE)
  F2  keep the expansion but drop the .md filter inside it -- the half a
      pathspec could not deliver, and the half a fix that only chased the
      artifact-vs-artifact case would have missed

CONTROL: the untouched copy must PASS, or F1/F2 are measuring a broken copy.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', 'harness', 'provenance.py'))
src = open(SRC).read()

V3_LOOP = """    for f in dirty:
        fp = os.path.join(root, f)
        if not os.path.exists(fp):
            continue
        for g in _porcelain_files(fp, root):
            if os.path.realpath(g) in excl:
                continue
            m = int(os.path.getmtime(g))
            if m > newest:
                newest, newest_file = m, os.path.relpath(g, root)"""
V2_LOOP = """    for f in dirty:
        fp = os.path.join(root, f)
        if not os.path.exists(fp) or os.path.realpath(fp) in excl:
            continue
        m = int(os.path.getmtime(fp))
        if m > newest:
            newest, newest_file = m, f"""
MD_FILTER = "            if fn.endswith('.md') or re.match(r'provenance.*\\.json$', fn):\n                continue\n"

rc = 0


def run(label, text, want_pass, is_mutation=True):
    global rc
    # The no-op guard applies to MUTATIONS only. v1 applied it to the control
    # too, where "text == src" is the entire point, so the falsifier died on its
    # own baseline before running anything -- a guard correct at three call sites
    # and wrong at the fourth.
    assert not is_mutation or text != src, \
        f'{label}: mutation was a NO-OP -- nothing was changed'
    d = tempfile.mkdtemp()
    try:
        for f in os.listdir(os.path.dirname(SRC)):
            p = os.path.join(os.path.dirname(SRC), f)
            if os.path.isfile(p):
                shutil.copy(p, d)
        open(os.path.join(d, 'provenance.py'), 'w').write(text)
        r = subprocess.run([sys.executable, 'provenance.py'], cwd=d,
                           capture_output=True, text=True, timeout=300)
        passed = r.returncode == 0
        ok = passed == want_pass
        tail = (r.stderr or r.stdout).strip().splitlines()
        note = tail[-1][:110] if tail else ''
        print(f"  {label:8s} {'PASS' if ok else 'FAIL'}  demo {'passed' if passed else 'failed'}"
              f" (wanted {'pass' if want_pass else 'fail'}) {note}")
        if not ok:
            rc = 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


print('=== H98 falsifiers (isolated copies; spikes/harness/provenance.py untouched) ===')
run('CONTROL', src, True, is_mutation=False)
assert V3_LOOP in src, 'v3 loop not found -- falsifier is anchored on absent text'
run('F1', src.replace(V3_LOOP, V2_LOOP), False)
assert MD_FILTER in src, 'md filter not found -- falsifier is anchored on absent text'
run('F2', src.replace(MD_FILTER, ''), False)
print(f"h98_falsify={'PASS' if rc == 0 else 'FAIL'}")
sys.exit(rc)
