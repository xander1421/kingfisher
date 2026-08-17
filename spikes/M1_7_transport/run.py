#!/usr/bin/env python3
"""Drive M1.7 end to end: queue jobs, let the phone dial in, collect envelopes."""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from shardstore import cid_of
import bansurface, server

PORT = int(os.environ.get('KF_PORT', '18080'))
DEV = '/data/local/tmp/m17'
CORPUS = os.path.join(HERE, '..', 'S57_hyperon_corpus', 'corpus')
BIN = os.path.join(HERE, '..', 'S30_speed_duel', 'bin', 'known', 'fuelrun.android')

def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
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

srv = server.serve(PORT)
print(f'coordinator on 127.0.0.1:{PORT} (loopback only), {len(progs)} jobs queued')

sh('adb', 'reverse', f'tcp:{PORT}', f'tcp:{PORT}')
sh('adb', 'shell', f'mkdir -p {DEV}/shards')
sh('adb', 'push', BIN, f'{DEV}/fuelrun')
sh('adb', 'shell', f'chmod +x {DEV}/fuelrun')
sh('adb', 'push', os.path.join(HERE, 'agent.sh'), f'{DEV}/agent.sh')
sh('adb', 'shell', f'chmod +x {DEV}/agent.sh')
sh('adb', 'shell', f'rm -rf {DEV}/shards; mkdir -p {DEV}/shards')   # cold cache

t0 = time.time()
proc = subprocess.Popen(['adb', 'shell',
                         f'KF_PORT={PORT} KF_MAXIDLE=2 sh {DEV}/agent.sh'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
while len(server.RESULTS) < len(progs) and time.time() - t0 < 300:
    time.sleep(0.2)
proc.terminate()
wall = time.time() - t0

got = {e['job_id']: e for e in server.RESULTS}
ok = sum(1 for e in server.RESULTS if e.get('status') == 'OK')
print(f'\nreturned {len(server.RESULTS)}/{len(progs)} envelopes in {wall:.1f}s, '
      f'{ok} status OK')
print('server stats:', json.dumps(server.STATS))

# cross-check every phone result against a host run of the same shard
HOSTBIN = os.path.join(HERE, '..', 'S30_speed_duel', 'bin', 'known', 'fuelrun.host')
agree = 0
for i, p in enumerate(progs):
    e = got.get(f'j{i:04d}')
    if not e:
        continue
    r = sh(HOSTBIN, os.path.join(CORPUS, p), '2000000')
    kv = dict(l.split(None, 1) for l in r.stdout.splitlines() if len(l.split(None, 1)) == 2)
    if (kv.get('fuel_used', '').strip() == e['fuel_used']
            and kv.get('sorted_hash', '').strip() == e['sorted_hash']):
        agree += 1
print(f'phone-over-HTTP vs host: {agree}/{len(got)} byte-identical '
      f'(fuel_used AND sorted_hash)')
json.dump({'envelopes': server.RESULTS, 'stats': server.STATS,
           'agree': agree, 'wall_s': round(wall, 1)},
          open(os.path.join(HERE, 'result.json'), 'w'), indent=1)
