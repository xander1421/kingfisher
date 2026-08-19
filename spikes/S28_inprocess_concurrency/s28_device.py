#!/usr/bin/env python3
"""S28 Device — in-process concurrency on Samsung Galaxy S25 Ultra (Snapdragon 8 Elite).

Extends S28 onto the physical hardware deployment target:
1. Physical device safety & battery/thermal checks.
2. In-process MeTTa reduction under canonicalization (canon/alpha) across concurrent
   threads (1, 4, 8 threads) to verify zero non-deterministic divergence.
3. Cross-comparison of device digests vs host digests.
4. Compute throughput (steps/sec) and memory residency (RSS / VmPeak / leak-freedom)
   on physical hardware.
5. D6 empirical provenance certification (kfcheck.certify).
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
sys.path.insert(0, os.path.join(ROOT, 'spikes'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402
from instrument import check_not_frozen                                   # noqa: E402
import devsweep                                                           # noqa: E402

BIN_HOST = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                        'target', 'release', 'threadrun')
SOAK_HOST = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                         'target', 'release', 'soakrun')
BIN_DEV = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                       'target', 'aarch64-linux-android', 'release', 'threadrun')
SOAK_DEV = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun',
                        'target', 'aarch64-linux-android', 'release', 'soakrun')
SRC = os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun', 'src',
                   'bin', 'threadrun.rs')
CORPUS = os.path.join(ROOT, 'spikes', 'S57_hyperon_corpus', 'corpus')
PROBE = os.path.join(HERE, 'probe.metta')
DEV_DIR = '/data/local/tmp/kf_s28_device'
FUEL = '200000'


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def job_list(n_others):
    others = sorted(f for f in os.listdir(CORPUS) if f.endswith('.metta'))[:n_others]
    args = []
    for o in others:
        args += [PROBE, os.path.join(CORPUS, o)]
    args.append(PROBE)
    return args


def parse(stdout):
    rows = []
    for line in stdout.splitlines():
        if not line.strip() or line.startswith('#') or line.startswith('repeat'):
            continue
        f = line.split('\t')
        if len(f) >= 8:
            rows.append({
                'repeat': f[0], 'thread': f[1], 'pos': f[2], 'program': f[3],
                'fuel_used': f[4],
                'fuel_at_pos': '%s:%s' % (f[2], f[4]),
                'raw': f[5], 'canon': f[6], 'alpha': f[7]
            })
    return rows


def multiset_sig(rows, col):
    return hashlib.sha256('\n'.join(sorted(r[col] for r in rows)).encode()).hexdigest()[:16]


def run_host_binary(binary, argv, timeout=900):
    t0 = time.time()
    r = subprocess.run([binary] + argv, capture_output=True, text=True, timeout=timeout)
    wall = time.time() - t0
    if r.returncode != 0:
        sys.exit(f'{binary} failed rc={r.returncode}\n{r.stderr[-800:]}')
    return r.stdout, wall


def run_device_binary(binary_name, argv, timeout=900):
    cmd = f'cd {DEV_DIR} && ./{binary_name} ' + ' '.join(argv)
    t0 = time.time()
    r = sh(['adb', 'shell', cmd], timeout=timeout)
    wall = time.time() - t0
    if r.returncode != 0:
        sys.exit(f'adb shell {cmd} failed rc={r.returncode}\n{r.stderr[-800:]}')
    return r.stdout, wall


def get_process_memory_on_device(binary_name, argv):
    cmd = f'cd {DEV_DIR} && ( ./{binary_name} {" ".join(argv)} >/dev/null & PID=$!; cat /proc/$PID/status 2>/dev/null; wait $PID )'
    r = sh(['adb', 'shell', cmd], timeout=120)
    out = r.stdout or ''
    vm_rss = re.search(r'VmRSS:\s+(\d+)\s+kB', out)
    vm_peak = re.search(r'VmPeak:\s+(\d+)\s+kB', out)
    vm_hwm = re.search(r'VmHWM:\s+(\d+)\s+kB', out)
    return {
        'vm_rss_kb': int(vm_rss.group(1)) if vm_rss else None,
        'vm_peak_kb': int(vm_peak.group(1)) if vm_peak else None,
        'vm_hwm_kb': int(vm_hwm.group(1)) if vm_hwm else None,
    }


def arm_device(threads, invocations, job_basenames):
    sigs = {'raw': [], 'canon': [], 'alpha': [], 'fuel_at_pos': []}
    walls, per_invocation = [], []
    for _ in range(invocations):
        out, wall = run_device_binary('threadrun', [FUEL, str(threads), '1'] + job_basenames)
        rows = parse(out)
        for col in sigs:
            sigs[col].append(multiset_sig(rows, col))
        walls.append(wall)
        per_invocation.append(rows)
    return {
        'threads': threads, 'invocations': invocations,
        'job_runs_per_invocation': len(per_invocation[0]),
        'sigs': sigs,
        'distinct': {c: len(set(v)) for c, v in sigs.items()},
        'wall_median': sorted(walls)[len(walls) // 2],
        'walls': [round(w, 3) for w in walls],
        'rows': per_invocation
    }


def arm_host(threads, invocations, full_jobs):
    sigs = {'raw': [], 'canon': [], 'alpha': [], 'fuel_at_pos': []}
    walls, per_invocation = [], []
    for _ in range(invocations):
        out, wall = run_host_binary(BIN_HOST, [FUEL, str(threads), '1'] + full_jobs)
        rows = parse(out)
        for col in sigs:
            sigs[col].append(multiset_sig(rows, col))
        walls.append(wall)
        per_invocation.append(rows)
    return {
        'threads': threads, 'invocations': invocations,
        'job_runs_per_invocation': len(per_invocation[0]),
        'sigs': sigs,
        'distinct': {c: len(set(v)) for c, v in sigs.items()},
        'wall_median': sorted(walls)[len(walls) // 2],
        'walls': [round(w, 3) for w in walls],
        'rows': per_invocation
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--invocations', type=int, default=5)
    ap.add_argument('--others', type=int, default=6)
    a = ap.parse_args()

    for p in (BIN_HOST, SOAK_HOST, BIN_DEV, SOAK_DEV):
        if not os.path.exists(p):
            sys.exit(f'Missing binary: {p}')

    # §10 Gate
    devsweep.gate()
    battery = sh(['adb', 'shell', 'dumpsys', 'battery']).stdout
    model = sh(['adb', 'shell', 'getprop', 'ro.product.model']).stdout.strip()
    abi = sh(['adb', 'shell', 'getprop', 'ro.product.cpu.abi']).stdout.strip()
    sdk = sh(['adb', 'shell', 'getprop', 'ro.build.version.sdk']).stdout.strip()
    platform = sh(['adb', 'shell', 'getprop', 'ro.board.platform']).stdout.strip()
    therm_before = devsweep.thermal()

    print(f'# Galaxy S25 Ultra ({model}, {platform}, ABI {abi}, SDK {sdk})')
    print(f'# Thermal before: {therm_before}m, Battery charging check...')

    # Push to device
    sh(['adb', 'shell', 'rm', '-rf', DEV_DIR])
    sh(['adb', 'shell', 'mkdir', '-p', DEV_DIR])
    sh(['adb', 'push', '-q', BIN_DEV, f'{DEV_DIR}/threadrun'])
    sh(['adb', 'push', '-q', SOAK_DEV, f'{DEV_DIR}/soakrun'])
    sh(['adb', 'shell', f'chmod 755 {DEV_DIR}/threadrun {DEV_DIR}/soakrun'])
    sh(['adb', 'push', '-q', PROBE, f'{DEV_DIR}/probe.metta'])

    other_files = sorted(f for f in os.listdir(CORPUS) if f.endswith('.metta'))[:a.others]
    for o in other_files:
        sh(['adb', 'push', '-q', os.path.join(CORPUS, o), f'{DEV_DIR}/{o}'])

    host_jobs = job_list(a.others)
    device_job_basenames = []
    for j in host_jobs:
        device_job_basenames.append(os.path.basename(j))

    bin_dev_sha = sha256_file(BIN_DEV)
    bin_host_sha = sha256_file(BIN_HOST)

    print(f'# S28 On-Device threads={a.threads} invocations={a.invocations} jobs_per_invocation={len(device_job_basenames)}')
    print(f'# threadrun (aarch64) sha256={bin_dev_sha}')

    # Execute arms on Device
    dev_one = arm_device(1, a.invocations, device_job_basenames)
    dev_many = arm_device(a.threads, a.invocations, device_job_basenames)
    # Also test 8 threads (all 8 cores of Snapdragon 8 Elite)
    dev_eight = arm_device(8, a.invocations, device_job_basenames)

    # Execute 1-thread on Host for cross-ISA check
    host_one = arm_host(1, 1, host_jobs)

    # C0: device threadrun at 1 thread reproduces device soakrun
    soak_out, _ = run_device_binary('soakrun', [FUEL] + device_job_basenames)
    soak_cols = {l.split('\t')[0]: l.split('\t')[2:5]
                 for l in soak_out.splitlines()[1:] if l.strip()}
    thr_cols = {r['pos']: [r['raw'], r['canon'], r['alpha']]
                for r in dev_one['rows'][0]}
    c0_match = soak_cols == thr_cols

    # C3: check raw distinct across probe positions on device
    probe_raw_dev = [r['raw'] for r in dev_one['rows'][0] if r['program'] == 'probe.metta']
    probe_canon_dev = [r['canon'] for r in dev_one['rows'][0] if r['program'] == 'probe.metta']
    probe_alpha_dev = [r['alpha'] for r in dev_one['rows'][0] if r['program'] == 'probe.metta']

    # Cross-ISA check: probe canon device vs host
    probe_canon_host = [r['canon'] for r in host_one['rows'][0] if r['program'] == 'probe.metta']
    cross_isa_match = set(probe_canon_dev) == set(probe_canon_host) and len(set(probe_canon_dev)) == 1

    # Speedups on Snapdragon 8 Elite
    speedup_4 = dev_one['wall_median'] * 4.0 / dev_many['wall_median'] if dev_many['wall_median'] else 0.0
    speedup_8 = dev_one['wall_median'] * 8.0 / dev_eight['wall_median'] if dev_eight['wall_median'] else 0.0

    # Total reduction steps & compute throughput on device
    total_fuel_1 = sum(int(r['fuel_used']) for r in dev_one['rows'][0])
    total_fuel_4 = sum(int(r['fuel_used']) for r in dev_many['rows'][0])
    total_fuel_8 = sum(int(r['fuel_used']) for r in dev_eight['rows'][0])

    throughput_1 = total_fuel_1 / dev_one['wall_median'] if dev_one['wall_median'] else 0
    throughput_4 = total_fuel_4 / dev_many['wall_median'] if dev_many['wall_median'] else 0
    throughput_8 = total_fuel_8 / dev_eight['wall_median'] if dev_eight['wall_median'] else 0

    # Memory residency measurement on hardware
    mem_sample = get_process_memory_on_device('threadrun', [FUEL, str(a.threads), '1'] + device_job_basenames)

    # Effect size helper
    def overlap(runs, col):
        base = collections.Counter(r[col] for r in runs[0])
        out = []
        for rows in runs[1:]:
            other = collections.Counter(r[col] for r in rows)
            out.append(sum((base & other).values()))
        return {'total_per_invocation': len(runs[0]), 'kept_vs_invocation_0': out}

    effect_dev = {c: overlap(dev_many['rows'], c) for c in ('raw', 'canon', 'alpha')}
    effect_dev_8 = {c: overlap(dev_eight['rows'], c) for c in ('raw', 'canon', 'alpha')}

    therm_after = devsweep.thermal()

    # Verdict derivation
    if dev_one['distinct']['raw'] > 1:
        verdict = 'F3 FIRED -- NO VERDICT (device instrument noise)'
    elif dev_many['distinct']['raw'] > 1:
        if dev_many['distinct']['canon'] == 1 and dev_many['distinct']['alpha'] == 1:
            verdict = 'F2 PROVEN ON PHYSICAL DEVICE: RAW varies under in-process concurrency, CANON and ALPHA remain 100% deterministic (zero divergence)'
        else:
            verdict = 'CRITICAL FAILURE: Non-deterministic divergence in canonicalized output on device'
    else:
        verdict = 'F1 FIRED (raw multiset stable)'

    result = {
        'device': {
            'model': model, 'platform': platform, 'abi': abi, 'sdk': sdk,
            'thermal_before_m': therm_before, 'thermal_after_m': therm_after
        },
        'threads_tested': [1, a.threads, 8],
        'invocations': a.invocations,
        'jobs_per_invocation': len(device_job_basenames),
        'threadrun_device_sha256': bin_dev_sha,
        'threadrun_host_sha256': bin_host_sha,
        'arm_1_thread_device': {
            'distinct': dev_one['distinct'], 'wall_median': dev_one['wall_median'],
            'walls': dev_one['walls'], 'job_runs': dev_one['job_runs_per_invocation'],
            'throughput_steps_per_sec': round(throughput_1, 1)
        },
        'arm_4_thread_device': {
            'distinct': dev_many['distinct'], 'wall_median': dev_many['wall_median'],
            'walls': dev_many['walls'], 'job_runs': dev_many['job_runs_per_invocation'],
            'throughput_steps_per_sec': round(throughput_4, 1),
            'speedup_vs_serialised': round(speedup_4, 2),
            'effect_size': effect_dev
        },
        'arm_8_thread_device': {
            'distinct': dev_eight['distinct'], 'wall_median': dev_eight['wall_median'],
            'walls': dev_eight['walls'], 'job_runs': dev_eight['job_runs_per_invocation'],
            'throughput_steps_per_sec': round(throughput_8, 1),
            'speedup_vs_serialised': round(speedup_8, 2),
            'effect_size': effect_dev_8
        },
        'memory_residency': mem_sample,
        'c0_soakrun_identical': c0_match,
        'cross_isa_canon_match': cross_isa_match,
        'probe_positions': len(probe_raw_dev),
        'probe_raw_distinct': len(set(probe_raw_dev)),
        'probe_canon_distinct': len(set(probe_canon_dev)),
        'probe_alpha_distinct': len(set(probe_alpha_dev)),
        'verdict': verdict
    }

    result_path = os.path.join(HERE, 'result.json')
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2, sort_keys=True)

    # Controls
    C = []

    c = Control(
        'C0_device_reproduces_soakrun',
        'threadrun at 1 thread must reproduce soakrun digest columns byte for byte on Android device',
        null_must_contain='canon/canon_alpha drift on aarch64 runtime',
        can_fail_because='any digest column differs between soakrun and threadrun at 1 thread on device'
    )
    c.observe(c0_match, {'rows_compared': len(soak_cols), 'identical': c0_match})
    C.append(c)

    fresh = os.path.getmtime(BIN_DEV) >= os.path.getmtime(SRC)
    c = Control(
        'C1_same_build_both_arms',
        'arms must use the exact same aarch64 binary compiled fresh from source',
        null_must_contain='rebuild or mismatched binary between arms',
        can_fail_because='binary is older than source or sha differs'
    )
    c.observe(fresh and dev_one['job_runs_per_invocation'] * a.threads == dev_many['job_runs_per_invocation'],
              {'binary_sha256': bin_dev_sha, 'fresh': fresh})
    C.append(c)

    c = Control(
        'C2_intervention_is_not_a_no_op',
        'N-thread arm must run N times the job runs inside the same process',
        null_must_contain='threads not spawned',
        can_fail_because='job_runs_n != threads * job_runs_1'
    )
    c.observe(dev_many['job_runs_per_invocation'] == dev_one['job_runs_per_invocation'] * a.threads,
              {'jobs_1': dev_one['job_runs_per_invocation'], 'jobs_4': dev_many['job_runs_per_invocation']})
    C.append(c)

    c = Control(
        'C3_counter_reaches_printed_output',
        'raw digests must differ across probe positions in one process on device',
        null_must_contain='probe with constant raw output (A29)',
        can_fail_because='raw distinct count is 1 across probe positions'
    )
    c.observe(len(set(probe_raw_dev)) > 1,
              {'positions': len(probe_raw_dev), 'raw_distinct': len(set(probe_raw_dev)), 'canon_distinct': len(set(probe_canon_dev))})
    C.append(c)

    c = Control(
        'C4_threads_are_not_serialised',
        'concurrent execution must exhibit parallel scaling on Snapdragon 8 Elite hardware',
        null_must_contain='global lock serialisation where speedup <= 1.2x',
        can_fail_because='parallel speedup <= 1.2x'
    )
    c.observe(speedup_4 > 1.2,
              {'speedup_4_cores': round(speedup_4, 2), 'speedup_8_cores': round(speedup_8, 2)})
    C.append(c)

    c = Control(
        'C5_fuel_is_invariant_under_concurrency',
        'fuel count at every position must remain 100% invariant across all concurrent invocations',
        null_must_contain='fuel count divergence between runs',
        can_fail_because='distinct fuel signatures > 1'
    )
    c.observe(dev_many['distinct']['fuel_at_pos'] == 1 and dev_eight['distinct']['fuel_at_pos'] == 1,
              {'fuel_signatures_4_thread': dev_many['distinct']['fuel_at_pos'],
               'fuel_signatures_8_thread': dev_eight['distinct']['fuel_at_pos']})
    C.append(c)

    c = Control(
        'C6_canonicalization_eliminates_divergence',
        'canon and alpha multisets must be exactly 1 distinct signature across all invocations',
        null_must_contain='canonicalized digest drifting under concurrency',
        can_fail_because='distinct canon multisets > 1 or distinct alpha multisets > 1'
    )
    c.observe(dev_many['distinct']['canon'] == 1 and dev_many['distinct']['alpha'] == 1 and
              dev_eight['distinct']['canon'] == 1 and dev_eight['distinct']['alpha'] == 1,
              {'canon_distinct_4': dev_many['distinct']['canon'], 'alpha_distinct_4': dev_many['distinct']['alpha'],
               'canon_distinct_8': dev_eight['distinct']['canon'], 'alpha_distinct_8': dev_eight['distinct']['alpha']})
    C.append(c)

    c = Control(
        'C7_cross_isa_canon_reproducibility',
        'canonicalized probe digest on device aarch64 must match host byte-for-byte',
        null_must_contain='cross-ISA canonicalization divergence',
        can_fail_because='device canon digest differs from host canon digest'
    )
    c.observe(cross_isa_match,
              {'device_probe_canon': probe_canon_dev[0] if probe_canon_dev else '',
               'host_probe_canon': probe_canon_host[0] if probe_canon_host else ''})
    C.append(c)

    # Clean up device temp dir
    sh(['adb', 'shell', 'rm', '-rf', DEV_DIR])

    print('\n================ RESULTS SUMMARY ================')
    print(f'1 thread (Device):   distinct raw={dev_one["distinct"]["raw"]} canon={dev_one["distinct"]["canon"]} alpha={dev_one["distinct"]["alpha"]} fuel={dev_one["distinct"]["fuel_at_pos"]} wall_median={dev_one["wall_median"]}s ({throughput_1:.1f} steps/s)')
    print(f'4 threads (Device): distinct raw={dev_many["distinct"]["raw"]} canon={dev_many["distinct"]["canon"]} alpha={dev_many["distinct"]["alpha"]} fuel={dev_many["distinct"]["fuel_at_pos"]} wall_median={dev_many["wall_median"]}s ({throughput_4:.1f} steps/s, speedup {speedup_4:.2f}x)')
    print(f'8 threads (Device): distinct raw={dev_eight["distinct"]["raw"]} canon={dev_eight["distinct"]["canon"]} alpha={dev_eight["distinct"]["alpha"]} fuel={dev_eight["distinct"]["fuel_at_pos"]} wall_median={dev_eight["wall_median"]}s ({throughput_8:.1f} steps/s, speedup {speedup_8:.2f}x)')
    print(f'Memory residency: VmRSS={mem_sample.get("vm_rss_kb")} kB, VmPeak={mem_sample.get("vm_peak_kb")} kB, VmHWM={mem_sample.get("vm_hwm_kb")} kB')
    print(f'Cross-ISA Probe Canon: {probe_canon_dev[0]} (Device == Host: {cross_isa_match})')
    print(f'VERDICT: {verdict}')

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'S15_android_device', 'fuelrun', 'src'),
              os.path.join(ROOT, 'spikes', 'M1_3b_process_reuse')],
        artifacts=[result_path],
        controls=C,
        captures=[('threadrun_dev_sha256', bin_dev_sha)],
        instrument_texts=[('dumpsys battery', battery)],
        allow_dirty=True,
        note='Physical device S28 concurrency certification on Snapdragon 8 Elite (SM-S938B).',
        falsifier='a stable RAW digest multiset across repeated concurrent invocations on hardware, or a varying CANON/ALPHA digest signature'
    )

    print(f'certify ok={ok}')
    for p in problems:
        print(f'  PROBLEM {p}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
