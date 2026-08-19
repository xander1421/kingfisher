#!/usr/bin/env python3
"""Certify H150. F2b firing is the finding, not a void."""
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
    d = json.loads((HERE / "draw.json").read_text())
    if d.get("pin") != PIN:
        raise SystemExit(f"pin moved: {d.get('pin')}")

    c1 = Control(
        "first_offer_tracks_stake",
        "R2 first offers must sit within 3pp of stake at every honest duty",
        null_must_contain="an online-set draw that can exceed stake by duty capture",
        can_fail_because="first_offer_adv more than 3pp from 0.20",
    )
    c1.observe(
        d["f1_first_offer_tracks_stake"] and d["null_online_set_captures"],
        {
            "f1": d["f1_first_offer_tracks_stake"],
            "null_captures": d["null_online_set_captures"],
            "d05_first": d["rows"]["0.05"]["first_offer_adv"],
            "d05_online": d["rows"]["0.05"]["online_set_adv"],
        },
    )

    c2 = Control(
        "decliner_gets_zero",
        "never-ack adversary accepted share ~0",
        null_must_contain="an accepted-share counter that can be zero or positive",
        can_fail_because="decliner_accepted_adv > 0.01",
    )
    c2.observe(
        d["f2_decliner_cannot_raise"],
        {"decliner": d["rows"]["0.05"]["decliner_accepted_adv"]},
    )

    f2b = Falsifier(
        "accepted_tracks_online_set",
        "R4 redraw-until-ack restores S69 duty capture on ACCEPTED seats",
        fires_when="accepted_adv > stake_share + 0.05 at any honest duty",
        null_must_contain="accepted shares that can sit at stake or at online-set",
    )
    f2b.observe(
        d["f2b_accepted_exceeds_stake"],
        {
            "d05_accepted": d["rows"]["0.05"]["accepted_adv"],
            "d05_online": d["rows"]["0.05"]["online_set_adv"],
            "stake": d["rows"]["0.05"]["stake_share"],
        },
    )

    ok, problems = certify(
        str(HERE),
        artifacts=[str(HERE / "draw.json")],
        controls=[c1, c2],
        falsifiers=[f2b],
        captures=[("draw", json.dumps(d, sort_keys=True))],
        falsifier="always-on accepted share exceeds stake because R4 redraws on silence",
        allow_dirty=True,
        no_deps_reason="coordinator-emulated D1; no elder",
        note="H150: R2 tracks stake; R4 accepted seats match the online set",
    )
    print(f"certify ok={ok}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
