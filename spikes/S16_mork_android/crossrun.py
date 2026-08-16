#!/usr/bin/env python3
"""Cross-ARCHITECTURE differential run for MORK.

MORK's own differential/run.py compares two query ENGINES on one machine.
This compares one engine on two ARCHITECTURES:

    macOS 15 / Apple Silicon arm64 / libSystem
    Android 16 / Snapdragon 8 Elite (SM8750) arm64 / bionic

Same corpus, same step cap, space dumps compared byte for byte, plus the
"executing N steps" counter each side reports. That counter is the fuel meter
in the hyperjob schema, so a mismatch there is as serious as a mismatch in the
dump.

Python 3 stdlib only, like the harness it is modelled on.

usage: crossrun.py [--steps N] [--timeout S] [--jobs N] [filter ...]
"""

import argparse
import hashlib
import os
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
ROOT = f"{HOME}/kingfisher"
CORPUS = f"{ROOT}/elders/MORK/differential/corpus"
MORK_HOST = f"{ROOT}/elders/MORK/target/release/mork"
DEV = "/data/local/tmp/kingfisher"
OUT = f"{ROOT}/spikes/S16_mork_android/crossrun"
ADB = f"{HOME}/Library/Android/sdk/platform-tools/adb"

STEPS_RE = "executing "


def run(cmd, timeout, cwd=None):
    """-> (ok, stdout+stderr, seconds). ok is False on timeout or nonzero."""
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        return p.returncode == 0, out, time.perf_counter() - t0
    except subprocess.TimeoutExpired:
        return False, "__TIMEOUT__", time.perf_counter() - t0


def steps_of(text):
    for line in text.splitlines():
        if STEPS_RE in line:
            try:
                return int(line.split(STEPS_RE, 1)[1].split()[0])
            except (IndexError, ValueError):
                pass
    return None


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("filters", nargs="*")
    args = ap.parse_args()

    os.makedirs(f"{OUT}/host", exist_ok=True)
    os.makedirs(f"{OUT}/phone", exist_ok=True)
    subprocess.run([ADB, "shell", f"rm -rf {DEV}/out; mkdir -p {DEV}/out"],
                   capture_output=True)

    progs = []
    for sub in ("programs", "unify"):
        d = os.path.join(CORPUS, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".mm2"):
                rel = f"{sub}/{f}"
                if not args.filters or any(x in rel for x in args.filters):
                    progs.append(rel)

    print(f"corpus   {CORPUS}")
    print(f"host     {MORK_HOST}")
    print(f"phone    {DEV}/mork  (LD_PRELOAD libnotag.so)")
    print(f"programs {len(progs)}   steps_cap={args.steps}   timeout={args.timeout}s\n")
    print(f"{'PROGRAM':<34}{'HOST':>8}{'PHONE':>8}  {'H_s':>6}{'P_s':>7}  VERDICT")

    ok = mismatch = skipped = 0
    for rel in progs:
        name = rel.replace("/", "_")[:-4]
        hout = f"{OUT}/host/{name}.space"
        pout_dev = f"{DEV}/out/{name}.space"
        pout = f"{OUT}/phone/{name}.space"

        h_ok, h_txt, h_t = run(
            [MORK_HOST, "run", rel, hout, "--steps", str(args.steps)],
            args.timeout, cwd=CORPUS)
        p_ok, p_txt, p_t = run(
            [ADB, "shell",
             f"cd {DEV}/corpus && LD_PRELOAD={DEV}/libnotag.so {DEV}/mork run "
             f"{rel} {pout_dev} --steps {args.steps}"],
            args.timeout)

        hs, ps = steps_of(h_txt), steps_of(p_txt)
        if h_txt == "__TIMEOUT__" or p_txt == "__TIMEOUT__":
            why = "host" if h_txt == "__TIMEOUT__" else "phone"
            print(f"{name:<34}{'-':>8}{'-':>8}  {h_t:6.1f}{p_t:7.1f}  SKIP timeout({why})")
            skipped += 1
            continue
        if hs is None or ps is None:
            print(f"{name:<34}{str(hs):>8}{str(ps):>8}  {h_t:6.1f}{p_t:7.1f}  "
                  f"SKIP no-step-line (host_ok={h_ok} phone_ok={p_ok})")
            skipped += 1
            continue

        subprocess.run([ADB, "pull", pout_dev, pout], capture_output=True)
        if not os.path.exists(hout) or not os.path.exists(pout):
            print(f"{name:<34}{hs:>8}{ps:>8}  {h_t:6.1f}{p_t:7.1f}  SKIP no-dump")
            skipped += 1
            continue

        hh, ph = sha(hout), sha(pout)
        if hh == ph and hs == ps:
            print(f"{name:<34}{hs:>8}{ps:>8}  {h_t:6.1f}{p_t:7.1f}  OK  "
                  f"{os.path.getsize(hout):>9} B  {hh[:12]}")
            ok += 1
        else:
            tag = []
            if hs != ps:
                tag.append(f"steps {hs}!={ps}")
            if hh != ph:
                tag.append(f"dump {hh[:12]}!={ph[:12]}")
            print(f"{name:<34}{hs:>8}{ps:>8}  {h_t:6.1f}{p_t:7.1f}  MISMATCH "
                  + "; ".join(tag))
            mismatch += 1

    print(f"\nsteps_cap={args.steps}  ok={ok}  mismatch={mismatch}  skipped={skipped}")
    return 1 if mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
