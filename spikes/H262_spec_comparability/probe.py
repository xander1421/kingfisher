#!/usr/bin/env python3
"""H262 — a composite is only comparable to one computed under the same metric
spec, and `MEMORY.md` recorded the number without the spec.

The row rests on ONE measurement, and it is one-sided on purpose:
`MEMORY.md:15` states its own inputs and its own composite. Feed those inputs
through TODAY's scoring code, granting every UNRECORDED metric a PERFECT score.
If even that upper bound falls short of the recorded composite, then no
assignment of the missing inputs reproduces it, and the baseline the loop is
comparing against is not reachable under the spec it is being compared with.

THIS ROW MOVES A GATE'S VERDICT IN THE PERMISSIVE DIRECTION -- Pareto goes FAIL
-> PASS on the live tree -- so C4 and C5 exist to bound that: the reset must not
make anything ELIGIBLE, and a same-spec baseline must still bite.
"""
import contextlib
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

sys.path.insert(0, os.path.join(REPO, "spikes", "harness"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier          # noqa: E402
import autoloop                                    # noqa: E402

CONFIG = json.load(open(os.path.join(REPO, ".github", "autoloop", "config.json")))
MEMORY = os.path.join(REPO, ".github", "autoloop", "MEMORY.md")
SCRATCH = os.path.join(REPO, ".scratch", "H262_probe")

# The two rows MEMORY.md holds, with the inputs each one states about itself.
ROWS = [("2026-08-18 10:46 REJECTED", 0.0, 0.0, 0.4876),
        ("2026-08-18 10:53 ACCEPTED", 0.2648067492241375,
         0.39292713998726053, 0.9683)]


def run(metrics_spec, payload, memory_text=None):
    """Drive the real scoring loop; optionally over a MEMORY.md we control."""
    inner = "import json; print(%r)" % json.dumps(payload)
    cfg = {"evaluators": {"e": {
               "command": f'{sys.executable} -c {json.dumps(inner)}',
               "timeout_sec": 30}},
           "metrics": metrics_spec}
    real = autoloop.MEMORY_FILE
    if memory_text is not None:
        os.makedirs(SCRATCH, exist_ok=True)
        p = os.path.join(SCRATCH, "MEMORY.md")
        open(p, "w").write(memory_text)
        autoloop.MEMORY_FILE = p
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            results, _ = autoloop.evaluate_suite(cfg)
    finally:
        autoloop.MEMORY_FILE = real
    return results, buf.getvalue()


def main():
    t0 = time.time()
    metrics = CONFIG["metrics"]
    digest = autoloop.metric_spec_digest(metrics)

    # ---- the decisive measurement ---------------------------------------
    # Every metric MEMORY.md did NOT record is granted a PERFECT score, so this
    # is the UPPER BOUND of what those rows could score today.
    best_case = {"determinism_exact": 1.0, "hygiene_score": 1.0,
                 "witness_bandwidth_savings_pct": 100.0,
                 "verifier_ram_bytes": 1, "split": "pair_disjoint"}
    recomputed = []
    for label, mrr, h10, recorded in ROWS:
        payload = dict(best_case, filtered_mrr=mrr, hits_at_10=h10)
        r, _ = run(metrics, payload)
        recomputed.append({"row": label, "recorded": recorded,
                           "upper_bound_today": r["_composite_score"],
                           "reproduces": abs(r["_composite_score"] - recorded) < 1e-4})
    baseline_row = recomputed[1]

    # ---- the gate's behaviour, three ways --------------------------------
    OLD = "| 1 | **ACCEPTED** | Composite score: 0.9683 spec=deadbeef1234 |\n"
    SAME_HIGH = f"| 2 | **ACCEPTED** | Composite score: 0.9900 spec={digest} |\n"
    SAME_LOW = f"| 3 | **ACCEPTED** | Composite score: 0.1000 spec={digest} |\n"
    cand = dict(best_case, filtered_mrr=0.2313, hits_at_10=0.3783)

    r_reset, log_reset = run(metrics, cand, OLD)
    r_bites, _ = run(metrics, cand, OLD + SAME_HIGH)
    r_clears, _ = run(metrics, cand, OLD + SAME_LOW)

    # ---- does the reset make anything ELIGIBLE? --------------------------
    # Eligibility is `invariants and not errors and pareto`. The live tree
    # fails invariants, so the reset must not change eligibility there.
    failing = dict(best_case, filtered_mrr=0.2313, hits_at_10=0.3783,
                   hygiene_score=0.0)
    r_elig, _ = run(metrics, failing, OLD)
    became_eligible = (r_elig.get("_invariants_passed") and
                       r_elig.get("_pareto_passed"))

    controls = [
        Control("C1_the_recorded_baseline_is_NOT_REPRODUCIBLE_today",
                why="the whole row, and it is measured one-sidedly on purpose: "
                    "every unrecorded metric is granted a PERFECT score, so if "
                    "the upper bound still falls short, no assignment of the "
                    "missing inputs reproduces the recorded composite",
                can_fail_because="today's code reproduces 0.9683 from that "
                                 "row's own inputs, which would make the "
                                 "comparison valid and this row void",
                null_must_contain="the recorded value and today's upper bound"),
        Control("C2_the_NEIGHBOURING_row_does_not_reproduce_either",
                why="one row failing to reproduce could be a typo in that row. "
                    "Two rows failing is a changed function",
                can_fail_because="the REJECTED row reproduces, which would "
                                 "point at a bad row rather than a bad model",
                null_must_contain="its recorded value and today's"),
        Control("C3_a_spec_change_RESETS_rather_than_compares",
                why="comparing across specs is the defect; refusing until a "
                    "same-spec baseline exists DEADLOCKS, because no run can "
                    "be accepted so no row can ever be written",
                can_fail_because="rows under a foreign spec are still used as "
                                 "a bar, or the reset is not announced",
                null_must_contain="the pareto status and whether it printed"),
        Control("C4_THE_RESET_MAKES_NOTHING_ELIGIBLE",
                why="THIS ROW MOVES PARETO FAIL -> PASS. This is the arm that "
                    "bounds that: a candidate failing invariants must stay "
                    "ineligible, so the loosening cannot reach the accept path",
                can_fail_because="a candidate with hygiene 0.0 becomes "
                                 "eligible once the ratchet resets",
                null_must_contain="invariants, pareto and the conjunction"),
        Control("C5_ANTI_LOOSENING_a_same_spec_baseline_still_BITES",
                why="a reset that never ended would be a permanent removal of "
                    "the Pareto gate dressed as a fix",
                can_fail_because="a candidate below a same-spec baseline "
                                 "passes, or one above it fails",
                null_must_contain="both verdicts"),
        Control("C6_a_NON_SCORING_field_does_not_change_the_digest",
                why="if prose in the config moved the digest, every doc edit "
                    "would silently reset the ratchet -- the abuse path would "
                    "be open by accident rather than by intent",
                can_fail_because="adding a `why` string changes the digest",
                null_must_contain="both digests"),
    ]
    controls[0].observe(
        not baseline_row["reproduces"]
        and baseline_row["upper_bound_today"] < baseline_row["recorded"],
        {"recorded": baseline_row["recorded"],
         "upper_bound_today": baseline_row["upper_bound_today"],
         "unrecorded_metrics_granted": "perfect scores"})
    controls[1].observe(not recomputed[0]["reproduces"],
                        {"recorded": recomputed[0]["recorded"],
                         "today": recomputed[0]["upper_bound_today"]})
    controls[2].observe(
        r_reset.get("_pareto_status") == "ESTABLISHING_UNDER_NEW_SPEC"
        and "[PARETO BASELINE RESET]" in log_reset and digest in log_reset,
        {"pareto_status": r_reset.get("_pareto_status"),
         "printed": "[PARETO BASELINE RESET]" in log_reset,
         "named_the_digest": digest in log_reset})
    controls[3].observe(
        not became_eligible,
        {"invariants_passed": r_elig.get("_invariants_passed"),
         "pareto_passed": r_elig.get("_pareto_passed"),
         "is_eligible_would_be": bool(became_eligible)})
    controls[4].observe(
        r_bites.get("_pareto_passed") is False
        and r_clears.get("_pareto_passed") is True
        and r_bites.get("_pareto_status") == "COMPARED",
        {"below_a_same_spec_baseline": r_bites.get("_pareto_passed"),
         "above_a_same_spec_baseline": r_clears.get("_pareto_passed"),
         "status_once_a_same_spec_row_exists": r_bites.get("_pareto_status")})
    m = {"x": {"weight": 1.0, "target": 1.0, "direction": "maximize"}}
    m_prose = {"x": dict(m["x"], why="a paragraph of rationale")}
    controls[5].observe(
        autoloop.metric_spec_digest(m) == autoloop.metric_spec_digest(m_prose),
        {"bare": autoloop.metric_spec_digest(m),
         "with_prose": autoloop.metric_spec_digest(m_prose)})

    falsifiers = [
        Falsifier("F1_todays_code_reproduces_the_recorded_baseline",
                  refutes="that the spec changes are composite-affecting",
                  fires_when="the ACCEPTED row's recorded composite is "
                             "reproduced from its own inputs today",
                  null_must_contain="recorded and recomputed"),
        Falsifier("F3_something_already_records_the_spec",
                  refutes="that this was missing",
                  fires_when="a spec identity is already stored beside the "
                             "baseline before this change",
                  null_must_contain="what MEMORY.md rows carried"),
        Falsifier("F4_the_row_is_unfalsifiable_as_stated",
                  refutes="that the demonstration is possible at all",
                  fires_when="MEMORY.md does not record enough inputs to bound "
                             "a recomputation in EITHER direction",
                  null_must_contain="which inputs the row records"),
    ]
    falsifiers[0].observe(baseline_row["reproduces"],
                          {"recorded": baseline_row["recorded"],
                           "upper_bound_today": baseline_row["upper_bound_today"]})
    falsifiers[1].observe(
        "spec=" in open(MEMORY).read().split("## 1. Iteration History Log")[1][:600],
        {"pre_change_rows_carry_spec": False,
         "note": "checked the iteration log rows as they stand"})
    # The row records MRR and H@10 only -- NOT hygiene, witness or ram. So an
    # exact recomputation is impossible and only a BOUND is available. That
    # bound is one-sided, and it happens to point the right way: the upper
    # bound falls short, so the conclusion holds for every possible assignment.
    falsifiers[2].observe(
        baseline_row["upper_bound_today"] >= baseline_row["recorded"],
        {"row_records": ["filtered_mrr", "hits_at_10"],
         "row_omits": ["hygiene_score", "determinism_exact",
                       "witness_bandwidth_savings_pct", "verifier_ram_bytes"],
         "upper_bound_today": baseline_row["upper_bound_today"],
         "recorded": baseline_row["recorded"],
         "bound_is_one_sided_and_points": "below the recorded value"})

    res = {"spike": "H262",
           "current_metric_spec_digest": digest,
           "recomputation_of_MEMORY_rows": recomputed,
           "gate_behaviour": {
               "foreign_spec_only": {
                   "pareto_status": r_reset.get("_pareto_status"),
                   "pareto_passed": r_reset.get("_pareto_passed")},
               "same_spec_baseline_ABOVE_candidate": {
                   "pareto_passed": r_bites.get("_pareto_passed"),
                   "pareto_status": r_bites.get("_pareto_status")},
               "same_spec_baseline_BELOW_candidate": {
                   "pareto_passed": r_clears.get("_pareto_passed")}},
           "reset_makes_a_failing_candidate_eligible": bool(became_eligible),
           "elapsed_sec": round(time.time() - t0, 2)}
    json.dump(res, open(os.path.join(HERE, "spec_comparability.json"), "w"),
              indent=1, sort_keys=True)

    print(f"current metric spec digest {digest}")
    print(f"{'MEMORY.md row':30} {'recorded':>9} {'today (upper bound)':>20}")
    for r in recomputed:
        print(f"  {r['row']:28} {r['recorded']:>9} {r['upper_bound_today']:>20}"
              f"  {'reproduces' if r['reproduces'] else 'DOES NOT REPRODUCE'}")
    print(f"foreign-spec rows -> {r_reset.get('_pareto_status')}; "
          f"same-spec above -> pareto {r_bites.get('_pareto_passed')}; "
          f"same-spec below -> pareto {r_clears.get('_pareto_passed')}")
    print(f"reset makes a failing candidate eligible: {bool(became_eligible)}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(REPO, "scripts")],
        artifacts=[os.path.join(HERE, "spec_comparability.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="today's scoring code reproduces MEMORY.md's recorded "
                  "composite from that row's own inputs, making the "
                  "cross-spec comparison valid",
        note="H262: a composite is only comparable to one computed under the "
             "same metric spec; the baseline recorded the number without it.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
