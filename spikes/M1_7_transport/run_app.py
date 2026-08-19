#!/usr/bin/env python3
"""M1.7 + M1.1 — the Android app as a real fleet member.

WorkManager schedules the worker under its declarative constraints; the worker
dials the coordinator, pulls shards by CID, evaluates MeTTa IN-PROCESS via JNI,
and posts envelopes. No adb push of programs, no adb-driven execution: adb only
provides the loopback tunnel and launches the app.
"""
import json, os, secrets, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(16))
from shardstore import cid_of
import bansurface, server

PORT = 18080
CORPUS = os.path.join(HERE, '..', 'S57_hyperon_corpus', 'corpus')
def sh(*a):
    if a and a[0] == 'adb' and '-s' not in a and 'ANDROID_SERIAL' not in os.environ:
        # Scope to physical phone by default
        a = ('adb', '-s', 'R5CY93675MK') + a[1:]
    return subprocess.run(a, capture_output=True, text=True)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
progs = sorted(f for f in os.listdir(CORPUS) if f.endswith('.metta'))
progs = [p for p in progs
         if bansurface.admit(open(os.path.join(CORPUS, p), 'rb').read())[0]][:n]
for p in progs:
    d = open(os.path.join(CORPUS, p), 'rb').read()
    server.SHARDS[cid_of(d)] = d
for i, p in enumerate(progs):
    d = open(os.path.join(CORPUS, p), 'rb').read()
    server.JOBS.put({'job_id': f'j{i:04d}', 'shard_cid': cid_of(d),
                     'fuel': 2000000, 'name': p})

server.serve(PORT)
sh('adb', 'reverse', f'tcp:{PORT}', f'tcp:{PORT}')
# INSTALL the APK we just built. Without this the device keeps whatever was
# installed last, and the run measures a stale artifact -- A24's family, and it
# cost a full 240 s timeout diagnosing a "transport bug" that was an old APK.
APK = os.path.join(HERE, '..', 'M1_1_android', 'app', 'build', 'outputs',
                   'apk', 'debug', 'app-debug.apk')
import hashlib
apk_sha = hashlib.sha256(open(APK, 'rb').read()).hexdigest()[:12]
r = sh('adb', 'install', '-r', APK)
if 'Success' not in r.stdout:
    print('APK install FAILED:', r.stdout.strip(), r.stderr.strip()); sys.exit(1)
print(f'installed app-debug.apk sha256 {apk_sha}')
sh('adb', 'shell', 'pm clear net.kingfisher')     # cold shard cache in app storage
sh('adb', 'logcat', '-c')
sh('adb', 'shell',
   f'am start -n net.kingfisher/.MainActivity --es token {os.environ["KF_TOKEN"]}')
print(f'{len(progs)} jobs queued; app launched, WorkManager will schedule the worker')

# give the verifier the SAME working dir the app uses, so filesystem-touching
# programs (file-open!, mkdocs) compare like with like
appdir = sh('adb','shell','run-as net.kingfisher pwd').stdout.strip() or ''
print('app files dir (for verifier parity):', appdir or '<unavailable>')

t0 = time.time()
while len(server.RESULTS) < len(progs) and time.time() - t0 < 240:
    time.sleep(0.3)
wall = time.time() - t0
print(f'\nenvelopes {len(server.RESULTS)}/{len(progs)} in {wall:.1f}s')
print('server stats:', json.dumps(server.STATS))
log = sh('adb', 'logcat', '-d', '-s', 'KFWORKER', 'KFNET').stdout
for l in log.splitlines():
    if any(k in l for k in ('FLEET RUN', 'PREFLIGHT', 'shard miss', 'METTA FAILED')):
        print('  ', l.split(': ', 1)[-1])
json.dump({'envelopes': server.RESULTS, 'stats': server.STATS,
           'wall_s': round(wall, 1)},
          open(os.path.join(HERE, 'result_app.json'), 'w'), indent=1)
