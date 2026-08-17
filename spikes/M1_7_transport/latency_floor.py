#!/usr/bin/env python3
"""What is the lowest achievable per-request latency for OUR pattern?

Our worker long-polls: ask for work, get one job, repeat. So the question is
not "which protocol has the fastest handshake" but "what does a request cost
when the connection is already open, and what does an idle gap cost".

Measures three things on device:
  A  per-request latency on a PERSISTENT connection (the floor)
  B  per-request latency with a fresh connection each time (what we ship today)
  C  first-request latency after an IDLE GAP -- the radio-wake cost, which is
     what a reconnect actually pays on a phone and what 0-RTT cannot remove
"""
import json, os, secrets, statistics as st, subprocess, sys, threading
import http.server
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
os.environ.setdefault('KF_TOKEN', secrets.token_urlsafe(16))
from shardstore import cid_of
import server

def sh(*a): return subprocess.run(a, capture_output=True, text=True, errors='replace')
ip = sh('ipconfig', 'getifaddr', 'en0').stdout.strip()

class KA(server.H):                      # keep-alive permitted
    def _send(self, code, body=b'', ctype='application/octet-stream'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if body: self.wfile.write(body)

small = os.urandom(256)
cid = cid_of(small); server.SHARDS[cid] = small
srv = http.server.ThreadingHTTPServer((ip, 18092), KA)
threading.Thread(target=srv.serve_forever, daemon=True).start()
server.serve(18093, bind=ip)             # production: Connection: close

A = f'-H "Authorization: Bearer {os.environ["KF_TOKEN"]}"'
def times(cmd):
    o = sh('adb', 'shell', cmd).stdout.split()
    return [float(x)*1000 for x in o if x.replace('.', '', 1).isdigit()]

N = 25
ka_urls = ' '.join(f'-o /dev/null http://{ip}:18092/shard/{cid}' for _ in range(N))
persistent = times(f'curl -s {A} -w "%{{time_total}} " {ka_urls}')
fresh_ka   = times(' '.join(f'curl -s {A} -o /dev/null -w "%{{time_total}} " '
                            f'http://{ip}:18092/shard/{cid};' for _ in range(N)))
prod       = times(' '.join(f'curl -s {A} -o /dev/null -w "%{{time_total}} " '
                            f'http://{ip}:18093/shard/{cid};' for _ in range(N)))

print(f'{"case":38} {"median ms":>10} {"p90 ms":>8}')
def row(name, v):
    v = sorted(v)
    if not v: print(f'{name:38} {"FAILED":>10}'); return None
    m, p90 = st.median(v), v[int(len(v)*0.9)-1]
    print(f'{name:38} {m:>10.1f} {p90:>8.1f}')
    return m
m_p = row('A persistent connection (floor)', persistent[1:])   # drop the setup one
m_f = row('B fresh conn, keep-alive server', fresh_ka)
m_x = row('C fresh conn, production server', prod)

print('\nidle-gap cost -- what a reconnect really pays on a phone:')
gaps = []
for gap in (0, 2, 5, 15):
    cmd = (f'sleep {gap}; curl -s {A} -o /dev/null -w "%{{time_total}}\\n" '
           f'http://{ip}:18092/shard/{cid}')
    v = [times(cmd)[0] for _ in range(3)]
    med = st.median(v)
    gaps.append((gap, med))
    print(f'  after {gap:>2}s idle: {med:7.1f} ms')

json.dump({'persistent_ms': m_p, 'fresh_keepalive_ms': m_f,
           'production_ms': m_x, 'idle_gaps': gaps},
          open(os.path.join(HERE, 'latency_floor.json'), 'w'), indent=1)
