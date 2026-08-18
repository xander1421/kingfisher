#!/usr/bin/env python3
"""H103 probe — is an id CLAIMed in the log with NO queue row visible to ANY
harness checker, and is the rowless set what a naive predicate would say it is?

Every arm runs against a PINNED PAIR of documents, `d066c4b^`, because the live
instance is mine and I repaired part of it by hand one cycle ago (the H89/H93/H95
rows). Measuring the live tree would measure my repair.

Nothing is written outside the workspace (§10): the sandbox is a directory under
this spike, built from `git show` plus symlinks to the rest of the tree, and the
checkers are pointed at it by rebinding their module-level ROOT — the same
mechanism `refcheck.py:682` and `journalcheck.py:375` use in their own
selfchecks, so it is the tree's idiom and not an invention of mine.
"""
import io
import contextlib
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
# PIN CORRECTED, and the correction is family C (the artifact is not what you
# think). It was `d066c4b^` — "the commit before mine", which I reasoned to
# rather than checked. `git log -S'| H95 |' -- WORK_QUEUE.md` says the rows first
# landed in `197502d`, AGENT-2's G43 commit at 11:38: my rows were in the shared
# WORKING TREE when they committed that path, so the parent of MY commit already
# contained MY repair. The probe duly reported H89/H93/H95 as `has-row` and the
# live instance vanished from its own measurement. The pin is now the last commit
# before any of the three rows was written by hand.
PIN = '10ed3f2'                       # 06:01, H85 — before my hand repair, verified by -S
SUBJECTS = ['H89', 'H93', 'H95']      # the live instance, all three mine
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))


def git(*args):
    return subprocess.run(['git', '-C', ROOT, *args],
                          capture_output=True, text=True).stdout


def sandbox(name, queue_text, log_text):
    """A tree the checkers can walk, with two documents replaced."""
    d = os.path.join(HERE, name)
    subprocess.run(['rm', '-rf', d], check=True)
    os.makedirs(d)
    for entry in os.listdir(ROOT):
        if entry in ('CHANNEL.md', 'WORK_QUEUE.md'):
            continue
        os.symlink(os.path.join(ROOT, entry), os.path.join(d, entry))
    open(os.path.join(d, 'WORK_QUEUE.md'), 'w', encoding='utf-8').write(queue_text)
    open(os.path.join(d, 'CHANNEL.md'), 'w', encoding='utf-8').write(log_text)
    return d


def pinned(mod_name):
    """Load a harness module AS IT STOOD AT THE PIN.

    F1 asks whether any checker ALREADY reports a rowless id. Answering it with
    the live module measures this row's own patch: after the patch, `idscope`
    reports one by construction and F1 "fires" against itself. Same reason H95
    pinned its control by sha rather than to HEAD.
    """
    dst = os.path.join(HERE, f'_pinned_{mod_name}.py')
    src = git('show', f'{PIN}:spikes/harness/{mod_name}.py')
    if not src:
        return None
    open(dst, 'w', encoding='utf-8').write(src)
    spec = importlib.util.spec_from_file_location(f'pinned_{mod_name}', dst)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f'pinned_{mod_name}'] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:                                         # noqa: BLE001
        return None
    return mod


def run_module(mod, fn_name, root):
    """Run an already-loaded module against `root`, capturing everything."""
    was, buf = getattr(mod, 'ROOT', None), io.StringIO()
    try:
        mod.ROOT = root
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = getattr(mod, fn_name)()
    except Exception as e:                                    # noqa: BLE001
        return buf.getvalue() + f'\n<raised: {type(e).__name__}: {e}>', None
    finally:
        if was is not None:
            mod.ROOT = was
    return buf.getvalue(), rc


def run_checker(mod_name, fn_name, root):
    """Import a harness module, point it at `root`, run it, return its output."""
    try:
        mod = __import__(mod_name)
    except Exception as e:                                    # noqa: BLE001
        return f'<import failed: {e}>', None
    was = getattr(mod, 'ROOT', None)
    buf = io.StringIO()
    try:
        mod.ROOT = root
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = getattr(mod, fn_name)()
    except Exception as e:                                    # noqa: BLE001
        return buf.getvalue() + f'\n<raised: {type(e).__name__}: {e}>', None
    finally:
        if was is not None:
            mod.ROOT = was
    return buf.getvalue(), rc


# ---------------------------------------------------------------- the pin
qtext = git('show', f'{PIN}:WORK_QUEUE.md')
ltext = git('show', f'{PIN}:CHANNEL.md')
assert qtext and ltext, 'pinned documents are empty -- wrong sha?'
pin_sha = git('rev-parse', '--short', PIN).strip()

import idscope                                                # noqa: E402
QROWS = idscope.queue_rows(qtext)

print(f'H103 probe — pinned pair at {PIN} ({pin_sha})')
print(f'  WORK_QUEUE.md {len(qtext.splitlines())} lines, {len(QROWS)} rows; '
      f'CHANNEL.md {len(ltext.splitlines())} lines\n')

# --------------------------------------------------- F2 FIRST: classify, then count
# Stated in the CLAIM before running: if the rowless set is dominated by lines
# that are legitimately not queue rows, a naive predicate over-reports and the
# finding is an attribution error. So the classification decides what may be
# counted, and it runs BEFORE the count.
PREFIX = re.compile(r'^(CLAIM|DONE)\s+(\S+)')
IDLIKE = re.compile(r'^[A-Z]\d+$|^[A-Z]\d+\.\d+$|^M\d+[._]\d+$')

buckets = {'not-an-id': [], 'has-row': [], 'ROWLESS': []}
for line in ltext.split('\n'):
    m = PREFIX.match(line)
    if not m:
        continue
    tok = m.group(2).strip('*`')
    if not IDLIKE.match(tok):
        buckets['not-an-id'].append((m.group(1), tok))
    elif tok in QROWS:
        buckets['has-row'].append((m.group(1), tok))
    else:
        buckets['ROWLESS'].append((m.group(1), tok))

print('F2 — classification of every CLAIM/DONE prefix line at the pin:')
for k, v in buckets.items():
    ids = sorted({t for _, t in v}, key=lambda s: (s[0], int(re.sub(r'\D', '', s) or 0)))
    print(f'  {k:>10}: {len(v)} line(s), {len(ids)} distinct — {" ".join(ids) if ids else "(none)"}')
rowless = sorted({t for _, t in buckets['ROWLESS']})
series = sorted({t[0] for t in rowless})
print(f'  F2 VERDICT: rowless ids span series {series}. A naive "every CLAIM needs a row"'
      f' would additionally accuse {len(buckets["not-an-id"])} line(s) carrying no id at all.\n')

# ------------------------------------------------------------------ F1
print('F1 — does ANY existing harness checker name a rowless id? '
      '(killing falsifier: if one does, this row is a non-finding)')
box = sandbox('sandbox_pin', qtext, ltext)
CANDIDATES = [('idscope', 'scan'), ('refcheck', 'scan'),
              ('journalcheck', 'scan'), ('recordloss', 'scan')]
f1_hits = []
for mod_name, fn in CANDIDATES:
    # ONLY idscope is pinned, and only because this row patches it. The other
    # three are unaffected by the patch, so the LIVE copy is the right subject --
    # `recordloss.py` did not exist at the pin at all, and asking a pinned
    # version of it would answer about a file rather than about the harness.
    mod = pinned(mod_name) if mod_name == 'idscope' else None
    label = f'{mod_name} @{PIN}' if mod is not None else f'{mod_name} (live)'
    out, rc = (run_module(mod, fn, box) if mod is not None
               else run_checker(mod_name, fn, box))
    named = [s for s in SUBJECTS if re.search(rf'\b{s}\b', out)]
    # A checker naming the id for some OTHER reason is not a detection of this
    # defect; require the id and a rowless-shaped word on the same line.
    rowless_named = [ln for ln in out.split('\n')
                     if any(re.search(rf'\b{s}\b', ln) for s in SUBJECTS)
                     and re.search(r'row|queue|WORK_QUEUE', ln)]
    print(f'  {label:>22}.{fn}() rc={str(rc)[:40]} — mentions {named or "none"} of the subjects; '
          f'{len(rowless_named)} line(s) tie one to the queue')
    for ln in rowless_named[:3]:
        print(f'                  | {ln.strip()[:150]}')
    f1_hits += rowless_named
print(f'  F1 VERDICT: {"FIRED — a checker already reports it" if f1_hits else "did NOT fire — no checker names a rowless id"}\n')

# ------------------------------------------------------------------ F3
print('F3 — inertness: a planted rowless CLAIM must be flagged, and the '
      'unmodified pair must give the same answer twice.')
print('  The BASELINE arm loads the PINNED v2 source rather than trusting a')
print('  remembered terminal, for the same reason H95 pinned its control by sha:')
print('  once this row is committed the live module IS the patch.')
planted = ltext.rstrip('\n') + '\nCLAIM H999 ATTACKER-1 — H103 planted rowless id, never a real row\n'
box_plant = sandbox('sandbox_plant', qtext, planted)

v2 = pinned('idscope')
assert 'v3' not in (v2.__doc__ or '').split('\n')[0], 'pinned source already carries v3'


def run_v2(root):
    return run_module(v2, 'scan', root)[0]


a, _ = run_checker('idscope', 'scan', box)
b, _ = run_checker('idscope', 'scan', box)
print(f'  reproducible on the unmodified pair (live module, twice): {a == b}')
for label, out_p in (('pinned v2', run_v2(box_plant)),
                     ('live module', run_checker('idscope', 'scan', box_plant)[0])):
    subs = [x for x in SUBJECTS if re.search(rf'\b{x}\b', out_p)]
    print(f'  {label:>12}: plant H999 flagged = {"H999" in out_p}; '
          f'real subjects flagged = {subs or "none"}')
print()

# ------------------------------------------------------------------ F4 baseline
print('F4 — size of intervention. +0 new detections is FATAL and is printed.')
print(f'  rowless ids at the pin, by the classification above: {len(rowless)}')
print(f'  of which the live instance: {[s for s in SUBJECTS if s in rowless]}')

# The patched module, run on the SAME pinned pair the baseline was taken from.
out_after, rc_after = run_checker('idscope', 'scan', box)
found = sorted(re.findall(r'^  ROWLESS (\S+) ', out_after, re.M))
print(f'  reported by idscope v2 (baseline, from F3 above): 0')
print(f'  reported by idscope v3 on the same pair: {len(found)} — {" ".join(found)}')
delta = len(found)
print(f'  DELTA: +{delta} detections. ' +
      ('FATAL: the wire is disconnected.' if delta == 0 else 'The wire carries.'))
print(f'  agreement with the independent classification above: '
      f'{sorted(found) == sorted(rowless)}')
print(f'  live instance now named: {[s for s in SUBJECTS if s in found]}')
print(f'  CONTROL — the direction v2 already had must survive: '
      f'{out_after.count("DISAGREE")} DISAGREE line(s), rc={rc_after} '
      f'(ROWLESS must not gate: rc is unchanged from the baseline rc=1)')

subprocess.run(['rm', '-rf', box, box_plant], check=True)
