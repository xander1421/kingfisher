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
  GET  /job?worker=W     long-poll; one job, or an EMPTY 200 after `timeout`
  GET  /shard/<cid>      fetch shard bytes by CID; 404 if unknown
  POST /result           submit an envelope
  GET  /stats            for the harness, not the device
"""
import hmac, json, os, queue, secrets, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
from shardstore import cid_of, parse_cid

# Shared-secret bearer token. Generated per run unless KF_TOKEN is set.
#
# This is NOT a substitute for the attestation root the `operator` domain axis
# needs -- it authenticates *the fleet*, not *a device*, so it cannot tell two
# workers apart and does nothing about collusion. What it does is stop an
# arbitrary host on the LAN from pulling jobs or posting envelopes, which
# becomes possible the moment this binds beyond loopback.
TOKEN = os.environ.get('KF_TOKEN') or secrets.token_urlsafe(24)

JOBS = queue.Queue()
SHARDS = {}
RESULTS = []
LOCK = threading.Lock()
STATS = {'polls': 0, 'jobs_out': 0, 'shard_bytes': 0, 'results': 0,
         'misses': 0, 'unauthorised': 0}


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass                                    # quiet; the harness reports

    def _send(self, code, body=b'', ctype='application/octet-stream'):
        self.send_response(code)
        # RFC 9110: a 204 MUST NOT carry a body, and Android's HttpURLConnection
        # (okhttp) throws "unexpected end of stream" when one arrives with
        # Content-Length. curl tolerates it, which is why this only showed up
        # once the real app polled -- the shell agent never noticed.
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        # No keep-alive. `BaseHTTPRequestHandler` under HTTP/1.1 advertises
        # persistent connections but drops them between long-polls, so okhttp
        # reuses a pooled socket the server has already closed and reports
        # "unexpected end of stream" -- instantly, and only on the SECOND poll.
        # That is why a run whose first poll had work appeared to succeed.
        self.send_header('Connection', 'close')
        self.close_connection = True
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _authed(self):
        got = self.headers.get('Authorization', '')
        want = 'Bearer ' + TOKEN
        # constant-time: a length/prefix-leaking compare on a LAN endpoint is
        # a real oracle, not a theoretical one
        if hmac.compare_digest(got, want):
            return True
        with LOCK:
            STATS['unauthorised'] = STATS.get('unauthorised', 0) + 1
        self._send(401, b'unauthorised')
        return False

    def do_GET(self):
        if not self._authed():
            return
        path, _, qs = self.path.partition('?')
        if path == '/job':
            with LOCK:
                STATS['polls'] += 1
            try:
                job = JOBS.get(timeout=float(os.environ.get('KF_POLL', '20')))
            except queue.Empty:
                # 200 with an EMPTY body, not 204. Android's HttpURLConnection
                # (okhttp) throws "unexpected end of stream" on a 204 whether or
                # not it carries Content-Length; curl accepts both, which is why
                # the shell agent never saw it and the real app failed instantly.
                # An empty 200 is unambiguous to both clients.
                return self._send(200, b'')
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
        if not self._authed():
            return
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


def serve(port, bind='127.0.0.1'):
    """Default stays loopback. `bind` is explicit at every call site so that
    putting a job-dispatch endpoint on a network is always a visible decision,
    never a default. Callers that widen it MUST have a token set."""
    if bind != '127.0.0.1' and not os.environ.get('KF_TOKEN'):
        raise RuntimeError(
            'refusing to bind beyond loopback without KF_TOKEN set explicitly')
    srv = ThreadingHTTPServer((bind, port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
