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
import hmac, json, os, queue, secrets, ssl, subprocess, sys, threading, time
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
    # TCP_NODELAY. Without it, Nagle collides with delayed ACK on a persistent
    # connection and small responses stall ~40 ms: measured 51.9 ms per request
    # against 7.0 ms with it -- i.e. enabling keep-alive WITHOUT this is 3x
    # slower than the fresh connections it replaces.
    disable_nagle_algorithm = True

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
        # Keep-alive is ON. `Connection: close` used to live here as a
        # workaround for okhttp's "unexpected end of stream" -- but that fault
        # was later traced to a MISSING AUTH HEADER, not to connection reuse.
        # The workaround cost 2.5x: fresh connection 17.8 ms vs persistent
        # 7.0 ms (LATENCY_FLOOR.md). Removing it is gated on the app still
        # working, which is the falsifier for this change.
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
                STATS.setdefault('poll_peers', []).append(self.client_address[0])
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
                STATS.setdefault('job_peers', []).append(self.client_address[0])
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
            # Observed by the coordinator, not declared by the worker (A22).
            STATS.setdefault('result_peers', []).append(self.client_address[0])
        return self._send(200, b'ok')


def make_cert(dirpath, ip):
    """Ephemeral self-signed cert for this run only.

    Not a PKI and not trying to be. There is no CA, nothing is installed into a
    trust store, and the key never leaves the workspace or outlives the process
    -- the device pins the public key by hash instead (`curl --pinnedpubkey`),
    which is the right shape when there is exactly one server and it is ours.

    This is transport confidentiality and server identity. It is NOT device
    authentication: pinning proves the phone is talking to OUR coordinator, and
    says nothing about which phone is talking. That remains `operator = 1`.
    """
    key = os.path.join(dirpath, 'kf-key.pem')
    crt = os.path.join(dirpath, 'kf-crt.pem')
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
        '-keyout', key, '-out', crt, '-days', '1',
        '-subj', '/CN=kingfisher-coordinator',
        '-addext', f'subjectAltName=IP:{ip}'], check=True, capture_output=True)
    spki = subprocess.run(
        f"openssl x509 -in {crt} -pubkey -noout | openssl pkey -pubin -outform der | "
        f"openssl dgst -sha256 -binary | openssl base64",
        shell=True, capture_output=True, text=True).stdout.strip()
    return key, crt, spki


def serve(port, bind='127.0.0.1', certfile=None, keyfile=None):
    """Default stays loopback. `bind` is explicit at every call site so that
    putting a job-dispatch endpoint on a network is always a visible decision,
    never a default. Callers that widen it MUST have a token set."""
    if bind != '127.0.0.1' and not os.environ.get('KF_TOKEN'):
        raise RuntimeError(
            'refusing to bind beyond loopback without KF_TOKEN set explicitly')
    srv = ThreadingHTTPServer((bind, port), H)
    if certfile:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(certfile, keyfile)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
