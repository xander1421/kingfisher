#!/usr/bin/env python3
"""G108 — every G-series headline on one scoreboard, as MARGIN OVER ITS OWN
SPLIT'S NULL, which `config.json`'s `bar_rule` says is the only comparable form.

THIS ROW BEGAN AS A WRONG ANSWER OF MINE. Sweeping the artifacts for the largest
leak-free MRR returned `G75/arms/F_dir_select = 0.3034` and I read it as "a
certified spike already beats the 0.2313 the evaluator scores". It does not:
G75's `split` is `official FB15k-237 train/valid/test`. My sweep had matched the
string `pair_disjoint` in a note field. Two correct numbers, different
denominators.

So this refuses to rank across groups. An MRR is comparable to another only when
BOTH the split AND the candidate set match -- ranking against all 14,541
entities and ranking against a predicate's train support are different tasks,
and a margin does not make them one.
"""
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "spikes", "harness"))

import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier          # noqa: E402

CONFIG = json.load(open(os.path.join(REPO, ".github", "autoloop", "config.json")))
SPLIT_NULLS = CONFIG["metrics"]["filtered_mrr"]["split_nulls"]

# A spike's free-text `split` mapped onto the keys config.json actually gates on.
# Substring matching, longest first, so `pair_disjoint (0 leak...)` and
# `pair_disjoint (G48)` both land on one key rather than becoming two groups.
SPLIT_KEYS = [
    ("official fb15k-237", "official_fb15k237"),
    ("pair_disjoint", "pair_disjoint"),
    ("shuffle", "shuffle_70_15_15"),
]
# n_test each split key is known to have, from the spikes that defined it.
EXPECTED_N_TEST = {"official_fb15k237": 20466, "pair_disjoint": 40817}

# CORRECTED mid-cycle, against my own first draft. v1 substituted
# "train_support_of_p (undeclared; G51 family default)" for any artifact that
# declared no candidate set, and then GROUPED BY that substitution. Two things
# were wrong with it and both are the same mistake: I supplied an input to a
# check applied to my own comparison (A22). It invented a protocol for spikes
# that never stated one, and it then placed G54 (undeclared) in a DIFFERENT
# group from G58 (which declares "train_support_of_p (same as G51)") -- a
# spurious split manufactured entirely by my own label.
#
# An undeclared candidate set is UNKNOWN, and an arm whose protocol is unknown
# cannot be placed on a scoreboard at all. It is refused, not guessed.
UNDECLARED = None


def canon_split(raw):
    if not isinstance(raw, str):
        return None
    low = raw.lower()
    for needle, key in SPLIT_KEYS:
        if needle in low:
            return key
    return None


def collect():
    arms, refused = [], []
    for path in sorted(glob.glob(os.path.join(REPO, "spikes", "G*", "*.json"))):
        if "provenance" in os.path.basename(path):
            continue
        try:
            d = json.load(open(path))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        table = d.get("arms")
        if not isinstance(table, dict):
            continue
        rel = os.path.relpath(path, REPO)
        key = canon_split(d.get("split"))
        cands = d.get("candidate_set") or UNDECLARED
        n_test = d.get("n_test")
        for name, arm in table.items():
            if not isinstance(arm, dict) or not isinstance(arm.get("mrr"), (int, float)):
                continue
            rec = {"spike": rel.split("/")[1], "artifact": rel, "arm": name,
                   "mrr": round(float(arm["mrr"]), 4),
                   "split_raw": d.get("split"), "split": key,
                   "candidate_set": cands, "n_test": n_test,
                   "is_headline": name == d.get("headline_arm")}
            if key is None:
                rec["refused"] = "the spike declares no split this scoreboard " \
                                 "can resolve, so it has no null to be a margin over"
                refused.append(rec)
                continue
            if cands is None:
                rec["refused"] = "the spike declares no candidate_set, so its " \
                                 "MRR has no protocol and cannot be compared " \
                                 "with any other arm -- guessing one would be " \
                                 "supplying the input to my own comparison"
                refused.append(rec)
                continue
            entry = SPLIT_NULLS.get(key) or {}
            null = entry.get("null_mrr")
            if null is None:
                rec["refused"] = f"split {key} has no measured null in config.json"
                refused.append(rec)
                continue
            if entry.get("gateable") is False:
                rec["refused"] = f"split {key} is measured but not a valid bar " \
                                 f"(H251): {entry.get('not_gateable_because','')[:60]}"
                refused.append(rec)
                continue
            rec["null"] = null
            rec["margin"] = round(rec["mrr"] - null, 4)
            arms.append(rec)
    return arms, refused


def main():
    t0 = time.time()
    arms, refused = collect()

    # Grouped by (split, candidate set). Ranking happens ONLY inside a group.
    groups = {}
    for a in arms:
        groups.setdefault((a["split"], a["candidate_set"]), []).append(a)
    for g in groups.values():
        g.sort(key=lambda r: -r["margin"])

    # n_test disagreeing with the split it claims is a mislabel, not a result.
    seen_ml = set()
    mislabelled = []
    for a in arms + refused:
        if (a.get("split") in EXPECTED_N_TEST and a.get("n_test") is not None
                and a["n_test"] != EXPECTED_N_TEST[a["split"]]
                and a["artifact"] not in seen_ml):
            seen_ml.add(a["artifact"])
            mislabelled.append(a)

    best_per_group = {f"{k[0]} | {k[1][:44]}": v[0] for k, v in groups.items()}
    n_groups = len(groups)
    cand_sets = sorted({a["candidate_set"] for a in arms})

    # The two numbers that started this row, looked up across RANKED AND
    # REFUSED alike -- a refused arm still has a split and a (missing)
    # candidate set, and "one of them cannot be placed at all" is a stronger
    # answer than "they are in different groups", not a weaker one.
    def find(prefix):
        for a in arms + refused:
            if a["spike"].startswith(prefix) and a["is_headline"]:
                return a
        return None

    def slot(a):
        return None if a is None else (a["split"], a["candidate_set"])

    g54, g75 = find("G54"), find("G75")
    g54_placed = g54 is not None and "margin" in g54
    g75_placed = g75 is not None and "margin" in g75

    controls = [
        Control("C1_more_than_one_GROUP_exists",
                why="if every arm shared one split and one candidate set there "
                    "would be nothing to refuse and no reason for the row",
                can_fail_because="all arms fall in a single group",
                null_must_contain="the group keys and their sizes"),
        Control("C2_the_two_numbers_that_started_this_are_in_DIFFERENT_groups",
                why="my error was ranking them against each other. If they "
                    "turn out to share a group, the correction is wrong and "
                    "the original reading stands",
                can_fail_because="G54's and G75's headlines share a "
                                 "(split, candidate set) group",
                null_must_contain="both arms' split and candidate set"),
        Control("C3_every_ranked_arm_has_a_MEASURED_null_on_its_own_split",
                why="ranking an arm whose split has no null is the exact thing "
                    "bar_rule forbids; the refusal list must absorb them",
                can_fail_because="a ranked arm carries no null",
                null_must_contain="the count ranked and the count refused"),
        Control("C4_the_refusal_path_actually_FIRES",
                why="a scoreboard that refuses nothing has not been tested as "
                    "a filter -- it would rank whatever it was handed",
                can_fail_because="nothing is refused, so the filter is unproven",
                null_must_contain="the refusal reasons and their counts"),
        Control("C5_a_declared_split_disagreeing_with_its_own_n_test_is_caught",
                why="a split label is a claim about which triples were scored; "
                    "n_test is the observable that can contradict it",
                can_fail_because="no artifact disagrees, in which case this is "
                                 "a clean bill and not a finding",
                null_must_contain="every disagreement found, or that there are none"),
        Control("C6_the_arm_the_LOOP_SCORES_is_itself_unplaceable",
                why="the sharpest form of the row. G54's headline is what "
                    "`--eval` publishes as filtered_mrr, and it declares no "
                    "candidate_set -- so the number the loop maximises cannot "
                    "be compared with anything, including its own successors",
                can_fail_because="G54 declares a candidate set after all, in "
                                 "which case it lands on the board and this is "
                                 "an ordinary ranking row",
                null_must_contain="what G54 declares and why it was refused"),
    ]
    controls[0].observe(n_groups > 1,
                        {"n_groups": n_groups,
                         "groups": {f"{k[0]} | {k[1][:44]}": len(v)
                                    for k, v in groups.items()}})
    controls[1].observe(
        g54 is not None and g75 is not None and slot(g54) != slot(g75),
        {"G54_headline": {"arm": g54 and g54["arm"], "mrr": g54 and g54["mrr"],
                          "split": g54 and g54["split"],
                          "candidates": g54 and g54["candidate_set"],
                          "placed_on_the_scoreboard": g54_placed,
                          "refused_because": g54 and g54.get("refused")},
         "G75_headline": {"arm": g75 and g75["arm"], "mrr": g75 and g75["mrr"],
                          "split": g75 and g75["split"],
                          "candidates": g75 and g75["candidate_set"],
                          "placed_on_the_scoreboard": g75_placed},
         "same_slot": slot(g54) == slot(g75)})
    controls[5].observe(
        g54 is not None and not g54_placed,
        {"the_arm_eval_scores": g54 and f"{g54['spike']} {g54['arm']} "
                                        f"mrr {g54['mrr']}",
         "declares_candidate_set": g54 and g54["candidate_set"],
         "refused_because": g54 and g54.get("refused"),
         "consequence": "the number the loop maximises cannot be placed beside "
                        "any other arm in its own series"})
    controls[2].observe(all("null" in a and a["null"] is not None for a in arms),
                        {"ranked": len(arms), "refused": len(refused)})
    controls[3].observe(len(refused) > 0,
                        {"n_refused": len(refused),
                         "reasons": sorted({r["refused"][:60] for r in refused})})
    controls[4].observe(
        True,
        {"n_mislabelled": len(mislabelled),
         "mislabelled": [{"artifact": m["artifact"], "claims": m["split"],
                          "n_test": m["n_test"],
                          "expected": EXPECTED_N_TEST[m["split"]]}
                         for m in mislabelled]})

    falsifiers = [
        Falsifier("F2_the_arms_are_incomparable_even_after_pairing_with_nulls",
                  refutes="that one ranked list across the G-series is possible",
                  fires_when="more than one candidate set appears among the "
                             "ranked arms",
                  null_must_contain="the candidate sets found"),
        Falsifier("F3_an_arm_is_ranked_without_a_null_on_its_split",
                  refutes="that the scoreboard is trustworthy at all",
                  fires_when="any ranked arm lacks a measured null",
                  null_must_contain="the offending arms"),
    ]
    falsifiers[0].observe(len(cand_sets) > 1, {"candidate_sets": cand_sets})
    falsifiers[1].observe(
        any(a.get("null") is None for a in arms),
        {"ranked_without_null": [a["arm"] for a in arms if a.get("null") is None]})

    res = {"spike": "G108",
           "n_arms_ranked": len(arms), "n_arms_refused": len(refused),
           "n_groups": n_groups,
           "candidate_sets_among_ranked": cand_sets,
           "groups": {f"{k[0]} || {k[1]}": v for k, v in groups.items()},
           "best_per_group": best_per_group,
           "refused": refused,
           "split_label_disagrees_with_n_test": mislabelled,
           "elapsed_sec": round(time.time() - t0, 2)}
    json.dump(res, open(os.path.join(HERE, "scoreboard.json"), "w"),
              indent=1, sort_keys=True)

    for (split, cands), rows in sorted(groups.items()):
        null = rows[0]["null"]
        print(f"\n=== {split}  |  candidates: {cands[:52]}  |  null {null}")
        for r in rows[:6]:
            mark = "  <-- --eval scores this" if r["spike"].startswith("G54") \
                and r["is_headline"] else ""
            print(f"  {r['margin']:+.4f}  mrr {r['mrr']:.4f}  "
                  f"{r['spike']:28} {r['arm']}{mark}")
    print(f"\nrefused {len(refused)} arm(s); "
          f"{len(cand_sets)} candidate set(s) among the ranked ones")
    if mislabelled:
        print("SPLIT LABEL DISAGREES WITH n_test:")
        for m in mislabelled:
            print(f"  {m['artifact']}: claims {m['split']} "
                  f"(n_test {EXPECTED_N_TEST[m['split']]}) but n_test={m['n_test']}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(REPO, "spikes")],
        artifacts=[os.path.join(HERE, "scoreboard.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the ranked arms turn out to share one split AND one "
                  "candidate set, making a single cross-series ranking valid "
                  "after all",
        note="G108: every G-series arm as a margin over its own split's null, "
             "grouped by (split, candidate set) and refusing to rank across "
             "groups.",
        allow_dirty=True)
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
