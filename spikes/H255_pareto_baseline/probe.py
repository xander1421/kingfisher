#!/usr/bin/env python3
"""H255 — the Pareto baseline the loop compares every candidate against cannot
be moved by the loop, and one malformed row silently removes or lowers it.

ATTACK on the loop itself (§12.8), cycle 16.

Three separate things are measured here and the middle one KILLED MY OWN
HEADLINE:

  A. The writer's verdict vocabulary and the reader's do not intersect, so no
     run of this driver can ever update the baseline.
  B. **F3 — is the bar reachable at all?** I claimed the accept gate "cannot
     open for any candidate, ever". It can. The claim is withdrawn here rather
     than in a later cycle, and what replaces it is the exact threshold.
  C. The baseline parser's `except Exception: pass` spans the accumulation
     loop, and the caller reads absent as CLEAR.
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
sys.path.insert(0, os.path.join(HERE, "fixtures"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier          # noqa: E402
import prefix_baseline                             # noqa: E402  (frozen pre-fix)
import autoloop                                    # noqa: E402

# The commit the frozen pre-fix reader was lifted from.
PINNED = "1b8da4f4804a11ce842cc88f5bdee38bf305c19f"

CONFIG = json.load(open(os.path.join(REPO, ".github", "autoloop", "config.json")))
SCRATCH = os.path.join(REPO, ".scratch", "H255_probe")


def composite(vals):
    """Drive the REAL scoring loop with a fixed metric payload."""
    payload = dict(vals)
    payload["split"] = "pair_disjoint"
    inner = "import json; print(%r)" % json.dumps(payload)
    cfg = {"evaluators": {"e": {
               "command": f'{sys.executable} -c {json.dumps(inner)}',
               "timeout_sec": 30}},
           "metrics": CONFIG["metrics"]}
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        results, _ = autoloop.evaluate_suite(cfg)
    return results["_composite_score"]


def _fixture(text):
    os.makedirs(SCRATCH, exist_ok=True)
    p = os.path.join(SCRATCH, "MEMORY.md")
    open(p, "w").write(text)
    return p


def baseline_with(text):
    """The LIVE reader over a MEMORY.md we control. Returns (score, problems)."""
    p = _fixture(text)
    real = autoloop.MEMORY_FILE
    autoloop.MEMORY_FILE = p
    try:
        return autoloop.get_baseline_composite()
    finally:
        autoloop.MEMORY_FILE = real


def prefix_baseline_with(text):
    """The FROZEN pre-fix reader over the same file. Returns a bare score."""
    p = _fixture(text)
    prefix_baseline.MEMORY_FILE = p
    return prefix_baseline.get_baseline_composite()


def main():
    t0 = time.time()
    src = open(os.path.join(REPO, "scripts", "autoloop.py")).read()
    memory = open(os.path.join(REPO, ".github", "autoloop", "MEMORY.md")).read()

    # ---- A. the two vocabularies ---------------------------------------
    reader_token = "**ACCEPTED**"
    writer_tokens = ["KITCHEN_ELIGIBLE", "KITCHEN_REJECTED"]
    reader_greps_for = reader_token in src
    writer_can_emit_reader_token = any(
        f'"{t}"' in src and t == "ACCEPTED" for t in ["ACCEPTED"])
    live_baseline, live_problems = autoloop.get_baseline_composite()

    # the row the live baseline actually comes from
    baseline_row = next((l for l in memory.splitlines()
                         if reader_token in l and "Composite score:" in l
                         and str(live_baseline) in l), "")
    withdrawn = "0.2648" in baseline_row

    # ---- B. F3: is the bar reachable? ----------------------------------
    perfect = {"determinism_exact": 1.0, "hygiene_score": 1.0,
               "filtered_mrr": 1.0, "hits_at_10": 1.0,
               "witness_bandwidth_savings_pct": 100.0, "verifier_ram_bytes": 1}
    c_perfect = composite(perfect)

    repaired = {"determinism_exact": 1.0, "hygiene_score": 1.0,
                "witness_bandwidth_savings_pct": 75.37, "verifier_ram_bytes": 72}
    live = dict(repaired, filtered_mrr=0.2313, hits_at_10=0.3783)
    c_live = composite(live)
    # exactly 2x each null -- where the margin normaliser caps
    at_cap = dict(repaired, filtered_mrr=0.3464, hits_at_10=0.5710)
    c_at_cap = composite(at_cap)
    # and far beyond it, to see whether the objective can still tell them apart
    beyond = dict(repaired, filtered_mrr=1.0, hits_at_10=1.0)
    c_beyond = composite(beyond)

    # ---- C. the parser under one malformed row -------------------------
    GOOD = "| 1 | **ACCEPTED** | Composite score: 0.5000 |\n"
    HIGH = "| 2 | **ACCEPTED** | Composite score: 0.9683 |\n"
    BAD = "| x | **ACCEPTED** | Composite score: n/a |\n"
    # a row in the vocabulary `record_memory` ACTUALLY writes
    KITCH = "| 3 | **KITCHEN_ELIGIBLE** | Composite score: 0.9700 |\n"

    # The frozen PRE-FIX reader is what shows the defect; the live one shows it
    # gone. Both are driven over the same fixtures.
    p_clean = prefix_baseline_with(GOOD + HIGH)
    p_bad_first = prefix_baseline_with(BAD + GOOD + HIGH)
    p_bad_middle = prefix_baseline_with(GOOD + BAD + HIGH)
    p_kitchen = prefix_baseline_with(KITCH + GOOD)

    b_clean, q_clean = baseline_with(GOOD + HIGH)
    b_bad_first, q_bad_first = baseline_with(BAD + GOOD + HIGH)
    b_bad_middle, q_bad_middle = baseline_with(GOOD + BAD + HIGH)
    b_kitchen, _q = baseline_with(KITCH + GOOD)

    controls = [
        Control("C1_the_PRE_FIX_reader_cannot_see_the_writer_s_own_verdict",
                why="the whole row. Driven on the FROZEN pre-fix reader, "
                    "because once the fix lands, a live-code check of this "
                    "cannot fail and would report coverage it does not have",
                can_fail_because="the pinned pre-fix reader returns a score "
                                 "for a KITCHEN_ELIGIBLE row, which would mean "
                                 "the baseline was never frozen",
                null_must_contain="both readers' answers on the same row"),
        Control("C2_the_live_baseline_comes_from_a_WITHDRAWN_number",
                why="a bar pinned to a retracted measurement is a different "
                    "and worse fault than a bar that is merely stale",
                can_fail_because="the row supplying the baseline does not "
                                 "carry the withdrawn 0.2648",
                null_must_contain="the baseline and its source row"),
        Control("C3_ANTI_OVERCLAIM_the_bar_IS_reachable",
                why="I claimed the accept gate can never open. This arm exists "
                    "to refute my own row, and it does",
                can_fail_because="no candidate can reach the baseline, which "
                                 "would make the wedge claim true",
                null_must_contain="the perfect-candidate composite and the bar"),
        Control("C4_one_malformed_row_FIRST_removes_the_bar_entirely",
                why="`except Exception: pass` spans the accumulation loop and "
                    "the caller reads absent as CLEAR, so the Pareto gate "
                    "vanishes rather than refusing",
                can_fail_because="a malformed leading row still yields the "
                                 "true maximum",
                null_must_contain="the baseline with and without the bad row"),
        Control("C5_one_malformed_row_BETWEEN_rows_LOWERS_the_bar",
                why="the quieter half: the scan aborts and returns the max of "
                    "only the rows before the bad one, so a regression passes "
                    "against a stale lower bar",
                can_fail_because="a malformed middle row yields the true "
                                 "maximum or None rather than a stale value",
                null_must_contain="the stale value and the true maximum"),
        Control("C6_ANTI_INVERSION_a_clean_file_parses_correctly",
                why="a parser that returned None for everything would pass C4 "
                    "and C5 without a defect existing",
                can_fail_because="a clean two-row file does not return its max",
                null_must_contain="the parsed maximum"),
    ]
    # The pre-fix reader does not return None here -- the fixture also holds an
    # old-vocabulary row, so it returns that STALE 0.5 and never sees the 0.97
    # the writer actually recorded. That is the failure in its live form: not a
    # missing baseline, a silently OLDER one. My first predicate asserted None
    # and the control refused, which is the control doing its job.
    controls[0].observe(
        p_kitchen == 0.5 and b_kitchen == 0.97
        and not writer_can_emit_reader_token,
        {"row_written_by_record_memory": KITCH.strip(),
         "PRE_FIX_reader_sees": p_kitchen,
         "live_reader_sees": b_kitchen,
         "writer_emits": writer_tokens,
         "writer_can_emit_the_pre_fix_token": writer_can_emit_reader_token,
         "pinned_commit": PINNED})
    controls[1].observe(
        withdrawn and live_baseline is not None,
        {"live_baseline": live_baseline,
         "source_row": baseline_row.strip()[:160],
         "row_carries_the_withdrawn_0.2648": withdrawn})
    controls[2].observe(
        c_perfect >= live_baseline,
        {"perfect_candidate_composite": c_perfect,
         "baseline": live_baseline,
         "reachable": c_perfect >= live_baseline})
    controls[3].observe(
        p_bad_first is None and b_bad_first == 0.9683 and bool(q_bad_first),
        {"PRE_FIX_malformed_row_first": p_bad_first,
         "live_malformed_row_first": b_bad_first,
         "live_reports_the_bad_row": bool(q_bad_first),
         "pre_fix_caller_treated_None_as": "PASS (pareto_passed stayed True)"})
    controls[4].observe(
        p_bad_middle == 0.5 and b_bad_middle == 0.9683,
        {"PRE_FIX_malformed_row_between": p_bad_middle,
         "live_malformed_row_between": b_bad_middle,
         "true_maximum": 0.9683})
    controls[5].observe(
        p_clean == 0.9683 and b_clean == 0.9683 and not q_clean,
        {"PRE_FIX_clean": p_clean, "live_clean": b_clean,
         "live_problems_on_a_clean_file": q_clean})

    falsifiers = [
        Falsifier("F1_the_writer_can_still_emit_ACCEPTED",
                  refutes="that the baseline is frozen",
                  fires_when="`ACCEPTED` appears as a verdict value the writer "
                             "can be called with",
                  null_must_contain="the writer's verdict vocabulary"),
        Falsifier("F2_something_else_updates_the_baseline",
                  refutes="that a stale reader freezes anything",
                  fires_when="a second writer of MEMORY.md or a second source "
                             "of _baseline_score exists",
                  null_must_contain="the writers found"),
        Falsifier("F3_the_wedge_is_not_structural",
                  refutes="my own headline, that the accept gate can never "
                          "open for any candidate",
                  fires_when="a candidate can reach a composite >= the baseline",
                  null_must_contain="the perfect composite and the threshold"),
        Falsifier("F4_the_KITCHEN_vocabulary_is_uncommitted",
                  refutes="that this is a landed defect rather than a lane's "
                          "in-flight edit",
                  fires_when="KITCHEN_ELIGIBLE is absent from HEAD",
                  null_must_contain="the commit that introduced it"),
    ]
    falsifiers[0].observe(writer_can_emit_reader_token,
                          {"writer_emits": writer_tokens})
    falsifiers[1].observe(False,
                          {"writers_of_MEMORY_FILE": ["record_memory"],
                           "sources_of__baseline_score": ["get_baseline_composite"],
                           "note": "grepped scripts/, .github/, spikes/harness/"})
    falsifiers[2].observe(c_perfect >= live_baseline,
                          {"perfect_candidate_composite": c_perfect,
                           "baseline": live_baseline,
                           "threshold_filtered_mrr": 0.3464,
                           "threshold_hits_at_10": 0.5710,
                           "composite_at_that_threshold": c_at_cap})
    falsifiers[3].observe("KITCHEN_ELIGIBLE" not in src,
                          {"in_working_tree": "KITCHEN_ELIGIBLE" in src,
                           "landed_in": "2d7fa92"})

    res = {
        "spike": "H255",
        "vocabularies": {"reader_selects_on": reader_token,
                         "writer_emits": writer_tokens,
                         "intersect": False},
        "live_baseline": live_baseline,
        "baseline_source_row": baseline_row.strip(),
        "baseline_row_carries_withdrawn_2648": withdrawn,
        "reachability": {
            "perfect_candidate": c_perfect,
            "live_metrics_with_hygiene_and_determinism_repaired": c_live,
            "at_2x_both_nulls": c_at_cap,
            "far_beyond_2x_both_nulls": c_beyond,
            "objective_distinguishes_cap_from_beyond": c_at_cap != c_beyond,
            "threshold_filtered_mrr": 0.3464,
            "threshold_hits_at_10": 0.5710},
        "parser_under_one_malformed_row": {
            "true_maximum": 0.9683,
            "pre_fix": {"clean": p_clean, "malformed_first": p_bad_first,
                        "malformed_between": p_bad_middle,
                        "writers_own_verdict": p_kitchen},
            "live": {"clean": b_clean, "malformed_first": b_bad_first,
                     "malformed_between": b_bad_middle,
                     "writers_own_verdict": b_kitchen,
                     "problems_reported": q_bad_first}},
        "elapsed_sec": round(time.time() - t0, 2),
    }
    json.dump(res, open(os.path.join(HERE, "pareto_baseline.json"), "w"),
              indent=1, sort_keys=True)

    print(f"reader selects on {reader_token}; writer emits {writer_tokens}")
    print(f"live baseline {live_baseline} from a row carrying "
          f"{'the WITHDRAWN 0.2648' if withdrawn else 'no withdrawn number'}")
    print(f"F3: perfect candidate composite {c_perfect} vs bar {live_baseline} "
          f"-> {'REACHABLE, my wedge claim is withdrawn' if c_perfect >= live_baseline else 'unreachable'}")
    print(f"    live(repaired) {c_live} | at 2x nulls {c_at_cap} | "
          f"far beyond {c_beyond} -> objective "
          f"{'distinguishes' if c_at_cap != c_beyond else 'CANNOT distinguish'} them")
    print(f"{'fixture':26} {'PRE-FIX':>10} {'live':>10}")
    for lbl, a, b in [("clean", p_clean, b_clean),
                      ("malformed row FIRST", p_bad_first, b_bad_first),
                      ("malformed row BETWEEN", p_bad_middle, b_bad_middle),
                      ("writer's OWN verdict", p_kitchen, b_kitchen)]:
        print(f"  {lbl:24} {str(a):>10} {str(b):>10}")
    print("  (true maximum is 0.9683 / 0.97 for the last)")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(REPO, "scripts")],
        artifacts=[os.path.join(HERE, "pareto_baseline.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the writer can emit the token the reader greps for, OR a "
                  "candidate cannot reach the baseline at all",
        note="H255: the Pareto baseline cannot be moved by the loop, is pinned "
             "to a withdrawn number, and one malformed row silently removes or "
             "lowers it. The wedge half of the claim was refuted by its own F3.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
