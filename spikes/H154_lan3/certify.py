#!/usr/bin/env python3
"""Certify H154. Falsifier: not 3 LAN workers on the frozen pin, or a phone used loopback."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
from kfcheck import Control, certify  # noqa: E402
from provenance import Falsifier  # noqa: E402

PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"


def main() -> int:
    d = json.loads((HERE / "lan3.json").read_text())
    c1 = Control(
        "three_workers_same_pin",
        "host-darwin + phone-s25 + phone-s24 each ACCEPT 590d8769 over LAN",
        null_must_contain="a worker set that can miss a name or a digest",
        can_fail_because="fewer than 3 workers, or any envelope digest != pin",
    )
    workers = set(d.get("workers") or [])
    want = {"host-darwin", "phone-s25", "phone-s24"}
    c1.observe(
        want <= workers
        and d.get("accepted_pin") == d.get("jobs_queued")
        and d.get("pin") == PIN,
        {
            "workers": sorted(workers),
            "accepted_pin": d.get("accepted_pin"),
            "queued": d.get("jobs_queued"),
        },
    )
    c2 = Control(
        "transport_is_lan_not_adb_reverse",
        "phones dial the LAN address; unauth is 401; bind is not 0.0.0.0",
        null_must_contain="127.0.0.1 peers, empty reverse list, or HTTP 200 unauth",
        can_fail_because="job_peers include 127.0.0.1, reverse set, unauth != 401, bind 0.0.0.0",
    )
    peers = d.get("job_peers") or []
    ctr = d.get("controls") or {}
    c2.observe(
        not d.get("adb_reverse_s25")
        and not d.get("adb_reverse_s24")
        and ctr.get("unauth_s25") == "401"
        and ctr.get("unauth_s24") == "401"
        and ctr.get("nonloopback_without_token_refused") is True
        and d.get("bind") != "0.0.0.0"
        and not any(str(p).startswith("127.") for p in peers)
        and d.get("shard_bytes", 0) > 0,
        {
            "job_peers": peers,
            "unauth": (ctr.get("unauth_s25"), ctr.get("unauth_s24")),
            "bind": d.get("bind"),
            "shard_bytes": d.get("shard_bytes"),
        },
    )
    f1 = Falsifier(
        "not_three_device_lan",
        "3-device LAN run missing a worker, pin, or used adb reverse",
        fires_when="workers < 3 OR accepted_pin < queued OR phone peer is 127.0.0.1 OR unauth != 401",
        null_must_contain="worker counts, peer IPs, and HTTP codes that can fail each check",
    )
    fired = (
        not (want <= workers)
        or d.get("accepted_pin") != d.get("jobs_queued")
        or any(str(p).startswith("127.") for p in peers)
        or ctr.get("unauth_s25") != "401"
        or ctr.get("unauth_s24") != "401"
    )
    f1.observe(
        fired,
        {
            "workers": sorted(workers),
            "accepted": d.get("accepted_pin"),
            "peers": peers,
            "unauth": (ctr.get("unauth_s25"), ctr.get("unauth_s24")),
        },
    )
    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "lan3.json")],
        controls=[c1, c2],
        falsifiers=[f1],
        captures=[("lan3", json.dumps(d, sort_keys=True))],
        falsifier=(
            "fewer than 3 workers ACCEPT 590d8769, or a phone peer is "
            "127.0.0.1, or unauth is not 401"
        ),
        allow_dirty=True,
        no_deps_reason="live LAN F001 on 3 machines; no elder",
        note="H154: 3 physical devices, LAN HTTP, no adb reverse. Not iroh. operator=1.",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
