#!/usr/bin/env python3
"""Mutation testing: what can the corpus actually DETECT?

CORPUS_COMPOSITION.md measured what the 64 programs *are*. This measures what
they can *catch*: inject a known-wrong change into the evaluator, rebuild, and
count how many programs change their agreement key.

The agreement key is `(status, fuel_used, result_hash)` -- exactly what
`q3.key()` compares -- so a program "detects" a mutation iff a quorum running
that program would have disagreed.

Reported per corpus class (empty / import-failure / error-only / evaluated),
because the interesting result is not the total but WHICH class catches WHICH
kind of fault.

    python3 mutate.py --baseline     # record the unmutated keys
    python3 mutate.py                # run every mutation

Safety: each mutation is a byte-exact backup/restore of one file in the
untrusted `elders/` clone. That tree carries the nondeterminism patches, so
`git checkout` would destroy real work; restore is from the backup, never git.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ELDERS = os.path.join(ROOT, 'elders', 'hyperon-experimental')
CRATE = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun')
BIN = os.path.join(CRATE, 'target', 'release', 'fuelrun')
CORPUS = os.path.join(ROOT, 'spikes', 'S57_hyperon_corpus', 'corpus')
FUEL = '2000000'
BASELINE = os.path.join(HERE, 'baseline.json')

ARITH = os.path.join(ELDERS, 'lib/src/metta/runner/stdlib/arithmetics.rs')
STDLIB = os.path.join(ELDERS, 'lib/src/metta/runner/stdlib/stdlib.metta')

# Each mutation is a known-wrong evaluator. A corpus that cannot tell these from
# the real one cannot tell a broken replica from an honest one either.
# `probe` is REQUIRED and is the control. A mutation that scores 0/67 is only
# evidence about the corpus if the mutant binary was genuinely different -- and
# 0/67 is exactly what a failed rebuild, a missed anchor, or a semantically
# inert edit also produces. The probe is a program the mutation MUST change; if
# it does not, the run is void and no detection rate is reported for it.
MUTATIONS = [
    ('sub-is-add', ARITH,
     'def_binary_number_op!(SubOp, -, ATOM_TYPE_NUMBER, Number);',
     'def_binary_number_op!(SubOp, +, ATOM_TYPE_NUMBER, Number);',
     'arithmetic: (- a b) computes a + b',
     '!(- 5 3)'),
    ('less-is-lesseq', ARITH,
     'def_binary_number_op!(LessOp, <, ATOM_TYPE_BOOL, Bool);',
     'def_binary_number_op!(LessOp, <=, ATOM_TYPE_BOOL, Bool);',
     'comparison: (< a a) becomes True -- an off-by-one at every boundary',
     '!(< 1 1)'),
]

EMPTY_H = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

# The quorum never runs these -- bansurface refuses them at admission -- so a
# detection rate that counted them would describe a corpus nobody dispatches.
# test_gnd_conv is the `flip` program and is the ENTIRE measured noise floor:
# across 4 identical unmutated sweeps it produced 3 distinct agreement keys, so
# it "detects" any mutation about a third of the time by being random. A
# nondeterministic program is not a detector, it is a false positive generator.
BANNED = {
    'integration_tests__das__test.metta',      # feature-gated-module
    'mkdocs.metta',                            # filesystem
    'python__sandbox__test_gnd_conv.metta',    # flip -- unseeded randomness
}


def classify(status, text):
    if not text:
        return 'empty'
    if 'Failed to resolve module' in text:
        return 'import-failure'
    if '(Error' in text:
        return 'error-only'
    return 'evaluated'


def run_one(path):
    """Return the agreement key q3 would compare, plus the text for classifying."""
    try:
        p = subprocess.run([BIN, path, FUEL], capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return ('TIMEOUT', '-', '-'), ''
    out = p.stdout
    status = fuel = ''
    lines, res = [], False
    for ln in out.splitlines():
        if ln.startswith('status'):
            status = ln.split(None, 1)[1].strip() if len(ln.split(None, 1)) > 1 else ''
        elif ln.startswith('fuel_used'):
            fuel = ln.split(None, 1)[1].strip() if len(ln.split(None, 1)) > 1 else ''
        elif ln.startswith('---'):
            res = True
        elif res:
            lines.append(ln)
    text = '\n'.join(lines).strip()
    return (status, fuel, hashlib.sha256(text.encode()).hexdigest()), text


def sweep():
    progs = sorted(f for f in os.listdir(CORPUS)
                   if f.endswith('.metta') and f not in BANNED)
    out = {}
    for n in progs:
        k, text = run_one(os.path.join(CORPUS, n))
        out[n] = {'key': list(k), 'class': classify(k[0], text)}
    return out


def _run_out(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).stdout


def probe_result(src):
    """Evaluate a one-line MeTTa program and return its result text."""
    p = os.path.join(HERE, '_probe.metta')
    with open(p, 'w') as f:
        f.write(src + '\n')
    try:
        return run_one(p)[1]
    finally:
        os.remove(p)


def build():
    r = subprocess.run(['cargo', 'build', '--release'], cwd=CRATE,
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('BUILD FAILED\n' + r.stderr[-2000:])


# What an UNMUTATED evaluator must answer. Asserted before the baseline is
# recorded, because a baseline taken from a mutated binary makes that mutation
# score 0/64 -- mutated compared against mutated -- which is indistinguishable
# from the corpus not noticing. This is the control that catches the bug above.
CLEAN_PROBES = [('!(- 5 3)', '0\t2'), ('!(< 1 1)', '0\tFalse')]


def assert_clean_binary():
    for src, want in CLEAN_PROBES:
        got = probe_result(src)
        if got != want:
            sys.exit(f'REFUSING: binary is not unmutated. {src} gave {got!r}, '
                     f'expected {want!r}. A baseline recorded here would be '
                     f'worthless.')
    print('clean-binary probes pass')


def apply(path, old, new):
    sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
    from edits import patch_file          # AnchorMissing if the site moved
    patch_file(path, [(old, new)])


def main():
    if '--baseline' in sys.argv:
        build()
        assert_clean_binary()
        json.dump(sweep(), open(BASELINE, 'w'), indent=1)
        print(f'baseline written: {len(json.load(open(BASELINE)))} programs')
        return

    base = json.load(open(BASELINE))
    classes = sorted({v['class'] for v in base.values()})
    results = {}

    for name, path, old, new, desc, probe in MUTATIONS:
        base_probe = probe_result(probe)
        backup = path + '.kf-backup'
        shutil.copy2(path, backup)
        try:
            apply(path, old, new)
            build()
            mut_probe = probe_result(probe)
            after = sweep()
        finally:
            shutil.move(backup, path)       # byte-exact restore, never git
            # copy2 PRESERVED the original mtime, so restoring moved the source
            # clock BACKWARDS and cargo saw nothing newer than the mutated
            # build -- it skipped the rebuild and left the MUTATED binary on
            # disk. baseline.json was then recorded against it. Family C, in
            # the harness whose entire job is deciding what a binary is.
            os.utime(path, None)
            build()

        if mut_probe == base_probe:
            print(f'\n{name}: VOID -- probe {probe} returned {base_probe!r} both '
                  f'before and after. The mutant is not live, so its 0/67 would '
                  f'have been a fact about this harness, not about the corpus.')
            results[name] = {'desc': desc, 'void': True, 'probe': probe}
            continue
        print(f'\n  probe {probe}: {base_probe!r} -> {mut_probe!r}  (mutant live)')

        caught = {c: [0, 0] for c in classes}   # [detected, total]
        detectors = []
        for n, b in base.items():
            if n in BANNED:
                continue
            c = b['class']
            caught[c][1] += 1
            if after.get(n, {}).get('key') != b['key']:
                caught[c][0] += 1
                detectors.append(n)
        results[name] = {'desc': desc, 'by_class': caught, 'detectors': detectors,
                         'total': sum(v[0] for v in caught.values()),
                         'n': sum(v[1] for v in caught.values())}
        print(f'\n{name}: {desc}')
        for c in classes:
            d, t = caught[c]
            print(f'  {c:15s} {d:3d}/{t:3d} detected')
        print(f'  TOTAL           {results[name]["total"]:3d}/{results[name]["n"]}')
        for d in detectors:
            print(f'      detector: {d}')

    build()   # restore the real binary
    # Record WHICH tree produced these numbers. Without it the artifact is
    # byte-identical across unrelated trees, so a deterministic re-run leaves
    # git with no new blob, the artifact keeps an older last-commit than its
    # own source, and `certify` calls it stale -- the success case of a
    # reproducible pipeline reading as a failure.
    results['_tree'] = {
        'elders_head': _run_out(['git', 'rev-parse', '--short', 'HEAD'], ELDERS),
        'elders_patch_sha256': hashlib.sha256(
            _run_out(['git', 'diff'], ELDERS).encode()).hexdigest()[:16],
    }
    json.dump(results, open(os.path.join(HERE, 'mutation.json'), 'w'), indent=1)
    print('\nrebuilt unmutated; wrote mutation.json')


if __name__ == '__main__':
    main()
