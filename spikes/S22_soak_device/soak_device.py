#!/usr/bin/env python3
"""S22 — M1.3b's soak, on the phone, and cross-compared with the host.

THE GAP, IN M1.3b's OWN WORDS
-----------------------------
    "Two probe shapes, 31 runs each, one process, HOST ONLY. Not run on device."

M1.3b closed the largest open M1 issue: `PORT_PLAN` M1.3 requires a fresh
process per job, WorkManager reuses the app process, and M1.3b showed that with
a fresh `Metta` per job plus `canon` at the comparison boundary, reuse is safe
for ground results. Every number in it came from an x86_64 host. The deployment
target is an aarch64 phone.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If the device's canonicalised digests differ from the host's, or the device
    shows more than ONE distinct canon digest across positions, then process
    reuse is not safe on the deployment target, M1.3b's conclusion does not
    transfer, and WorkManager goes back to blocked.

WHAT THE COMPARISON BINDS, WHICH IS MORE THAN IT LOOKS
------------------------------------------------------
`soakrun` hashes the string `fuel=<N>\\n<results>`. So a canon digest that
matches across ISAs asserts **identical fuel counts as well as identical
results** -- the single asset in this project that has survived every attack.
A device that agreed on results while spending different fuel would NOT match.

THE CONTROL THAT MAKES THE CLAIM MEAN ANYTHING (M1.3b's own)
-------------------------------------------------------------
The RAW digest must DIFFER across positions on the device. Raw carries hyperon's
process-global variable counter, so a reused process is exactly where drift
shows. If raw came back constant, the run would not be exercising process reuse
at all and `canon == 1` would be vacuous -- a clean null from a probe that never
reached its target (A29).

§10 GATE
--------
`devsweep.gate()`, imported rather than reimplemented: it REFUSES -- not warns --
on an absent device, on a battery service that is a frozen override
(`UPDATES STOPPED`, the defect that once read a discharging phone as charging),
and on a device not on external power.

  python3 soak_device.py [--positions 30]
"""
import argparse, collections, json, os, subprocess, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
sys.path.insert(0, os.path.join(ROOT, 'spikes'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402
from instrument import check_not_frozen                                   # noqa: E402
import devsweep                                                           # noqa: E402

FUEL = '200000'
DEV_DIR = '/data/local/tmp/kf_s22'
BIN_HOST = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                        'target', 'release', 'soakrun')
BIN_DEV = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                       'target', 'aarch64-linux-android', 'release', 'soakrun')
SRC = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun', 'src',
                   'bin', 'soakrun.rs')
CORPUS = os.path.join(ROOT, 'spikes', 'S57_hyperon_corpus', 'corpus')
# M1.3b's probe, verbatim. A data-origin variable is the whole point: it is what
# carries the process counter into printed output.
PROBE = '(implies (Frog $x) (Green $x))\n!(match &self (implies $p $q) ($p $q))\n'


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(65536), b''):
            h.update(b)
    return h.hexdigest()


def parse(stdout):
    rows = [l.split('\t') for l in stdout.splitlines()[1:] if l.strip()]
    return [r for r in rows if len(r) == 5]


def run_host(progs, probe_path):
    args = []
    for p in progs:
        args += [probe_path, p]
    args.append(probe_path)
    r = sh([BIN_HOST, FUEL] + args, timeout=900)
    if r.returncode != 0:
        sys.exit('host soakrun failed rc=%d\n%s' % (r.returncode, r.stderr[-600:]))
    return parse(r.stdout)


def run_device(prog_names):
    sh(['adb', 'shell', 'rm', '-rf', DEV_DIR])
    sh(['adb', 'shell', 'mkdir', '-p', DEV_DIR])
    sh(['adb', 'push', BIN_DEV, DEV_DIR + '/soakrun'])
    sh(['adb', 'shell', 'chmod', '755', DEV_DIR + '/soakrun'])
    probe_local = os.path.join(HERE, 'probe.metta')
    sh(['adb', 'push', probe_local, DEV_DIR + '/probe.metta'])
    for n in prog_names:
        sh(['adb', 'push', os.path.join(CORPUS, n), DEV_DIR + '/' + n])
    args = []
    for n in prog_names:
        args += ['probe.metta', n]
    args.append('probe.metta')
    cmd = 'cd %s && ./soakrun %s %s' % (DEV_DIR, FUEL, ' '.join(args))
    r = sh(['adb', 'shell', cmd], timeout=1800)
    if r.returncode != 0:
        sys.exit('device soakrun failed rc=%d\n%s' % (r.returncode, r.stderr[-600:]))
    return parse(r.stdout), r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--positions', type=int, default=30)
    a = ap.parse_args()

    for p in (BIN_HOST, BIN_DEV, SRC):
        if not os.path.exists(p):
            sys.exit('missing: %s' % p)
    devsweep.gate()                       # §10; refuses, does not warn

    battery = sh(['adb', 'shell', 'dumpsys', 'battery']).stdout
    model = sh(['adb', 'shell', 'getprop', 'ro.product.model']).stdout.strip()
    abi = sh(['adb', 'shell', 'getprop', 'ro.product.cpu.abi']).stdout.strip()
    therm_before = devsweep.thermal()

    names = sorted(f for f in os.listdir(CORPUS) if f.endswith('.metta'))[:a.positions]
    probe_path = os.path.join(HERE, 'probe.metta')
    with open(probe_path, 'w') as f:
        f.write(PROBE)

    host_rows = run_host([os.path.join(CORPUS, n) for n in names], probe_path)
    dev_rows, dev_raw_stdout = run_device(names)
    therm_after = devsweep.thermal()

    def split(rows):
        probe = [r for r in rows if r[1] == 'probe.metta']
        other = {r[1]: r for r in rows if r[1] != 'probe.metta'}
        return probe, other

    hp, ho = split(host_rows)
    dp, do = split(dev_rows)

    out = {
        'device': {'model': model, 'abi': abi,
                   'thermal_before_m': therm_before, 'thermal_after_m': therm_after},
        'positions_requested': a.positions,
        'binaries': {'host_sha256': sha256(BIN_HOST), 'device_sha256': sha256(BIN_DEV),
                     'source_sha256': sha256(SRC),
                     'device_binary_newer_than_source':
                         os.path.getmtime(BIN_DEV) > os.path.getmtime(SRC)},
        'probe_positions': {'host': len(hp), 'device': len(dp)},
        'distinct': {
            'host': {'raw': len({r[2] for r in hp}), 'canon': len({r[3] for r in hp}),
                     'alpha': len({r[4] for r in hp})},
            'device': {'raw': len({r[2] for r in dp}), 'canon': len({r[3] for r in dp}),
                       'alpha': len({r[4] for r in dp})}},
        'probe_canon': {'host': sorted({r[3] for r in hp}),
                        'device': sorted({r[3] for r in dp})},
    }

    # Per-corpus-program cross-ISA comparison. The probe answers "does position
    # in a reused process change the result"; these answer "does the ISA".
    shared = sorted(set(ho) & set(do))
    agree_canon = [n for n in shared if ho[n][3] == do[n][3]]
    agree_raw = [n for n in shared if ho[n][2] == do[n][2]]
    out['corpus_cross_isa'] = {
        'programs_compared': len(shared),
        'canon_identical': len(agree_canon),
        'raw_identical': len(agree_raw),
        'canon_disagreements': [{'program': n, 'host': ho[n][3], 'device': do[n][3]}
                                for n in shared if ho[n][3] != do[n][3]][:20],
    }

    fired = not (out['distinct']['device']['canon'] == 1 and
                 out['probe_canon']['host'] == out['probe_canon']['device'])
    out['falsifier_fired'] = fired

    with open(os.path.join(HERE, 'soak_device.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)
    with open(os.path.join(HERE, 'device_soak.tsv'), 'w') as f:
        f.write(dev_raw_stdout)

    C = []

    # C1 -- GATING, and it compares DIGESTS and not only counts. The first
    # version of this control compared 31/1/1 against M1.3b's published counts,
    # which it reproduces -- and the committed per-row digests do NOT reproduce
    # (see F_committed_rows_reproduce below). A control that checks the SHAPE of
    # a table passes over a change in its CONTENT.
    committed = os.path.join(ROOT, 'spikes', 'M1_3b_process_reuse', 'soak.tsv')
    crows = parse(open(committed).read())
    cprobe = sorted({r[3] for r in crows if r[1] == 'probe.metta'})
    prev = {'raw': 31, 'canon': 1, 'alpha': 1, 'positions': 31}
    now = dict(out['distinct']['host'], positions=len(hp))
    c = Control('C_host_reproduces_M1_3b',
                'the host side of this run must reproduce M1.3b\'s published '
                '31 raw / 1 canon / 1 alpha over 31 probe positions AND its '
                'committed probe canon digest, before any device number is '
                'compared against it',
                null_must_contain='a changed corpus, binary or probe would move '
                                  'the counts or the digest',
                can_fail_because='the host run gives a different number of probe '
                                 'positions, of distinct digests, or a different '
                                 'canon digest than M1.3b committed')
    c.observe(now == prev and cprobe == out['probe_canon']['host'],
              {'published_counts': prev, 'now_counts': now,
               'committed_probe_canon': cprobe,
               'host_probe_canon': out['probe_canon']['host']})
    C.append(c)

    # C2 -- M1.3b's own control, on the device. Without it, canon == 1 is vacuous.
    c = Control('C_raw_drifts_on_device',
                'raw digests MUST differ across positions on the device, or the '
                'run is not exercising process reuse at all and a constant canon '
                'is a clean null from a probe that never reached its target (A29)',
                null_must_contain='a device where the process-global variable '
                                  'counter did not advance would give raw == 1',
                can_fail_because='device raw distinct count is 1, i.e. no drift '
                                 'to canonicalise away')
    c.observe(out['distinct']['device']['raw'] > 1,
              {'device_raw_distinct': out['distinct']['device']['raw'],
               'device_positions': len(dp),
               'host_raw_distinct': out['distinct']['host']['raw']})
    C.append(c)

    # C3 -- the device is the device, and the battery instrument is not frozen.
    inst_ok, inst_why = check_not_frozen(battery, name='dumpsys battery')
    c = Control('C_device_identified',
                'the numbers must be attributable to a named aarch64 device with '
                'a live battery service -- family B: a frozen override reports '
                'whatever it was told to',
                null_must_contain='an emulator, an empty getprop, or a battery '
                                  'service pinned by a test override',
                can_fail_because='model or abi is empty, abi is not arm64, or the '
                                 'battery dump is a frozen override')
    c.observe(bool(model) and abi.startswith('arm64') and inst_ok,
              {'model': model, 'abi': abi, 'battery_instrument_ok': inst_ok,
               'battery_instrument_detail': inst_why,
               'thermal_before_m': therm_before, 'thermal_after_m': therm_after})
    C.append(c)

    # C4 -- A24. Which binary produced this, and is it older than its source?
    c = Control('C_binary_provenance',
                'A24: a digest pins WHICH artifact. Both binaries are hashed and '
                'the device binary must post-date the source it was built from -- '
                'the `fuelrun.v2.*` case that burned both lanes',
                null_must_contain='a device binary older than soakrun.rs, which '
                                  'is the stale-artifact case',
                can_fail_because='the device binary predates its source, or the '
                                 'two binaries hash identically (which would mean '
                                 'one ISA never ran)')
    c.observe(out['binaries']['device_binary_newer_than_source'] and
              out['binaries']['host_sha256'] != out['binaries']['device_sha256'],
              out['binaries'])
    C.append(c)

    F = Falsifier('F_reuse_not_safe_on_device',
                  refutes='M1.3b\'s conclusion transferring to the deployment '
                          'target: if it fires, process reuse is not safe on the '
                          'phone and WorkManager goes back to blocked',
                  fires_when='the device shows more than one distinct canon digest '
                             'across positions, OR the device probe canon digest '
                             'differs from the host\'s',
                  null_must_contain='a device whose canon digests drift with '
                                    'position, or differ from the host\'s')
    F.observe(fired, {'device_canon_distinct': out['distinct']['device']['canon'],
                      'probe_canon_host': out['probe_canon']['host'],
                      'probe_canon_device': out['probe_canon']['device'],
                      'corpus_canon_identical': out['corpus_cross_isa']['canon_identical'],
                      'corpus_programs_compared': out['corpus_cross_isa']['programs_compared']})

    # F2 -- the committed artifact, row by row. M1.3b published a TSV of
    # digests; today's build reproduces its conclusion and not its rows. Firing
    # is the finding, so this is a Falsifier and does not gate `ok` (H25).
    pairs = list(zip(crows, dev_rows))
    same_rows = [x for x, y in pairs if x[1:] == y[1:]]
    first_div = next(({'pos': x[0], 'program': x[1], 'committed': x[2:],
                       'device_today': y[2:]} for x, y in pairs if x[1:] != y[1:]),
                     None)
    F2 = Falsifier('F_committed_rows_reproduce',
                   refutes='M1.3b\'s committed soak.tsv as a REPRODUCIBLE '
                           'artifact: if its rows do not reproduce, the digests '
                           'in it are a record of one build, not of the corpus',
                   fires_when='any row of the committed TSV differs from the same '
                              'position measured today',
                   null_must_contain='a build whose per-row digests are unchanged '
                                     'since 08:47, which is what "the corpus is '
                                     'deterministic" is usually taken to mean')
    F2.observe(len(same_rows) != len(pairs),
               {'rows_compared': len(pairs), 'rows_identical': len(same_rows),
                'first_divergence': first_div,
                'committed_probe_canon': cprobe,
                'probe_canon_today': out['probe_canon']['device']})
    out['committed_rows'] = {'compared': len(pairs), 'identical': len(same_rows),
                             'first_divergence': first_div}
    with open(os.path.join(HERE, 'soak_device.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'M1_3b_process_reuse')],
        artifacts=[os.path.join(HERE, 'soak_device.json'),
                   os.path.join(HERE, 'device_soak.tsv')],
        controls=C, falsifiers=[F, F2],
        captures=[('device_soak_tsv', dev_raw_stdout)],
        instrument_texts=[('dumpsys battery', battery)],
        falsifier='device canon digests drifting with position, or differing '
                  'from the host\'s, which would mean process reuse is unsafe '
                  'on the deployment target')

    print(json.dumps({k: out[k] for k in
                      ('device', 'distinct', 'probe_canon', 'corpus_cross_isa',
                       'falsifier_fired')}, indent=2, sort_keys=True)[:2000])
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
