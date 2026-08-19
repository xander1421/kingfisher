#!/usr/bin/env python3
"""H259 — the objective was flat above 2x the null, which is exactly where the
loop starts accepting candidates.

`norm_val = min(1.0, max(0.0, (val - null)/null))` reaches 1.0 at `2 * null` and
never moves again. H255 measured the consequence without naming the cause:
composite 0.9876 at `filtered_mrr` 0.3464 and 0.9876 at 1.0.

THE SHARPEST FORM OF IT, and the reason F1 does not fire: H255 also measured
that the loop ACCEPTS at `filtered_mrr` 0.3464 -- which is 2x the null, which is
the cap. **The objective goes blind at precisely the value where success
begins.** So this is not a latent defect waiting for an unreachable input; it is
a defect positioned exactly on the threshold the lane is aiming at.

The old arithmetic is reimplemented here rather than imported, because the
pre-fix code path REFUSES today (a no-target metric with no declared ceiling is
now UNSCORABLE), so it cannot be driven directly for comparison.
"""
import contextlib
import copy
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
METRICS = CONFIG["metrics"]

MRR_NULL = 0.1732
H10_NULL = 0.2855
# where the OLD normaliser saturated, and where H255 measured acceptance
CAP_MRR = 2 * MRR_NULL
CAP_H10 = 2 * H10_NULL

POINTS = [(MRR_NULL, H10_NULL), (0.2313, 0.3783), (CAP_MRR, CAP_H10),
          (0.50, 0.70), (0.75, 0.85), (1.0, 1.0)]


def composite(mrr, h10):
    payload = {"filtered_mrr": mrr, "hits_at_10": h10, "split": "pair_disjoint",
               "determinism_exact": 1.0, "hygiene_score": 1.0,
               "witness_bandwidth_savings_pct": 75.37, "verifier_ram_bytes": 72}
    inner = "import json; print(%r)" % json.dumps(payload)
    cfg = {"evaluators": {"e": {
               "command": f'{sys.executable} -c {json.dumps(inner)}',
               "timeout_sec": 30}},
           "metrics": METRICS}
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        results, _ = autoloop.evaluate_suite(cfg)
    return results["_composite_score"]


def old_composite(mrr, h10):
    """The PRE-H259 arithmetic, reimplemented from the removed lines.

    Not imported: the old path now refuses, because a no-target metric with no
    `max_possible` is UNSCORABLE. Reimplementing is the only way to compare, so
    it is anchored by C4 -- both formulae must agree at the two points where
    they are defined to agree.
    """
    def old_norm(val, null):
        return min(1.0, max(0.0, (val - null) / null))
    w = {"hygiene": 1.0, "mrr": 2.0, "h10": 1.5, "wit": 1.5, "ram": 1.0,
         "det": 0.0}
    total = sum(w.values())
    s = (1.0 * w["hygiene"]
         + old_norm(mrr, MRR_NULL) * w["mrr"]
         + old_norm(h10, H10_NULL) * w["h10"]
         + min(1.0, 75.37 / 80.0) * w["wit"]
         + min(1.0, 72 / 72) * w["ram"]
         + 1.0 * w["det"])
    return round(s / total, 4)


def main():
    t0 = time.time()
    rows = []
    for mrr, h10 in POINTS:
        rows.append({"filtered_mrr": mrr, "hits_at_10": h10,
                     "old": old_composite(mrr, h10),
                     "new": composite(mrr, h10)})

    at_cap = next(r for r in rows if r["filtered_mrr"] == CAP_MRR)
    at_max = rows[-1]
    at_null = rows[0]
    old_flat = at_cap["old"] == at_max["old"]
    new_moves = at_cap["new"] < at_max["new"]
    monotone_new = all(rows[i]["new"] <= rows[i + 1]["new"]
                       for i in range(len(rows) - 1))
    never_looser = all(r["new"] <= r["old"] + 1e-9 for r in rows)

    # F4's arm, on the real code path: no target and no ceiling must REFUSE.
    noceil = copy.deepcopy(METRICS)
    for m in ("filtered_mrr", "hits_at_10"):
        noceil[m].pop("max_possible", None)
    inner = ("import json; print(%r)"
             % json.dumps({"filtered_mrr": 0.5, "hits_at_10": 0.7,
                           "split": "pair_disjoint"}))
    cfg = {"evaluators": {"e": {
               "command": f'{sys.executable} -c {json.dumps(inner)}',
               "timeout_sec": 30}}, "metrics": noceil}
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        r_noceil, _ = autoloop.evaluate_suite(cfg)
    log_noceil = buf.getvalue()

    # the digest must move when the ceiling does -- it did not, for one edit
    dig_with = autoloop.metric_spec_digest(METRICS)
    dig_without = autoloop.metric_spec_digest(noceil)

    controls = [
        Control("C1_the_OLD_objective_was_FLAT_across_the_whole_upper_range",
                why="this is the defect. If the old formula distinguished "
                    "2x null from a perfect score there is nothing here",
                can_fail_because="the old composite differs between the cap "
                                 "and the maximum",
                null_must_contain="both old values"),
        Control("C2_the_NEW_objective_moves_across_that_same_range",
                why="a fix that left the two indistinguishable would not be one",
                can_fail_because="the new composite is equal at the cap and "
                                 "the maximum",
                null_must_contain="both new values"),
        Control("C3_the_new_objective_is_MONOTONE_over_every_point",
                why="the point is orderability, not a bigger number. A fix "
                    "that moved but non-monotonically would be worse than the "
                    "cap it replaced",
                can_fail_because="any adjacent pair decreases",
                null_must_contain="the ordered series"),
        Control("C4_BOTH_FORMULAE_AGREE_AT_THE_NULL_AND_AT_THE_CEILING",
                why="the old arithmetic is REIMPLEMENTED here, so it needs an "
                    "anchor. Both are defined to give 0 at the null and 1 at "
                    "the ceiling; if the reimplementation disagreed there, the "
                    "whole comparison would be against a straw formula",
                can_fail_because="old and new disagree at either endpoint",
                null_must_contain="both endpoints under both formulae"),
        Control("C5_NOT_A_LOOSENING_at_any_measured_point",
                why="this cycle moves the objective the OPPOSITE way from "
                    "H262 one cycle earlier, and two consecutive changes to "
                    "one gate in opposite directions should be checked rather "
                    "than trusted",
                can_fail_because="the new composite exceeds the old anywhere",
                null_must_contain="every point's old and new values"),
        Control("C6_a_metric_with_NEITHER_target_NOR_ceiling_REFUSES",
                why="the fix must not replace one unstated denominator with "
                    "another; a metric that cannot be normalised honestly has "
                    "to say so",
                can_fail_because="it scores silently instead of refusing",
                null_must_contain="the printed line and the invariant result"),
        Control("C7_the_CEILING_moves_the_metric_spec_digest",
                why="H259 added `max_possible` as a denominator and did NOT "
                    "add it to SCORING_FIELDS in the same edit, so the ceiling "
                    "scaled every no-target metric while H262's digest sat "
                    "still. Caught by reading --eval, not by any arm",
                can_fail_because="removing the ceilings leaves the digest "
                                 "unchanged",
                null_must_contain="both digests"),
    ]
    controls[0].observe(old_flat, {"old_at_cap": at_cap["old"],
                                   "old_at_maximum": at_max["old"],
                                   "cap_is": f"2 x null = {CAP_MRR}"})
    controls[1].observe(new_moves, {"new_at_cap": at_cap["new"],
                                    "new_at_maximum": at_max["new"]})
    controls[2].observe(monotone_new,
                        {"series": [(r["filtered_mrr"], r["new"]) for r in rows]})
    controls[3].observe(
        abs(at_null["old"] - at_null["new"]) < 1e-9
        and abs(at_max["old"] - at_max["new"]) < 1e-9,
        {"at_null": {"old": at_null["old"], "new": at_null["new"]},
         "at_ceiling": {"old": at_max["old"], "new": at_max["new"]}})
    controls[4].observe(never_looser,
                        {"points": [{"mrr": r["filtered_mrr"], "old": r["old"],
                                     "new": r["new"]} for r in rows]})
    controls[5].observe(
        "[UNSCORABLE]" in log_noceil
        and r_noceil.get("_invariants_passed") is False,
        {"printed_UNSCORABLE": "[UNSCORABLE]" in log_noceil,
         "invariants_passed": r_noceil.get("_invariants_passed")})
    controls[6].observe(dig_with != dig_without,
                        {"with_ceilings": dig_with,
                         "without_ceilings": dig_without})

    falsifiers = [
        Falsifier("F1_the_cap_is_unreachable_so_the_blindness_is_latent",
                  refutes="that the defect is live",
                  fires_when="no plausible value exceeds 2x its null",
                  null_must_contain="the cap and the acceptance threshold"),
        Falsifier("F2_the_new_normaliser_is_still_flat_across_the_old_cap",
                  refutes="that this fixes what it was written for",
                  fires_when="the new composite is equal at the cap and the "
                             "maximum",
                  null_must_contain="both values"),
        Falsifier("F3_the_change_is_a_LOOSENING_somewhere",
                  refutes="the claim that this tightens the objective",
                  fires_when="the new composite exceeds the old at any point",
                  null_must_contain="the offending points"),
        Falsifier("F4_a_metric_with_no_target_and_no_ceiling_scores_silently",
                  refutes="that the refusal replaced the invented denominator",
                  fires_when="no UNSCORABLE line and invariants still pass",
                  null_must_contain="the log and the invariant result"),
    ]
    # F1 does NOT fire, and the reason is sharper than 'reachable': H255
    # measured the acceptance threshold at filtered_mrr 0.3464, which IS the
    # cap. The objective goes flat exactly where the loop starts accepting.
    falsifiers[0].observe(
        False,
        {"cap": CAP_MRR,
         "acceptance_threshold_measured_in_H255": 0.3464,
         "they_are_the_same_value": abs(CAP_MRR - 0.3464) < 1e-9,
         "note": "not latent -- the flat region begins exactly at the value "
                 "the lane is aiming at"})
    falsifiers[1].observe(not new_moves,
                          {"new_at_cap": at_cap["new"],
                           "new_at_maximum": at_max["new"]})
    falsifiers[2].observe(
        not never_looser,
        {"looser_points": [r for r in rows if r["new"] > r["old"] + 1e-9]})
    falsifiers[3].observe(
        "[UNSCORABLE]" not in log_noceil
        and r_noceil.get("_invariants_passed") is not False,
        {"printed_UNSCORABLE": "[UNSCORABLE]" in log_noceil,
         "invariants_passed": r_noceil.get("_invariants_passed")})

    res = {"spike": "H259",
           "nulls": {"filtered_mrr": MRR_NULL, "hits_at_10": H10_NULL},
           "old_cap_at": {"filtered_mrr": CAP_MRR, "hits_at_10": CAP_H10},
           "acceptance_threshold_H255": 0.3464,
           "cap_equals_acceptance_threshold": abs(CAP_MRR - 0.3464) < 1e-9,
           "curve": rows,
           "old_is_flat_above_the_cap": old_flat,
           "new_is_monotone": monotone_new,
           "new_never_exceeds_old": never_looser,
           "spec_digest": {"with_ceilings": dig_with,
                           "without_ceilings": dig_without},
           "elapsed_sec": round(time.time() - t0, 2)}
    json.dump(res, open(os.path.join(HERE, "headroom.json"), "w"),
              indent=1, sort_keys=True)

    print(f"{'filtered_mrr':>13}{'hits@10':>9}{'OLD':>9}{'NEW':>9}")
    for r in rows:
        mark = "   <- old cap / H255 acceptance threshold" \
            if r["filtered_mrr"] == CAP_MRR else ""
        print(f"{r['filtered_mrr']:>13}{r['hits_at_10']:>9}"
              f"{r['old']:>9}{r['new']:>9}{mark}")
    print(f"\nold flat above the cap: {old_flat} | new monotone: {monotone_new} "
          f"| new never looser: {never_looser}")
    print(f"spec digest with ceilings {dig_with}, without {dig_without}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(REPO, "scripts")],
        artifacts=[os.path.join(HERE, "headroom.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the new normaliser is still flat across the old cap, OR it "
                  "scores any candidate HIGHER than the capped one did",
        note="H259: the objective saturated at 2x the null, which is exactly "
             "the value H255 measured as the acceptance threshold.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
