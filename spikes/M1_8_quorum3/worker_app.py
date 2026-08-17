#!/usr/bin/env python3
"""q3 worker shim for the real Android app.

The other workers are `fuelrun` subprocesses driven by a filesystem inbox. The
app is driven by HTTP: WorkManager schedules it, it dials out, pulls shards by
CID and posts envelopes. This bridges the two so the quorum can include the
actual product rather than an adb-driven copy of the verifier.

Why it matters for the domain vector: the app is a different binary AND a
different manifest (`libhyperonc` takes workspace defaults; `fuelrun` has its
own Cargo.toml), so it raises `binary` and `manifest` honestly rather than by
relabelling the same artifact.
"""
import argparse, hashlib, json, os, secrets, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(24))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_7_transport'))
from shardstore import ShardStore, cid_of
import server


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--inbox', required=True)
    ap.add_argument('--outbox', required=True)
    ap.add_argument('--store', required=True)
    # MUST match the port the app polls. MainActivity enqueues work without a
    # `port` key, so MettaWorker falls back to getInt("port", 18080). A shim
    # on any other port produces instant connection failures that look like
    # a transport bug -- which cost a 10-minute q3 timeout to find.
    ap.add_argument('--port', type=int, default=18080)
    ap.add_argument('--apk', default=os.path.join(
        HERE, '..', 'M1_1_android', 'app', 'build', 'outputs', 'apk', 'debug',
        'app-debug.apk'))
    a = ap.parse_args()
    os.makedirs(a.outbox, exist_ok=True)
    store = ShardStore(a.store)

    print(f'[shim] serving on 127.0.0.1:{a.port}', flush=True)
    server.serve(a.port)
    sh('adb', 'reverse', f'tcp:{a.port}', f'tcp:{a.port}')
    sh('adb', 'install', '-r', a.apk)

    # WAIT for work before launching the app.
    #
    # OPEN BUG, worked around here rather than fixed: if the app's FIRST poll
    # finds an empty queue, every subsequent poll fails instantly with okhttp's
    # "unexpected end of stream" and the worker gives up. Adding `Connection:
    # close` on both sides did not fix it, and `curl` handles the same responses
    # correctly, so it is specific to HttpURLConnection. `run_app.py` never hit
    # it because it queues jobs before launching. Matching that ordering.
    def load_inbox():
        n = 0
        for jf in sorted(f for f in os.listdir(a.inbox) if f.endswith('.job')):
            jp = os.path.join(a.inbox, jf)
            try:
                job = json.load(open(jp))
            except Exception:
                continue
            os.remove(jp)
            data = store.get(job['shard_cid'])
            if data is None:
                continue
            server.SHARDS[job['shard_cid']] = data
            server.JOBS.put(job)
            n += 1
        return n

    print('[shim] adb reverse + install done', flush=True)
    waited = 0
    while load_inbox() == 0 and waited < 300:
        time.sleep(0.1)
        waited += 1
    print(f'[shim] queue depth {server.JOBS.qsize()}, shards {len(server.SHARDS)}; launching app', flush=True)
    # `pm clear`, not `force-stop`. WorkManager persists its work database, so
    # a force-stopped app re-launches into whatever state prior runs left --
    # including backoff windows from earlier Result.retry()s. `run_app.py` did
    # `pm clear` from the start and worked; this shim did `force-stop` and saw
    # ZERO requests reach the server while curl from the same device got 200.
    sh('adb', 'shell', 'pm clear net.kingfisher')
    tok = os.environ.get('KF_TOKEN', '')
    sh('adb', 'shell',
       f'am start -n net.kingfisher/.MainActivity --es token {tok}')

    seen, idle = set(), 0
    while idle < 400:                       # ~40 s of no new work
        idle = 0 if load_inbox() else idle + 1
        if idle and idle % 100 == 0:
            print(f'[shim] idle={idle} stats={server.STATS} results={len(server.RESULTS)}', flush=True)
        # drain whatever the app has posted back
        while server.RESULTS:
            env = server.RESULTS.pop(0)
            jid = env.get('job_id')
            if not jid or jid in seen:
                continue
            seen.add(jid)
            env['worker'] = a.id
            env['results_text'] = env.get('results', '')
            tmp = os.path.join(a.outbox, jid + '.tmp')
            with open(tmp, 'w') as f:
                json.dump(env, f)
            os.rename(tmp, os.path.join(a.outbox, jid + '.env'))
        time.sleep(0.1)


main()
