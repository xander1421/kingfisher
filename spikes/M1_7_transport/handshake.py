#!/usr/bin/env python3
"""How many round trips does a connection cost, and what is one worth?

The cellular question needs two numbers: the RTT, and how many round trips a
connection setup takes. Then 0-RTT's saving is (setup_RTTs - 0) * RTT.

ICMP is the wrong instrument for the first: 23.3 ms average from the phone
under WiFi power-save, against a 7.1 ms minimum. A data flow keeps the radio
awake and an ICMP probe does not, so ping measures the idle-radio path.

curl reports the handshake phases directly, on device:
  time_connect     TCP handshake complete
  time_appconnect  TLS handshake complete (0 on plain HTTP)
"""
import json, os, secrets, statistics as st, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(16))
from shardstore import cid_of
import server

def sh(*a): return subprocess.run(a, capture_output=True, text=True, errors='replace')
ip = sh('ipconfig', 'getifaddr', 'en0').stdout.strip()
blob = os.urandom(4 << 10)
cid = cid_of(blob); server.SHARDS[cid] = blob

PLAIN, TLSP = 18086, 18087
server.serve(PLAIN, bind=ip)
certdir = tempfile.mkdtemp(prefix='kf-hs-')
key, crt, spki = server.make_cert(certdir, ip)
server.serve(TLSP, bind=ip, certfile=crt, keyfile=key)
AUTH = f'-H "Authorization: Bearer {os.environ["KF_TOKEN"]}"'
print(f'plain {ip}:{PLAIN}   tls {ip}:{TLSP}')

def probe(scheme, port, extra=''):
    url = f'{scheme}://{ip}:{port}/shard/{cid}'
    cmd = (f'for i in 1 2 3 4 5 6 7; do curl -s -o /dev/null {extra} {AUTH} '
           f'-w "%{{time_connect}} %{{time_appconnect}} %{{time_starttransfer}} '
           f'%{{time_total}}\\n" {url}; done')
    out = sh('adb', 'shell', cmd).stdout.split()
    v = [float(x) for x in out if x.replace('.', '', 1).replace('-', '', 1).isdigit()]
    rows = [v[i:i+4] for i in range(0, len(v) - 3, 4)]
    if not rows: return None
    med = [st.median(c) * 1000 for c in zip(*rows)]
    return dict(connect=med[0], appconnect=med[1], starttransfer=med[2], total=med[3])

p = probe('http', PLAIN)
t = probe('https', TLSP, f'-k --pinnedpubkey sha256//{spki}')
print(f"\n{'phase':>16} {'plain ms':>10} {'tls ms':>10}")
for k in ('connect', 'appconnect', 'starttransfer', 'total'):
    print(f'{k:>16} {p[k]:>10.1f} {t[k]:>10.1f}')

tcp = p['connect']
tls_extra = t['appconnect'] - t['connect'] if t['appconnect'] else 0.0
print(f'\nTCP handshake        {tcp:6.1f} ms   (1 round trip)')
print(f'TLS handshake        {tls_extra:6.1f} ms   ({tls_extra/max(tcp,1e-9):.1f} x the TCP RTT)')
print(f'total setup          {tcp + tls_extra:6.1f} ms')
print(f'\nimplied one-way RTT  {tcp:6.1f} ms  (TCP handshake is 1 RTT)')
for rtt in (30, 50, 80):
    rtts = (tcp + tls_extra) / max(tcp, 1e-9)
    print(f'  at {rtt:>3} ms RTT: setup ~= {rtts*rtt:6.0f} ms  -> 0-RTT would save that')
json.dump({'plain': p, 'tls': t, 'tcp_ms': tcp, 'tls_extra_ms': tls_extra},
          open(os.path.join(HERE, 'handshake.json'), 'w'), indent=1)
