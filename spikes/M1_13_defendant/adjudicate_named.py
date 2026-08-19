#!/usr/bin/env python3
"""M1.13 — adjudicate plus the defendant. Does not edit q3.py (H19).

Uses S26's pinned q3_head.py and dissenters(). Attribution is a set
difference over envelopes result.json already records.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S26 = HERE.parent / "S26_cheat_attribution"
sys.path.insert(0, str(S26))
import cheat_attr as S26mod  # noqa: E402


def adjudicate_named(envs):
    """(*adjudicate(envs), defendants).

    defendants = workers whose key() != majority key. Empty when there is
    no majority or no live keys (NO_RESULTS).
    """
    verdict = S26mod.Q3NS["adjudicate"](envs)
    named = S26mod.dissenters(envs)
    if isinstance(verdict, tuple):
        return (*verdict, named)
    return verdict, named


def name_row(row: dict) -> list:
    return S26mod.dissenters(row.get("envelopes") or [])


def main() -> int:
    src = S26 / "result.head.json"
    rows = json.loads(src.read_text())["rows"]
    n_named = 0
    for row in rows:
        envs = row.get("envelopes") or []
        if not envs:
            continue
        cheat = S26mod.cheat(envs[0])
        if cheat is None:
            continue
        tampered = [cheat, *envs[1:]]
        *_, defs = adjudicate_named(tampered)
        if defs == [envs[0].get("worker")]:
            n_named += 1
    print(f"M1.13: injected cheats named exactly one worker: {n_named}")
    return 0 if n_named else 1


if __name__ == "__main__":
    sys.exit(main())
