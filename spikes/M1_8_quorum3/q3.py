#!/usr/bin/env python3
"""M1.8 -- quorum-3 pipeline end to end. Coordinator + 3 worker processes.

Adjudication is BOINC's majority rule (sample_bitwise_validator.cc:17-18):
a result is accepted when >=2 of 3 replicas agree BYTE FOR BYTE. What must
match is (status, fuel_used, sorted_hash) -- fuel_used is in the key because
S57 established that equal output with unequal fuel is a divergence, not an
agreement.
"""
import argparse, json, os, shutil, subprocess, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
BIN  = os.path.join(HERE, '..', 'S30_speed_duel', 'bin')
DEVDIR = '/data/local/tmp/m18'

def key(e):
    if e is None: return None
    return (e.get('status'), e.get('fuel_used'), e.get('sorted_hash'))

def adjudicate(envs):
    """>=2 of 3 identical -> ACCEPT. Returns (verdict, key, agree_count)."""
    ks = [key(e) for e in envs]
    live = [k for k in ks if k is not None]
    if not live:
        return 'NO_RESULTS', None, 0
    k, n = Counter(live).most_common(1)[0]
    if n >= 2:
        return ('UNANIMOUS' if n == len(ks) else 'MAJORITY'), k, n
    return 'NO_QUORUM', None, n

def stage_device(prog_dir, android_bin):
    subprocess.run(['adb', 'shell', f'mkdir -p {DEVDIR}/corpus'], check=True)
    subprocess.run(['adb', 'push', android_bin, DEVDIR + '/'],
                   check=True, capture_output=True)
    subprocess.run(['adb', 'shell',
                    f'chmod +x {DEVDIR}/{os.path.basename(android_bin)}'],
                   check=True)
    subprocess.run(['adb', 'push', prog_dir, DEVDIR + '/'],
                   check=True, capture_output=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=os.path.join(
        HERE, '..', 'S57_hyperon_corpus', 'corpus'))
    ap.add_argument('--fuel', type=int, default=2000000)
    ap.add_argument('--limit', type=int, default=0, help='0 = whole corpus')
    ap.add_argument('--work', default=os.path.join(HERE, 'run'))
    ap.add_argument('--no-device', action='store_true')
    a = ap.parse_args()

    progs = sorted(f for f in os.listdir(a.corpus) if f.endswith('.metta'))
    if a.limit: progs = progs[:a.limit]

    # MISSION_LOOP 10: device work is gated, and the gate result is recorded
    gate = None
    if not a.no_device:
        g = subprocess.run([os.path.join(HERE, '..', 'quiet.sh'), '--device'],
                           capture_output=True, text=True)
        gate = g.stdout.strip() or g.stderr.strip()
        if g.returncode != 0:
            print('device gate REFUSED:', gate); sys.exit(2)
        print('gate:', gate)
        stage_device(a.corpus, os.path.join(BIN, 'fuelrun.v2.android'))

    workers = [
        ('host-a', os.path.join(BIN, 'fuelrun.v2.host'), 'local'),
        ('host-b', os.path.join(BIN, 'fuelrun.v2.host'), 'local'),
    ]
    if not a.no_device:
        workers.append(('phone', os.path.join(BIN, 'fuelrun.v2.android'), 'adb'))
    else:
        workers.append(('host-c', os.path.join(BIN, 'fuelrun.v2.host'), 'local'))

    shutil.rmtree(a.work, ignore_errors=True)
    procs = []
    for wid, binary, via in workers:
        inbox  = os.path.join(a.work, wid, 'in')
        outbox = os.path.join(a.work, wid, 'out')
        os.makedirs(inbox); os.makedirs(outbox)
        procs.append(subprocess.Popen(
            [sys.executable, os.path.join(HERE, 'worker.py'),
             '--id', wid, '--inbox', inbox, '--outbox', outbox,
             '--bin', binary, '--via', via, '--devdir', DEVDIR]))

    # dispatch: same (program, fuel) to all three. Paths differ per transport.
    for i, p in enumerate(progs):
        jid = f'j{i:04d}'
        for wid, _, via in workers:
            prog = (f'corpus/{p}' if via == 'adb'
                    else os.path.join(a.corpus, p))
            job = {'job_id': jid, 'program': prog, 'fuel': a.fuel, 'name': p}
            d = os.path.join(a.work, wid, 'in')
            tmp = os.path.join(d, jid + '.tmp')
            with open(tmp, 'w') as f: json.dump(job, f)
            os.rename(tmp, os.path.join(d, jid + '.job'))

    # collect
    rows, t0 = [], time.time()
    for i, p in enumerate(progs):
        jid = f'j{i:04d}'
        envs = []
        for wid, _, _ in workers:
            fp = os.path.join(a.work, wid, 'out', jid + '.env')
            while not os.path.exists(fp) and time.time() - t0 < 1800:
                time.sleep(0.02)
            envs.append(json.load(open(fp)) if os.path.exists(fp) else None)
        v, k, n = adjudicate(envs)
        rows.append((p, v, n, k, envs))

    for pr in procs: pr.terminate()

    # report
    tally = Counter(r[1] for r in rows)
    print(f'\n{"program":56} {"verdict":10} {"agree":5} fuel')
    for p, v, n, k, envs in rows:
        flag = '' if v in ('UNANIMOUS',) else '   <<<'
        print(f'{p[:56]:56} {v:10} {n}/3   {(k[1] if k else "-"):>9}{flag}')
    print('\n' + '  '.join(f'{kk}={vv}' for kk, vv in sorted(tally.items())))
    accepted = tally['UNANIMOUS'] + tally['MAJORITY']
    print(f'accepted {accepted}/{len(rows)}')

    json.dump({'gate': gate, 'fuel': a.fuel,
               'workers': [w[0] for w in workers],
               'tally': dict(tally),
               'rows': [{'program': p, 'verdict': v, 'agree': n,
                         'key': k, 'envelopes': e} for p, v, n, k, e in rows]},
              open(os.path.join(HERE, 'result.json'), 'w'), indent=1)
    print('-> result.json')

main()
