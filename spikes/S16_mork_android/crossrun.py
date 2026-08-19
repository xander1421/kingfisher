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

usage: crossrun.py [--steps N] [--timeout S] [--serial SER] [--expect KIND]
                   [filter ...]

v2, 2026-08-19, AGENT-1 (S92). TWO DEFECTS, ROUTED BY ATOM-3 AT 987470d AND
NEITHER FOUND BY THIS FILE'S AUTHOR (A22). Both had one cause -- the second
target was NAMED and never IDENTIFIED -- and one fix: a precondition that
REFUSES when the target is ambiguous or unasserted, rather than a run that
proceeds and mislabels. Same class that H218 fixed one directory over.

  1. v1 called its second target "phone" whichever it was. `:75` wrote
     `{OUT}/phone/` and `:92` printed `phone` with no reference to what was
     actually connected. ATOM-3 ran it against an EMULATOR and the result is on
     disk as a phone result. Family C, upstream of a domain-independence claim:
     S76 measured the emulator guest reporting `implementer 0x61, Apple` -- the
     same M4 Pro silicon as this script's HOST arm -- so against an emulator
     `host` is ONE domain, not two, and a harness filing both under `phone/`
     reports a one-host result in the shape of a two-host one.
     v2 derives the label from what the device SAYS it is and writes
     `crossrun/target.json` next to the dumps, so a later reader cannot mistake
     one for the other.

  2. v1 called `adb shell` / `adb pull` with no `-s` and no serial. With a
     second device attached adb refuses, every program reports
     `SKIP no-step-line`, and that is exactly what happened for two days -- and
     was recorded as a TARGET failure three times before the cause was found.
     v2 routes every invocation through one `adb_cmd()` that prepends
     `-s <serial>`; there is no second call site to forget.

Check that fails when this breaks (§12.3, D6):
    python3 spikes/S92_target_identity/probe.py
"""

import argparse
import hashlib
import json
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

# Properties read off the device to decide WHAT it is. `ro.product.model` is the
# identity assertion: a target that will not name itself is unasserted, and an
# unasserted target is refused rather than labelled by default.
PROPS = ("ro.product.model", "ro.product.manufacturer", "ro.product.cpu.abi",
         "ro.build.characteristics", "ro.kernel.qemu", "ro.hardware",
         "ro.build.version.release")


class TargetRefused(Exception):
    """The precondition refused. It REFUSES, it does not warn (CLAUDE.md)."""


def adb_cmd(serial, *args):
    """The ONLY place `ADB` is turned into a command line.

    Defect 2 was three call sites each having to remember `-s`. One helper is a
    smaller diff than a flag on every caller, and there is no fourth site to
    forget when the next one is added.
    """
    if not serial:
        raise TargetRefused("adb_cmd called with no serial -- the target was "
                            "never resolved")
    return [ADB, "-s", serial, *args]


def adb_devices():
    """-> [(serial, state)] from `adb devices`, header and blanks dropped."""
    p = subprocess.run([ADB, "devices"], capture_output=True)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append((parts[0], parts[1]))
    return rows


def is_emulator(serial, props):
    """Four independent tells, because any one of them can be absent.

    Deliberately NOT a name grep on the model string alone (A30): `ro.kernel.qemu`
    and `ro.hardware` are properties of the machine, not vocabulary about it.
    """
    tells = []
    if serial.startswith("emulator-"):
        tells.append("serial prefix `emulator-`")
    if props.get("ro.kernel.qemu") == "1":
        tells.append("ro.kernel.qemu=1")
    if "emulator" in props.get("ro.build.characteristics", ""):
        tells.append("ro.build.characteristics contains `emulator`")
    if props.get("ro.hardware", "") in ("ranchu", "goldfish"):
        tells.append(f"ro.hardware={props['ro.hardware']}")
    return tells


def resolve_target(serial=None, expect=None):
    """Pin ONE device and assert what it is, or refuse. -> dict

    REFUSES on: no device, more than one with no serial given, a named serial
    that is absent or not in `device` state, and a device that will not report
    `ro.product.model`. Every one of those is a state in which v1 proceeded.
    """
    rows = adb_devices()
    live = [(s, st) for s, st in rows if st == "device"]

    if serial:
        states = dict(rows)
        if serial not in states:
            raise TargetRefused(
                f"serial {serial!r} is not attached. adb reports: "
                + (", ".join(f"{s}({st})" for s, st in rows) or "nothing"))
        if states[serial] != "device":
            raise TargetRefused(
                f"serial {serial!r} is in state {states[serial]!r}, not `device`")
    elif not live:
        raise TargetRefused(
            "no device in state `device`. adb reports: "
            + (", ".join(f"{s}({st})" for s, st in rows) or "nothing")
            + ".  This is the refusal, not a warning: a cross-ARCHITECTURE "
              "differential with one architecture attached measures nothing.")
    elif len(live) > 1:
        raise TargetRefused(
            "AMBIGUOUS TARGET -- " + str(len(live)) + " devices attached: "
            + ", ".join(s for s, _ in live)
            + ".  Pass --serial (or set ANDROID_SERIAL). This is the state that "
              "made all 35 programs report SKIP no-step-line for two days, "
              "because adb refuses an unqualified `shell` and the failure was "
              "credited to the target three times.")
    else:
        serial = live[0][0]

    props = {}
    for k in PROPS:
        p = subprocess.run(adb_cmd(serial, "shell", "getprop", k),
                           capture_output=True)
        props[k] = (p.stdout + p.stderr).decode("utf-8", "replace").strip()

    if not props.get("ro.product.model"):
        raise TargetRefused(
            f"{serial} will not report `ro.product.model`. An UNASSERTED target "
            "is refused rather than labelled by default -- that default is the "
            "whole defect this precondition removes.")

    tells = is_emulator(serial, props)
    kind = "emulator" if tells else "phone"
    if expect and expect != kind:
        raise TargetRefused(
            f"--expect {expect}, but {serial} resolves to {kind}"
            + (" (" + "; ".join(tells) + ")" if tells else "")
            + ".  Refusing rather than filing the run under the wrong target.")
    return {"serial": serial, "kind": kind, "emulator_tells": tells,
            "props": props}


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
    ap.add_argument("--serial", default=os.environ.get("ANDROID_SERIAL"),
                    help="pin the device. Required when more than one is "
                         "attached; defaults to $ANDROID_SERIAL")
    ap.add_argument("--expect", choices=("phone", "emulator"), default=None,
                    help="refuse unless the resolved target is this kind")
    ap.add_argument("filters", nargs="*")
    args = ap.parse_args()

    # ---- PRECONDITION. It refuses; it does not warn. ----------------------
    try:
        target = resolve_target(args.serial, args.expect)
    except TargetRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    serial, kind = target["serial"], target["kind"]

    os.makedirs(f"{OUT}/host", exist_ok=True)
    os.makedirs(f"{OUT}/{kind}", exist_ok=True)
    # The record of WHAT the second arm was, written next to the dumps. v1 left
    # a reader with a directory name and nothing to check it against.
    with open(f"{OUT}/target.json", "w") as fh:
        json.dump(target, fh, indent=2, sort_keys=True)
        fh.write("\n")
    subprocess.run(adb_cmd(serial, "shell",
                           f"rm -rf {DEV}/out; mkdir -p {DEV}/out"),
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
    print(f"{kind:<9}{DEV}/mork  (LD_PRELOAD libnotag.so)")
    print(f"target   {serial}  {target['props']['ro.product.manufacturer']} "
          f"{target['props']['ro.product.model']}  "
          f"{target['props']['ro.product.cpu.abi']}  -> {kind.upper()}"
          + ("  [" + "; ".join(target["emulator_tells"]) + "]"
             if target["emulator_tells"] else ""))
    if kind == "emulator":
        print("         NOTE: an emulator guest runs on the HOST's silicon, so "
              "`host` is ONE domain across these two arms, not two (S76).")
    print(f"programs {len(progs)}   steps_cap={args.steps}   timeout={args.timeout}s\n")
    # The column is neutral on purpose. v1's header said PHONE whatever was
    # attached; putting the RESOLVED kind here instead would just move the same
    # width problem (`EMULATOR` is exactly 8 and closes the gap). The identity
    # is on the `target` line above and in `crossrun/target.json`, once each.
    print(f"{'PROGRAM':<34}{'HOST':>8}{'DEVICE':>8}  {'H_s':>6}{'P_s':>7}  VERDICT")

    ok = mismatch = skipped = 0
    for rel in progs:
        name = rel.replace("/", "_")[:-4]
        hout = f"{OUT}/host/{name}.space"
        pout_dev = f"{DEV}/out/{name}.space"
        pout = f"{OUT}/{kind}/{name}.space"

        h_ok, h_txt, h_t = run(
            [MORK_HOST, "run", rel, hout, "--steps", str(args.steps)],
            args.timeout, cwd=CORPUS)
        p_ok, p_txt, p_t = run(
            adb_cmd(serial, "shell",
                    f"cd {DEV}/corpus && LD_PRELOAD={DEV}/libnotag.so "
                    f"{DEV}/mork run {rel} {pout_dev} --steps {args.steps}"),
            args.timeout)

        hs, ps = steps_of(h_txt), steps_of(p_txt)
        if h_txt == "__TIMEOUT__" or p_txt == "__TIMEOUT__":
            why = "host" if h_txt == "__TIMEOUT__" else kind
            print(f"{name:<34}{'-':>8}{'-':>8}  {h_t:6.1f}{p_t:7.1f}  SKIP timeout({why})")
            skipped += 1
            continue
        if hs is None or ps is None:
            print(f"{name:<34}{str(hs):>8}{str(ps):>8}  {h_t:6.1f}{p_t:7.1f}  "
                  f"SKIP no-step-line (host_ok={h_ok} {kind}_ok={p_ok})")
            skipped += 1
            continue

        subprocess.run(adb_cmd(serial, "pull", pout_dev, pout),
                       capture_output=True)
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

    print(f"\nsteps_cap={args.steps}  ok={ok}  mismatch={mismatch}  "
          f"skipped={skipped}  target={kind}({serial})")
    return 1 if mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
