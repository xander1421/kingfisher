#!/usr/bin/env python3
"""S83 — can `verifier2.py`'s 17 cases DETECT a broken verifier?

`out/LEDGER.md`, grade **E**, "highest-risk artefact here":

    | `verifier2.py` untested by anyone but its author | 17 self-authored cases
    | -- *exactly v1's evidentiary profile*, and v1's 13/13 contained a test
    | that never called the verifier.

Two attacks, in the order the LEDGER's own warning implies:

  A. DEAD TESTS. v1's suite contained a case that never called the verifier.
     §12.2 says fix the class, not the site, so the first question is whether
     v2 carries the same shape. Counted mechanically: every `compare` and
     `check_envelope` call is tallied per case, and a case that reaches neither
     is asserting something about nothing.

  B. MUTATION COVERAGE. "17/17 pass" is a statement about the verifier, not
     about the suite. Each mutant below removes ONE real guard -- each is a
     defect v1 actually had, or a rule the code goes out of its way to state --
     and the suite must go red. A mutant that SURVIVES is a hole: that defect
     could be reintroduced tomorrow and every case would still print `ok`.
     Precedent in this repo: "the corpus cannot detect a broken `<`: 0 of 64
     programs notice", which is graded A.

ISOLATION: every mutant is applied to a COPY. The original is never written.
Mutations go through `edits.anchored_replace`, so a mutation whose anchor has
drifted RAISES instead of silently testing nothing -- otherwise a stale anchor
reports the mutant as killed when it was never applied.

usage: python3 spikes/S83_verifier2_attack/attack.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'spikes', 'harness'))
from edits import anchored_replace, AnchorMissing            # noqa: E402

SRC = os.path.join(REPO, 'spikes/S49_schema_v1/verifier2.py')

# (id, what guard is removed, anchor, replacement)
# Every one is a defect v1 HAD, or a rule this file's own comments insist on.
MUTANTS = [
    ('M1', 'self-quorum: one device agreeing with itself is independent again '
           '(v1 HIGH 5)',
     'if a.device_did == b.device_did:', 'if False:'),
    ('M2', 'cross-job replay is comparable again (v1 HIGH 5)',
     'if a.job_id != b.job_id:', 'if False:'),
    ('M3', 'contracts may differ and still be compared (v1 HIGH 4)',
     'if a.contract != b.contract:\n        raise Abstain("contracts differ',
     'if False:\n        raise Abstain("contracts differ'),
    ('M4', 'the sealed value need not BE the verdict value -- v1\'s CENTRAL '
           'defect, which this file names as its central fix',
     'if env.result_hash != want:', 'if False:'),
    ('M5', 'the S31 cutoff bound is gone: cutoff may land on the clipping '
           'boundary, where recall went silently to 0/8',
     'if cut > max_code(env.contract.output_bits):', 'if False:'),
    ('M6', 'a (timing ...) record may travel in the payload',
     'if TIMING_RE.search(env.payload):', 'if False:'),
    ('M7', 'the envelope\'s contract need not match the job\'s pinned contract',
     'if env.contract != job.contract:', 'if False:'),
    ('M8', 'an unregistered commitment is accepted (no commit-before-close)',
     'if c is None:', 'if False:'),
    ('M9', 'the commitment need not recompute',
     'if c != env.commitment():', 'if False:'),
    ('M10', 'SORTED_SET degrades to SORTED_BAG: a set and a bag now differ',
     'return "\\n".join(sorted(set(lines)))', 'return "\\n".join(sorted(lines))'),
    ('M11', 'inexact units may vote',
     'if env.unit not in EXACT_UNITS:', 'if False:'),
    ('M12', 'fuel disagreement no longer makes a DISAGREE',
     'if a.fuel_used != b.fuel_used:', 'if False:'),
    ('M13', 'the nonce length floor is gone (16 bytes -> 0)',
     'if len(env.nonce) < 16:', 'if False:'),
    ('M14', 'fuel_used range check is gone',
     'if not 0 <= env.fuel_used < (1 << 64):', 'if False:'),
    ('M15', 'cutoff rounding changes from round-half-up to round-down -- the '
            'rule this function\'s docstring exists to state',
     'return (2 * job.nnz * den * 2 + num) // (2 * num)',
     'return (2 * job.nnz * den * 2) // (2 * num)'),
    ('M16', 'output_bits is unvalidated (8/16/32 no longer enforced)',
     'if env.contract.output_bits not in (8, 16, 32):', 'if False:'),
]

# Wrapper appended to the copy: counts verifier entries so a case that never
# reaches the verifier is visible. Rebinding the module-level name works because
# Python resolves globals at CALL time, and main() looks `compare` up then.
SHIM = '''

# ---- S83 instrumentation (appended to a COPY; the original is untouched)
_S83 = {'n': 0}
_s83_compare, _s83_check = compare, check_envelope


def compare(job, a, b, registry):                     # noqa: F811
    _S83['n'] += 1
    return _s83_compare(job, a, b, registry)


def check_envelope(env, job, registry):               # noqa: F811
    _S83['n'] += 1
    return _s83_check(env, job, registry)
'''

# `run` is nested inside main(), so the counter delta is taken there.
RUN_OLD = """    def run(name, fn, expect):
        try:
            got = fn()[0]"""
RUN_NEW = """    def run(name, fn, expect):
        _b = _S83['n']
        try:
            got = fn()[0]"""
TALLY_OLD = """        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<56} -> {got}")"""
TALLY_NEW = """        ok = got == expect
        if _S83['n'] == _b:
            print(f"  DEADTEST {name}")
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<56} -> {got}")"""


def build(dst, mutation=None):
    """Write an instrumented (and optionally mutated) copy of the verifier."""
    s = open(SRC).read()
    if mutation:
        s = anchored_replace(s, mutation[0], mutation[1])   # raises if drifted
    s = anchored_replace(s, RUN_OLD, RUN_NEW)
    s = anchored_replace(s, TALLY_OLD, TALLY_NEW)
    s = anchored_replace(s, '\nif __name__ == "__main__":',
                         SHIM + '\nif __name__ == "__main__":')
    open(dst, 'w').write(s)


def run_copy(path):
    """-> (n_fail, n_dead, n_cases, output)."""
    p = subprocess.run([sys.executable, os.path.basename(path)],
                       cwd=os.path.dirname(path), capture_output=True, text=True)
    out = p.stdout + p.stderr
    return (len(re.findall(r'^  FAIL ', out, re.M)),
            len(re.findall(r'^  DEADTEST ', out, re.M)),
            len(re.findall(r'^  (?:ok  |FAIL) ', out, re.M)),
            out)


def main():
    tmp = tempfile.mkdtemp(prefix='s83_')
    problems = []
    try:
        # --- CONTROL. Unmutated and instrumented: the suite must be all-green,
        # or every "the mutant was killed" below is really "the copy is rubble".
        base = os.path.join(tmp, 'verifier2.py')
        build(base)
        nf, nd, nc, out = run_copy(base)
        print(f'CONTROL  unmutated: {nc} cases, {nf} fail, {nd} dead')
        if nf:
            problems.append(f'control has {nf} failing case(s)')
            print(out)

        # --- ATTACK A · dead tests
        print()
        if nd:
            print(f'A · DEAD TESTS: {nd} case(s) never reached the verifier')
            for ln in out.splitlines():
                if ln.startswith('  DEADTEST'):
                    print('   ', ln.strip())
        else:
            print(f'A · DEAD TESTS: none — all {nc} cases reach '
                  f'compare()/check_envelope(). v1\'s defect is not present.')

        # --- ATTACK B · mutation coverage
        print(f'\nB · MUTATION COVERAGE ({len(MUTANTS)} mutants, each removing '
              f'one real guard)')
        survived = []
        for mid, why, old, new in MUTANTS:
            d = os.path.join(tmp, f'{mid}.py')
            try:
                build(d, (old, new))
            except AnchorMissing as e:
                problems.append(f'{mid}: anchor drifted, MUTANT NEVER APPLIED ({e})')
                print(f'  {mid:<4} ANCHOR MISSING — not tested')
                continue
            mf, md, mc, _ = run_copy(d)
            if mf:
                print(f'  {mid:<4} killed by {mf}/{mc} case(s)')
            else:
                survived.append((mid, why))
                print(f'  {mid:<4} SURVIVED — 0/{mc} cases notice')
                print(f'       {why}')

        print()
        killed = len(MUTANTS) - len(survived) - sum(
            1 for p in problems if 'anchor drifted' in p)
        print(f'MUTATION SCORE: {killed}/{len(MUTANTS)} killed, '
              f'{len(survived)} SURVIVED')
        if survived:
            print('\nSURVIVORS — each is a guard the 17 cases cannot see removed:')
            for mid, why in survived:
                print(f'  {mid}  {why}')
        for p in problems:
            print(f'  PROBLEM: {p}')
        return 1 if (survived or problems) else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
