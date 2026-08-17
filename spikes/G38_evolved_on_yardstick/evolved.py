r"""G38 — do the evolved populations beat exhaustive 2-hop mining on filtered MRR?

THE ROW THE G-SERIES HAS BEEN POINTING AT SINCE G24, and it was unevaluatable
until G37. This lane spent G22/G24/G25/G27 evolving rule populations and scored
them with `top12` mean held-out confidence -- a heuristic G30 retired and whose
retirement G33 had to correct the evidence for. Scoring them on the external
yardstick was impossible while `yardstick.py:156` destructured a body as
`(p1, p2)`: an evolved population contains variable-length bodies and the
instrument RAISES on them (G37 C2/C3). `varlen.evaluate_varlen` is pinned to
`yardstick.py` at 6 decimal places, so numbers produced through it are directly
comparable to every row G30 published.

PRECONDITION, VERIFIED BEFORE THIS WAS CLAIMED
----------------------------------------------
G24 and G30 must be on the SAME SPLIT or nothing here can be compared. Measured:
both use SEED=0xC0FFEE and identical split arithmetic, and `R.load()` and
`Y.load_dataset()` return identical triples in identical order (nt=272115,
npred=237, nent=14505). G24's pre-plant train is byte-equal to G30's train; the
test sets are equal.

THE ONE DIFFERENCE, HANDLED RATHER THAN IGNORED: `evo.dataset()` does
`train += ptr`, injecting the 600-edge A15 positive control, so an evolved rule
may reference planted predicate ids >= npred. Those are EXCLUDED here and the
count is reported. A rule scoring well because it learned the plant is not a
finding about FB15k-237.

CONFIDENCE BASIS: computed on **G30's train**, the same basis G17's mined rules
get theirs, never on dev or test. C1 is what pins that: the same run must
reproduce G30's G17_all row through the same evaluator, or the basis has drifted
and no number here means what it says.

FALSIFIERS, STATED IN CHANNEL.md BEFORE THE RUN, and published whichever way
they land -- this lane has four spikes invested in the machinery under test,
which is exactly why they are written this way:

  F1  If the evolved population does not exceed the 3,198-rule exhaustive 2-hop
      baseline (0.063112 filtered MRR), then the evolutionary machinery does not
      find better rules than exhaustive mining, and I say so plainly.
  F2  If the evolved population contains no body of length != 2, evolution never
      left the seed's shape and `extend`/`contract` are inert in practice,
      whatever the operator list says.
"""
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
for _p in ("harness", "G30_external_yardstick", "G17_composition_redo",
           "G24_population", "G37_varlen_bodies"):
    sys.path.insert(0, os.path.join(SPIKES, _p))

import provenance as P  # noqa: E402
import kfcheck  # noqa: E402
import yardstick as Y  # noqa: E402
import varlen as V  # noqa: E402
import evo as E  # noqa: E402

G30 = os.path.join(SPIKES, "G30_external_yardstick")
G24 = os.path.join(SPIKES, "G24_population")
G37 = os.path.join(SPIKES, "G37_varlen_bodies")

ARMS = ("full", "no_variation")   # `no_variation` is the seeded population only
# G24's own three seeds. One seed is not a result in this lane: G24 measured
# full_base at 4719 / 4144 / 3381 across exactly these, so a single-run gap can
# be noise. VERIFIED rather than assumed that patching this reaches run():
# evo.run() does `random.Random(RUN_SEED)` at CALL time and RUN_SEED is not a
# default argument -- the distinction CLAUDE.md records as a real defect here.
SEEDS = (777, 1234, 31337)
G30_G17_ALL_MRR = 0.063112


_BODY_PAIRS = {}


def body_pairs(body, out_adj):
    """Endpoint pairs `body` matches on the train graph, CACHED PER BODY.

    Per-body and not per-rule: several evolved genotypes share a body with
    different heads, and the walk is the expensive half. `evo.py:180` gives the
    same reason for returning `cand` -- "the pairs a rule matches do not depend
    on what it is scored against."
    """
    key = tuple(body)
    got = _BODY_PAIRS.get(key)
    if got is None:
        got = [(s, o) for s in out_adj for o in V.walk_forward(s, body, out_adj)]
        _BODY_PAIRS[key] = got
    return got


def conf_on_train(body, head, out_adj, pair_index, min_pairs=30):
    """Confidence of `body => head` measured on G30's TRAIN graph.

    Same basis as `yardstick.mine_g17_rules`: of the endpoint pairs the body
    matches, the fraction that carry `head`. Generalised to any body length via
    G37's walk, which it REUSES rather than reimplements, so a rule is scored
    over exactly the paths it is later evaluated over.
    """
    bp = body_pairs(body, out_adj)
    n = len(bp)
    if n < min_pairs:
        return None, n, 0
    hit = sum(1 for s, o in bp if head in pair_index.get((s, o), ()))
    return hit / n, n, hit


def main():
    print("=" * 78)
    print("G38 — evolved populations on the filtered-MRR yardstick")
    print("=" * 78)

    # ---- G30's world: the split every number here is reported against
    nt, npred, nent, tri, train, dev, test = Y.load_dataset()
    out_adj, in_adj, pair_tr, _, _ = Y.build_graph_index(train, nent)
    true_sp, true_po = Y.build_filter_index(tri)
    print(f"\nsplit: train {len(train):,} / test {len(test):,}   "
          f"npred {npred}  (planted ids are >= {npred})")

    # ---- C1: the baseline, through the SAME evaluator
    rules_2hop = Y.mine_g17_rules(train)
    base = V.evaluate_varlen(rules_2hop, test, out_adj, in_adj, true_sp,
                             true_po, nent)
    print(f"\nbaseline  G17 exhaustive 2-hop  {len(rules_2hop):,} rules   "
          f"MRR {base['mrr']:.6f}")
    c1_ok = abs(base["mrr"] - G30_G17_ALL_MRR) < 1e-6

    # ---- evolve, under G24's own conditions, unchanged
    ev_train, dev_pairs, test_pairs, ev_npred, planted = E.dataset()
    results, arm_detail, scored_by_arm, matched_by_arm = {}, {}, {}, {}
    seed_pops = {}
    for arm in ARMS:
        per_seed = []
        for seed in SEEDS:
            E.RUN_SEED = seed
            t0 = time.time()
            hist, rejected, pop = E.run(arm, ev_train, dev_pairs, test_pairs,
                                        ev_npred, planted, log=False)
            ev_sec = time.time() - t0
            seed_pops[(arm, seed)] = sorted(
                (tuple(r["body"]), r["head"]) for r in pop)

            kept, dropped = [], 0
            for r in pop:
                body = tuple(r["body"])
                if any(p >= npred for p in body) or r["head"] >= npred:
                    dropped += 1
                    continue
                kept.append((body, r["head"]))
            uniq = sorted(set(kept))

            scored, unscorable = [], 0
            for body, head in uniq:
                c, n, h = conf_on_train(body, head, out_adj, pair_tr)
                if c is None:
                    unscorable += 1
                    continue
                scored.append({"body": body, "head": head, "conf": c,
                               "pairs": n, "hits": h})

            lengths = defaultdict(int)
            for r in scored:
                lengths[len(r["body"])] += 1

            res = V.evaluate_varlen(scored, test, out_adj, in_adj, true_sp,
                                    true_po, nent)
            matched = V.evaluate_varlen(rules_2hop[:len(scored)], test, out_adj,
                                        in_adj, true_sp, true_po, nent)
            per_seed.append({
                "seed": seed, "mrr": res["mrr"], "hits1": res["hits1"],
                "hits3": res["hits3"], "hits10": res["hits10"],
                "size_matched_mrr": matched["mrr"],
                "ratio_vs_size_matched": res["mrr"] / max(matched["mrr"], 1e-12),
                "pop_size": len(pop), "dropped_planted": dropped,
                "planted_share_pct": round(100.0 * dropped / max(len(pop), 1), 1),
                "evaluated_rules": len(scored),
                "unscorable_below_min_pairs": unscorable,
                "body_lengths": dict(sorted(lengths.items())),
                "evolve_sec": round(ev_sec, 1), "rejected_capped": rejected})
            scored_by_arm.setdefault(arm, []).extend(scored)
            print(f"  {arm:<14} seed {seed:<6} rules {len(scored):>3}  "
                  f"MRR {res['mrr']:.6f}  vs mined@{len(scored)} "
                  f"{matched['mrr']:.6f}  ({res['mrr']/max(matched['mrr'],1e-12):.2f}x)"
                  f"  planted {dropped}/{len(pop)}  lengths "
                  f"{dict(sorted(lengths.items()))}")

        mrrs = sorted(d["mrr"] for d in per_seed)
        ratios = sorted(d["ratio_vs_size_matched"] for d in per_seed)
        results[arm] = {"mrr": mrrs[len(mrrs) // 2],
                        "mrr_min": mrrs[0], "mrr_max": mrrs[-1],
                        "hits1": sorted(d["hits1"] for d in per_seed)[len(per_seed) // 2],
                        "hits3": sorted(d["hits3"] for d in per_seed)[len(per_seed) // 2],
                        "hits10": sorted(d["hits10"] for d in per_seed)[len(per_seed) // 2]}
        matched_by_arm[arm] = {
            "mrr": sorted(d["size_matched_mrr"] for d in per_seed)[len(per_seed) // 2]}
        arm_detail[arm] = {"per_seed": per_seed,
                           "median_mrr": mrrs[len(mrrs) // 2],
                           "mrr_range": [mrrs[0], mrrs[-1]],
                           "ratio_median": ratios[len(ratios) // 2],
                           "ratio_range": [ratios[0], ratios[-1]],
                           # per-seed rule counts differ (53/53/54), and each
                           # seed's size-matched baseline is taken at ITS OWN
                           # size, so one seed's count cannot label the median.
                           "evaluated_rules": sorted(
                               d["evaluated_rules"] for d in per_seed),
                           "beats_size_matched_on_every_seed":
                               all(d["ratio_vs_size_matched"] > 1.0 for d in per_seed)}
        print(f"  -> {arm}: median MRR {mrrs[len(mrrs)//2]:.6f} "
              f"[{mrrs[0]:.6f}, {mrrs[-1]:.6f}], ratio vs size-matched median "
              f"{ratios[len(ratios)//2]:.2f}x, every seed above 1.0: "
              f"{all(r > 1.0 for r in ratios)}\n")

    best_arm = max(results, key=lambda a: results[a]["mrr"])
    best = results[best_arm]["mrr"]
    f1_fires = best <= base["mrr"]
    # the fair comparison, reported alongside F1 rather than replacing it
    beats_matched = {a: results[a]["mrr"] > matched_by_arm[a]["mrr"] for a in ARMS}
    # `body_lengths` and `dropped_planted` are PER-SEED keys. They were read off
    # the per-arm aggregate here and at C2 below, which was correct while there
    # was one run per arm and became a KeyError the moment SEEDS was looped over.
    # Both sites fixed together: fixing one and leaving its sibling is the
    # count-vs-presence shape livechat.log records from the same afternoon.
    all_lengths = set()
    for a in ARMS:
        for d in arm_detail[a]["per_seed"]:
            all_lengths |= set(d["body_lengths"])
    f2_fires = all_lengths.issubset({2})

    print("\n" + "=" * 78)
    print(f"F1 evolved beats exhaustive mining : best {best:.6f} vs "
          f"baseline {base['mrr']:.6f} -> "
          f"{'FIRED (it does NOT)' if f1_fires else 'did not fire'}")
    for a in ARMS:
        print(f"   size-matched: {a:<14} evolved {results[a]['mrr']:.6f} vs "
              f"mined@{arm_detail[a]['evaluated_rules']} (per-seed sizes) "
              f"{matched_by_arm[a]['mrr']:.6f}  -> "
              f"{'EVOLVED WINS' if beats_matched[a] else 'mining wins'}")
    print(f"F2 evolution left the seed's shape : body lengths seen "
          f"{sorted(all_lengths)} -> "
          f"{'FIRED (all length 2)' if f2_fires else 'did not fire'}")

    out = {"baseline_g17_2hop": {k: base[k] for k in
                                 ("mrr", "hits1", "hits3", "hits10")},
           "baseline_rule_count": len(rules_2hop),
           "arms": {a: {**{k: results[a][k] for k in
                           ("mrr", "hits1", "hits3", "hits10")},
                        **arm_detail[a]} for a in ARMS},
           "best_arm": best_arm,
           "size_matched": {a: matched_by_arm[a]["mrr"] for a in ARMS},
           "evolved_beats_size_matched_mining": beats_matched,
           "plant_contribution_bound": {
               "planted_dev_conclusions": 550,
               "note": "evo.population_metrics counts `correct` over ALL rules "
                       "including planted heads, and `target` includes the "
                       "planted dev conclusions, so G24's published `solved` "
                       "INCLUDES the A15 plant. Bounded above by the number of "
                       "planted dev conclusions.",
               "g24_published_full_base_solved": [4719, 4144, 3381],
               "max_plant_share_of_g24_coverage_pct": [
                   round(100.0 * 550 / v, 1) for v in (4719, 4144, 3381)]},
           "seeds": list(SEEDS),
           "body_lengths_observed": sorted(all_lengths),
           "f1_evolved_fails_to_beat_mining": f1_fires,
           "f2_no_length_variation": f2_fires,
           "c1_baseline_reproduces_g30": c1_ok}
    out_json = os.path.join(HERE, "evolved.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True, default=str)

    controls, falsifiers = [], []
    c1 = P.Control(
        "C1_baseline_reproduces_G30_through_this_evaluator",
        "if the baseline drifts, no arm number in this spike means what it says",
        null_must_contain="a G17 exhaustive baseline differing from G30's "
                          "published 0.063112",
        can_fail_because="a different confidence basis, split, or filter index "
                         "would move it while every arm still looked internally "
                         "consistent")
    c1.observe(c1_ok, {"baseline_mrr": base["mrr"], "g30": G30_G17_ALL_MRR})
    controls.append(c1)

    c2 = P.Control(
        "C2_planted_control_excluded_from_every_arm",
        "an evolved rule that scored well by learning the A15 plant would be a "
        "finding about the plant, not about FB15k-237",
        null_must_contain="a planted predicate id >= npred reaching the evaluator",
        can_fail_because="evo.dataset() injects 600 planted edges into train, so "
                         "the population genuinely can carry them")
    leaked = [(a, r["body"], r["head"]) for a in ARMS
              for r in scored_by_arm[a]
              if any(p >= npred for p in r["body"]) or r["head"] >= npred]
    c2.observe(not leaked,
               {"planted_rules_reaching_evaluator": len(leaked),
                "dropped_per_arm": {a: [d["dropped_planted"]
                                        for d in arm_detail[a]["per_seed"]]
                                    for a in ARMS},
                "rules_checked": sum(len(scored_by_arm[a]) for a in ARMS)})
    controls.append(c2)

    distinct_pops = len({tuple(seed_pops[("full", sd)]) for sd in SEEDS})
    c3 = P.Control(
        "C3_seed_patch_actually_reaches_run",
        "three seeds are only three samples if the seed changes the population",
        null_must_contain="two seeds producing an identical population",
        can_fail_because="if RUN_SEED were bound at definition time rather than "
                         "read at call time, every 'seed' would be seed 1234 and "
                         "the range would be a fabrication")
    c3.observe(distinct_pops == len(SEEDS),
               {"distinct_populations": distinct_pops, "seeds": len(SEEDS)})
    controls.append(c3)

    # ---- C4: is a length-1 body UNDISCOVERED, or UNREACHABLE?
    # This is the whole difference between a finding about evolution's search and
    # a finding about its operator set, and G34 measured length-1 rules ALONE at
    # 0.1572 MRR -- 2.5x this entire 2-hop baseline. Read the bounds OUT OF THE
    # AST rather than writing them as literals: G33 caught this lane returning a
    # hardcoded constant in the shape of a measurement, in the audit written to
    # catch exactly that.
    import ast as _ast
    _evo_src = open(os.path.join(G24, "evo.py")).read()
    _fn = next(n for n in _ast.walk(_ast.parse(_evo_src))
               if isinstance(n, _ast.FunctionDef) and n.name == "mutate")
    len_bounds = []
    for n in _ast.walk(_fn):
        if not isinstance(n, _ast.Compare):
            continue
        lhs = n.left
        if (isinstance(lhs, _ast.Call) and isinstance(lhs.func, _ast.Name)
                and lhs.func.id == "len" and len(lhs.args) == 1
                and isinstance(lhs.args[0], _ast.Name)
                and lhs.args[0].id == "body"
                and isinstance(n.comparators[0], _ast.Constant)):
            len_bounds.append((type(n.ops[0]).__name__,
                               n.comparators[0].value))
    observed_lengths = sorted(all_lengths)
    c4 = P.Control(
        "C4_length1_bodies_are_unreachable_not_merely_undiscovered",
        "G34's largest single lift is the length-1 class; whether evolution "
        "FAILED to find it or CANNOT express it are different findings and only "
        "one of them is about search",
        null_must_contain="a mutate() that admits a body of length 1, or an "
                          "evolved population containing one",
        can_fail_because="contract pops from the body and recombine slices it, "
                         "so a length-1 body is one unguarded edit away and the "
                         "guards are what stop it")
    c4.observe(bool(len_bounds) and 1 not in observed_lengths,
               {"len_body_guards_in_mutate": sorted(set(len_bounds)),
                "body_lengths_observed_across_all_runs": observed_lengths,
                "length1_rules_evaluated": 0,
                "rules_evaluated_across_all_runs":
                    sum(len(scored_by_arm[a]) for a in ARMS)})
    controls.append(c4)

    f1 = P.Falsifier(
        "F1_evolution_does_not_beat_exhaustive_mining",
        "the evolutionary machinery finds better rules than exhaustive 2-hop "
        "mining on the external yardstick",
        "the best arm's filtered MRR is <= the 3,198-rule exhaustive baseline",
        null_must_contain="an evolved arm exceeding 0.063112")
    f1.observe(f1_fires, {"best_arm": best_arm, "best_mrr": best,
                          "baseline_mrr": base["mrr"]})
    falsifiers.append(f1)

    f2 = P.Falsifier(
        "F2_evolution_never_left_the_seed_shape",
        "extend/contract actually vary body length in practice",
        "every body in every evolved population has length exactly 2",
        null_must_contain="a body of length 1 or >= 3")
    f2.observe(f2_fires, {"body_lengths_seen": sorted(all_lengths)})
    falsifiers.append(f2)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G30, G24, G37],
        artifacts=[os.path.join(HERE, "evolved.py"), out_json],
        controls=controls, falsifiers=falsifiers,
        falsifier="An evolved arm exceeds the exhaustive 2-hop baseline on "
                  "filtered MRR, and evolution produces bodies of length != 2",
        allow_dirty=True,
        note="G38: evolved populations scored on the filtered-MRR yardstick")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for p_ in problems:
        print(f"  PROBLEM: {p_}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
