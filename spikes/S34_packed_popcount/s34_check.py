#!/usr/bin/env python3
"""Packed popcount is bit-exact vs scalar and SDOT, on BOTH machines.

The claim spans two ISAs, so a reproducer that runs only the host build proves
half of it. This runs `kernels_host` here and `kernels` on the phone and
requires every kernel on every machine to agree on one FNV hash.

Control: the hash must DISCRIMINATE. The same binary also reports a hash over a
different buffer (`K2 fnv ... (40000000 bytes)`), and that one must differ. If
every hash in the output were equal, "identical" would be a property of the
instrument rather than of the kernels, and this would pass no matter how wrong
the popcount was.

    python3 s34_check.py            # host + device
    python3 s34_check.py --host     # host only
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DEV = '/data/local/tmp/kf_kernels'
KERNEL = re.compile(r'^\s*(K\d)\s+(\S+)\s+fnv\s+([0-9a-f]{16})', re.M)
OTHER = re.compile(r'fnv ([0-9a-f]{16})\s+\(\d+ bytes\)')


def host():
    b = os.path.join(HERE, 'kernels_host')
    if not os.path.exists(b):
        sys.exit(f'missing {b} -- build it from kernels.c')
    return subprocess.run([b], cwd=HERE, capture_output=True, text=True,
                          timeout=300).stdout


def device():
    """§10: the phone is only used while on external power, and the battery
    instrument is checked for a frozen override BEFORE it is read."""
    sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
    from instrument import check_not_frozen
    bat = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'],
                         capture_output=True, text=True).stdout
    if not bat.strip():
        return None
    ok, why = check_not_frozen(bat)
    if not ok:
        sys.exit(f'REFUSING: battery instrument is {why}')
    if 'powered: true' not in bat:
        sys.exit('REFUSING: device is not on external power (MISSION_LOOP §10)')
    subprocess.run(['adb', 'push', '-q', os.path.join(HERE, 'kernels'), DEV],
                   capture_output=True)
    subprocess.run(['adb', 'shell', f'chmod 755 {DEV}'], capture_output=True)
    return subprocess.run(['adb', 'shell', DEV], capture_output=True,
                          text=True, timeout=600).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', action='store_true', help='skip the device half')
    a = ap.parse_args()

    outs = {'host': host()}
    if not a.host:
        d = device()
        if d is None:
            print('no device attached -- host half only, claim NOT fully checked')
        else:
            outs['device'] = d

    hashes, discriminator = {}, set()
    for machine, text in outs.items():
        for k, name, h in KERNEL.findall(text):
            hashes[(machine, k, name)] = h
        discriminator |= set(OTHER.findall(text))
        print(f'{machine}:')
        for (m, k, name), h in hashes.items():
            if m == machine:
                print(f'  {k} {name:10s} {h}')

    vals = set(hashes.values())
    problems = []
    if not hashes:
        problems.append('parsed no kernel hashes -- the output format moved')
    if len(vals) != 1:
        problems.append(f'kernels DISAGREE: {sorted(vals)}')
    if not discriminator - vals:
        problems.append('CONTROL DEAD: every hash in the output is the same value, '
                        'so "identical" says nothing about the kernels')
    if len(outs) < 2:
        problems.append('device half not run -- "both machines" is unverified')

    print(f'\nkernel hashes: {len(vals)} distinct across {len(outs)} machine(s)')
    print(f'control (different buffer): {sorted(discriminator - vals) or "NONE"}')
    for p in problems:
        print('  !! ' + p)
    print('\nbit-exact across scalar/SDOT/popcount and machines: '
          + ('YES' if not problems else 'NOT ESTABLISHED'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
