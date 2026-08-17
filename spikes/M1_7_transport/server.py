#!/usr/bin/env python3
"""M1.7 — phone-initiated transport. The device always dials.

S8's finding: the DAS bus dials clients back, and a phone cannot accept that —
no stable address, no inbound port, asleep most of the time. So every
connection here is outbound from the device.

Bound to **127.0.0.1 only**. The phone reaches it through `adb reverse
tcp:PORT tcp:PORT`, which forwards a device-local port to the host loopback.
Nothing is exposed on any network interface: this is a real dial-out transport
with zero external surface, which is what MISSION_LOOP §10 requires.

Endpoints, all device-initiated:
  GET  /job?worker=W     long-poll; returns one job or 204 after `timeout`
  GET  /shard/<cid>      fetch shard bytes by CID; 404 if unknown
  POST /result           submit an envelope
  GET  /stats            for the harness, not the device
"""
import json, os, queue, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
from shardstore import cid_of, parse_cid

JOBS = queue.Queue()
SHARDS = {}
RESULTS = []
LOCK = threading.Lock()
STATS = {'polls': 0, 'jobs_out': 0, 'shard_bytes': 0, 'results': 0, 'misses': 0}


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass                                    # quiet; the harness reports

    def _send(self, code, body=b'', ctype='application/octet-stream'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path, _, qs = self.path.partition('?')
        if path == '/job':
            with LOCK:
                STATS['polls'] += 1
            try:
                job = JOBS.get(timeout=float(os.environ.get('KF_POLL', '20')))
            except queue.Empty:
                return self._send(204)
            with LOCK:
                STATS['jobs_out'] += 1
            return self._send(200, json.dumps(job).encode(), 'application/json')

        if path.startswith('/shard/'):
            cid = path[len('/shard/'):]
            data = SHARDS.get(cid)
            if data is None:
                with LOCK:
                    STATS['misses'] += 1
                return self._send(404)
            # serve by CID and verify on the way out: the store is
            # content-addressed, so a mismatch here is our bug, not the device's
            assert cid_of(data) == cid, 'served bytes do not match their CID'
            with LOCK:
                STATS['shard_bytes'] += len(data)
            return self._send(200, data)

        if path == '/stats':
            with LOCK:
                return self._send(200, json.dumps(STATS).encode(),
                                  'application/json')
        return self._send(404)

    def do_POST(self):
        if self.path != '/result':
            return self._send(404)
        n = int(self.headers.get('Content-Length', 0))
        try:
            env = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            return self._send(400)
        with LOCK:
            RESULTS.append(env)
            STATS['results'] += 1
        return self._send(200, b'ok')


def serve(port):
    # 127.0.0.1 ONLY. Never 0.0.0.0 -- binding wide would put a job-dispatch
    # endpoint on the LAN, and nothing here authenticates anything.
    srv = ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
