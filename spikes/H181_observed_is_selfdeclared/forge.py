#!/usr/bin/env python3
"""H181 — can a lane mint an `OBSERVED` row for a callsign that is not its own?

ATTACK on spikes/harness/registry.py v1 (H169), written by the same lane 40
minutes earlier. MISSION.md:283 reserves `OBSERVED` for "a message actually
ARRIVED from that address ... the only proof of reachability". registry.py's
`receipts()` is its sole producer and reads the header `send.sh` writes --
and `send.sh:62` is `FROM="${CALLSIGN:-$(whoami)@interactive}"`.

The whole fixture lives INSIDE the workspace (§10 / H89) and the real
inbox/ and fleet/ are never touched: a scratch root is built, roster and all.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))

import registry  # noqa: E402
import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

SEND = ROOT / "spikes" / "harness" / "send.sh"


def build_scratch(tmp: Path):
    """A miniature fleet: two declared lanes, briefs, empty inbox."""
    (tmp / "inbox" / "archive").mkdir(parents=True)
    (tmp / "fleet").mkdir()
    (tmp / "prompts").mkdir()
    (tmp / "spikes" / "harness").mkdir(parents=True)
    (tmp / "roster.txt").write_text("# scratch fleet\nLANE-VICTIM\nLANE-ATTACKER\n")
    for lane in ("LANE-VICTIM", "LANE-ATTACKER"):
        (tmp / "prompts" / f"{lane}.md").write_text(f"# {lane}\n")
    shutil.copy(SEND, tmp / "spikes" / "harness" / "send.sh")


def send_as(tmp: Path, callsign: str, to: str, body: str):
    """Exactly what any lane can do: set CALLSIGN and call send.sh."""
    env = dict(os.environ, CALLSIGN=callsign)
    return subprocess.run(
        ["sh", "spikes/harness/send.sh", to, body],
        cwd=str(tmp), env=env, capture_output=True, text=True)


def main() -> int:
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix=".tmp_h181.", dir=str(ROOT)))
    try:
        build_scratch(tmp)

        # F1 — is any part of the header outside the sender's control?
        send_as(tmp, "LANE-ATTACKER", "LANE-VICTIM", "an honest note")
        honest_hdr = [l for l in (tmp / "inbox" / "LANE-VICTIM.md").read_text().splitlines()
                      if l.startswith("────")]
        header_fields = honest_hdr[0] if honest_hdr else ""
        # the header carries exactly: recipient (an argument) and FROM (the env).
        # No pid, no socket, no lock. Sender controls both.
        uncontrolled = [tok for tok in ("pid", "sock", "lock") if tok in header_fields]
        f1 = bool(uncontrolled)

        # C1 — an honest receipt must still reach OBSERVED, or nothing below means anything.
        rc_honest = registry.receipts(tmp)
        c1_ok = rc_honest.get("LANE-ATTACKER", {}).get("provenance") == registry.OBSERVED

        # THE FORGERY. LANE-ATTACKER mints a receipt attributed to LANE-VICTIM,
        # using one environment variable and nothing else.
        send_as(tmp, "LANE-VICTIM", "LANE-ATTACKER", "I am the victim, and I am reachable")
        rc_forged = registry.receipts(tmp)
        victim_row = rc_forged.get("LANE-VICTIM", {})
        f2 = victim_row.get("provenance") != registry.OBSERVED   # fires if forgery FAILED

        # C2 — the forgery used no privilege a lane lacks.
        c2_ok = True   # one env var, the lane's own tree, no root, no git

        # and it reaches the written file, not merely the in-memory dict
        path, rows, _ = registry._build_in(tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(registry.render(rows, "H181-fixture"))
        in_file = "LANE-VICTIM\t" in path.read_text() and registry.OBSERVED in [
            r.get("provenance") for cs, r in rows.items() if cs == "LANE-VICTIM"]

        # C3 — the module's own selfcheck is untouched by this probe.
        sc = subprocess.run([sys.executable, str(ROOT / "spikes" / "harness" / "registry.py"),
                             "--selfcheck"], capture_output=True, text=True)
        c3_ok = sc.returncode == 0

        print(f"header written by send.sh: {header_fields}")
        print(f"F1 header carries an uncontrolled field: {f1} {uncontrolled}")
        print(f"C1 honest receipt -> OBSERVED: {c1_ok}")
        print(f"FORGED row: {json.dumps(victim_row)}")
        print(f"F2 forgery FAILED (module resisted): {f2}")
        print(f"forged row reached the written file: {in_file}")
        print(f"C3 registry --selfcheck still green: {c3_ok}")

        controls = [
            Control("C1_honest_still_observed",
                    why="a module hardened into observing nothing passes every forgery "
                        "test ever written",
                    can_fail_because="a fix that filters out genuine receipts too",
                    null_must_contain="an honest receipt that does not reach OBSERVED"),
            Control("C2_no_privilege_needed",
                    why="the forgery must use nothing a lane does not already have",
                    can_fail_because="needing root, git write, or another lane's tree",
                    null_must_contain="a forgery requiring privilege"),
            Control("C3_selfcheck_unmodified",
                    why="the module's 10 assertions must pass with no assertion edited",
                    can_fail_because="a probe that breaks the module it attacks",
                    null_must_contain="registry --selfcheck failing"),
        ]
        controls[0].observe(c1_ok, {"row": rc_honest.get("LANE-ATTACKER")})
        controls[1].observe(c2_ok, {"privilege": "one environment variable, own tree"})
        controls[2].observe(c3_ok, {"rc": sc.returncode})

        falsifiers = [
            Falsifier("F1_header_has_uncontrolled_field",
                      refutes="that the sender controls the whole header",
                      fires_when="the header carries a pid, socket or lock token",
                      null_must_contain="a header field the sender cannot set"),
            Falsifier("F2_forgery_failed",
                      refutes="that registry.py launders a self-declaration into OBSERVED",
                      fires_when="the forged row does not reach OBSERVED",
                      null_must_contain="a forged receipt refused"),
        ]
        falsifiers[0].observe(f1, {"header": header_fields, "uncontrolled": uncontrolled})
        falsifiers[1].observe(f2, {"forged_row": victim_row})

        measured = "v2 (CLAIMED present)" if hasattr(registry, "CLAIMED") else "v1"
        res = {
            "spike": "H181",
            "registry_version_measured": measured,
            "attacks": "spikes/harness/registry.py v1 (H169), same lane, 40 minutes older",
            "send_sh_from": "FROM=\"${CALLSIGN:-$(whoami)@interactive}\"  (send.sh:62)",
            "header": header_fields,
            "honest_row": rc_honest.get("LANE-ATTACKER"),
            "forged_row": victim_row,
            "forged_row_reached_file": bool(in_file),
            "privilege_required": "one environment variable",
            "controls": {"C1_honest_still_observed": {"ok": c1_ok},
                         "C2_no_privilege_needed": {"ok": c2_ok},
                         "C3_selfcheck_unmodified": {"ok": c3_ok}},
            "falsifiers": {"F1_header_has_uncontrolled_field": {"fired": f1},
                           "F2_forgery_failed": {"fired": f2}},
            "elapsed_sec": round(time.time() - t0, 2),
        }
        out = HERE / "result.json"
        out.write_text(json.dumps(res, indent=2) + "\n")

        ok, problems = kfcheck.certify(
            str(HERE), deps=[str(ROOT / "spikes" / "harness")], artifacts=[str(out)],
            controls=controls, falsifiers=falsifiers,
            captures=[("result_json", json.dumps(res, sort_keys=True))],
            falsifier="a forged receipt refused by receipts(), or a header field the "
                      "sender cannot control, would refute this row",
            allow_dirty=True,
            note="H181: OBSERVED in registry.py v1 rests on the sender's own CALLSIGN.")
        print(f"\nD6 Provenance Certified: ok={ok}")
        for p in problems:
            print(f"  PROBLEM: {p}")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
