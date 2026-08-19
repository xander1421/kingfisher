#!/usr/bin/env python3
"""H251 — the split-null gate had two states and needed three.

`null_mrr: <number>` meant GATEABLE and `null_mrr: null` meant "never
measured", so the only way to record a measured null was to arm a bar over it.
`shuffle_70_15_15` is the split that breaks on that: its null IS measurable
(G106 did it) and a bar over it would certify a 30.01% leak.

Two things are checked here, and the first is the one the row rests on:

  A. THE ARITHMETIC. Does subtracting a split's OWN null remove the leak?
     Computed from G106's certified artifact, not restated from prose.
  B. THE VOCABULARY. All three states driven through the REAL consumer in
     `scripts/autoloop.py`, including the anti-inversion arm — a gate that
     refuses everything would pass a one-sided test.
"""
import contextlib
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
G106 = os.path.join(REPO, "spikes", "G106_shuffle_null")

sys.path.insert(0, os.path.join(REPO, "spikes", "harness"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier          # noqa: E402
import autoloop                                    # noqa: E402

# The tolerance below which "the null absorbed the leak" would be true.
ABSORBED_TOL = 0.005


def drive(split_nulls, declared, val):
    """One metric through the real scoring path. Returns (results, stderr)."""
    payload = json.dumps({"m": val, "split": declared})
    cfg = {
        "evaluators": {"e": {
            "command": f'{sys.executable} -c {json.dumps("import json; print(%r)" % payload)}',
            "timeout_sec": 30}},
        "metrics": {"m": {"direction": "maximize", "target": None,
                          "min_acceptable": None, "weight": 1.0,
                          "split_nulls": split_nulls}},
    }
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        results, _errors = autoloop.evaluate_suite(cfg)
    return results, buf.getvalue()


def main():
    t0 = time.time()

    # ---- A. the arithmetic, from G106's artifact ------------------------
    g = json.load(open(os.path.join(G106, "shuffle_null.json")))
    sh, pd = g["shuffle_split"], g["pair_disjoint_split"]
    sh_null = sh["null"]["mrr"]
    pd_null = pd["null_recomputed_here"]
    sh_sys = sh["system_mrr_withdrawn_headline"]
    pd_sys = pd["system_mrr"]
    leak_rate = sh["same_pair_leak_rate"]

    null_gap = abs(sh_null - pd_null)
    sh_margin = sh_sys - sh_null
    pd_margin = pd_sys - pd_null
    survives = abs(sh_margin - pd_margin)

    # ---- B. the three states through the real consumer ------------------
    LEAKED = {"leaky": {"null_mrr": sh_null, "gateable": False,
                        "not_gateable_because": "the null is leak-insensitive"}}
    HONEST = {"honest": {"null_mrr": pd_null}}
    UNMEASURED = {"never": {"null_mrr": None}}

    r_leak, log_leak = drive(LEAKED, "leaky", sh_sys)
    r_ok, log_ok = drive(HONEST, "honest", 0.2313)
    r_unm, log_unm = drive(UNMEASURED, "never", sh_sys)

    controls = [
        Control("C1_the_leaked_split_would_have_PASSED_its_own_null",
                why="the row claims a bar over this null certifies the leak. "
                    "If the leaked system did not clear its own null there "
                    "would be nothing to prevent",
                can_fail_because="0.2648 does not exceed the shuffle null",
                null_must_contain="the margin over its own split's null"),
        Control("C2_the_same_system_FAILS_on_the_leak_free_split",
                why="the two margins must disagree in SIGN, or the leaked bar "
                    "is not certifying anything the honest one would refuse",
                can_fail_because="the leak-free margin is also positive",
                null_must_contain="both margins"),
        Control("C3_the_third_state_is_REACHABLE_and_says_why",
                why="A15 applied to my own fix: a branch nothing can reach is "
                    "not a gate, and one that vetoes without a reason is not "
                    "reviewable",
                can_fail_because="the consumer does not refuse a "
                                 "gateable:false split, or prints no reason",
                null_must_contain="the invariant result and the printed reason"),
        Control("C4_ANTI_INVERSION_a_gateable_split_still_passes",
                why="a consumer that refused every split would pass C3. This "
                    "is the arm that stops the fix from being a blanket veto",
                can_fail_because="an honest split clearing its null fails",
                null_must_contain="its invariant result and margin line"),
        Control("C5_NEVER_MEASURED_keeps_its_own_distinct_message",
                why="the third state must be added WITHOUT collapsing the two "
                    "that already worked -- three states, not a renamed two",
                can_fail_because="null_mrr None stops printing NEVER MEASURED, "
                                 "or stops failing invariants",
                null_must_contain="its invariant result and message"),
    ]
    controls[0].observe(sh_margin > 0,
                        {"system": sh_sys, "its_own_null": sh_null,
                         "margin": round(sh_margin, 6),
                         "leak_rate_of_this_split": leak_rate})
    controls[1].observe(pd_margin < 0 < sh_margin,
                        {"shuffle_margin": round(sh_margin, 6),
                         "leak_free_margin": round(pd_margin, 6)})
    controls[2].observe(
        r_leak.get("_invariants_passed") is False
        and "[UNGATEABLE]" in log_leak
        and "the null IS measured" in log_leak
        and "leak-insensitive" in log_leak,
        {"invariants_passed": r_leak.get("_invariants_passed"),
         "printed_UNGATEABLE": "[UNGATEABLE]" in log_leak,
         "said_the_null_was_measured": "the null IS measured" in log_leak,
         "printed_a_reason": "leak-insensitive" in log_leak})
    controls[3].observe(
        r_ok.get("_invariants_passed") is True and "[SPLIT NULL]" in log_ok,
        {"invariants_passed": r_ok.get("_invariants_passed"),
         "printed_SPLIT_NULL": "[SPLIT NULL]" in log_ok})
    controls[4].observe(
        r_unm.get("_invariants_passed") is False and "NEVER MEASURED" in log_unm,
        {"invariants_passed": r_unm.get("_invariants_passed"),
         "printed_NEVER_MEASURED": "NEVER MEASURED" in log_unm})

    falsifiers = [
        Falsifier("F1_the_split_s_own_null_absorbs_the_leak",
                  refutes="that bar_rule is insufficient on a leaked split -- "
                          "if it fires, gateable:false is wrong and the row is "
                          "void",
                  fires_when=f"|shuffle margin - leak-free margin| <= {ABSORBED_TOL}",
                  null_must_contain="both margins and the surviving leak"),
        Falsifier("F4_the_consumer_already_refused_leaked_splits",
                  refutes="that a third state was needed at all",
                  fires_when="a gateable:false split is refused with the "
                             "pre-H251 consumer, i.e. the branch is redundant",
                  null_must_contain="whether the refusal cites the new reason"),
    ]
    falsifiers[0].observe(survives <= ABSORBED_TOL,
                          {"shuffle_margin": round(sh_margin, 6),
                           "leak_free_margin": round(pd_margin, 6),
                           "leak_surviving_the_subtraction": round(survives, 6),
                           "gap_between_the_two_NULLS": round(null_gap, 6)})
    # Pre-H251 the ONLY refusal paths were "split absent" and "null_mrr is
    # None". A gateable:false entry carrying a number took neither, so the
    # branch is redundant only if something else refused it.
    falsifiers[1].observe(
        "gateable" not in log_leak and "[UNGATEABLE]" not in log_leak,
        {"pre_h251_refusal_paths": ["declared_split absent",
                                    "declared_split not in split_nulls",
                                    "null_mrr is None"],
         "gateable_false_entry_carries_a_number": True})

    res = {"spike": "H251",
           "arithmetic": {
               "shuffle_null": sh_null, "pair_disjoint_null": pd_null,
               "gap_between_the_nulls": round(null_gap, 6),
               "shuffle_system": sh_sys, "leak_free_system": pd_sys,
               "shuffle_margin_over_its_own_null": round(sh_margin, 6),
               "leak_free_margin_over_its_own_null": round(pd_margin, 6),
               "leak_surviving_same_split_subtraction": round(survives, 6),
               "leak_rate": leak_rate},
           "gate_states": {
               "measured_but_not_a_bar": {
                   "invariants": r_leak.get("_invariants_passed"),
                   "ungateable": "[UNGATEABLE]" in log_leak},
               "gateable": {
                   "invariants": r_ok.get("_invariants_passed"),
                   "split_null_line": "[SPLIT NULL]" in log_ok},
               "never_measured": {
                   "invariants": r_unm.get("_invariants_passed"),
                   "never_measured_line": "NEVER MEASURED" in log_unm}},
           "elapsed_sec": round(time.time() - t0, 2)}
    json.dump(res, open(os.path.join(HERE, "third_state.json"), "w"),
              indent=1, sort_keys=True)

    print(f"shuffle   {sh_sys:.4f} - {sh_null:.6f} = {sh_margin:+.4f}  <- would PASS")
    print(f"leak-free {pd_sys:.4f} - {pd_null:.6f} = {pd_margin:+.4f}  <- fails")
    print(f"the two NULLS differ by {null_gap:.6f}; "
          f"the leak surviving the subtraction is {survives:.4f}")
    print(f"states: not-a-bar={r_leak.get('_invariants_passed')} "
          f"gateable={r_ok.get('_invariants_passed')} "
          f"never={r_unm.get('_invariants_passed')}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G106, os.path.join(REPO, "scripts")],
        artifacts=[os.path.join(HERE, "third_state.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the shuffle split's own null absorbs its leak, making "
                  "bar_rule sufficient and `gateable:false` wrong",
        note="H251: a split whose null is MEASURED and which is still not a "
             "valid bar, and the gate vocabulary that could not say so.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
