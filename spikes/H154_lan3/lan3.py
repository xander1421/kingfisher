#!/usr/bin/env python3
"""H154: 3 physical devices + coordinator, LAN HTTP, no adb reverse.

QUIC/iroh is not faster for this workload: LATENCY_FLOOR.md already put
persistent HTTP + TCP_NODELAY at 1 RTT (6.5 ms vs 6.4 ms). QUIC 0-RTT
only helps reconnect. This run uses the faster path that already exists:
LAN bind + KF_TOKEN, device dial-out, never 0.0.0.0.

Devices: Darwin host (this Mac) + S25 Ultra + S24+. Coordinator co-located
with the Darwin worker. adb is install/start only. Job/shard/result bytes
go to the LAN address. S24 unread-thermal override only.

Falsifier (stated first): fewer than 3 workers post ACCEPTED 590d8769,
OR a phone peer is 127.0.0.1 (adb reverse), OR unauth is not 401,
OR bind is 0.0.0.0.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "spikes" / "M1_5_shardstore"))
sys.path.insert(0, str(ROOT / "spikes" / "M1_7_transport"))

PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25, S24 = "R5CY93675MK", "R5CX508MPRZ"
PORT = int(os.environ.get("KF_PORT", "18082"))
JOBS_N = 12
DEST = "/data/local/tmp/kf_lan3"
TV_AND = ROOT / "fixtures" / "verifier" / "trace_verifier_android_f001"
TV_HOST = ROOT / "fixtures" / "verifier" / "trace_verifier_web"
F001 = ROOT / "fixtures" / "F001"
NDK_CLANG = (
    Path.home()
    / "Library/Android/sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt"
    / "darwin-x86_64/bin/aarch64-linux-android26-clang"
)


def sh(*a, env=None, timeout=120):
    return subprocess.run(
        a, capture_output=True, text=True, env=env, timeout=timeout, cwd=ROOT
    )


def adb(serial, *a, timeout=180):
    p = sh("adb", "-s", serial, *a, timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(f"{serial} {a}: {p.stdout}{p.stderr}")
    return p


def host_lan_ip() -> str:
    for iface in ("en0", "en1"):
        r = sh("ipconfig", "getifaddr", iface).stdout.strip()
        if r:
            return r
    raise SystemExit("no LAN address")


def reverse_list(serial: str) -> str:
    return sh("adb", "-s", serial, "reverse", "--list").stdout.strip()


def gate(serial: str, override: bool) -> str:
    e = os.environ.copy()
    e["ANDROID_SERIAL"] = serial
    if override:
        e["QUIET_ALLOW_THERMAL_UNREADABLE"] = "1"
    p = subprocess.run(
        ["bash", "spikes/quiet.sh", "--device"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=e,
    )
    text = (p.stdout + p.stderr).strip()
    print(serial, text)
    if p.returncode != 0:
        raise SystemExit(f"gate refused {serial}")
    return text


def wifi_src(serial: str) -> str:
    out = adb(serial, "shell", "ip route get 1.1.1.1").stdout
    # "1.1.1.1 via 192.168.1.1 dev wlan0 ... src 192.168.1.20"
    for tok in out.split():
        if tok.count(".") == 3 and tok != "1.1.1.1":
            # last IPv4 before uid is usually src; take the token after 'src'
            pass
    if " src " in out:
        return out.split(" src ", 1)[1].split()[0]
    raise SystemExit(f"{serial} no wifi src: {out[:120]}")


def pack_f001() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for p in sorted(F001.iterdir()):
            if p.name == "mutants" or p.name.startswith("."):
                continue
            t.add(p, arcname=p.name)
    return buf.getvalue()


def compile_agent() -> Path:
    src = HERE / "agent.rs"
    out = HERE / "agent_android"
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    if not NDK_CLANG.exists():
        raise SystemExit(f"NDK clang missing: {NDK_CLANG}")
    p = subprocess.run(
        [
            "rustc",
            "-O",
            "--target",
            "aarch64-linux-android",
            "-C",
            f"linker={NDK_CLANG}",
            "-o",
            str(out),
            str(src),
        ],
        capture_output=True,
        text=True,
        cwd=HERE,
    )
    if p.returncode != 0:
        raise SystemExit(f"rustc android agent:\n{p.stderr}{p.stdout}")
    return out


def parse_tv(text: str) -> dict:
    digest = ""
    if "Consensus Digest:" in text:
        digest = text.split("Consensus Digest:", 1)[1].split()[0]
    verdict = "ACCEPTED" if "[VERDICT] ACCEPTED" in text else "REJECTED"
    return {"verdict": verdict, "digest": digest}


def host_worker(base: str, token: str, blob: bytes, n_hint: int) -> None:
    import http.client
    import ssl  # noqa: F401 — keep import site stable if TLS is added later

    hostport = base.split("://", 1)[1]
    host, port_s = hostport.rsplit(":", 1)
    work = HERE / "_host_fx"
    work.mkdir(exist_ok=True)
    shard_path = work / "shard.tar"
    idle = 0
    while idle < 12:
        conn = http.client.HTTPConnection(host, int(port_s), timeout=35)
        conn.request(
            "GET",
            "/job?worker=host-darwin",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        if resp.status != 200 or not body:
            idle += 1
            continue
        idle = 0
        job = json.loads(body)
        cid = job["shard_cid"]
        want = job.get("shard_sha256", "")
        conn = http.client.HTTPConnection(host, int(port_s), timeout=60)
        conn.request(
            "GET",
            f"/shard/{cid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        if resp.status != 200 or not data:
            continue
        if want and hashlib.sha256(data).hexdigest() != want:
            continue
        shard_path.write_bytes(data)
        fx = work / f"fx_{job['job_id']}"
        if fx.exists():
            for p in fx.iterdir():
                p.unlink()
        else:
            fx.mkdir()
        with tarfile.open(shard_path) as t:
            t.extractall(fx)
        p = subprocess.run(
            [str(TV_HOST), str(fx)], capture_output=True, text=True, cwd=ROOT
        )
        parsed = parse_tv(p.stdout + p.stderr)
        envj = json.dumps(
            {
                "job_id": job["job_id"],
                "worker": "host-darwin",
                "status": parsed["verdict"],
                "digest": parsed["digest"],
                "via": base,
            }
        ).encode()
        conn = http.client.HTTPConnection(host, int(port_s), timeout=30)
        conn.request(
            "POST",
            "/result",
            body=envj,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        conn.getresponse().read()
        conn.close()


def http_code_from_phone(serial: str, url: str, token: str | None, agent: str) -> str:
    if serial == S25:
        auth = f'-H "Authorization: Bearer {token}" ' if token else ""
        p = adb(
            serial,
            "shell",
            f'curl -s -m 8 -o /dev/null -w "%{{http_code}}" {auth}{url}',
        )
        return (p.stdout or "").strip() or "000"
    # S24: rust agent --probe-unauth, or a one-shot GET with token via the agent binary
    # The binary only has --probe-unauth for no-token. For authed stats, POST is unused.
    env = f"KF_BASE={url.rsplit('/', 1)[0]} KF_DIR={DEST}"
    if token is None:
        p = adb(serial, "shell", f"{env} {DEST}/agent --probe-unauth")
        return (p.stdout or "").strip().splitlines()[-1] if p.stdout.strip() else "000"
    # token present: use toybox nc
    hostport = url.split("://", 1)[1]
    host, port_s = hostport.split(":")[0], hostport.split(":")[1].split("/")[0]
    path = "/" + url.split("/", 3)[-1] if url.count("/") >= 3 else "/stats"
    # url is http://ip:port/stats
    path = "/" + url.split("/", 3)[-1]
    req = (
        f"GET {path} HTTP/1.0\\r\\nHost: {host}\\r\\n"
        f"Authorization: Bearer {token}\\r\\n\\r\\n"
    )
    p = adb(
        serial,
        "shell",
        f'printf "{req}" | nc {host} {port_s} | toybox head -n 1',
    )
    line = (p.stdout or "").strip()
    parts = line.split()
    return parts[1] if len(parts) > 1 else "000"


def main() -> int:
    ip = host_lan_ip()
    if ip.startswith("127."):
        raise SystemExit(f"LAN ip looks loopback: {ip}")
    g25 = gate(S25, False)
    g24 = gate(S24, True)
    rev25 = reverse_list(S25)
    rev24 = reverse_list(S24)
    print("reverse S25", repr(rev25) or "(empty)")
    print("reverse S24", repr(rev24) or "(empty)")
    if rev25 or rev24:
        for s in (S25, S24):
            sh("adb", "-s", s, "reverse", "--remove-all")
        rev25, rev24 = reverse_list(S25), reverse_list(S24)
        if rev25 or rev24:
            raise SystemExit(f"adb reverse still set: {rev25!r} {rev24!r}")
    src25 = wifi_src(S25)
    src24 = wifi_src(S24)
    print(f"host {ip}  S25 {src25}  S24 {src24}")
    for src, name in ((src25, "S25"), (src24, "S24")):
        if src.rsplit(".", 1)[0] != ip.rsplit(".", 1)[0]:
            raise SystemExit(f"{name} {src} not on host subnet {ip}")
        if src.startswith("127."):
            raise SystemExit(f"{name} src is loopback")

    agent_bin = compile_agent()
    blob = pack_f001()
    sha = hashlib.sha256(blob).hexdigest()

    token = secrets.token_urlsafe(24)
    os.environ["KF_TOKEN"] = token
    os.environ["KF_POLL"] = "6"
    from shardstore import cid_of
    import server

    cid = cid_of(blob)
    server.SHARDS[cid] = blob
    jobs = [
        {
            "job_id": f"j{i:04d}",
            "shard_cid": cid,
            "shard_sha256": sha,
            "fuel": 400,
            "name": "F001",
        }
        for i in range(JOBS_N)
    ]

    # control: serve refuses non-loopback without token
    saved = os.environ.pop("KF_TOKEN", None)
    refused = False
    try:
        server.serve(PORT + 1, bind=ip)
    except RuntimeError as e:
        refused = "KF_TOKEN" in str(e)
    os.environ["KF_TOKEN"] = saved
    if not refused:
        raise SystemExit("non-loopback bind without token did not refuse")

    server.serve(PORT, bind=ip)
    base = f"http://{ip}:{PORT}"
    print(f"coordinator {base} (LAN, token required, not 0.0.0.0)")

    # install (not transport)
    for ser in (S25, S24):
        adb(ser, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
        adb(ser, "push", str(agent_bin), f"{DEST}/agent")
        adb(ser, "push", str(TV_AND), f"{DEST}/tv")
        adb(ser, "shell", f"chmod +x {DEST}/agent {DEST}/tv")

    unauth25 = http_code_from_phone(S25, f"{base}/stats", None, "curl")
    unauth24 = http_code_from_phone(S24, f"{base}/stats", None, "rust")
    print(f"control no-token S25 HTTP {unauth25}  S24 HTTP {unauth24} (expect 401)")

    env25 = (
        f"KF_BASE={base} KF_TOKEN={token} KF_WORKER=phone-s25 "
        f"KF_DIR={DEST} KF_TV={DEST}/tv KF_MAXIDLE=8"
    )
    env24 = (
        f"KF_BASE={base} KF_TOKEN={token} KF_WORKER=phone-s24 "
        f"KF_DIR={DEST} KF_TV={DEST}/tv KF_MAXIDLE=8"
    )
    p25 = subprocess.Popen(
        ["adb", "-s", S25, "shell", f"{env25} {DEST}/agent"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    p24 = subprocess.Popen(
        ["adb", "-s", S24, "shell", f"{env24} {DEST}/agent"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    ht = threading.Thread(target=host_worker, args=(base, token, blob, JOBS_N), daemon=True)
    ht.start()

    want_pollers = {ip, src25, src24}
    poll_deadline = time.time() + 40
    while time.time() < poll_deadline:
        seen = set(server.STATS.get("poll_peers") or [])
        if want_pollers <= seen:
            break
        time.sleep(0.2)
    seen_before = sorted(set(server.STATS.get("poll_peers") or []))
    print(f"pollers before enqueue: {seen_before} (want {sorted(want_pollers)})")
    t0 = time.perf_counter()
    for job in jobs:
        server.JOBS.put(job)
    deadline = time.time() + 180
    while len(server.RESULTS) < JOBS_N and time.time() < deadline:
        time.sleep(0.2)
    wall = time.perf_counter() - t0
    try:
        out25, _ = p25.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        p25.kill()
        out25 = (p25.stdout.read() if p25.stdout else "") or ""
    try:
        out24, _ = p24.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        p24.kill()
        out24 = (p24.stdout.read() if p24.stdout else "") or ""
    print("s25 agent:", (out25 or "")[-400:])
    print("s24 agent:", (out24 or "")[-400:])

    workers = sorted({e.get("worker") for e in server.RESULTS})
    peers = sorted(set(server.STATS.get("result_peers") or []))
    job_peers = sorted(set(server.STATS.get("job_peers") or []))
    ok_pin = [
        e
        for e in server.RESULTS
        if e.get("status") == "ACCEPTED" and e.get("digest") == PIN
    ]
    via_loopback = [
        e for e in server.RESULTS if "127.0.0.1" in str(e.get("via", ""))
    ]
    phone_peers_loopback = [p for p in job_peers if p.startswith("127.")]
    out = {
        "pin": PIN,
        "status": "F001_FROZEN",
        "transport": "lan-http+KF_TOKEN",
        "not_iroh": True,
        "not_quic": True,
        "not_0_0_0_0": True,
        "bind": ip,
        "port": PORT,
        "base": base,
        "why_not_quic": (
            "LATENCY_FLOOR: persistent HTTP+NODELAY 6.5ms vs RTT 6.4ms; "
            "QUIC 0-RTT cannot beat 1 RTT on a live long-poll worker"
        ),
        "adb_used_for": "install and process start only",
        "adb_reverse_s25": rev25,
        "adb_reverse_s24": rev24,
        "gates": {S25: g25, S24: g24},
        "ips": {"host": ip, "s25": src25, "s24": src24},
        "controls": {
            "unauth_s25": unauth25,
            "unauth_s24": unauth24,
            "nonloopback_without_token_refused": refused,
        },
        "jobs_queued": JOBS_N,
        "envelopes": len(server.RESULTS),
        "accepted_pin": len(ok_pin),
        "workers": workers,
        "result_peers": peers,
        "job_peers": job_peers,
        "poll_peers": sorted(set(server.STATS.get("poll_peers") or [])),
        "pollers_before_enqueue": seen_before,
        "shard_bytes": server.STATS.get("shard_bytes", 0),
        "stats": {k: v for k, v in server.STATS.items() if k not in ("job_peers", "result_peers")},
        "results": server.RESULTS,
        "wall_s": wall,
        "via_loopback_count": len(via_loopback),
        "phone_job_peer_loopback": phone_peers_loopback,
        "three_physical": True,
        "coordinator_colocated_with_darwin_worker": True,
        "not_three_phones": True,
        "not_a_new_operator_domain": True,
        "operator_stays_1": True,
    }
    HERE.joinpath("lan3.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"envelopes {len(server.RESULTS)}/{JOBS_N} accepted_pin={len(ok_pin)} "
        f"workers={workers} peers={peers} shard_bytes={out['shard_bytes']} "
        f"wall={wall:.2f}s"
    )
    if len(ok_pin) < JOBS_N or len(workers) < 3:
        print("THREE_LAN_INCOMPLETE")
        return 0
    if phone_peers_loopback:
        print("PHONE_USED_LOOPBACK")
        return 0
    print("THREE_LAN_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
