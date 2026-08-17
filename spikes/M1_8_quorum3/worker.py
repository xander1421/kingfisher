#!/usr/bin/env python3
"""M1.8 worker — one process, one device. Polls a filesystem inbox, runs
fuelrun on the job, writes an envelope to the outbox.

Filesystem transport is prime-rl's testing trick (PORT_PLAN M1.7) and it is
also the honest shape here: the phone always dials, and adb is a pull.
A fresh fuelrun process per job is required, not an optimisation --
PORT_PLAN M1.3 gives two independent derivations (S60/A8 atomspace pollution,
and process-global NEXT_VARIABLE_ID).
"""
import argparse, json, os, subprocess, sys, time

def run_local(binary, prog, fuel):
    return subprocess.run([binary, prog, str(fuel)],
                          capture_output=True, text=True, timeout=300)

def run_adb(binary, prog, fuel, devdir):
    # program already staged on device by the coordinator
    cmd = f'cd {devdir} && ./{os.path.basename(binary)} {prog} {fuel}'
    return subprocess.run(['adb', 'shell', cmd],
                          capture_output=True, text=True, timeout=300)

def parse(out):
    """fuelrun prints 'key value' lines. Missing keys must be visible, not
    defaulted -- S57 v1 hardcoded status='ok' and recorded a FUEL_EXHAUSTED
    program as OK."""
    kv = {}
    for line in out.splitlines():
        p = line.split(None, 1)
        if len(p) == 2:
            kv[p[0]] = p[1].strip()
    need = ('status', 'fuel_used', 'sorted_hash', 'raw_hash', 'n_results')
    missing = [k for k in need if k not in kv]
    if missing:
        return None, f'NO_PARSE missing={",".join(missing)}'
    return kv, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--inbox', required=True)
    ap.add_argument('--outbox', required=True)
    ap.add_argument('--bin', required=True)
    ap.add_argument('--via', choices=['local', 'adb'], default='local')
    ap.add_argument('--devdir', default='/data/local/tmp/m18')
    a = ap.parse_args()
    os.makedirs(a.outbox, exist_ok=True)
    idle = 0
    while idle < 60:
        jobs = sorted(f for f in os.listdir(a.inbox) if f.endswith('.job'))
        if not jobs:
            time.sleep(0.05); idle += 1; continue
        idle = 0
        for jf in jobs:
            jp = os.path.join(a.inbox, jf)
            try:
                job = json.load(open(jp))
            except Exception:
                continue
            os.remove(jp)
            if job.get('op') == 'stop':
                return
            t0 = time.time()
            try:
                r = (run_adb(a.bin, job['program'], job['fuel'], a.devdir)
                     if a.via == 'adb' else
                     run_local(a.bin, job['program'], job['fuel']))
                kv, err = parse(r.stdout)
                if r.returncode != 0 and kv is None:
                    env = {'status': 'CRASH', 'detail': r.stderr[-300:]}
                elif err:
                    env = {'status': err}
                else:
                    env = {k: kv[k] for k in
                           ('status','fuel_used','raw_hash','sorted_hash',
                            'n_results','arch','os') if k in kv}
            except subprocess.TimeoutExpired:
                env = {'status': 'TIMEOUT'}
            env.update(worker=a.id, job_id=job['job_id'],
                       program=job['program'], fuel_limit=job['fuel'],
                       wall_ms=round((time.time()-t0)*1000, 1))
            tmp = os.path.join(a.outbox, job['job_id'] + '.tmp')
            with open(tmp, 'w') as f:
                json.dump(env, f)
            os.rename(tmp, os.path.join(a.outbox, job['job_id'] + '.env'))

main()
