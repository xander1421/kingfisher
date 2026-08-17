#!/usr/bin/env python3
"""M1.7c — the transfer curve over real WiFi.

M1.5b measured `63.2 ms fixed + 37.9 MB/s marginal` over adb/USB, and ~47 ms of
that fixed cost was three adb process spawns in the harness (A18/A24). That
split is what deferred QUIC, so it needs a value rather than a shape.

Timing is done ON DEVICE with curl's own `%{time_total}`, so adb is not in the
measurement at all -- only in launching it.
"""
import json, os, secrets, statistics as st, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(24))
from shardstore import cid_of
import server

PORT = int(os.environ.get('KF_PORT', '18081'))
def sh(*a): return subprocess.run(a, capture_output=True, text=True)
ip = sh('ipconfig', 'getifaddr', 'en0').stdout.strip() or sh('ipconfig','getifaddr','en1').stdout.strip()

sizes = [4, 16, 64, 256, 1024, 4096, 16384]          # KiB
cids = {}
for k in sizes:
    d = os.urandom(k << 10)                          # incompressible
    cids[k] = cid_of(d)
    server.SHARDS[cids[k]] = d
server.serve(PORT, bind=ip)
print(f'coordinator {ip}:{PORT}, {len(sizes)} blobs')
print(f"{'KiB':>7} {'ms':>9} {'MB/s':>8}   (median of 5, on-device curl timing)")

rows = []
for k in sizes:
    url = f'http://{ip}:{PORT}/shard/{cids[k]}'
    cmd = (f'for i in 1 2 3 4 5; do curl -s -o /dev/null '
           f'-H "Authorization: Bearer {os.environ["KF_TOKEN"]}" '
           f'-w "%{{time_total}}\\n" {url}; done')
    out = sh('adb', 'shell', cmd).stdout.split()
    ts = sorted(float(x) * 1000 for x in out if x.replace('.', '', 1).isdigit())
    if not ts:
        print(f'{k:>7} FAILED'); continue
    ms = ts[len(ts)//2]
    rows.append((k, ms))
    print(f'{k:>7} {ms:9.1f} {(k/1024)/(ms/1000):8.1f}')

if len(rows) >= 2:
    (k1, m1), (k2, m2) = rows[-2], rows[-1]
    bw = ((k2 - k1) / 1024) / ((m2 - m1) / 1000)
    ov = m1 - (k1 / 1024) / bw * 1000
    print(f'\nfit on the two largest: {ov:.1f} ms fixed + {bw:.1f} MB/s marginal')
    print(f'adb/USB was:            63.2 ms fixed + 37.9 MB/s marginal')
    for mb, lbl in ((6.41, 'B=32'), (34.83, 'B=1')):
        print(f'  {lbl:5} {mb:5.2f} MB -> WiFi {ov + mb/bw*1000:7.0f} ms  '
              f'| USB {63.2 + mb/37.9*1000:7.0f} ms')
    json.dump({'rows': rows, 'fixed_ms': round(ov,1), 'marginal_mbs': round(bw,1)},
              open(os.path.join(HERE, 'xfer_lan.json'), 'w'), indent=1)
