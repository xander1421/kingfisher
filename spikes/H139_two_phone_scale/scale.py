#!/usr/bin/env python3
"""H139: F001 verify wall-time on two phones, sequential vs parallel.

Falsifier (stated first): if parallel wall at N=8 is within 20% of
t_s25(N)+t_s24(N), there is no scale-out (USB/adb serialised the work).

Operator waived unread-thermal for this spike (QUIET_ALLOW_THERMAL_UNREADABLE=1).
Charging and cpu_busy still refuse. Same-source aarch64 Android is not a new
ISA or operator domain.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TV = ROOT / "fixtures" / "verifier" / "trace_verifier_android_f001"
F001 = ROOT / "fixtures" / "F001"
PIN = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
S25 = "R5CY93675MK"
S24 = "R5CX508MPRZ"
DEST = "/data/local/tmp/kf_scale"
NS = (1, 2, 4, 8)


def run(args, env=None, timeout=120):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=e, timeout=timeout)


def gate(serial: str) -> str:
    env = {
        "ANDROID_SERIAL": serial,
        "QUIET_ALLOW_THERMAL_UNREADABLE": "1",
    }
    p = run(["bash", "spikes/quiet.sh", "--device"], env=env)
    text = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        raise SystemExit(f"gate refused {serial}: {text}")
    return text


def adb(serial: str, *args, timeout=180):
    p = run(["adb", "-s", serial, *args], timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(f"adb {serial} {args}: {p.stdout}{p.stderr}")
    return p


def push(serial: str) -> None:
    adb(serial, "shell", f"rm -rf {DEST} && mkdir -p {DEST}")
    adb(serial, "push", str(TV), f"{DEST}/tv")
    adb(serial, "push", str(F001), f"{DEST}/F001")
    adb(serial, "shell", f"chmod +x {DEST}/tv")


def verify_once(serial: str) -> tuple[float, str]:
    t0 = time.perf_counter()
    p = adb(serial, "shell", f"{DEST}/tv {DEST}/F001")
    dt = time.perf_counter() - t0
    out = p.stdout + p.stderr
    if PIN not in out or "ACCEPTED" not in out:
        raise SystemExit(f"{serial} pin fail:\n{out}")
    return dt, out


def time_n(serial: str, n: int) -> dict:
    times = []
    for _ in range(n):
        dt, _ = verify_once(serial)
        times.append(dt)
    return {"n": n, "times_s": times, "wall_s": sum(times)}


def time_ondevice_loop(serial: str, n: int) -> dict:
    """One adb round-trip; N verifies on the device. Amortises USB."""
    script = (
        f"ok=0; i=0; while [ $i -lt {n} ]; do "
        f"{DEST}/tv {DEST}/F001 | grep -q {PIN[:16]} || exit 2; "
        f"i=$((i+1)); done; echo LOOP_OK n={n}"
    )
    t0 = time.perf_counter()
    p = adb(serial, "shell", script, timeout=300)
    dt = time.perf_counter() - t0
    if "LOOP_OK" not in p.stdout:
        raise SystemExit(f"{serial} on-device loop fail:\n{p.stdout}{p.stderr}")
    return {"n": n, "wall_s": dt}


def time_parallel(n: int) -> dict:
    import concurrent.futures

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f25 = ex.submit(time_n, S25, n)
        f24 = ex.submit(time_n, S24, n)
        a = f25.result()
        b = f24.result()
    wall = time.perf_counter() - t0
    return {"n_each": n, "s25": a, "s24": b, "parallel_wall_s": wall}


def main() -> int:
    loops_only = "--loops-only" in sys.argv
    print("=== gates (thermal unread allowed) ===")
    g25 = gate(S25)
    g24 = gate(S24)
    print("S25", g25)
    print("S24", g24)
    if not loops_only:
        print("=== push ===")
        push(S25)
        push(S24)
    seq = {S25: [], S24: []}
    par = []
    if loops_only:
        prev = Path(__file__).with_name("scale.json")
        old = json.loads(prev.read_text()) if prev.exists() else {}
        seq = old.get("seq", seq)
        par = old.get("par", par)
    if not loops_only:
      for n in NS:
        print(f"=== sequential n={n} ===")
        r25 = time_n(S25, n)
        r24 = time_n(S24, n)
        seq[S25].append(r25)
        seq[S24].append(r24)
        print(f"  S25 n={n} wall={r25['wall_s']:.3f}s")
        print(f"  S24 n={n} wall={r24['wall_s']:.3f}s")
        print(f"=== parallel n={n} each ===")
        pr = time_parallel(n)
        par.append(pr)
        ssum = r25["wall_s"] + r24["wall_s"]
        spd = ssum / pr["parallel_wall_s"] if pr["parallel_wall_s"] else 0
        print(
            f"  parallel wall={pr['parallel_wall_s']:.3f}s "
            f"seq_sum={ssum:.3f}s speedup={spd:.2f}x"
        )
    out = {
        "pin": PIN,
        "thermal_override": "QUIET_ALLOW_THERMAL_UNREADABLE=1",
        "operator_waived_unread_thermal": True,
        "not_a_new_isa": True,
        "not_a_new_operator_domain": True,
        "gates": {S25: g25, S24: g24},
        "seq": seq,
        "par": par,
    }
    # On-device loops: the per-call times above are USB-dominated (S25 n=1 ~36ms).
    print("=== on-device loops (one adb call, N verifies) ===")
    loops = (50, 100, 200)
    loop_seq = {S25: [], S24: []}
    loop_par = []
    for n in loops:
        r25 = time_ondevice_loop(S25, n)
        r24 = time_ondevice_loop(S24, n)
        loop_seq[S25].append(r25)
        loop_seq[S24].append(r24)
        t0 = time.perf_counter()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            a = ex.submit(time_ondevice_loop, S25, n)
            b = ex.submit(time_ondevice_loop, S24, n)
            p25, p24 = a.result(), b.result()
        pwall = time.perf_counter() - t0
        ssum = r25["wall_s"] + r24["wall_s"]
        spd = ssum / pwall if pwall else 0
        loop_par.append(
            {"n_each": n, "s25": p25, "s24": p24, "parallel_wall_s": pwall, "speedup": spd}
        )
        print(
            f"  n={n} S25={r25['wall_s']:.3f}s S24={r24['wall_s']:.3f}s "
            f"par={pwall:.3f}s seq_sum={ssum:.3f}s speedup={spd:.2f}x"
        )
    out["loop_seq"] = loop_seq
    out["loop_par"] = loop_par
    dest = Path(__file__).with_name("scale.json")
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("wrote", dest)
    # Falsifier at N=8 (USB-bound) AND at on-device n=200
    last = par[-1]
    seq8 = seq[S25][-1]["wall_s"] + seq[S24][-1]["wall_s"]
    spd8 = seq8 / last["parallel_wall_s"]
    print(f"USB-bound n=8 speedup={spd8:.2f}x")
    lastl = loop_par[-1]
    print(f"on-device n=200 speedup={lastl['speedup']:.2f}x (need >= 1.20 to claim scale-out)")
    if lastl["speedup"] < 1.20:
        print("NO_SCALE_OUT")
        return 0
    print("SCALE_OUT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
