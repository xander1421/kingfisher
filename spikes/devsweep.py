#!/usr/bin/env python3
"""Re-run the ANDROID-only reproducers. `sweep.py` cannot reach these.

Six spike binaries are aarch64 and give `Exec format error` on the host, so a
host-only sweep reports "none broken" while never executing them. Those claims
have been unverifiable by any command in the repo.

Two things bite here that never bite on the host:

1. **CWD.** `adb shell <binary>` runs with CWD `/`, which is not writable and
   contains no data files. `prefilter` defaults to writing `shortlist.mm2` into
   it and dies `FORTIFY: fwrite: null FILE*`; `realkg` opens `triples.bin` and
   dies `triples.bin missing`. Neither is broken -- both work from a writable
   directory with their inputs beside them.
2. **Thermal.** These are benchmarks. One `mc` run took the phone from 37 C to
   50.5 C and blocked the next two. The device suite cannot be re-run
   back-to-back, and that is a property of the claims, not of this script.

    python3 devsweep.py            # everything under the gate
    python3 devsweep.py --only mc

Honest limit: this asserts each reproducer RUNS and EMITS its quantity. It does
not re-derive the LEDGER's exact number -- that needs a per-claim comparison and
is not what this file claims to do.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = '/data/local/tmp/kf_devsweep'
THERM_LIMIT = 45000        # millidegrees; q3's device gate refuses around here
COOL_TARGET = 42000

# (name, spike, binary, data files to push, args, must-match, timeout)
JOBS = [
    ('threadcost', 'S45_stacked_device', 'threadcost', [], [],
     r'threads\s+spawn\+join_us', 120),
    ('streamroof', 'S45_stacked_device', 'streamroof', [], [],
     r'GB/s', 120),
    ('prefilter', 'S45_stacked_device', 'prefilter', [], ['8', 'shortlist.mm2'],
     r'ms|GOP/s', 180),
    ('realkg', 'S52_realkg', 'realkg', ['triples.bin'], [],
     r'\d', 300),
    ('nnapi', 'S31_nnapi_probe', 'probe', [], [],
     r'NNAPI devices', 180),
    ('mc', 'S51_multicore', 'mc', [], [], r'\d', 600),
    ('mcx0', 'S51_multicore', 'mcx0', [], [], r'\d', 600),
    ('mcx1', 'S51_multicore', 'mcx1', [], [], r'\d', 600),
]


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def thermal():
    out = sh(['adb', 'shell', 'cat', '/sys/class/thermal/thermal_zone0/temp']).stdout.strip()
    return int(out) if out.isdigit() else -1


def gate():
    """§10. REFUSES rather than warns, and checks the instrument before reading it."""
    sys.path.insert(0, os.path.join(HERE, 'harness'))
    from instrument import check_not_frozen
    if 'device' not in sh(['adb', 'devices']).stdout:
        sys.exit('REFUSING: no device attached')
    bat = sh(['adb', 'shell', 'dumpsys', 'battery']).stdout
    ok, why = check_not_frozen(bat)
    if not ok:
        sys.exit(f'REFUSING: battery instrument is {why} -- a frozen override reports '
                 f'whatever it was told to, which once read a discharging phone as charging')
    if 'powered: true' not in bat:
        sys.exit('REFUSING: device is not on external power (MISSION_LOOP §10)')
    return True


def cool(limit, timeout=240):
    """Wait for the device to come back under the gate. Reports rather than
    silently proceeding hot -- a benchmark on a throttling core is a different
    measurement, not a slower one."""
    t0 = time.time()
    while thermal() > limit and time.time() - t0 < timeout:
        time.sleep(10)
    return thermal()


def run_job(job):
    """Returns (status, t_before, t_after, detail).

    BOTH temperatures, because only one of them means anything about the gate.
    The first version reported the post-run value, so `mc` printed 52500m and
    read as though it had been allowed to start above the 45000m limit -- when
    in fact it was gated at 42000m and heated itself to 52500m while running.
    The gate is a PRE-CHECK, not a supervisor: nothing stops a benchmark once
    it is under way, and these benchmarks raise the die 10-15 C on their own.
    """
    name, spike, binary, data, args, must, timeout = job
    t = thermal()
    if t > THERM_LIMIT:
        t = cool(COOL_TARGET)
        if t > THERM_LIMIT:
            return 'DECLINED', t, t, f'still {t}m after cooling'
    src = os.path.join(HERE, spike, binary)
    if not os.path.exists(src):
        return 'MISSING', t, t, src
    sh(['adb', 'shell', f'mkdir -p {DEV}'])
    sh(['adb', 'push', '-q', src, f'{DEV}/{binary}'])
    sh(['adb', 'shell', f'chmod 755 {DEV}/{binary}'])
    for d in data:
        p = os.path.join(HERE, spike, d)
        if not os.path.exists(p):
            return 'PRECONDITION', t, t, f'input {d} not in {spike}'
        sh(['adb', 'push', '-q', p, f'{DEV}/{d}'])
    # cd into a WRITABLE directory that holds the inputs. Without this the
    # binaries fail on CWD, not on their own logic.
    cmd = f'cd {DEV} && ./{binary} ' + ' '.join(args)
    try:
        r = sh(['adb', 'shell', cmd], timeout=timeout)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', t, thermal(), f'>{timeout}s'
    out = (r.stdout or '') + (r.stderr or '')
    if not re.search(must, out):
        head = ' | '.join(l for l in out.splitlines() if l.strip())[:120]
        return 'FAIL', t, thermal(), head or '(no output)'
    return 'PASS', t, thermal(), out.strip().splitlines()[0][:70]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='run one job by name')
    a = ap.parse_args()
    gate()
    jobs = [j for j in JOBS if not a.only or j[0] == a.only]
    rows, bad = [], []
    print(f'start thermal {thermal()}m, limit {THERM_LIMIT}m '
          f'(shown as before->after; the gate only reads BEFORE)\n', flush=True)
    for j in jobs:
        status, t0, t1, detail = run_job(j)
        rows.append((j[0], status, t0, t1, detail))
        print(f'{status:11s} {t0:6d}->{t1:6d}m {j[0]:11s} {detail}', flush=True)
        if status in ('FAIL', 'MISSING', 'TIMEOUT'):
            bad.append(j[0])
    sh(['adb', 'shell', f'rm -rf {DEV}'])
    if not a.only:
        json.dump([{'name': n, 'status': s, 'therm_before': t0, 'therm_after': t1,
                    'detail': d} for n, s, t0, t1, d in rows],
                  open(os.path.join(HERE, 'devsweep.json'), 'w'), indent=1)
    print(f'\n{len(jobs)} device reproducers, broken: {bad or "none"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
