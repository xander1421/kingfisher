#!/usr/bin/env python3
"""H111 — can the autoloop's only VETO gate tell one candidate from another?

Run with the interpreter `config.json` names, which is the only one that can
answer for the deployed gate:

    ./spikes/S5_hdc_prototype/.venv/bin/python spikes/H111_veto_input/probe.py

NOTHING IS PUBLISHED AND NO WORKFLOW IS RUN (§11). The mutation arm operates on
a `git archive HEAD` extraction under this spike directory, never on the shared
working tree: three lanes are editing it right now and mutating a target in
place would land in whoever commits that path next (H79/H66, measured against
this lane three times in one span).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
GATE = os.path.join(ROOT, '.github/autoloop/evaluators/eval_determinism.py')
CFG = json.load(open(os.path.join(ROOT, '.github/autoloop/config.json')))
TARGETS = CFG['mutation_targets']
PY = sys.executable


def run(script, cwd, env=None):
    p = subprocess.run([PY, script], cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    try:
        return json.loads(p.stdout), p.returncode, p.stderr
    except json.JSONDecodeError:
        return None, p.returncode, (p.stdout + p.stderr)


print('H111 — the veto gate, attacked')
print(f'  interpreter: {PY}')
import numpy as np                                            # noqa: E402
print(f'  numpy: {np.__version__}  (bitwise_count present: {hasattr(np, "bitwise_count")})')
print(f'  mutation_targets from config.json: {len(TARGETS)}')
for t in TARGETS:
    print(f'    - {t}  ({"present" if os.path.exists(os.path.join(ROOT, t)) else "ABSENT"})')

# ---------------------------------------------------------------- A1 baseline
base, rc, _ = run(GATE, ROOT)
print(f'\nA1 baseline: {json.dumps(base)}  rc={rc}')
again, _, _ = run(GATE, ROOT)
print(f'   deterministic across two runs: {base == again}')

# ------------------------------------------------------------ A2 the INPUT SET
# The structural half, and it is complete rather than sampled: every file the
# gate opens and every repo module it imports, recorded by an audit hook in the
# gate's own process. A mutation can only move a metric through an input.
probe_src = r'''
import sys, json, os, runpy
ROOT = sys.argv[1]
opened = []
def hook(event, args):
    if event == 'open':
        p = args[0]
        if isinstance(p, str) and os.path.abspath(p).startswith(ROOT):
            opened.append(os.path.relpath(os.path.abspath(p), ROOT))
sys.addaudithook(hook)
sys.argv = [sys.argv[2]]
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit:
    pass
repo_mods = sorted({m for m, v in sys.modules.items()
                    if getattr(v, '__file__', None)
                    and os.path.abspath(v.__file__).startswith(ROOT)
                    and '.venv' not in v.__file__})
print('AUDIT ' + json.dumps({'opened': sorted(set(opened)), 'repo_modules': repo_mods}))
'''
open(os.path.join(HERE, '_audit.py'), 'w').write(probe_src)
p = subprocess.run([PY, os.path.join(HERE, '_audit.py'), ROOT, GATE],
                   cwd=ROOT, capture_output=True, text=True)
audit = json.loads([l for l in p.stdout.split('\n') if l.startswith('AUDIT ')][0][6:])
inside = [f for f in audit['opened'] if not f.startswith('.git/')]
print(f'\nA2 INPUT SET (audit hook, complete rather than sampled):')
print(f'   repo files opened by the gate: {inside or "NONE"}')
print(f'   repo modules imported by the gate: {audit["repo_modules"] or "NONE"}')
print(f'   mutation targets among them: '
      f'{[t for t in TARGETS if t in inside or any(t in m for m in audit["repo_modules"])] or "NONE"}')

# --------------------------------------------------------- A3 the MUTATION ARM
# F1, the falsifier that would kill this row: if any mutation of any target
# moves the metric, the gate discriminates. Sampled, on an isolated extraction.
SBX = os.path.join(HERE, 'sandbox')


def fresh_sandbox():
    """HEAD, extracted -- plus the gate, because the gate is not in HEAD.

    THE FIRST VERSION OF THIS ARM WAS A BROKEN FIXTURE AND IT READ AS A FINDING.
    `git archive HEAD | tar -x` produced a tree with no `.github/autoloop/` in
    it, so every arm ran a file that did not exist: all three mutations and the
    baseline returned `null` at rc=2, the probe printed `MOVED` three times and
    concluded `F1 FIRED -- the gate discriminates`. A uniform result across every
    arm INCLUDING the control is a disconnected wire, not an effect, and the only
    reason it was caught is that the baseline arm was in the table beside them.
    rc=2 is also exactly the gate's own REFUSED_NUMPY_MISSING code, so the
    interpreter's "can't open file" was indistinguishable from the gate's
    considered refusal.

    Why the file is not in HEAD is A3b below, and it is the larger finding.
    """
    subprocess.run(['rm', '-rf', SBX], check=True)
    os.makedirs(SBX)
    subprocess.run(f'git -C {ROOT} archive HEAD | tar -x -C {SBX}', shell=True, check=True)
    subprocess.run(['mkdir', '-p', os.path.join(SBX, '.github')], check=True)
    subprocess.run(['cp', '-R', os.path.join(ROOT, '.github/autoloop'),
                    os.path.join(SBX, '.github/autoloop')], check=True)


tracked = subprocess.run(['git', '-C', ROOT, 'ls-files', '.github/autoloop/'],
                         capture_output=True, text=True).stdout.strip()
ignored = subprocess.run(['git', '-C', ROOT, 'check-ignore', '.github/autoloop/config.json'],
                         capture_output=True, text=True).returncode
print(f'\nA3b THE GATE ITSELF (family C: the artifact is not what you think)')
print(f'   files of .github/autoloop/ tracked by git: {len(tracked.splitlines())}')
print(f'   git-ignored: {ignored == 0}  -> so it is UNCOMMITTED, not deliberately excluded')
print(f'   consequence: the veto protecting the keystone claim exists in ONE working')
print(f'   tree. Any clean checkout, any other lane, any CI runner has no gate at all.')

fresh_sandbox()
sb_gate = os.path.join(SBX, '.github/autoloop/evaluators/eval_determinism.py')
sb_base, sb_rc, _ = run(sb_gate, SBX)
print(f'\nA3 MUTATION ARM (HEAD + the working-tree gate; shared tree untouched)')
print(f'   sandbox baseline equals live baseline: {sb_base == base}  '
      f'(rc={sb_rc}) -- if this is False every arm below is void')

MUTATIONS = [
    ('truncated to empty', lambda p: open(p, 'w').close()),
    ('replaced with a syntax error', lambda p: open(p, 'w').write('def (\n')),
    ('deleted outright', lambda p: os.remove(p)),
]
moved = []
for label, mutate in MUTATIONS:
    fresh_sandbox()
    for t in TARGETS:
        fp = os.path.join(SBX, t)
        if os.path.exists(fp):
            mutate(fp)
    got, grc, _ = run(sb_gate, SBX)
    same = got == sb_base
    print(f'   all {len(TARGETS)} targets {label:<28} -> '
          f'{"IDENTICAL" if same else "MOVED"}  {json.dumps(got)}  rc={grc}')
    if not same:
        moved.append(label)
print(f'   F1 VERDICT: {"FIRED — the gate discriminates" if moved else "did NOT fire — the verdict is invariant over every mutation applied"}')

# --------------------------------------------- A4 NEGATIVE CONTROL (F3, the ask)
# The peer's own words: "it has no negative control. It has never been shown to
# FAIL." A gate never seen red is a green light with no wire behind it.
print('\nA4 NEGATIVE CONTROL — can it go RED at all?')
src = open(GATE).read()
BREAKS = [
    ('the identity itself: D - 2*h  ->  D - h', 'got[k] = D - 2 * h', 'got[k] = D - h'),
    ('one score off by one (a PARTIAL break)',
     'exact = bool(np.array_equal(ref, got))',
     'got[0, 0] += 1\n    exact = bool(np.array_equal(ref, got))'),
    # KEPT, RELABELLED, AND IT IS MY ERROR RATHER THAN THE GATE'S MISS. I planted
    # `T > 0` -> `T >= 0` as a break and it stayed GREEN. On bipolar data T is in
    # {-1,+1}, so `>= 0` and `> 0` select the SAME bits: it is not a break, it is
    # an equivalent transformation, and "the gate missed it" would have been a
    # published false accusation. A no-op intervention producing an unchanged
    # number is the disconnected wire, and here the wire is mine.
    ('NOT A BREAK (equivalent on bipolar data): T > 0 -> T >= 0',
     'Tp, Qp = np.packbits(T > 0, axis=1), np.packbits(Qv > 0, axis=1)',
     'Tp, Qp = np.packbits(T >= 0, axis=1), np.packbits(Qv > 0, axis=1)'),
    # the real third break: select every bit
    ('the packing: T > 0 -> T > -2 (all-ones)',
     'Tp, Qp = np.packbits(T > 0, axis=1), np.packbits(Qv > 0, axis=1)',
     'Tp, Qp = np.packbits(T > -2, axis=1), np.packbits(Qv > 0, axis=1)'),
]
reds = 0
for label, old, new in BREAKS:
    assert src.count(old) == 1, f'anchor not unique: {old}'
    bp = os.path.join(HERE, '_broken.py')
    open(bp, 'w').write(src.replace(old, new))
    got, grc, err = run(bp, ROOT)
    red = bool(got and got.get('determinism_exact') == 0.0 and grc == 1)
    reds += red
    print(f'   {label:<48} -> {"RED" if red else "STILL GREEN"}  '
          f'{json.dumps(got) if got else err.strip().split(chr(10))[-1][:60]}  rc={grc}')
real_breaks = [b for b in BREAKS if not b[0].startswith('NOT A BREAK')]
print(f'   F3 VERDICT: {reds}/{len(real_breaks)} REAL planted breaks turn it red '
      f'(the 4th arm is a no-op and must stay green)')

# ------------------------------------------------- A5 the SECOND DEPENDENCY DOOR
# F4. The ImportError guard covers numpy ABSENT. `np.bitwise_count` was added in
# numpy 2.0, so numpy PRESENT BUT OLDER takes no guarded path at all.
print('\nA5 THE SECOND DEPENDENCY DOOR (numpy present, too old)')
bp = os.path.join(HERE, '_oldnumpy.py')
open(bp, 'w').write(src.replace('import numpy as np',
                                'import numpy as np\n    del np.bitwise_count'))
got, grc, err = run(bp, ROOT)
last = (err.strip().split('\n') or [''])[-1]
print(f'   metric emitted: {got is not None}   rc={grc}')
print(f'   what the caller sees instead: {last[:110]}')
print(f'   F4 VERDICT: {"guarded" if got or grc == 2 else "UNGUARDED — dies with no metric, and rc=1 is the SAME code as IDENTITY_BROKEN"}')

# ------------------------------------------------------- A6 what the digest is for
# F5. Do not kill the wrong thing: `exact` comes from array_equal, so the XOR
# fold is a REPORTING field, not the verdict. Its weakness matters only where a
# reader compares digests.
print('\nA6 THE DIGEST (F5 — measure its ROLE before attacking its strength)')
print(f'   verdict source: {"np.array_equal" if "np.array_equal(ref, got)" in src else "?"}'
      f'   digest used in the verdict: {bool(re.search(r"exact.*digest|digest.*exact", src))}')
a = np.arange(32000, dtype=np.uint32)
b = a.copy(); b[[0, 1]] = b[[1, 0]]                       # a permutation
c = a.copy(); c[0] ^= 0; c[[2, 3]] = c[[3, 2]]
fold = lambda x: int(np.bitwise_xor.reduce(x))
print(f'   permuted scores collide with the original: {fold(a) == fold(b)}')
d = a.copy(); d[5] = d[6]                                  # duplicate a value
e = d.copy(); e[5], e[6] = 0, 0                            # and cancel the pair
print(f'   a duplicated pair and a zeroed pair collide: {fold(d) == fold(e)}')

subprocess.run(['rm', '-rf', SBX], check=True)
for f in ('_audit.py', '_broken.py', '_oldnumpy.py'):
    os.remove(os.path.join(HERE, f))
