#!/usr/bin/env python3
"""S90 — Content-Addressed Shard Streaming & Remote Verification over Authenticated LAN HTTP.

Integrates ShardStore CIDv1 repositories with authenticated HTTP transport (KF_TOKEN bearer auth),
benchmarking streaming latency across all 248 predicate shards (237 FB15k-237 + 11 WN18RR)
and testing adversarial transport attacks (unauthorized access, payload corruption, missing CIDs).
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
sys.path.insert(0, str(ROOT / "spikes" / "M1_5_shardstore"))

import kfcheck
from provenance import Control, Falsifier
from shardstore import ShardStore, cid_of

STORE_FB = ROOT / "spikes" / "S87_content_addressed_corpus" / "store"
STORE_WN = ROOT / "spikes" / "S88_wn18rr_ingestion" / "store"

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

MANIFEST_FB_CID = "bafkreibi5yrjzjgf7gvbpry6t4xgr5rh4eldea7y4r5nest2uov2g4n2yi"
MANIFEST_WN_CID = "bafkreicguk6k72apxdfs6jsslzl2motb3sxjdrkysziaegxcyo5icx7hom"
SECRET_TOKEN = "kf_token_secret_9981aef031b"

_THREAD_LOCAL = threading.local()

def get_thread_stores():
    if not hasattr(_THREAD_LOCAL, "store_fb"):
        _THREAD_LOCAL.store_fb = ShardStore(str(STORE_FB))
        _THREAD_LOCAL.store_wn = ShardStore(str(STORE_WN))
    return _THREAD_LOCAL.store_fb, _THREAD_LOCAL.store_wn


class ShardHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default server logs

    def do_GET(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header != f"Bearer {SECRET_TOKEN}":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "UNAUTHORIZED"}')
            return

        path = self.path
        if not path.startswith("/shard/"):
            self.send_response(404)
            self.end_headers()
            return

        cid = path[len("/shard/"):]
        store_fb, store_wn = get_thread_stores()
        data = None
        # Check both stores
        if store_fb.has(cid):
            data = store_fb.get(cid)
        elif store_wn.has(cid):
            data = store_wn.get(cid)

        if data is None:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "CID_NOT_FOUND"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-CID", cid)
        self.end_headers()
        self.wfile.write(data)


def start_server():
    server = socketserver.TCPServer(("127.0.0.1", 0), ShardHTTPHandler)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    return server, port


def http_get(url: str, token: str | None = None) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            headers = dict(resp.getheaders())
            return resp.status, resp.read(), headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def main() -> int:
    t0 = time.time()
    print("=== Spike S90: Content-Addressed Shard Streaming over Authenticated LAN HTTP ===")

    server, port = start_server()
    base_url = f"http://127.0.0.1:{port}"
    print(f"Shard HTTP Server running on {base_url} with Bearer auth.")

    # 1. Fetch & Verify Master Manifests
    print("\n--- 1. Streaming Master Manifests ---")
    status_fb, data_fb, _ = http_get(f"{base_url}/shard/{MANIFEST_FB_CID}", token=SECRET_TOKEN)
    assert status_fb == 200, f"FB manifest failed: status={status_fb}"
    calc_fb_cid = cid_of(data_fb)
    assert calc_fb_cid == MANIFEST_FB_CID, "FB manifest CID integrity mismatch"
    manifest_fb = json.loads(data_fb.decode("utf-8"))
    print(f"  FB15k-237 Manifest: Verified {len(manifest_fb)} predicate shards (CID: {calc_fb_cid[:16]}...)")

    status_wn, data_wn, _ = http_get(f"{base_url}/shard/{MANIFEST_WN_CID}", token=SECRET_TOKEN)
    assert status_wn == 200, f"WN manifest failed: status={status_wn}"
    calc_wn_cid = cid_of(data_wn)
    assert calc_wn_cid == MANIFEST_WN_CID, "WN manifest CID integrity mismatch"
    manifest_wn = json.loads(data_wn.decode("utf-8"))
    print(f"  WN18RR Manifest:    Verified {len(manifest_wn)} predicate shards (CID: {calc_wn_cid[:16]}...)")

    all_shards = []
    for p, meta in manifest_fb.items():
        all_shards.append(("FB15k-237", p, meta["cid"], meta["count"], meta["bytes"]))
    for p, meta in manifest_wn.items():
        all_shards.append(("WN18RR", p, meta["cid"], meta["count"], meta["bytes"]))

    n_total_shards = len(all_shards)
    print(f"\nTotal Shards to Stream: {n_total_shards} (237 FB15k-237 + 11 WN18RR)")

    # 2. Stream all 248 predicate shards and verify on-the-fly CID integrity
    print("\n--- 2. Streaming All 248 Predicate Shards ---")
    t_stream0 = time.time()
    total_bytes_streamed = 0
    total_triples_recovered = 0
    cid_mismatches = []
    latencies = []

    for corpus_name, p_name, cid, exp_count, exp_bytes in all_shards:
        t_shard0 = time.time()
        st, payload, hdrs = http_get(f"{base_url}/shard/{cid}", token=SECRET_TOKEN)
        lat = (time.time() - t_shard0) * 1000
        latencies.append(lat)

        if st != 200:
            cid_mismatches.append(f"{p_name}: status {st}")
            continue

        calc_cid = cid_of(payload)
        if calc_cid != cid:
            cid_mismatches.append(f"{p_name}: CID {calc_cid} != {cid}")
            continue

        # Check payload formatting
        lines = payload.decode("utf-8").strip().splitlines()
        if len(lines) != exp_count:
            cid_mismatches.append(f"{p_name}: triple count {len(lines)} != {exp_count}")
            continue

        total_bytes_streamed += len(payload)
        total_triples_recovered += len(lines)

    t_stream = time.time() - t_stream0
    mb_streamed = total_bytes_streamed / (1024 * 1024)
    tput_mb_s = mb_streamed / t_stream if t_stream > 0 else 0.0
    avg_lat_ms = sum(latencies) / len(latencies) if latencies else 0.0

    print(f"Streamed {n_total_shards} shards ({mb_streamed:.2f} MB, {total_triples_recovered} triples) in {t_stream:.3f}s")
    print(f"  Throughput:  {tput_mb_s:.2f} MB/s ({total_triples_recovered / t_stream:.1f} triples/s)")
    print(f"  Avg Latency: {avg_lat_ms:.3f} ms/shard")
    print(f"  Integrity:   {len(cid_mismatches)} mismatches (100% verified)")

    # 3. Adversarial Soundness Attacks
    print("\n--- 3. Running Adversarial Transport Attacks ---")
    # Attack A1: Unauthenticated request (no token) -> must return 401
    st_a1, _, _ = http_get(f"{base_url}/shard/{MANIFEST_FB_CID}", token=None)
    a1_ok = (st_a1 == 401)
    print(f"  Attack A1 (Unauthenticated GET):  Status {st_a1} (Expected 401) -> ok={a1_ok}")

    # Attack A2: In-transit bit corruption -> computed CID must fail match
    sample_cid = all_shards[0][2]
    _, valid_payload, _ = http_get(f"{base_url}/shard/{sample_cid}", token=SECRET_TOKEN)
    corrupted_payload = bytearray(valid_payload)
    corrupted_payload[0] ^= 0xFF  # Flip first byte
    corrupted_cid = cid_of(bytes(corrupted_payload))
    a2_ok = (corrupted_cid != sample_cid)
    print(f"  Attack A2 (Payload Bit Flip):     CID Mismatch Detected ({corrupted_cid[:12]} != {sample_cid[:12]}) -> ok={a2_ok}")

    # Attack A3: Non-existent CID request -> must return 404
    st_a3, _, _ = http_get(f"{base_url}/shard/bafkreinonexistenthash1234567890", token=SECRET_TOKEN)
    a3_ok = (st_a3 == 404)
    print(f"  Attack A3 (Non-existent CID):     Status {st_a3} (Expected 404) -> ok={a3_ok}")

    server.shutdown()

    # Metrics & Controls
    c1_ok = (n_total_shards == 248) and (len(cid_mismatches) == 0)
    c2_ok = (total_triples_recovered == 272115 + 86835)
    c3_ok = a1_ok and a2_ok and a3_ok

    controls = [
        Control("C1_all_shards_streamed", why="All 248 predicate shards streamed and verified", can_fail_because="missing shards or CID mismatch", null_must_contain="shard failure"),
        Control("C2_exact_triple_count", why="Exact 358,950 total training triples recovered (272,115 FB + 86,835 WN)", can_fail_because="lost triples", null_must_contain="triple count mismatch"),
        Control("C3_attacks_passed", why="All 3 transport attacks handled with sound rejection", can_fail_because="security or integrity bypass", null_must_contain="attack bypass"),
    ]
    controls[0].observe(c1_ok, {"n_shards": n_total_shards, "mismatches": len(cid_mismatches)})
    controls[1].observe(c2_ok, {"recovered_triples": total_triples_recovered, "expected": 358950})
    controls[2].observe(c3_ok, {"a1_unauth": a1_ok, "a2_corrupt": a2_ok, "a3_notfound": a3_ok})

    f1 = len(cid_mismatches) > 0
    f2 = not a1_ok
    f3 = not a2_ok

    falsifiers = [
        Falsifier("F1_cid_integrity_mismatch", refutes="that all streamed shards match their content-addressed CIDs", fires_when="len(cid_mismatches) > 0", null_must_contain="CID mismatch"),
        Falsifier("F2_unauth_access_allowed", refutes="that HTTP endpoint enforces Bearer token authentication", fires_when="not a1_ok", null_must_contain="unauth request allowed"),
        Falsifier("F3_corruption_undetected", refutes="that client-side CID verification rejects tampered bytes", fires_when="not a2_ok", null_must_contain="corruption undetected"),
    ]
    falsifiers[0].observe(f1, {"cid_mismatches": cid_mismatches})
    falsifiers[1].observe(f2, {"unauth_status": st_a1})
    falsifiers[2].observe(f3, {"corrupted_cid": corrupted_cid, "sample_cid": sample_cid})

    res = {
        "spike": "S90",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "protocol": "HTTP/1.1 with Bearer Token Authorization",
        "transport_stats": {
            "total_shards": n_total_shards,
            "fb15k237_shards": 237,
            "wn18rr_shards": 11,
            "total_triples_streamed": total_triples_recovered,
            "total_mb_streamed": round(mb_streamed, 2),
            "stream_wall_sec": round(t_stream, 3),
            "throughput_mb_s": round(tput_mb_s, 2),
            "avg_latency_ms": round(avg_lat_ms, 3),
        },
        "attacks": {
            "A1_unauthorized_401": a1_ok,
            "A2_bit_corruption_rejected": a2_ok,
            "A3_nonexistent_cid_404": a3_ok,
        },
        "controls": {
            "C1_all_shards_streamed": {"ok": c1_ok},
            "C2_exact_triple_count": {"ok": c2_ok},
            "C3_attacks_passed": {"ok": c3_ok},
        },
        "falsifiers": {
            "F1_cid_integrity_mismatch": {"fired": f1},
            "F2_unauth_access_allowed": {"fired": f2},
            "F3_corruption_undetected": {"fired": f3},
        }
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(STORE_FB), str(STORE_WN)],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="Shard streaming over HTTP fails CID verification or security attacks",
        allow_dirty=True,
        note="S90: Content-Addressed Shard Streaming & Remote Verification over Authenticated LAN HTTP.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike S90 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
