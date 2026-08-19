#!/usr/bin/env python3
"""S92 — `crossrun.py` named its second target and never identified it.

TWO DEFECTS ROUTED BY ATOM-3 (987470d), ONE CAUSE, ONE FIX. This probe drives
the REAL `crossrun.main()` with `subprocess.run` replaced by a recorder, so the
arms exercise the shipped call sites rather than a re-implementation of them.

TWO-SIDED THROUGHOUT. Every refusal arm has an acceptance twin, because a
precondition that refuses everything is indistinguishable from one that works
and is the cheaper thing to ship by accident:

  A1  no device attached            -> REFUSED      (twin: A5 accepts one phone)
  A2  two devices, no --serial      -> REFUSED      (twin: A3 accepts with one)
  A3  two devices, --serial given   -> accepted, AND every adb argv carries -s
  A4  one emulator                  -> kind=emulator, filed under emulator/
  A5  one phone                     -> kind=phone,    filed under phone/
  A6  --expect phone vs emulator    -> REFUSED
  A7  device reports no model       -> REFUSED       (identity unasserted)
  A8  --expect emulator vs emulator -> accepted      (twin of A6)
  A9  named serial is unauthorized  -> REFUSED

FALSIFIER, STATED BEFORE RUNNING: if A3's argv recorder comes back with ZERO adb
invocations, every `-s` assertion is vacuously true and the run is VOID rather
than green. A3b asserts the recorder saw the calls it is judging.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout, redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TARGET = os.path.join(ROOT, "spikes", "S16_mork_android", "crossrun.py")

spec = importlib.util.spec_from_file_location("crossrun", TARGET)
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)

fail = 0
results = {}


def ck(name, got, want):
    global fail
    if got == want:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} (want {want!r}, got {got!r})")
        fail += 1


PHONE = {"ro.product.model": "SM-S938B", "ro.product.manufacturer": "samsung",
         "ro.product.cpu.abi": "arm64-v8a", "ro.build.characteristics": "nosdcard",
         "ro.kernel.qemu": "", "ro.hardware": "qcom",
         "ro.build.version.release": "16"}
EMU = {"ro.product.model": "sdk_gphone64_arm64", "ro.product.manufacturer": "Google",
       "ro.product.cpu.abi": "arm64-v8a", "ro.build.characteristics": "emulator",
       "ro.kernel.qemu": "1", "ro.hardware": "ranchu",
       "ro.build.version.release": "16"}
BLANK = dict(PHONE, **{"ro.product.model": ""})


class Recorder:
    """Stands in for subprocess.run. Records every argv; answers adb only."""

    def __init__(self, devices, props_by_serial):
        self.devices = devices                  # [(serial, state)]
        self.props = props_by_serial            # {serial: {prop: value}}
        self.calls = []

    def __call__(self, cmd, *a, **kw):
        self.calls.append(list(cmd))
        out = b""
        if cmd[0] == cr.ADB:
            if cmd[1] == "devices":
                rows = "".join(f"{s}\t{st}\n" for s, st in self.devices)
                out = ("List of devices attached\n" + rows + "\n").encode()
            elif "getprop" in cmd:
                serial = cmd[2]
                out = self.props.get(serial, {}).get(cmd[-1], "").encode()
        return subprocess.CompletedProcess(cmd, 0, out, b"")


def drive(devices, props, argv, outdir):
    """Run the REAL main() against a recorded adb. -> (rc, stdout, recorder)"""
    rec = Recorder(devices, props)
    old_run, old_sub, old_out = cr.run, cr.subprocess.run, cr.OUT
    cr.subprocess.run = rec
    # `run()` is the host/device executor. Stubbed so no MORK binary is needed
    # and no device is contacted; it still routes through the same argv the
    # recorder sees, which is what A3 is about.
    cr.run = lambda cmd, timeout, cwd=None: (rec(cmd) and None) or (
        True, "executing 5 steps\n", 0.01)
    cr.sha = lambda p: "d" * 64
    cr.OUT = outdir
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            sys.argv = ["crossrun.py"] + argv
            rc = cr.main()
    except SystemExit as e:                       # argparse
        rc = e.code
    finally:
        cr.run, cr.subprocess.run, cr.OUT = old_run, old_sub, old_out
    return rc, buf.getvalue(), rec


tmp = tempfile.mkdtemp(dir=os.path.join(ROOT, ".scratch")
                       if os.path.isdir(os.path.join(ROOT, ".scratch"))
                       else None, prefix="S92.")
try:
    # ------------------------------------------------------------------ A1 ---
    rc, out, _ = drive([], {}, ["--steps", "1"], os.path.join(tmp, "a1"))
    ck("A1 no device attached -> REFUSED", rc, 2)
    ck("A1b ...and says so, naming the state it looked for",
       "no device in state `device`" in out, True)
    results["A1"] = {"rc": rc, "refused": "REFUSED" in out}

    # ------------------------------------------------------------------ A2 ---
    two = [("R5CX00PHONE", "device"), ("emulator-5554", "device")]
    props2 = {"R5CX00PHONE": PHONE, "emulator-5554": EMU}
    rc, out, _ = drive(two, props2, ["--steps", "1"], os.path.join(tmp, "a2"))
    ck("A2 two devices and no --serial -> REFUSED", rc, 2)
    ck("A2b ...and names BOTH serials, so the operator can pick",
       ("R5CX00PHONE" in out) and ("emulator-5554" in out), True)
    results["A2"] = {"rc": rc, "named_both": ("R5CX00PHONE" in out
                                              and "emulator-5554" in out)}

    # ------------------------------------------------------------------ A3 ---
    # THE ARM FOR DEFECT 2. Two devices attached -- the exact state that made 35
    # programs SKIP for two days -- with the serial pinned.
    rc, out, rec = drive(two, props2,
                         ["--steps", "1", "--serial", "R5CX00PHONE"],
                         os.path.join(tmp, "a3"))
    adb_calls = [c for c in rec.calls if c and c[0] == cr.ADB]
    enum = [c for c in adb_calls if c[1:2] == ["devices"]]
    targeted = [c for c in adb_calls if c[1:2] != ["devices"]]
    unqualified = [c for c in targeted
                   if c[1:3] != ["-s", "R5CX00PHONE"]]
    ck("A3 two devices with --serial -> accepted", rc, 0)
    ck("A3b the recorder actually saw adb calls (else every -s check is vacuous)",
       len(targeted) > 0, True)
    ck("A3c EVERY targeted adb invocation carries -s <serial>",
       len(unqualified), 0)
    ck("A3d `adb devices` is the one call that correctly takes no -s",
       len(enum), 1)
    results["A3"] = {"rc": rc, "targeted_adb_calls": len(targeted),
                     "unqualified": len(unqualified), "enumerations": len(enum)}

    # ------------------------------------------------------------------ A4 ---
    rc, out, _ = drive([("emulator-5554", "device")], {"emulator-5554": EMU},
                       ["--steps", "1"], os.path.join(tmp, "a4"))
    tj = json.load(open(os.path.join(tmp, "a4", "target.json")))
    ck("A4 a lone emulator resolves to kind=emulator", tj["kind"], "emulator")
    ck("A4b ...and its dumps are filed under emulator/, not phone/",
       os.path.isdir(os.path.join(tmp, "a4", "emulator"))
       and not os.path.isdir(os.path.join(tmp, "a4", "phone")), True)
    ck("A4c ...and the run says why `host` is one domain, not two",
       "host` is ONE domain" in out, True)
    ck("A4d the emulator verdict rests on machine properties, not the model name",
       sorted(t.split("=")[0].split(" ")[0] for t in tj["emulator_tells"]),
       ["ro.build.characteristics", "ro.hardware", "ro.kernel.qemu", "serial"])
    results["A4"] = {"kind": tj["kind"], "tells": tj["emulator_tells"]}

    # ------------------------------------------------------------------ A5 ---
    rc, out, _ = drive([("R5CX00PHONE", "device")], {"R5CX00PHONE": PHONE},
                       ["--steps", "1"], os.path.join(tmp, "a5"))
    tj5 = json.load(open(os.path.join(tmp, "a5", "target.json")))
    ck("A5 a lone phone resolves to kind=phone", tj5["kind"], "phone")
    ck("A5b ...with NO emulator tells, so A4 is not matching everything",
       tj5["emulator_tells"], [])
    ck("A5c ...and its dumps are filed under phone/",
       os.path.isdir(os.path.join(tmp, "a5", "phone")), True)
    results["A5"] = {"kind": tj5["kind"], "tells": tj5["emulator_tells"]}

    # ------------------------------------------------------------------ A6 ---
    rc, out, _ = drive([("emulator-5554", "device")], {"emulator-5554": EMU},
                       ["--steps", "1", "--expect", "phone"],
                       os.path.join(tmp, "a6"))
    ck("A6 --expect phone against an emulator -> REFUSED", rc, 2)
    ck("A6b ...and names what it found instead", "resolves to emulator" in out, True)
    results["A6"] = {"rc": rc}

    # ------------------------------------------------------------------ A7 ---
    rc, out, _ = drive([("R5CX00PHONE", "device")], {"R5CX00PHONE": BLANK},
                       ["--steps", "1"], os.path.join(tmp, "a7"))
    ck("A7 a device that will not name itself -> REFUSED", rc, 2)
    ck("A7b ...for being UNASSERTED, not for being the wrong kind",
       "UNASSERTED target" in out, True)
    results["A7"] = {"rc": rc}

    # ------------------------------------------------------------------ A8 ---
    rc, out, _ = drive([("emulator-5554", "device")], {"emulator-5554": EMU},
                       ["--steps", "1", "--expect", "emulator"],
                       os.path.join(tmp, "a8"))
    ck("A8 --expect emulator against an emulator -> accepted (twin of A6)", rc, 0)
    results["A8"] = {"rc": rc}

    # ------------------------------------------------------------------ A9 ---
    rc, out, _ = drive([("R5CX00PHONE", "unauthorized")], {"R5CX00PHONE": PHONE},
                       ["--steps", "1", "--serial", "R5CX00PHONE"],
                       os.path.join(tmp, "a9"))
    ck("A9 a named serial in state `unauthorized` -> REFUSED", rc, 2)
    ck("A9b ...naming the state, since `attached` and `usable` are not the same",
       "not `device`" in out, True)
    results["A9"] = {"rc": rc}
finally:
    shutil.rmtree(tmp, ignore_errors=True)

with open(os.path.join(HERE, "result.json"), "w") as fh:
    json.dump({"checks_failed": fail, "arms": results}, fh,
              indent=2, sort_keys=True)
    fh.write("\n")

print(f"\nchecks failed: {fail}")
sys.exit(1 if fail else 0)
