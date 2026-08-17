#!/usr/bin/env python3
"""Are the nondeterminism patches LIVE in every quorum member's binary?

`elders/hyperon-experimental` carries six patches (proposed/hyperon-nondeterminism).
They were verified once, on one host build. The quorum dispatches to FOUR
binaries, and `fuelrun.host.min` is compiled with a DIFFERENT feature set
(`--no-default-features --features pkg_mgmt`).

M1.9 established that a patch applied to a `#[cfg]`-excluded line is a silent
no-op with a clean build. So "the patch is in the tree" does not imply "the
patch is in this binary". If a fix is absent from one member, that member is
nondeterministic while the others are not, and 64/64 agreement is luck.

Each probe runs N times per binary and counts DISTINCT results. Patched => 1.

    python3 probe.py                 # all host binaries
    python3 probe.py --runs 40
"""
import argparse
import collections
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BIN = os.path.join(ROOT, 'spikes', 'S30_speed_duel', 'bin', 'known')

# Straight from the upstream report. Each names the defect it detects and the
# pre-patch signature, so a failure is self-explaining.
PROBES = {
    # Issue 1: atom_to_trie_key maps every variable to one Wildcard, so index
    # construction evicts unrelated buckets. Pre-patch: 9x card=5, 4x card=3,
    # 2x a DIFFERENT card=3, over 15 runs. Needs TWO variables to show.
    'intersection': '!(intersection-atom (A $x B $y C) ($y C A $x B))',
    # Issue 1, same code path. The bug needs TWO variables on BOTH sides and
    # an order that makes the wildcard collapse evict a live bucket; the first
    # version here, `(subtraction-atom (A $x B $y C) ($y C))`, was stable on an
    # UNPATCHED build -- an inert probe reporting distinct=1, which reads
    # exactly like a passing patch.
    'subtraction': '!(subtraction-atom (A $x B $y C) ($y C A $x))',
    # Issue 2: Display printed {self:p}. Pre-patch: a different heap address
    # every run, e.g. GroundingSpace-0xbf0df03d8.
    'new_space': '!(new-space)',
    # Issue 2, the other two sites: grounded atoms are printed inside error
    # atoms, so a program that never prints a handle still emits one on error.
    # The `import!` is REQUIRED: builtin mods are load_module_direct'd but not
    # imported automatically, so without it the expression stays unreduced and
    # the probe never reaches the Display code -- inert, distinct=1, and it
    # scored the unpatched build as passing.
    'random_err': '!(import! &self random)\n!(random-int (new-random-generator 0) 5 0)',
}


def run(binary, src, fuel='200000'):
    p = os.path.join(HERE, '_probe.metta')
    with open(p, 'w') as f:
        f.write(src + '\n')
    try:
        r = subprocess.run([binary, p, fuel], capture_output=True, text=True, timeout=60)
    finally:
        os.remove(p)
    out, keep = [], False
    for ln in r.stdout.splitlines():
        if ln.startswith('---'):
            keep = True
        elif keep:
            out.append(ln)
    return '\n'.join(out).strip()


DEV = '/data/local/tmp/kf_patchlive'


def run_adb(binary_dev, src, fuel='200000'):
    """Same probe, executed ON the device. The phone is the one quorum member
    on a different ISA and OS, so it is the member a host-only check cannot
    speak for."""
    p = os.path.join(HERE, '_probe.metta')
    with open(p, 'w') as f:
        f.write(src + '\n')
    try:
        subprocess.run(['adb', 'push', '-q', p, f'{DEV}/p.metta'],
                       capture_output=True, text=True)
    finally:
        os.remove(p)
    r = subprocess.run(['adb', 'shell', f'{binary_dev} {DEV}/p.metta {fuel}'],
                       capture_output=True, text=True, timeout=120)
    out, keep = [], False
    for ln in r.stdout.splitlines():
        if ln.startswith('---'):
            keep = True
        elif keep:
            out.append(ln)
    return '\n'.join(out).strip()


def sweep_adb(binary_dev, runs):
    res = {}
    for name, src in PROBES.items():
        seen = collections.Counter(run_adb(binary_dev, src) for _ in range(runs))
        res[name] = {'distinct': len(seen),
                     'samples': [s[:90] for s in list(seen)[:3]],
                     'counts': sorted(seen.values(), reverse=True)}
    return res


def phone(runs):
    """§10: device work only while charging and idle. The gate REFUSES."""
    sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
    from instrument import check_not_frozen
    bat = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'],
                         capture_output=True, text=True).stdout
    ok, why = check_not_frozen(bat)
    if not ok:
        sys.exit(f'REFUSING: battery instrument is {why} -- a frozen override '
                 f'reports whatever it was told to, which is how a discharging '
                 f'phone once read as charging all session.')
    if 'powered: true' not in bat:
        sys.exit('REFUSING: device is not on external power (MISSION_LOOP §10)')
    local = os.path.join(BIN, 'fuelrun.android')
    subprocess.run(['adb', 'shell', f'mkdir -p {DEV}'], capture_output=True)
    subprocess.run(['adb', 'push', '-q', local, f'{DEV}/fuelrun'], capture_output=True)
    subprocess.run(['adb', 'shell', f'chmod 755 {DEV}/fuelrun'], capture_output=True)
    r = sweep_adb(f'{DEV}/fuelrun', runs)
    r['_sha256'] = hashlib.sha256(open(local, 'rb').read()).hexdigest()[:12]
    return r


def sweep(binary, runs):
    res = {}
    for name, src in PROBES.items():
        seen = collections.Counter(run(binary, src) for _ in range(runs))
        res[name] = {'distinct': len(seen),
                     'samples': [s[:90] for s in list(seen)[:3]],
                     'counts': sorted(seen.values(), reverse=True)}
    return res


# The three patched files each probe actually depends on. HEAD is pristine
# upstream 3f76dc4, so `git checkout` gives the UNPATCHED text.
PATCHED_FILES = [
    'lib/src/space/grounding/mod.rs',        # new_space Display
    'lib/src/metta/runner/builtin_mods/random.rs',   # random_err Display
    'lib/src/metta/runner/stdlib/atom.rs',   # intersection / subtraction
]
ELDERS = os.path.join(ROOT, 'elders', 'hyperon-experimental')
CRATE = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun')


def _build():
    r = subprocess.run(['cargo', 'build', '--release'], cwd=CRATE,
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('BUILD FAILED\n' + r.stderr[-1500:])


def control(runs):
    """NEGATIVE CONTROL. distinct=1 is also what an INERT probe returns -- a
    typo'd builtin, a silently empty capture, a probe measuring nothing. So
    revert the three patches, rebuild, and require every probe to CHANGE.

    Restore is from a byte backup, never `git checkout`: the elders tree is a
    vendored clone carrying six real patches and git would take the other three
    with it. mtime is forced forward after restore, because copy2 preserves it
    and cargo then skips the rebuild -- that is how M1.9 nearly shipped a
    mutated binary.
    """
    import shutil
    bak = {}
    try:
        for rel in PATCHED_FILES:
            p = os.path.join(ELDERS, rel)
            bak[p] = p + '.kf-backup'
            shutil.copy2(p, bak[p])
            subprocess.run(['git', 'checkout', '--', rel], cwd=ELDERS, check=True)
        _build()
        return sweep(os.path.join(CRATE, 'target', 'release', 'fuelrun'), runs)
    finally:
        for p, b in bak.items():
            shutil.move(b, p)
            os.utime(p, None)
        _build()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=30)
    ap.add_argument('--out', default=os.path.join(HERE, 'patchlive.json'))
    ap.add_argument('--no-phone', action='store_true')
    ap.add_argument('--control', action='store_true',
                    help='revert the patches, rebuild, and show the probes fire')
    a = ap.parse_args()

    if a.control:
        r = control(a.runs)
        print(f'UNPATCHED build, {a.runs} runs each:')
        fired = 0
        for name in PROBES:
            d = r[name]['distinct']
            print(f'  {name:14s} distinct={d}  {r[name]["samples"][0][:70]}')
        json.dump(r, open(os.path.join(HERE, 'control_unpatched.json'), 'w'), indent=1)
        return r

    targets = [('host-a', 'fuelrun.host'),
               ('host-min', 'fuelrun.host.min'),
               ('host-x86', 'fuelrun.host.x86_64')]
    report, bad = {}, []
    for worker, fn in targets:
        path = os.path.join(BIN, fn)
        if not os.path.exists(path):
            print(f'{worker}: MISSING {path}')
            continue
        r = sweep(path, a.runs)
        r['_sha256'] = hashlib.sha256(open(path, 'rb').read()).hexdigest()[:12]
        report[worker] = r
        print(f'\n{worker}  ({r["_sha256"]}, {a.runs} runs each)')
        for name in PROBES:
            d = r[name]['distinct']
            flag = 'OK ' if d == 1 else '!! '
            print(f'  {flag}{name:14s} distinct={d}  {r[name]["samples"][0][:70]}')
            if d != 1:
                bad.append((worker, name, d))
    if not a.no_phone:
        r = phone(a.runs)
        report['phone'] = r
        print(f'\nphone  ({r["_sha256"]}, {a.runs} runs each, on-device)')
        for name in PROBES:
            d = r[name]['distinct']
            print(f'  {"OK " if d == 1 else "!! "}{name:14s} distinct={d}  '
                  f'{r[name]["samples"][0][:60]}')
            if d != 1:
                bad.append(('phone', name, d))

    json.dump(report, open(a.out, 'w'), indent=1)
    print(f'\nnondeterministic (worker, probe, distinct): {bad or "none"}')
    return bad


def demo():
    """The parser is the claim: a probe that silently returned '' for every run
    would report distinct=1 and read as PATCHED."""
    assert run(os.path.join(BIN, 'fuelrun.host'), '!(+ 1 2)') != '', \
        'empty capture would score distinct=1 and look like a passing patch'
    print('probe: parser returns non-empty output')


if __name__ == '__main__':
    demo()
    main()
