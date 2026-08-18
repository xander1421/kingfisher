#!/usr/bin/env python3
"""H117 — ATTACK on the three gates this lane added in three cycles.

Every arm runs against a THROWAWAY repo built under the workspace (§10), with
copies of the modules under test, so nothing here can refuse a live lane's commit.
Falsifiers are stated in the CHANNEL claim before this file existed:

  FA1  a row moving OPEN->DONE in the same commit as the journal recording it.
       `statuscheck.gate()` reads the queue from HEAD, so the journal is judged
       against the row's PREVIOUS status. Expected to REFUSE, i.e. a fleet-stop.
  FA2  `git mv` of a journal: every `## Cycle` key leaves the old path.
  FA3  the wedge test — a refusal the committing lane cannot act on.

  python3 spikes/H117_gate_attack/attack.py
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
HARNESS = os.path.join(ROOT, 'spikes', 'harness')


def sh(*a, cwd, check=True):
    p = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode:
        raise SystemExit(f'{a} failed in {cwd}:\n{p.stdout}\n{p.stderr}')
    return p


# The two v2 fixes, as reverts. `--v1` restores the state the attack was run
# against, so "FA1 fired before the fix" is a command and not a sentence in a
# RESULT.md. A revert that no-ops raises: an arm testing an unmutated module
# would score the fix as the defect.
V1_REVERTS = {
    'statuscheck.py': [(
        "    qs = queue_status(blob(':WORK_QUEUE.md') or blob('HEAD:WORK_QUEUE.md') or",
        "    qs = queue_status(blob('HEAD:WORK_QUEUE.md') or")],
    'recordloss.py': [(
        "    status = git(['diff', '--cached', '--name-status', '-M'], cwd) or ''",
        "    status = '\\n'.join('M\\t' + p for p in "
        "(git(['diff', '--cached', '--name-only'], cwd) or '').split('\\n') if p)")],
}


def build(t, v1=False):
    """A repo shaped like this one: a queue, a journal, and the two modules."""
    os.makedirs(os.path.join(t, 'spikes', 'harness'), exist_ok=True)
    for m in ('recordloss.py', 'statuscheck.py', 'edits.py'):
        src = os.path.join(HARNESS, m)
        dst = os.path.join(t, 'spikes', 'harness', m)
        text = open(src, encoding='utf-8').read()
        if v1:
            for old, new in V1_REVERTS.get(m, ()):
                if old not in text:
                    raise SystemExit(f'--v1 revert anchor missing in {m}: {old[:50]}')
                text = text.replace(old, new)
        open(dst, 'w', encoding='utf-8').write(text)
    sh('git', 'init', '-q', '.', cwd=t)
    sh('git', 'config', 'user.email', 'a@b', cwd=t)
    sh('git', 'config', 'user.name', 'a', cwd=t)
    open(os.path.join(t, 'WORK_QUEUE.md'), 'w').write(
        '## H\n\n| id | what | status | who |\n|---|---|---|---|\n'
        '| H90 | a thing | OPEN | ok-1 |\n')
    open(os.path.join(t, 'HANDOFF.ok-1.md'), 'w').write(
        '# journal\n\n## Cycle 1 — first\n\ntext\n\n## NEXT 3\n1. **H90** is OPEN and mine\n')
    os.makedirs(os.path.join(t, 'prompts'), exist_ok=True)
    open(os.path.join(t, 'prompts', 'ok-1.md'), 'w').write('# brief\n')
    sh('git', 'add', '-A', cwd=t)          # scratch repo, not the workspace
    sh('git', 'commit', '-q', '-m', 'base', cwd=t)


def run_gate(module, t):
    """Run the module's default (gate) mode with the scratch repo as its ROOT."""
    p = subprocess.run([sys.executable, os.path.join(t, 'spikes', 'harness', module)],
                       cwd=t, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def edit(path, old, new):
    """Read, then write, and REFUSE a no-op.

    v1 of this file was `open(p,'w').write(open(p).read().replace(...))`, and
    CPython evaluates `open(p,'w')` FIRST -- so the file is truncated before it
    is read and every fixture below was written as an EMPTY STRING. All three
    arms then came back "quiet" and I was one paragraph from publishing "the
    gates are fine". This repo has recorded the same bug twice (H14's falsify.py
    truncated its file the same way); the defence is not care, it is that a
    silent no-op edit must raise.
    """
    text = open(path, encoding='utf-8').read()
    out = text.replace(old, new)
    if out == text:
        raise SystemExit(f'fixture no-op: {old!r} not in {path}')
    open(path, 'w', encoding='utf-8').write(out)


def arm_fa0(t):
    """POSITIVE CONTROL. A journal that contradicts an UNCHANGED queue must be
    refused. Without this arm, an empty or unreached fixture reads as a pass --
    which is exactly what happened to v1 of this file."""
    edit(os.path.join(t, 'HANDOFF.ok-1.md'),
         '1. **H90** is OPEN and mine', '1. **H90** is DONE, next is H91')
    sh('git', 'add', 'HANDOFF.ok-1.md', cwd=t)
    return run_gate('statuscheck.py', t)


def arm_fa1(t):
    """The commonest commit in this repo: close the row, record it in the journal."""
    edit(os.path.join(t, 'WORK_QUEUE.md'),
         '| H90 | a thing | OPEN | ok-1 |', '| H90 | a thing | DONE (ok-1) | ok-1 |')
    edit(os.path.join(t, 'HANDOFF.ok-1.md'),
         '1. **H90** is OPEN and mine', '1. **H90** is DONE, and the next row is H91')
    sh('git', 'add', 'WORK_QUEUE.md', 'HANDOFF.ok-1.md', cwd=t)
    return run_gate('statuscheck.py', t)


def arm_fa2(t):
    """A journal rename: every `## Cycle` key leaves the old path."""
    sh('git', 'mv', 'HANDOFF.ok-1.md', 'HANDOFF.ok-2.md', cwd=t)
    return run_gate('recordloss.py', t)


def arm_fa2b(t):
    """CONTROL for FA2: a PURE deletion must refuse. If this is quiet too, the
    module is not running in this fixture at all and FA2 says nothing."""
    sh('git', 'rm', '-q', 'HANDOFF.ok-1.md', cwd=t)
    return run_gate('recordloss.py', t)


def arm_fa2c(t):
    """THE ARM THAT DECIDES WHAT FA2's SILENCE MEANS: rename the journal AND drop
    a cycle from it. The record genuinely leaves the repo. Quiet here is not
    "renames are fine", it is BLINDNESS -- `git diff --cached --name-only`
    collapses a rename to the destination path, so the source is never walked."""
    sh('git', 'mv', 'HANDOFF.ok-1.md', 'HANDOFF.ok-2.md', cwd=t)
    j = os.path.join(t, 'HANDOFF.ok-2.md')
    edit(j, '## Cycle 1 — first\n\ntext\n\n', '')
    sh('git', 'add', 'HANDOFF.ok-2.md', cwd=t)
    return run_gate('recordloss.py', t)


V1 = '--v1' in sys.argv


def main():
    print('MODULES: ' + ('v1, the state this attack was RUN against' if V1
                         else 'v2, current — the fixes in place'))
    scratch = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.scratch')
    shutil.rmtree(scratch, ignore_errors=True)
    verdicts = {}
    try:
        t = os.path.join(scratch, 'fa0')
        os.makedirs(t)
        build(t, V1)
        rc, out = arm_fa0(t)
        print(f'FA0  POSITIVE CONTROL, journal contradicts an unchanged queue: rc={rc}')
        print('     ' + (out.replace('\n', '\n     ') or '(quiet)'))
        verdicts['FA0'] = rc
        if rc == 0:
            print('\nREFUSE: the positive control did not fire, so no arm below is '
                  'evidence about anything (A29).')
            return 2

        t = os.path.join(scratch, 'fa1')
        os.makedirs(t)
        build(t, V1)
        rc, out = arm_fa1(t)
        print(f'FA1  statuscheck on a DONE-cycle commit: rc={rc}')
        print('     ' + (out.replace('\n', '\n     ') or '(quiet)'))
        verdicts['FA1'] = rc

        t = os.path.join(scratch, 'fa2')
        os.makedirs(t)
        build(t, V1)
        rc, out = arm_fa2(t)
        print(f'FA2  recordloss on `git mv` of a journal: rc={rc}')
        print('     ' + (out.replace('\n', '\n     ') or '(quiet)'))
        verdicts['FA2'] = rc

        for name, fn, why in (('FA2b', arm_fa2b, 'PURE deletion (control for FA2)'),
                              ('FA2c', arm_fa2c, 'rename AND drop a cycle — the record leaves')):
            t = os.path.join(scratch, name)
            os.makedirs(t)
            build(t, V1)
            rc, out = fn(t)
            print(f'{name}  recordloss, {why}: rc={rc}')
            print('     ' + (out.replace('\n', '\n     ') or '(quiet)'))
            verdicts[name] = rc

        # FA3, the wedge test, is decided from FA1/FA2 rather than run: a refusal
        # is a wedge only if NO action by the committing lane clears it. Both arms
        # above are checked for an escape that is not `--no-verify`.
        t = os.path.join(scratch, 'fa3')
        os.makedirs(t)
        build(t, V1)
        arm_fa1(t)
        j = os.path.join(t, 'HANDOFF.ok-1.md')
        edit(j, '1. **H90** is DONE, and the next row is H91',
             '1. **H91** is next; H90 closed this cycle')
        sh('git', 'add', 'HANDOFF.ok-1.md', cwd=t)
        rc, out = run_gate('statuscheck.py', t)
        print(f'FA3  same commit, verdict phrased without an is-DONE claim: rc={rc}')
        print('     ' + (out.replace('\n', '\n     ') or '(quiet)'))
        verdicts['FA3'] = rc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    print()
    print('FA1 FIRES — the gate refuses the repo\'s commonest commit shape'
          if verdicts.get('FA1') else
          'FA1 quiet — expected under v2; under --v1 it must FIRE or the finding '
          'was never real')
    print('FA2 FIRES — a journal rename is refused' if verdicts.get('FA2') else
          'FA2 quiet — and FA2b/FA2c below say whether that is correctness or blindness')
    print('FA2b FIRES — a pure deletion is refused, so the module RUNS here'
          if verdicts.get('FA2b') else
          'FA2b QUIET — the module is not reaching this fixture; FA2 is not evidence')
    print('FA2c FIRES — a record leaving under a rename is caught'
          if verdicts.get('FA2c') else
          'FA2c QUIET — BLIND: `git diff --cached --name-only` collapses a rename to '
          'the destination, so the source path is never walked and its records leave unseen')
    print('FA3: an escape exists that is not --no-verify' if not verdicts.get('FA3') else
          'FA3: WEDGE — the lane cannot phrase its way out')
    return 0


sys.exit(main())
