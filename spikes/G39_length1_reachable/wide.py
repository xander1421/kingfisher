r"""G39 — is the evolutionary machinery SEARCH-limited or SELECTION-limited?

G38 measured that `evo.mutate` **cannot express** a length-1 body: `len(body) < 2`
rejects at `evo.py:366`, `contract` floors at `:347`, `extend` caps at `:343`, so
the genotype space is exactly length 2 or 3. G34 measured the length-1 class ALONE
at 0.1572 filtered MRR -- 5.89x G38's best evolved arm and 2.49x the whole
3,198-rule exhaustive 2-hop baseline. So the question G38 left open is sharp:

  * if the machinery is SEARCH-limited, widening the guards moves the arm toward
    0.1572 and the operator set was the ceiling;
  * if it is SELECTION-limited at `MAX_POP = 200`, it does not move, and G38's
    2.11x per-rule advantage is the whole of what evolution buys.

METHOD, AND IT IS THE PART THAT COULD HAVE GONE WRONG QUIETLY
------------------------------------------------------------
`evo.py` is NOT edited. G24/G25/G27 are published against it, and a mid-sweep
edit to a shared generator is exactly the `pick_parent` contamination C7 paid for
with 6 of 12 runs split across two algorithms under identical arm names. The file
is COPIED into this spike, the guards changed in the copy, and **C3 measures that
the guards are the only difference** -- diffed, never asserted, because an
ablation that changes more than it names cannot measure the named part (A25,
earned in this lane on G24's `no_death`).

THE THIRD CHANGED LINE IS REPORTED, NOT BURIED IN "THE GUARDS". Widening
`contract` makes `recombine`'s `rng.randrange(1, len(body))` reachable at
`len(body) == 1`, where it RAISES. The added guard is a no-op for every body the
unwidened `evo.py` can hold, but it is a third change and C3 names it.

BOTH ARMS ARE FED THE SAME DATASET OBJECT, built once by the original module, so
"same split" is not an argument -- it is the same Python objects.

FALSIFIERS, POSTED TO CHANNEL.md BEFORE THIS RAN:
  F1  If the widened arm's median filtered MRR does not exceed G38's `full`
      median 0.026695, reaching length-1 does not help: the ceiling is SELECTION
      at MAX_POP, not the operator set. This is the outcome that costs most --
      it closes the widening path -- and it is published as it lands.
  F2  If the widened populations contain no body of length 1, the guard change is
      INERT in practice and this run measures nothing about search (family A).
"""
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
for _p in ("harness", "G30_external_yardstick", "G17_composition_redo",
           "G24_population", "G37_varlen_bodies", "G38_evolved_on_yardstick"):
    sys.path.insert(0, os.path.join(SPIKES, _p))
sys.path.insert(0, HERE)

import provenance as P       # noqa: E402
import kfcheck               # noqa: E402
import yardstick as Y        # noqa: E402
import varlen as V           # noqa: E402
import evo as E              # noqa: E402  the ORIGINAL, untouched
import evo_wide as W         # noqa: E402  the copy, guards widened
# G38's scoring helpers are IMPORTED rather than reimplemented, so C4's
# instrument-identity check is over the same code path and not a lookalike.
import evolved as G38        # noqa: E402

G30 = os.path.join(SPIKES, "G30_external_yardstick")
G24 = os.path.join(SPIKES, "G24_population")
G37 = os.path.join(SPIKES, "G37_varlen_bodies")
G38D = os.path.join(SPIKES, "G38_evolved_on_yardstick")

SEEDS = (777, 1234, 31337)
G30_G17_ALL_MRR = 0.063112
G38_FULL_MEDIAN = 0.02669542335020429     # G38 evolved.json, arms.full.mrr
G38_FULL_RULES = [53, 53, 54]             # G38 evolved.json, per-seed
G34_LENGTH1_ONLY_MRR = 0.1572             # G34, the class this widening targets


def diff_guards():
    """What differs between `evo.py` and the widened copy — structurally.

    AST-level and not line-level, and that is not a convenience. The first draft
    of this control asserted *"every changed line contains `len(body)`"*, which
    flagged the guard's own `return None` as an offence. Loosening the predicate
    to let that through would have been weakening a control to pass it; comparing
    ASTs instead is STRICTER, because it ignores comments and whitespace entirely
    while refusing any change anywhere outside the one function.

    Returns `(changed_lines, differing_units)`. `differing_units` is every named
    module-level unit whose AST is not identical between the two files, and C3
    requires it to be exactly `['mutate']` -- nothing else in a 600-line module
    moved.
    """
    import ast
    import difflib
    src_a = open(os.path.join(G24, "evo.py")).read()
    src_b = open(os.path.join(HERE, "evo_wide.py")).read()

    def units(src):
        """name -> ast.dump, for every top-level unit including the module body
        outside function/class defs (so a changed constant is not invisible)."""
        tree = ast.parse(src)
        out, loose = {}, []
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
                out[n.name] = ast.dump(n)
            elif not (isinstance(n, ast.Expr)
                      and isinstance(n.value, ast.Constant)):
                loose.append(ast.dump(n))   # skips the module docstring only
        out["<module-level statements>"] = "\n".join(loose)
        return out

    ua, ub = units(src_a), units(src_b)
    differing = sorted(set(ua) ^ set(ub))
    differing += sorted(k for k in set(ua) & set(ub) if ua[k] != ub[k])
    changed = [l[2:] for l in difflib.ndiff(src_a.split("\n"),
                                            src_b.split("\n"))
               if l[:2] in ("- ", "+ ")]
    return changed, sorted(set(differing))


def evaluate(pop, npred, out_adj, in_adj, pair_tr, true_sp, true_po, test,
             nent, rules_2hop):
    """G38's scoring path, unchanged: drop planted, dedupe, confidence on
    G30's train, score with the variable-length walk, size-matched baseline."""
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
        c, n, h = G38.conf_on_train(body, head, out_adj, pair_tr)
        if c is None:
            unscorable += 1
            continue
        scored.append({"body": body, "head": head, "conf": c,
                       "pairs": n, "hits": h})

    lengths = defaultdict(int)
    for r in scored:
        lengths[len(r["body"])] += 1

    res = V.evaluate_varlen(scored, test, out_adj, in_adj, true_sp, true_po,
                            nent)
    matched = V.evaluate_varlen(rules_2hop[:len(scored)], test, out_adj, in_adj,
                                true_sp, true_po, nent)

    # A25, THE REASON THIS EXISTS. The two arms differ in their whole search
    # trajectory and in population size, not only in what lengths they can hold,
    # so "widening raised the arm" does NOT license "the length-1 rules are what
    # raised it" -- that is `CLAUDE.md`'s correct-numbers-wrong-attribution, and
    # it is the claim a reader will take away unless it is measured. Scoring-time
    # ablation, on the SAME population: drop the length-1 rules and re-score, and
    # score them alone. No re-evolution, so nothing else moves.
    def sub(pred):
        rs = [r for r in scored if pred(len(r["body"]))]
        if not rs:
            return None
        return {"mrr": V.evaluate_varlen(rs, test, out_adj, in_adj, true_sp,
                                         true_po, nent)["mrr"], "rules": len(rs)}

    return scored, {
        "ablate_drop_length1": sub(lambda n: n > 1),
        "ablate_only_length1": sub(lambda n: n == 1),
        "mrr": res["mrr"], "hits1": res["hits1"], "hits3": res["hits3"],
        "hits10": res["hits10"], "size_matched_mrr": matched["mrr"],
        "ratio_vs_size_matched": res["mrr"] / max(matched["mrr"], 1e-12),
        "pop_size": len(pop), "dropped_planted": dropped,
        "evaluated_rules": len(scored),
        "unscorable_below_min_pairs": unscorable,
        "body_lengths": dict(sorted(lengths.items()))}


def main():
    print("=" * 78)
    print("G39 — does reaching length-1 move the arm, or is the ceiling MAX_POP?")
    print("=" * 78)

    nt, npred, nent, tri, train, dev, test = Y.load_dataset()
    out_adj, in_adj, pair_tr, _, _ = Y.build_graph_index(train, nent)
    true_sp, true_po = Y.build_filter_index(tri)
    rules_2hop = Y.mine_g17_rules(train)
    base = V.evaluate_varlen(rules_2hop, test, out_adj, in_adj, true_sp,
                             true_po, nent)
    c1_ok = abs(base["mrr"] - G30_G17_ALL_MRR) < 1e-6
    print(f"\nbaseline  G17 exhaustive 2-hop  {len(rules_2hop):,} rules   "
          f"MRR {base['mrr']:.6f}   (C1 {'ok' if c1_ok else 'FAILED'})")

    changed, differing = diff_guards()
    c3_ok = differing == ["mutate"]
    print(f"\nC3: of every top-level unit in evo.py, the AST differs in "
          f"{differing} -> {'ok' if c3_ok else 'FAILED'}")
    for l in changed:
        if l.strip():
            print(f"    {l.strip()[:88]}")

    # ONE dataset, built once by the ORIGINAL module and handed to both arms.
    ev_train, dev_pairs, test_pairs, ev_npred, planted = E.dataset()

    arms = {"orig": E, "wide": W}
    detail, scored_by_arm = {}, {}
    for name, mod in arms.items():
        per_seed = []
        for seed in SEEDS:
            mod.RUN_SEED = seed
            t0 = time.time()
            _, rejected, pop = mod.run("full", ev_train, dev_pairs, test_pairs,
                                       ev_npred, planted, log=False)
            scored, row = evaluate(pop, npred, out_adj, in_adj, pair_tr,
                                   true_sp, true_po, test, nent, rules_2hop)
            row.update(seed=seed, evolve_sec=round(time.time() - t0, 1),
                       rejected_capped=rejected)
            per_seed.append(row)
            scored_by_arm.setdefault(name, []).extend(scored)
            print(f"  {name:<6} seed {seed:<6} rules {row['evaluated_rules']:>3}  "
                  f"MRR {row['mrr']:.6f}  vs mined@{row['evaluated_rules']} "
                  f"{row['size_matched_mrr']:.6f}  "
                  f"({row['ratio_vs_size_matched']:.2f}x)  planted "
                  f"{row['dropped_planted']}/{row['pop_size']}  lengths "
                  f"{row['body_lengths']}")
        mrrs = sorted(d["mrr"] for d in per_seed)
        drops = sorted(d["ablate_drop_length1"]["mrr"] for d in per_seed
                       if d["ablate_drop_length1"])
        onlys = sorted(d["ablate_only_length1"]["mrr"] for d in per_seed
                       if d["ablate_only_length1"])
        detail[name] = {
            "median_mrr_without_length1": drops[len(drops) // 2] if drops else None,
            "median_mrr_length1_only": onlys[len(onlys) // 2] if onlys else None,
            "per_seed": per_seed,
            "median_mrr": mrrs[len(mrrs) // 2],
            "mrr_range": [mrrs[0], mrrs[-1]],
            "evaluated_rules": sorted(d["evaluated_rules"] for d in per_seed),
            "length1_rules": sum(d["body_lengths"].get(1, 0) for d in per_seed),
            "body_lengths_seen": sorted(
                {k for d in per_seed for k in d["body_lengths"]})}
        print(f"  -> {name}: median MRR {detail[name]['median_mrr']:.6f} "
              f"[{mrrs[0]:.6f}, {mrrs[-1]:.6f}], lengths "
              f"{detail[name]['body_lengths_seen']}, "
              f"{detail[name]['length1_rules']} length-1 rule(s)")
        d1 = detail[name]["median_mrr_without_length1"]
        o1 = detail[name]["median_mrr_length1_only"]
        print(f"     A25 ablation on the SAME population: drop length-1 -> "
              f"{('%.6f' % d1) if d1 is not None else 'n/a'}   "
              f"length-1 alone -> {('%.6f' % o1) if o1 is not None else 'n/a'}\n")

    wide_med, orig_med = detail["wide"]["median_mrr"], detail["orig"]["median_mrr"]
    f1_fires = wide_med <= G38_FULL_MEDIAN
    f2_fires = detail["wide"]["length1_rules"] == 0
    c4_ok = (abs(orig_med - G38_FULL_MEDIAN) < 1e-12
             and detail["orig"]["evaluated_rules"] == G38_FULL_RULES)

    print("=" * 78)
    print(f"C4 instrument identity : orig arm {orig_med:.6f} vs G38's "
          f"{G38_FULL_MEDIAN:.6f}, rules {detail['orig']['evaluated_rules']} vs "
          f"{G38_FULL_RULES} -> {'ok' if c4_ok else 'FAILED'}")
    print(f"F1 widening helps      : wide {wide_med:.6f} vs G38 full "
          f"{G38_FULL_MEDIAN:.6f} -> "
          f"{'FIRED (it does NOT help)' if f1_fires else 'did not fire'}")
    print(f"F2 the edit is live    : {detail['wide']['length1_rules']} length-1 "
          f"rule(s) in the widened arm -> "
          f"{'FIRED (inert edit)' if f2_fires else 'did not fire'}")
    print(f"   for scale, G34's length-1 class alone: "
          f"{G34_LENGTH1_ONLY_MRR}")

    out = {"baseline_g17_2hop_mrr": base["mrr"],
           "baseline_rule_count": len(rules_2hop),
           "arms": detail,
           "g38_full_median": G38_FULL_MEDIAN,
           "g34_length1_only_mrr": G34_LENGTH1_ONLY_MRR,
           "changed_code_lines": changed,
           "seeds": list(SEEDS),
           "c1_baseline_reproduces_g30": c1_ok,
           "c3_only_mutate_differs": c3_ok,
           "differing_ast_units": differing,
           "c4_orig_arm_reproduces_g38": c4_ok,
           "f1_widening_does_not_help": f1_fires,
           "f2_edit_inert": f2_fires}
    out_json = os.path.join(HERE, "wide.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True, default=str)

    controls, falsifiers = [], []
    c1 = P.Control(
        "C1_baseline_reproduces_G30_through_this_evaluator",
        "if the baseline drifts, no arm number here means what it says",
        null_must_contain="a G17 exhaustive baseline differing from 0.063112",
        can_fail_because="a different confidence basis, split or filter index "
                         "would move it while both arms stayed self-consistent")
    c1.observe(c1_ok, {"baseline_mrr": base["mrr"], "g30": G30_G17_ALL_MRR})
    controls.append(c1)

    c2 = P.Control(
        "C2_planted_control_excluded_from_both_arms",
        "a rule that scored well by learning the A15 plant would be a finding "
        "about the plant, not about FB15k-237",
        null_must_contain="a planted predicate id >= npred reaching the evaluator",
        can_fail_because="evo.dataset() injects 600 planted edges into train, so "
                         "both populations genuinely can carry them")
    leaked = [r for a in arms for r in scored_by_arm[a]
              if any(p >= npred for p in r["body"]) or r["head"] >= npred]
    c2.observe(not leaked,
               {"planted_rules_reaching_evaluator": len(leaked),
                "dropped_per_arm": {a: [d["dropped_planted"]
                                        for d in detail[a]["per_seed"]]
                                    for a in arms},
                "rules_checked": sum(len(scored_by_arm[a]) for a in arms)})
    controls.append(c2)

    c3 = P.Control(
        "C3_mutate_is_the_only_unit_that_differs",
        "an ablation that changes more than it names cannot measure the named "
        "part (A25, earned in this lane on G24's no_death arm)",
        null_must_contain="a top-level unit other than `mutate` whose AST differs",
        can_fail_because="the widened file is a full copy of a 600-line module "
                         "with 18 top-level units, so an edit to any constant, "
                         "any other function, or the module body would appear here")
    c3.observe(c3_ok,
               {"differing_ast_units": differing,
                "units_compared": 18,
                "changed_source_lines": [l for l in changed if l.strip()]})
    controls.append(c3)

    c4 = P.Control(
        "C4_unwidened_arm_reproduces_G38_exactly",
        "if the unwidened arm does not return G38's numbers, this script changed "
        "something other than the guards and no between-arm difference means "
        "anything",
        null_must_contain="an orig-arm median differing from G38's 0.02669542335020429",
        can_fail_because="this script rebuilt the evaluation loop around G38's "
                         "helpers, so a different dedupe, drop or min_pairs step "
                         "would move it while both arms stayed comparable")
    c4.observe(c4_ok, {"orig_median": orig_med, "g38_median": G38_FULL_MEDIAN,
                       "orig_rules": detail["orig"]["evaluated_rules"],
                       "g38_rules": G38_FULL_RULES})
    controls.append(c4)

    f1 = P.Falsifier(
        "F1_widening_to_length1_does_not_help",
        "reaching length-1 bodies raises the evolved arm toward G34's 0.1572",
        "the widened arm's median filtered MRR is <= G38's full median",
        null_must_contain="a widened arm exceeding 0.02669542335020429")
    f1.observe(f1_fires, {"wide_median": wide_med, "orig_median": orig_med,
                          "g38_full_median": G38_FULL_MEDIAN,
                          "g34_length1_only": G34_LENGTH1_ONLY_MRR,
                          "wide_median_without_length1":
                              detail["wide"]["median_mrr_without_length1"],
                          "wide_median_length1_only":
                              detail["wide"]["median_mrr_length1_only"],
                          "paired_seed_deltas": [
                              (s_, round(w["mrr"] - o["mrr"], 6))
                              for s_, o, w in zip(SEEDS, detail["orig"]["per_seed"],
                                                  detail["wide"]["per_seed"])]})
    falsifiers.append(f1)

    f2 = P.Falsifier(
        "F2_the_guard_change_is_inert",
        "the widened guards actually produce length-1 bodies in practice",
        "the widened populations contain no body of length 1",
        null_must_contain="a scored rule whose body has length 1")
    f2.observe(f2_fires,
               {"length1_rules_wide": detail["wide"]["length1_rules"],
                "length1_rules_orig": detail["orig"]["length1_rules"],
                "body_lengths_wide": detail["wide"]["body_lengths_seen"],
                "body_lengths_orig": detail["orig"]["body_lengths_seen"]})
    falsifiers.append(f2)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G30, G24, G37, G38D],
        artifacts=[os.path.join(HERE, "wide.py"),
                   os.path.join(HERE, "evo_wide.py"), out_json],
        controls=controls, falsifiers=falsifiers,
        falsifier="The widened arm exceeds G38's full median, and it does so "
                  "because length-1 bodies it could not previously express "
                  "survive selection",
        allow_dirty=True,
        note="G39: is the machinery search-limited or selection-limited?")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for p_ in problems:
        print(f"  PROBLEM: {p_}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
