#!/usr/bin/env python3
"""Does plain-TCP keep-alive capture most of what QUIC would buy?

Stated as a falsifier in LAN_RESULT.md and left unrun. If reuse recovers most of
the per-request cost, QUIC's 0-RTT argument is largely redundant on this path
and the deferral holds on its own merits. If it does not, QUIC comes back.

One curl invocation with N URLs reuses the connection; N invocations do not.
Both timed ON DEVICE, so the comparison is like for like and adb is excluded.
"""
import json, os, secrets, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(24))
from shardstore import cid_of
import server

PORT = int(os.environ.get('KF_PORT', '18082'))
def sh(*a):
    return subprocess.run(a, capture_output=True, text=True,
                          errors='replace')
ip = sh('ipconfig','getifaddr','en0').stdout.strip() or sh('ipconfig','getifaddr','en1').stdout.strip()

N = 20
for size_kib in (4, 64, 1024):
    cids = []
    for i in range(N):
        d = os.urandom(size_kib << 10)
        c = cid_of(d); server.SHARDS[c] = d; cids.append(c)
    globals().setdefault('SETS', {})[size_kib] = cids

server.serve(PORT, bind=ip)
AUTH = f'-H "Authorization: Bearer {os.environ["KF_TOKEN"]}"'
print(f'coordinator {ip}:{PORT}, {N} blobs per size, on-device timing')
print(f"{'KiB':>6} {'fresh ms':>10} {'reuse ms':>10} {'saved':>8} {'per-req saved':>14}")

rows = []
for size_kib, cids in SETS.items():
    urls = ' '.join(f'http://{ip}:{PORT}/shard/{c}' for c in cids)
    # N separate connections
    # toybox `date +%s%N` does not expand %N reliably -- it produced negative
    # deltas at the largest size. Use curl's own %{time_total}, summed across
    # URLs: for a reused connection connect-time collapses toward zero, which
    # is exactly the quantity under test.
    def run(cmd):
        out = sh('adb', 'shell', cmd).stdout.split()
        vals = [float(x) for x in out if x.replace('.', '', 1).isdigit()]
        return round(sum(vals) * 1000, 1) if vals else None

    fresh_cmd = (f'for u in {urls}; do curl -s {AUTH} -o /dev/null '
                 f'-w "%{{time_total}}\n" $u; done')
    reuse_cmd = (f'curl -s {AUTH} -w "%{{time_total}}\n" '
                 f'{" ".join("-o /dev/null " + u for u in urls.split())}')
    fresh = [run(fresh_cmd) for _ in range(3)]
    reuse = [run(reuse_cmd) for _ in range(3)]
    fresh = [x for x in fresh if x]; reuse = [x for x in reuse if x]
    if not fresh or not reuse:
        print(f'{size_kib:>6}  FAILED'); continue
    f_ms, r_ms = sorted(fresh)[1], sorted(reuse)[1]
    saved = 100*(f_ms-r_ms)/max(f_ms,1)
    per = (f_ms-r_ms)/N
    rows.append(dict(kib=size_kib, fresh_ms=f_ms, reuse_ms=r_ms,
                     saved_pct=round(saved,1), per_req_saved_ms=round(per,1)))
    print(f'{size_kib:>6} {f_ms:>10} {r_ms:>10} {saved:>7.1f}% {per:>13.1f}')

json.dump(rows, open(os.path.join(HERE,'keepalive.json'),'w'), indent=1)
print('\nfalsifier: if reuse saves most of the per-request cost, QUIC 0-RTT is')
print('largely redundant on this path. If it saves little, QUIC returns.')
