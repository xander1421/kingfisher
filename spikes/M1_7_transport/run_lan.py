#!/usr/bin/env python3
"""M1.7b — the phone dials the coordinator over REAL WiFi, not adb loopback.

Every transport number so far was measured over `adb reverse`, i.e. USB. That
makes them shapes, not values: no RTT, no loss, no radio. This binds the
coordinator to the host's LAN address and has the phone reach it over WiFi.

EXPOSURE, stated plainly. This puts a job-dispatch endpoint on the local
network. Mitigations, in order of how much they actually buy:
  - a bearer token is REQUIRED; `server.serve()` refuses a non-loopback bind
    without `KF_TOKEN` set (control verified: it raises).
  - the bind is to the specific LAN address, not 0.0.0.0.
  - the server runs only for the duration of this script.
What that does NOT buy: the token authenticates *the fleet*, not *a device*, so
it cannot distinguish two workers and does nothing about collusion. It is not
the attestation root `operator=1` needs. There is still no TLS, so the token
crosses the LAN in clear text — item (2) on the queue.
"""
import json, os, secrets, socket, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(24))
from shardstore import cid_of
import bansurface, server

PORT = int(os.environ.get('KF_PORT', '18080'))
CORPUS = os.path.join(HERE, '..', 'S57_hyperon_corpus', 'corpus')
BIN = os.path.join(HERE, '..', 'S30_speed_duel', 'bin', 'known', 'fuelrun.android')
DEV = '/data/local/tmp/m17lan'


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def host_lan_ip():
    for iface in ('en0', 'en1'):
        r = sh('ipconfig', 'getifaddr', iface).stdout.strip()
        if r:
            return r
    raise SystemExit('no LAN address found')


n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
ip = host_lan_ip()
phone_net = sh('adb', 'shell', 'ip route get 1.1.1.1').stdout
if ip.rsplit('.', 1)[0] not in phone_net:
    raise SystemExit(f'phone is not on the host subnet ({ip}): {phone_net.strip()[:60]}')

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

import tempfile
certdir = tempfile.mkdtemp(prefix='kf-tls-')
key, crt, spki = server.make_cert(certdir, ip)
server.serve(PORT, bind=ip, certfile=crt, keyfile=key)
SCHEME = 'https'
print(f'coordinator on {ip}:{PORT}  (LAN bind, TLS, token required)')
print(f'  pinned SPKI sha256: {spki}')
print(f'{len(progs)} jobs queued')

sh('adb', 'shell', f'mkdir -p {DEV}/shards')
sh('adb', 'push', BIN, f'{DEV}/fuelrun')
sh('adb', 'shell', f'chmod +x {DEV}/fuelrun')
sh('adb', 'push', os.path.join(HERE, 'agent.sh'), f'{DEV}/agent.sh')
sh('adb', 'shell', f'chmod +x {DEV}/agent.sh')
sh('adb', 'shell', f'rm -rf {DEV}/shards; mkdir -p {DEV}/shards')

# CONTROL: an unauthenticated request from the phone must be refused
# CONTROL 1: no token -> 401 (pin supplied, so TLS itself must succeed)
bad = sh('adb', 'shell',
         f'curl -s -m 8 -o /dev/null -k --pinnedpubkey sha256//{spki} '
         f'-w "%{{http_code}}" https://{ip}:{PORT}/stats')
print(f'control A, no token:        HTTP {bad.stdout.strip() or "(fail)"} (expect 401)')
# CONTROL 2: WRONG pin must be refused by TLS before auth is even reached
wrongpin = 'A' * 43 + '='
bad2 = sh('adb', 'shell',
          f'curl -s -m 8 -o /dev/null -k --pinnedpubkey sha256//{wrongpin} '
          f'-w "%{{http_code}}" https://{ip}:{PORT}/stats')
print(f'control B, wrong pin:       HTTP {bad2.stdout.strip() or "(refused)"} (expect refused)')
# CONTROL 3: plain HTTP against a TLS port must fail
bad3 = sh('adb', 'shell',
          f'curl -s -m 8 -o /dev/null -w "%{{http_code}}" http://{ip}:{PORT}/stats')
print(f'control C, cleartext:       HTTP {bad3.stdout.strip() or "(refused)"} (expect refused)')

t0 = time.time()
env = (f'KF_DIR={DEV} KF_BASE=https://{ip}:{PORT} KF_PIN={spki} '
       f'KF_TOKEN={os.environ["KF_TOKEN"]} KF_MAXIDLE=2')
proc = subprocess.Popen(['adb', 'shell', f'{env} sh {DEV}/agent.sh'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
while len(server.RESULTS) < len(progs) and time.time() - t0 < 300:
    time.sleep(0.2)
proc.terminate()
wall = time.time() - t0

ok = sum(1 for e in server.RESULTS if e.get('status') == 'OK')
print(f'\nover WiFi: {len(server.RESULTS)}/{len(progs)} envelopes in {wall:.1f}s, {ok} OK')
print('server stats:', json.dumps(server.STATS))
json.dump({'lan_ip': ip, 'tls': True, 'spki_sha256': spki, 'envelopes': server.RESULTS, 'stats': server.STATS,
           'wall_s': round(wall, 1)},
          open(os.path.join(HERE, 'result_lan.json'), 'w'), indent=1)
