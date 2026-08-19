#!/usr/bin/env python3
"""M1.13 — the defendant field. Fails when `dissenters()` breaks.

READS THE LIVE `q3.py`, never a copy. `main()` is called unguarded at q3.py's
module level, so it cannot be imported; S26 answered that by committing
`q3_head.py`, a head-COPY, and a copy is the C-family failure (the artifact is
not what you think — it drifts from the file it stands for and nothing says so).
Here the prefix of the real file is exec'd, so this check cannot pass against a
q3.py it is not actually testing.

THE ASSERTION THAT MATTERS IS THE NEGATIVE CONTROL. `C_regression` requires
S26's shipped `dissenters()` to NAME a worker that merely went silent, on the
same input where q3's must not. Without it, every "names nobody" line below
passes just as happily against a function that names nobody ever, and the check
would prove nothing about the defect it exists to hold shut.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S26 = HERE.parent / "S26_cheat_attribution"
Q3 = HERE / "q3.py"


def load_q3_prefix():
    """Exec q3.py up to its unguarded `main()` call, in a private namespace."""
    src = Q3.read_text()
    marker = "\nmain()"
    assert marker in src, "q3.py no longer ends in an unguarded main() — re-read this loader"
    ns = {"__name__": "q3_under_test", "__file__": str(Q3)}
    exec(compile(src.split(marker)[0], str(Q3), "exec"), ns)
    return ns


def main() -> int:
    bad = []

    def ck(cond, note):
        print(f"  {'ok  ' if cond else 'FAIL'}  {note}")
        if not cond:
            bad.append(note)

    q3 = load_q3_prefix()
    dissenters = q3["dissenters"]

    sys.path.insert(0, str(S26))
    import cheat_attr as S26mod

    rows = json.loads((S26 / "result.head.json").read_text())["rows"]

    live_row = next((r["envelopes"] for r in rows
                     if r.get("envelopes")
                     and all(q3["key"](e) is not None for e in r["envelopes"])), None)
    nores_row = next((r["envelopes"] for r in rows
                      if r.get("verdict") == "NO_RESULTS" and r.get("envelopes")), None)
    ck(live_row is not None, "fixture: an all-live-key row exists")
    ck(nores_row is not None, "fixture: a NO_RESULTS row exists")
    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1

    # C1 — an honest quorum accuses nobody. A field that always fires names the innocent.
    ck(dissenters(live_row) == [], f"C1 honest run names nobody (got {dissenters(live_row)})")

    # C2 — a planted cheat names EXACTLY the planted worker.
    cheated = S26mod.cheat(live_row[0])
    ck(cheated is not None, "fixture: the cheat is expressible on this envelope")
    if cheated is not None:
        tampered = [cheated, *live_row[1:]]
        got = dissenters(tampered)
        ck(got == [live_row[0].get("worker")],
           f"C2 planted cheat names exactly the liar (got {got}, "
           f"planted {live_row[0].get('worker')})")

    # F3 — nothing to dissent from is not a defendant.
    ck(dissenters(nores_row) == [], f"F3 NO_RESULTS names nobody (got {dissenters(nores_row)})")

    # THE REGRESSION. A worker that did not ANSWER did not DISAGREE.
    silent = copy.deepcopy(live_row)
    silent[-1]["results_text"] = ""
    silent[-1]["sorted_hash"] = ""
    victim = silent[-1].get("worker")
    ck(q3["key"](silent[-1]) is None, "fixture: the silenced worker's key is None")
    got_q3 = dissenters(silent)
    ck(victim not in got_q3,
       f"C_absence a silent worker is not accused (got {got_q3}, silenced {victim})")

    # NEGATIVE CONTROL — the shipped S26 helper MUST name it, or the line above
    # is empty and this file cannot tell a fixed dissenters() from a mute one.
    got_s26 = S26mod.dissenters(silent)
    ck(victim in got_s26,
       f"C_regression negative control: S26's dissenters() still names the silent "
       f"worker (got {got_s26}) — if this fails the fixture stopped reproducing the defect")

    # No majority to dissent FROM: every live key distinct.
    split = copy.deepcopy(live_row)
    for i, e in enumerate(split):
        e["results_text"] = f"(distinct-{i})"
        e.pop("sorted_hash", None)
    ck(dissenters(split) == [], f"C_noquorum a tie names nobody (got {dissenters(split)})")

    # F2 — the whole committed run, not one row. q3's defendant must agree with
    # S26's INDEPENDENTLY WRITTEN attribution everywhere, and must reproduce its
    # certified 200-of-200. Prose in a RESULT.md decays; an assertion does not.
    inj = named = agreed = 0
    for r in rows:
        envs = r.get("envelopes") or []
        for i in range(len(envs)):
            c = S26mod.cheat(envs[i])
            if c is None:
                continue
            tam = [*envs[:i], c, *envs[i + 1:]]
            inj += 1
            mine, theirs = dissenters(tam), S26mod.dissenters(tam)
            if mine == [envs[i].get("worker")]:
                named += 1
            if mine == theirs:
                agreed += 1
    ck(agreed == inj, f"F2 q3 and S26 agree on every injection ({agreed}/{inj})")
    ck(named == 200, f"F2 reproduces S26's certified 200 named (got {named} of {inj})")
    ck(inj - named == 56, f"F2 the unnameable are S26's 56 (14 NO_RESULTS x 4 workers), got {inj - named}")

    # The field is actually WIRED into the row, not merely defined.
    src = Q3.read_text()
    ck("'defendants': dissenters(e)," in src, "row dict carries 'defendants'")
    ck("accused = dissenters(envs)" in src, "report line computes the defendant")

    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1
    print("test_dissenters: the quorum names its defendant, and never a silent worker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
