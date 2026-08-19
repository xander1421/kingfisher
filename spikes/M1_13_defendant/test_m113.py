#!/usr/bin/env python3
"""Drive shipped S26 + adjudicate_named. q3.py is not imported."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adjudicate_named as M  # noqa: E402


def main() -> int:
    bad = []

    def ck(cond, note):
        print(f"  {'ok  ' if cond else 'FAIL'}  {note}")
        if not cond:
            bad.append(note)

    src = HERE.parent / "S26_cheat_attribution" / "result.head.json"
    rows = json.loads(src.read_text())["rows"]
    named = 0
    for row in rows:
        envs = row.get("envelopes") or []
        if row.get("verdict") == "NO_RESULTS" or len(envs) < 3:
            continue
        cheat = M.S26mod.cheat(envs[0])
        if cheat is None:
            continue
        tampered = [cheat, *envs[1:]]
        out = M.adjudicate_named(tampered)
        defs = out[-1]
        if defs == [envs[0].get("worker")]:
            named += 1
    ck(named >= 1, f"at least one cheat named (got {named})")
    ck(M.adjudicate_named.__doc__ and "q3.py" in (HERE / "adjudicate_named.py").read_text(),
       "sidecar states it does not edit q3.py")
    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1
    print(f"m113: {named} injected cheats named exactly one worker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
