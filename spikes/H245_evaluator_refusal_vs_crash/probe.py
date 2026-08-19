#!/usr/bin/env python3
"""H245 — an evaluator that REFUSED and one that CRASHED are the same event to
the loop's runner, because `run_evaluator` returns on the exit code before the
payload is ever parsed.

Runs every shape an evaluator can end in through the FROZEN pre-fix runner and
through the LIVE one, and reports where the two disagree. The pre-fix side is a
verbatim AST copy pinned in `fixtures/prefix_runner.py`, not a re-read of
`HEAD`: H237's pre-fix arm read `HEAD` after the fix had landed there and so
could not fail.

The arm that decides whether this is a fix or a loosening is C5 — the recovered
payload must still FAIL invariants, and it must fail them as an INVARIANT
VIOLATION rather than as a MISSING METRIC.
"""
import io
import json
import os
import subprocess
import sys
import time
from contextlib import redirect_stderr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "fixtures")

sys.path.insert(0, os.path.join(REPO, "spikes", "harness"))
sys.path.insert(0, FIX)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier          # noqa: E402
import prefix_runner                               # noqa: E402  (frozen pre-fix)
import autoloop                                    # noqa: E402  (live)

# The commit the frozen copy was lifted from, so a reader can diff it.
PINNED = "cb6264fdb1a1e72b7fef00e222d7e112a564c74a"

# name -> (fixture, what it is, does a MEASUREMENT exist in it?)
SHAPES = [
    ("refuse_with_payload", "ev_refuse_with_payload.py",
     "ran and refused: full payload on stdout, exit 1", True),
    ("crash", "ev_crash.py",
     "crashed: empty stdout, traceback on stderr, exit != 0", False),
    ("truncated", "ev_truncated.py",
     "died mid-write: half a JSON object, exit 1", False),
    ("error_payload_exit0", "ev_error_payload_exit0.py",
     "the existing lesson: exit 0, zeroed metrics, `error` set", False),
    ("clean", "ev_clean.py",
     "ran and passed: payload, exit 0", True),
    ("refuse_no_payload", "ev_refuse_no_payload.py",
     "the documented exit-2 contract: refuses, emits NO metric", False),
    ("json_list", "ev_json_list.py",
     "well-formed JSON that is not a payload: a list, exit 0", False),
]


def drive(runner, fixture):
    """(kept, err) for one runner against one fixture."""
    cmd = f"{sys.executable} {os.path.join(FIX, fixture)}"
    data, err = runner("probe", cmd, cwd=REPO, timeout=30)
    return data, err


def end_to_end():
    """C5. The real scoring path, with hygiene's refusal payload present.

    A synthetic config so this cannot depend on the tree's live metric values,
    and so the arm still means something on a machine with no `adb`.
    """
    cfg = {
        "evaluators": {
            "hygiene": {"command": f"{sys.executable} "
                                   f"{os.path.join(FIX, 'ev_refuse_with_payload.py')}",
                        "timeout_sec": 30},
        },
        "metrics": {
            "hygiene_score": {"direction": "maximize", "target": 1.0,
                              "min_acceptable": 1.0, "weight": 1.0},
        },
    }
    buf = io.StringIO()
    with redirect_stderr(buf):
        results, errors = autoloop.evaluate_suite(cfg)
    return results, errors, buf.getvalue()


def main():
    t0 = time.time()
    rows = []
    for name, fixture, what, measurement_exists in SHAPES:
        pre_data, pre_err = drive(prefix_runner.run_evaluator, fixture)
        post_data, post_err = drive(autoloop.run_evaluator, fixture)
        rows.append({
            "shape": name,
            "what_it_is": what,
            "a_measurement_exists": measurement_exists,
            "prefix_kept_it": pre_data is not None,
            "prefix_err": (pre_err or "")[:80],
            "live_kept_it": post_data is not None,
            "live_err": (post_err or "")[:80],
            "disagree": (pre_data is None) != (post_data is None),
        })

    by = {r["shape"]: r for r in rows}
    # correct == the runner keeps a payload exactly when a measurement exists
    pre_wrong = [r["shape"] for r in rows
                 if r["prefix_kept_it"] != r["a_measurement_exists"]]
    live_wrong = [r["shape"] for r in rows
                  if r["live_kept_it"] != r["a_measurement_exists"]]

    e_results, e_errors, e_log = end_to_end()
    e_val = e_results.get("hygiene_score")
    e_inv = e_results.get("_invariants_passed")
    e_violation = "[INVARIANT VIOLATION] hygiene_score" in e_log
    e_missing = "[MISSING METRIC] hygiene_score" in e_log

    controls = [
        Control("C1_the_prefix_runner_really_does_discard_a_refusal",
                why="if it kept the payload there is no defect and the row is "
                    "void; this is the arm that can retire the whole row",
                can_fail_because="the pinned pre-fix runner returns the "
                                 "payload for `refuse_with_payload`",
                null_must_contain="the pre-fix verdict for that shape"),
        Control("C2_the_fix_does_not_swallow_a_crash",
                why="the mirror collapse. Trading `refusal read as crash` for "
                    "`crash read as measurement` is not a fix",
                can_fail_because="the live runner keeps a payload for crash, "
                                 "truncated or refuse_no_payload",
                null_must_contain="the live verdict for all three"),
        Control("C3_the_exit0_plus_error_lesson_survives",
                why="already learned once, in the opposite direction; a fix "
                    "that regresses it re-opens the cold-start defect",
                can_fail_because="the live runner keeps `error_payload_exit0`",
                null_must_contain="its live verdict"),
        Control("C4_the_happy_path_is_untouched",
                why="a runner that broke exit-0 evaluators to fix exit-1 ones "
                    "would trade the whole loop for one metric",
                can_fail_because="the live runner drops `clean`",
                null_must_contain="its live verdict"),
        Control("C6_NOT_A_LOOSENING_the_refusal_is_still_an_error",
                why="`is_eligible` is `invariants and not errors and pareto`. "
                    "Returning only the payload would move an evaluator that "
                    "refused while emitting IN-BOUNDS metrics from REJECTED to "
                    "ELIGIBLE -- a path no other arm here touches, because "
                    "hygiene's 0.0 fails invariants anyway and hides it",
                can_fail_because="the refusal is dropped from `errors` once "
                                 "its payload is kept",
                null_must_contain="the errors list from the end-to-end run"),
        Control("C5_NOT_A_LOOSENING_the_recovered_payload_still_fails",
                why="THE ARM THAT DECIDES fix vs loosening. hygiene_score 0.0 "
                    "recovered from a refusal must FAIL invariants, and must "
                    "fail as a VIOLATION, not as a MISSING METRIC",
                can_fail_because="invariants pass with 0.0 present, or the run "
                                 "still reports the metric as missing",
                null_must_contain="the recovered value, the invariant result "
                                  "and which of the two lines was printed"),
    ]
    controls[0].observe(
        by["refuse_with_payload"]["prefix_kept_it"] is False,
        {"prefix_kept_it": by["refuse_with_payload"]["prefix_kept_it"],
         "prefix_err": by["refuse_with_payload"]["prefix_err"],
         "pinned_commit": PINNED})
    controls[1].observe(
        not any(by[s]["live_kept_it"]
                for s in ("crash", "truncated", "refuse_no_payload")),
        {s: by[s]["live_kept_it"]
         for s in ("crash", "truncated", "refuse_no_payload")})
    controls[2].observe(
        by["error_payload_exit0"]["live_kept_it"] is False,
        {"live_kept_it": by["error_payload_exit0"]["live_kept_it"],
         "live_err": by["error_payload_exit0"]["live_err"]})
    controls[3].observe(
        by["clean"]["live_kept_it"] is True,
        {"live_kept_it": by["clean"]["live_kept_it"],
         "live_err": by["clean"]["live_err"]})
    controls[4].observe(
        len(e_errors) == 1 and e_errors[0][0] == "hygiene",
        {"errors": [f"{n}: {e[:70]}" for n, e in e_errors],
         "n_errors": len(e_errors),
         "why_it_matters": "is_eligible = invariants and not errors and pareto"})
    controls[5].observe(
        e_val == 0.0 and e_inv is False and e_violation and not e_missing,
        {"recovered_hygiene_score": e_val,
         "invariants_passed": e_inv,
         "printed_INVARIANT_VIOLATION": e_violation,
         "printed_MISSING_METRIC": e_missing})

    falsifiers = [
        Falsifier("F1_the_fix_changes_no_verdict",
                  refutes="that the defect is more than cosmetic",
                  fires_when="the live runner and the pinned pre-fix runner "
                             "agree on every one of the seven shapes",
                  null_must_contain="the count of shapes they disagree on"),
        Falsifier("F2_the_fix_swallows_a_genuine_crash",
                  refutes="that this is a fix rather than the mirror collapse",
                  fires_when="the live runner keeps a payload for any shape "
                             "that carries no measurement",
                  null_must_contain="the shapes the live runner gets wrong"),
        Falsifier("F3_the_existing_exit0_error_lesson_regressed",
                  refutes="that the change is additive",
                  fires_when="`error_payload_exit0` is kept by the live runner",
                  null_must_contain="its live verdict"),
    ]
    falsifiers[0].observe(
        not any(r["disagree"] for r in rows),
        {"shapes_they_disagree_on": [r["shape"] for r in rows if r["disagree"]],
         "n_disagree": sum(1 for r in rows if r["disagree"])})
    kept_without_measurement = [r["shape"] for r in rows
                                if r["live_kept_it"]
                                and not r["a_measurement_exists"]]
    falsifiers[1].observe(
        bool(kept_without_measurement),
        {"kept_without_measurement": kept_without_measurement,
         "live_wrong": live_wrong})
    falsifiers[2].observe(
        by["error_payload_exit0"]["live_kept_it"],
        {"live_kept_it": by["error_payload_exit0"]["live_kept_it"]})

    res = {
        "spike": "H245",
        "pinned_prefix_commit": PINNED,
        "shapes": rows,
        "prefix_runner_gets_wrong": pre_wrong,
        "live_runner_gets_wrong": live_wrong,
        "end_to_end": {
            "recovered_hygiene_score": e_val,
            "invariants_passed": e_inv,
            "printed_INVARIANT_VIOLATION": e_violation,
            "printed_MISSING_METRIC": e_missing,
            "errors": [f"{n}: {e[:60]}" for n, e in e_errors],
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    json.dump(res, open(os.path.join(HERE, "refusal_vs_crash.json"), "w"),
              indent=1, sort_keys=True)

    print(f"{'shape':22} {'measurement?':13} {'pre-fix':9} {'live':9}")
    for r in rows:
        print(f"  {r['shape']:20} {str(r['a_measurement_exists']):13} "
              f"{'KEPT' if r['prefix_kept_it'] else 'dropped':9} "
              f"{'KEPT' if r['live_kept_it'] else 'dropped':9}"
              f"{'   <- disagree' if r['disagree'] else ''}")
    print(f"\npre-fix runner gets wrong: {pre_wrong or 'nothing'}")
    print(f"live    runner gets wrong: {live_wrong or 'nothing'}")
    print(f"end-to-end: hygiene_score={e_val} invariants={e_inv} "
          f"VIOLATION={e_violation} MISSING={e_missing}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(REPO, "scripts"), FIX],
        artifacts=[os.path.join(HERE, "refusal_vs_crash.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the pinned pre-fix runner turns out to keep the refusal "
                  "payload (no defect), OR the live runner keeps a payload for "
                  "a shape that carries no measurement (the mirror collapse)",
        note="H245: the loop's runner returned on the exit code before parsing "
             "the payload, so a REFUSAL and a CRASH were one event and the "
             "loop reported `could not be checked` over a metric it checked.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
