#!/usr/bin/env python3
"""H176 — H163's parity control accepts either pin for every task.

THE CLAIM UNDER ATTACK: H163's "250 tasks dispatched, 100% bit parity (250/250)"
as evidence of heterogeneous multi-device consensus.

AN HONEST NEGATIVE FIRST. The hypothesis I was handed -- that these rows read one
digest and compare it to itself -- is WRONG, and it is stated here before my own
finding. `H163/run.py::run_single` shells a real binary on each target (adb shell
on two Androids, `xcrun simctl spawn` on the iOS sim, two local binaries) and
parses the digest out of THAT process's own stdout. Five independent
recomputations. That part of H163 stands.

MY FINDING IS DIFFERENT. H163 dispatches `tasks[i] = "F001" if i%2==0 else
"F002_specv1"`, but `run_single` returns `(rc, dig)` and the REQUESTED FIXTURE IS
NEVER CARRIED INTO `results`. The verdict then DISJOINS the two pins, so either
is accepted for every task. A target that ignores its argument and always
computes F001 scores 250/250.

CLASS SWEEP (MISSION_LOOP 12.2) -- and it is why this is a regression and not a
missing idea. The CORRECT form already exists twice in this repo:
    H161/run.py:172   if dig1 != PIN_F001 or dig2 != PIN_F002      <- BINDS
    H155/run.py:187   d1 == PIN_F001 and d2 == PIN_F002            <- BINDS
    H163/run.py:162   if rc != 0 or (dig != PIN_F001 and dig != PIN_F002)   <- DISJOINS
H161 and H155 each run exactly two jobs and can bind positionally. H163 runs 250
through a ThreadPoolExecutor drained by `as_completed`, which DESTROYS the
dispatch order -- so the disjunction is what you write when the fixture is no
longer in hand. The fix is to carry it back, not to re-order.

SCOPE, STATED SO IT CANNOT BE READ WIDER: this attacks the CONTROL, not the
devices. Nothing here shows any target misbehaved or that H163's 250 digests were
wrong -- they match the pins. The claim is that the check would not have noticed
if they had been misrouted.

THE DEVICE ARM IS GATED, NOT DROPPED. `sh spikes/quiet.sh --device` exits 1 with
`REFUSED - multiple(R5CY93675MK emulator-5554)` -- the MISSION_LOOP 10 gate
refuses while two targets are attached, so no device job runs here. That is the
gate working, and the finding does not need one: the defect is decidable from the
predicate.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
H163 = os.path.join(SPIKES, "H163_tri_device_p2p_swarm", "run.py")

sys.path.insert(0, os.path.join(SPIKES, "harness"))
import kfcheck                                    # noqa: E402
from provenance import Control, Falsifier         # noqa: E402

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"
N_TASKS = 250

# H163/run.py:160-164, byte-for-byte. Pinned below by SOURCE_ASSERT so this file
# cannot silently drift away from the thing it claims to be testing -- a copy
# that drifts is MISSION_LOOP 12.2's own defect class.
SOURCE_ASSERT = """    f1_divergence = False
    for rc, dig in results:
        if rc != 0 or (dig != PIN_F001 and dig != PIN_F002):
            f1_divergence = True
            break"""


def h163_verdict(results):
    """H163's parity predicate, verbatim. Returns f1_divergence."""
    f1_divergence = False
    for rc, dig in results:
        if rc != 0 or (dig != PIN_F001 and dig != PIN_F002):
            f1_divergence = True
            break
    return f1_divergence


def bound_verdict(results_with_fixture):
    """What H161:172 and H155:187 already do: bind the digest to ITS fixture."""
    expected = {"F001": PIN_F001, "F002_specv1": PIN_F002}
    for rc, dig, fix in results_with_fixture:
        if rc != 0 or dig != expected[fix]:
            return True
    return False


def tasks():
    return ["F001" if i % 2 == 0 else "F002_specv1" for i in range(N_TASKS)]


def main() -> int:
    t0 = time.perf_counter()
    print("=== H176: H163's parity control vs a worker that ignores its input ===\n")

    src = Path(H163).read_text(encoding="utf-8")
    source_pinned = SOURCE_ASSERT in src
    print(f"C0 source pin -- H163/run.py still contains the predicate tested here: {source_pinned}")
    if not source_pinned:
        print("  REFUSING: H163's predicate has changed. This row is about the old one.")
        return 2

    fix = tasks()
    expected = {"F001": PIN_F001, "F002_specv1": PIN_F002}

    # ARM A -- honest. Every worker computes the fixture it was given.
    arm_a = [(0, expected[f]) for f in fix]
    arm_a_bound = [(0, expected[f], f) for f in fix]

    # ARM B -- THE MUTANT. Every worker ignores its argument and computes F001.
    arm_b = [(0, PIN_F001) for _ in fix]
    arm_b_bound = [(0, PIN_F001, f) for f in fix]
    n_wrong_b = sum(1 for f in fix if expected[f] != PIN_F001)

    # ARM C -- POSITIVE CONTROL. One genuinely corrupt digest.
    bad = "de" + "0" * 62
    arm_c = list(arm_a); arm_c[137] = (0, bad)

    # ARM D -- POSITIVE CONTROL. One non-zero return code.
    arm_d = list(arm_a); arm_d[42] = (1, expected[fix[42]])

    rows = [
        ("A honest (every worker runs its own fixture)", arm_a, 0),
        ("B MUTANT: worker ignores input, always F001", arm_b, n_wrong_b),
        ("C positive control: one corrupt digest", arm_c, 1),
        ("D positive control: one rc != 0", arm_d, 1),
    ]
    print(f"\n{'arm':<46}{'tasks wrong':>12}{'H163 verdict':>16}")
    verdicts = {}
    for name, res, nwrong in rows:
        div = h163_verdict(res)
        verdicts[name[0]] = div
        print(f"{name:<46}{nwrong:>12}{('DIVERGENCE' if div else 'parity 250/250'):>16}")

    bound_a = bound_verdict(arm_a_bound)
    bound_b = bound_verdict(arm_b_bound)
    print(f"\nSame two arms under the BOUND predicate H161:172 / H155:187 already use:")
    print(f"  A honest -> {'DIVERGENCE' if bound_a else 'parity 250/250'}")
    print(f"  B MUTANT -> {'DIVERGENCE' if bound_b else 'parity 250/250'}")

    print(f"\nSIZE OF THE INTERVENTION: arm B changes {n_wrong_b} of {N_TASKS} digests "
          f"({100.0*n_wrong_b/N_TASKS:.0f}% of the workload) and H163's check reports "
          f"{'parity' if not verdicts['B'] else 'divergence'}.")

    # --- CONTROLS ---
    c1_ok = PIN_F001 != PIN_F002
    c2_ok = (verdicts["A"] is False) and (len(arm_a) == N_TASKS)
    c3_ok = PIN_F001.startswith("590d8769") and PIN_F002.startswith("c43b1eab")
    controls = [
        Control("C1_pins_distinct",
                why="if the two pins were equal, 'either pin accepted' would not be a weakening and there is no finding",
                can_fail_because="the two fixtures could hash to the same digest",
                null_must_contain="pins identical"),
        Control("C2_honest_arm_reproduces",
                why="the honest arm must report 250/250 so the mutant arm changes ONE variable and not my harness",
                can_fail_because="my reconstruction of H163's dispatch is wrong",
                null_must_contain="honest arm diverges"),
        Control("C3_pins_intact", why="F001/F002 unchanged", can_fail_because="pin drift",
                null_must_contain="pins moved"),
    ]
    controls[0].observe(c1_ok, {"f001": PIN_F001[:16], "f002": PIN_F002[:16]})
    controls[1].observe(c2_ok, {"honest_divergence": verdicts["A"], "n": len(arm_a)})
    controls[2].observe(c3_ok, {"f001": PIN_F001, "f002": PIN_F002})

    # --- FALSIFIERS (preregistered in CHANNEL.md before this directory existed) ---
    f1 = not source_pinned                 # refutes ME: predicate isn't what I said
    f2 = verdicts["B"]                     # refutes ME: the blindness does not exist
    f3 = not (verdicts["C"] and verdicts["D"])   # my harness is inert -> row worthless
    falsifiers = [
        Falsifier("F1_fixture_is_bound",
                  refutes="my claim that H163's verdict path never binds the fixture to the digest",
                  fires_when="H163/run.py no longer contains the disjoining predicate",
                  null_must_contain="predicate bound"),
        Falsifier("F2_mutant_is_caught",
                  refutes="my claim that a worker ignoring its input passes",
                  fires_when="H163's predicate reports divergence on arm B",
                  null_must_contain="mutant caught"),
        Falsifier("F3_my_harness_is_inert",
                  refutes="that a green arm B means anything at all",
                  fires_when="arm C or arm D fails to report divergence",
                  null_must_contain="positive control did not fire"),
    ]
    falsifiers[0].observe(f1, {"source_pinned": source_pinned})
    falsifiers[1].observe(f2, {"arm_b_divergence": verdicts["B"], "tasks_misrouted": n_wrong_b})
    falsifiers[2].observe(f3, {"arm_c": verdicts["C"], "arm_d": verdicts["D"]})

    res = {
        "spike": "H176",
        "attacks": "H163 (C2_exact_bit_parity / F1_digest_divergence)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.perf_counter() - t0, 3),
        "device_arm": "GATED, not dropped: `sh spikes/quiet.sh --device` exits 1, "
                      "REFUSED - multiple(R5CY93675MK emulator-5554)",
        "digests_are_recomputed_per_device": True,
        "digests_note": "run_single shells a real binary per target and parses that "
                        "process's own stdout; the read-one-compare-to-itself hypothesis is FALSE",
        "arms": {
            "A_honest": {"divergence": verdicts["A"], "tasks_wrong": 0},
            "B_mutant_ignores_input": {"divergence": verdicts["B"], "tasks_wrong": n_wrong_b},
            "C_positive_control_corrupt_digest": {"divergence": verdicts["C"], "tasks_wrong": 1},
            "D_positive_control_rc_nonzero": {"divergence": verdicts["D"], "tasks_wrong": 1},
        },
        "bound_predicate_H161_172": {"A_honest": bound_a, "B_mutant": bound_b},
        "class_sweep": {
            "H163/run.py:162": "DISJOINS -- blind to misroute",
            "H161/run.py:172": "BINDS (dig1 != PIN_F001 or dig2 != PIN_F002)",
            "H155/run.py:187": "BINDS (d1 == PIN_F001 and d2 == PIN_F002)",
            "why": "H161/H155 run two jobs and bind positionally; H163 drains 250 "
                   "futures with as_completed, which destroys dispatch order",
        },
        "controls": {"C1_pins_distinct": {"ok": c1_ok},
                     "C2_honest_arm_reproduces": {"ok": c2_ok},
                     "C3_pins_intact": {"ok": c3_ok}},
        "falsifiers": {"F1_fixture_is_bound": {"fired": f1},
                       "F2_mutant_is_caught": {"fired": f2},
                       "F3_my_harness_is_inert": {"fired": f3}},
    }
    out = Path(HERE) / "result.json"
    out.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[os.path.join(SPIKES, "H163_tri_device_p2p_swarm")],
        artifacts=[str(out)],
        controls=controls, falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="H163's parity predicate binds each digest to the fixture that was "
                  "requested, so a worker ignoring its input is caught",
        allow_dirty=True,
        note="H176: H163's parity control accepts either pin for every task.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
