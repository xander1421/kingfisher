#!/usr/bin/env python3
"""G104 — the loop's objective has no null beside it, so it cannot tell
"improved" from "still worse than not mining at all".

Run: PYTHONUNBUFFERED=1 python3 spikes/G104_null_in_the_loop/run.py   (~3 min)

WHAT IS BEING ATTACKED
  `.github/autoloop/evaluators/eval_graph_ai.py` (ATOM-3, G102) now emits the
  LEAK-FREE number, which is the right fix and is not in question here. What it
  emits beside it is:

      "status": "D6_EXECUTION_CERTIFIED_LEAK_FREE"

  Every word true -- the run is certified, the split does not leak -- printed
  next to `filtered_mrr` 0.1358, which is **0.0374 BELOW the no-rules frequency
  prior on that same split** (G49: 0.1732). **A status field that certifies
  PROVENANCE reads as certifying QUALITY.** A loop maximising `filtered_mrr`
  with no null in its output cannot distinguish "improved" from "still below
  the baseline of doing nothing".

WHY THE NULL IS RECOMPUTED HERE RATHER THAN QUOTED FROM G49
  G49's 0.1732 is committed and reproducible, and quoting it would be cheaper.
  It would also be a number from a different composition: this recomputes the
  prior through the EVALUATOR'S OWN path -- `L.load_dataset`,
  `pair_disjoint_split(tri, L.SEED)` -- so the null is produced by the same
  instrument as the metric it is meant to bound. F1 is the check that the two
  agree; if they do not, this becomes a retraction of G49 rather than a fix to
  the loop.

THE PRIOR, STATED SO IT CANNOT BE CONFUSED WITH A MODEL
  Rank candidate entities by how often they appear in the answer position for
  that PREDICATE in train. No bodies, no composition, no confidence, no mining.
  Filtered exactly as the system is: other true triples are removed from the
  ranking. A tie is scored at its MIDPOINT rank, which is the only choice that
  neither flatters nor punishes a prior that ties a lot.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
EVAL = os.path.join(ROOT, ".github", "autoloop", "evaluators", "eval_graph_ai.py")
G34 = os.path.join(SPIKES, "G34_length1_and_constants")
G48 = os.path.join(SPIKES, "G48_pairdisjoint_split")

for d in (os.path.join(SPIKES, "harness"), G34, G48):
    sys.path.insert(0, d)

import kfcheck                                            # noqa: E402
import length1_constants as L                             # noqa: E402
from provenance import Control, Falsifier                 # noqa: E402
from split import pair_disjoint_split, leak_count         # noqa: E402

G49_NULL = 0.1732          # published, pair-disjoint split
G49_FULL = 0.1358          # published, same split
TOL = 0.0005


def sha256_of_file(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def prior_scores(train, npred):
    """count[predicate][entity] over train, per answer position. The whole model.

    THE TUPLE IS `(p, s, o)` -- PREDICATE FIRST. The first version of this
    function and of `evaluate_prior` unpacked `for s, p, o in ...`, i.e. it
    conditioned the prior on the SUBJECT and looked the filter up under the
    wrong key. It returned MRR 0.2607 against G49's 0.1732 and F1 fired.
    Verified rather than assumed: `length1_constants.py:78` is
    `for p, s, o in triples` and `:91-93` builds `true_sp[(s, p)]` from the
    same unpacking. **The transposed model was internally consistent -- MRR
    below Hits@10, controls green -- and only the comparison to an
    independently-written null could see it.**"""
    tail = defaultdict(lambda: defaultdict(int))
    head = defaultdict(lambda: defaultdict(int))
    for p, s, o in train:
        tail[p][o] += 1
        head[p][s] += 1
    return head, tail


def rank_of(target, cand_counts, filtered_out, nent):
    """Midpoint rank of `target` under descending count, filtered.

    Entities with no count are all tied at the bottom; a target among them gets
    the midpoint of that block rather than the top of it. Scoring a tie at its
    best position is how a prior that abstains gets flattered into a model.
    """
    t_score = cand_counts.get(target, 0)
    better = 0
    equal = 0
    for e, c in cand_counts.items():
        if e == target or e in filtered_out:
            continue
        if c > t_score:
            better += 1
        elif c == t_score:
            equal += 1
    if t_score == 0:
        # every uncounted, unfiltered entity ties with the target
        scored = set(cand_counts)
        n_zero = nent - len(scored) - len(filtered_out - scored)
        equal += max(0, n_zero - 1)
    # MIDPOINT OF THE TIED BLOCK, and the first version of this line was
    # `better + (equal + 1) / 2.0`, which returns **0.5** for an untied target:
    # reciprocal rank 2.0, on a scale whose maximum is 1.0. It produced MRR
    # 0.4729 against Hits@10 0.3712 -- **internally impossible, since MRR can
    # never exceed Hits@10** -- and F1 fired against G49's 0.1732. The tied
    # block has `equal + 1` members counting the target, so its midpoint is
    # `better + ((equal + 1) + 1) / 2`.
    return better + (equal + 2) / 2.0


def evaluate_prior(test, head, tail, true_sp, true_po, nent):
    rr = h1 = h3 = h10 = 0.0
    n = 0
    scored_targets = 0
    for p, s, o in test:
        # tail query (s, p, ?)  -- the TUPLE is (p, s, o); see prior_scores
        filt = set(true_sp.get((s, p), ())) - {o}
        r = rank_of(o, tail.get(p, {}), filt, nent)
        scored_targets += tail.get(p, {}).get(o, 0) > 0
        rr += 1.0 / r
        h1 += r <= 1
        h3 += r <= 3
        h10 += r <= 10
        n += 1
        # head query (?, p, o)
        filt = set(true_po.get((p, o), ())) - {s}
        r = rank_of(s, head.get(p, {}), filt, nent)
        scored_targets += head.get(p, {}).get(s, 0) > 0
        rr += 1.0 / r
        h1 += r <= 1
        h3 += r <= 3
        h10 += r <= 10
        n += 1
    return {"mrr": rr / n, "hits1": h1 / n, "hits3": h3 / n, "hits10": h10 / n,
            "n_queries": n, "queries_with_a_scored_target": scored_targets}


def main() -> int:
    t0 = time.time()
    eval_sha = sha256_of_file(EVAL)
    print(f"eval_graph_ai.py sha256 {eval_sha[:16]}", flush=True)

    _nt, npred, nent, tri, _a, _b, _c = L.load_dataset()
    train, _dev, test, _n = pair_disjoint_split(tri, L.SEED)
    leak = leak_count(train, test)
    true_sp, true_po = L.build_filter_index(tri)
    head, tail = prior_scores(train, npred)
    null = evaluate_prior(test, head, tail, true_sp, true_po, nent)
    print(f"null mrr {null['mrr']:.4f}  hits10 {null['hits10']:.4f}  "
          f"n_queries {null['n_queries']}", flush=True)

    delta = G49_FULL - null["mrr"]
    controls = [
        Control("C1_split_does_not_leak",
                why="the null must be measured on the same leak-free split as "
                    "the metric it bounds, or it is not its null",
                can_fail_because="pair_disjoint_split stops being pair-disjoint",
                null_must_contain="the measured leak count"),
        Control("C2_both_halves_of_every_query_are_scored",
                why="a null scored on tail queries only would be half a "
                    "measurement compared against a full one",
                can_fail_because="n_queries != 2 * n_test",
                null_must_contain="n_queries and n_test"),
        Control("C3_ties_are_not_scored_at_their_best_position",
                why="a prior that abstains ties on most of the entity set; "
                    "ranking a tie at its top turns abstention into skill",
                can_fail_because="a target with count 0 receives rank 1",
                null_must_contain="the rank of a zero-count target"),
    ]
    controls[0].observe(leak == 0, {"leak_count": leak})
    controls[1].observe(null["n_queries"] == 2 * len(test),
                        {"n_queries": null["n_queries"], "n_test": len(test)})
    probe = rank_of("__not_an_entity__", {"a": 5, "b": 3}, set(), nent)
    controls[2].observe(probe > 10, {"rank_of_zero_count_target": probe,
                                     "nent": nent})
    # C4 was added AFTER the first run returned MRR 0.4729 against Hits@10
    # 0.3712. No external reference was needed to know that is wrong: an
    # untied top-ranked target was being given rank 0.5, i.e. reciprocal rank
    # 2.0 on a scale whose maximum is 1. **The invariant is internal to the
    # measurement and it is cheaper than the comparison that caught it.**
    # CORRECTED 2026-08-19 by AGENT-2 after AGENT-3 measured this predicate
    # against all 370 published arms and got TEN FALSE POSITIVES, every one the
    # `Empty_baseline` arm of G30/G34/G35/G36/G45 at
    # `mrr=0.00013946 > hits10=0.0`. Those are not defects. **`mrr <= hits10` is
    # only true as Hits@10 approaches 1**: if every rank exceeds 10 then Hits@10
    # is 0 while MRR stays positive -- 0.000139 is about rank 7,170. My "cheaper
    # than the comparison that caught it" claim above was right about the idea
    # and wrong about the bound, which is A18's shape: the number was real and
    # the model around it did not hold.
    #
    # THE TIGHT BOUND, AGENT-3's, adopted verbatim: a fraction `h` ranks 1 at
    # best and the remaining `(1-h)` ranks 11 at worst, so
    #
    #     MRR <= h + (1 - h) / 11
    #
    # It still catches the defect this control was written for: MRR 0.4729
    # against Hits@10 0.3712 gives a bound of 0.4284 -- CAUGHT. `Empty_baseline`
    # at h=0 gives 0.0909 -- correctly clean. Under the tight bound AGENT-3
    # measured **0 impossible arms across all 370**, which is the reassuring
    # half: the transposed-tuple defect is not anywhere else in the tree.
    mrr_bound = null["hits10"] + (1.0 - null["hits10"]) / 11.0
    controls.append(Control(
        "C4_mrr_cannot_exceed_its_hits10_bound",
        why="MRR is a mean of 1/rank. A fraction Hits@10 of queries rank 1 at "
            "best; the rest rank 11 at worst. Exceeding h + (1-h)/11 is not a "
            "surprising result but an arithmetic impossibility",
        can_fail_because="a rank function that returns a rank below 1",
        null_must_contain="both quantities and the bound"))
    controls[3].observe(null["mrr"] <= mrr_bound + 1e-12,
                        {"mrr": round(null["mrr"], 6),
                         "hits10": round(null["hits10"], 6),
                         "bound_h_plus_1_minus_h_over_11": round(mrr_bound, 6),
                         "superseded_predicate": "mrr <= hits10 (false at h=0)"})
    # And the direct probe of the defect: a target that beats everything, with
    # no ties, must be rank 1 exactly.
    controls.append(Control(
        "C5_an_untied_winner_is_rank_1",
        why="the first version returned 0.5 here and nothing else in the run "
            "could see it",
        can_fail_because="the tied-block midpoint is computed off by one",
        null_must_contain="the rank returned"))
    top = rank_of("w", {"w": 99, "a": 5, "b": 3}, set(), nent)
    controls[4].observe(abs(top - 1.0) < 1e-9, {"rank": top})

    falsifiers = [
        Falsifier("F1_null_does_not_reproduce_through_this_path",
                  refutes="that G49's null and the evaluator's split are the "
                          "same object",
                  fires_when=f"|null - {G49_NULL}| > {TOL}",
                  null_must_contain="both values and the difference"),
        Falsifier("F2_the_system_is_not_below_its_null",
                  refutes="the whole row; the status string would be fine",
                  fires_when="filtered_mrr >= null mrr",
                  null_must_contain="both numbers and the signed gap"),
    ]
    falsifiers[0].observe(abs(null["mrr"] - G49_NULL) > TOL,
                          {"recomputed": round(null["mrr"], 6),
                           "g49_published": G49_NULL,
                           "abs_diff": round(abs(null["mrr"] - G49_NULL), 6),
                           "tolerance": TOL})
    falsifiers[1].observe(G49_FULL >= null["mrr"],
                          {"filtered_mrr": G49_FULL,
                           "null_mrr": round(null["mrr"], 6),
                           "signed_gap": round(delta, 6)})

    res = {"spike": "G104",
           "split": "G48_pair_disjoint",
           "eval_graph_ai_sha256": eval_sha,
           "same_pair_leak": leak,
           "n_test": len(test), "n_train": len(train),
           "null": {k: (round(v, 6) if isinstance(v, float) else v)
                    for k, v in null.items()},
           "system_filtered_mrr_published": G49_FULL,
           "system_minus_null": round(delta, 6),
           "proposed_field_for_eval_graph_ai": {
               "null_mrr": round(null["mrr"], 6),
               "objective": "filtered_mrr - null_mrr",
               "why": "a status field that certifies provenance reads as "
                      "certifying quality; the null is what makes the metric "
                      "readable"},
           "elapsed_sec": round(time.time() - t0, 2)}
    json.dump(res, open(os.path.join(HERE, "null_in_the_loop.json"), "w"),
              indent=1, sort_keys=True)

    print(f"system {G49_FULL}  null {null['mrr']:.4f}  "
          f"system - null = {delta:+.4f}", flush=True)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G34, G48],
        artifacts=[os.path.join(HERE, "null_in_the_loop.json")],
        controls=controls, falsifiers=falsifiers,
        falsifier="the null does not reproduce through the evaluator's own "
                  "composition, OR the system is not in fact below it",
        note="G104: the no-rules prior on the loop's own split, recomputed "
             "through the evaluator's composition.")
    print(f"certify ok={ok}")
    for p in problems:
        print("  ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
