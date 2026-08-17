#!/usr/bin/env python3
"""G22 — does a graph that rewrites itself become able to find rules it could
not find before?

Everything in the G-series so far MEASURES a graph. Nothing evolves one. This
closes the loop:

    round 0   mine composition rules from train
    rewrite   materialise the best rules' conclusions as real edges
    round 1   re-mine on the AUGMENTED graph
    question  is there a rule that is minable ONLY after the rewrite, and does
              it predict held-out edges better than chance?

A rule findable only once another rule's conclusions are materialised is
second-order structure: the base graph contains it, but not in a form 2-hop
mining can reach. That is the closest thing to discovery this substrate can be
made to do, and unlike "the graph got bigger" it is falsifiable.

--------------------------------------------------------------------------
LEAKAGE, AND WHY THE SPLIT IS THREE-WAY
--------------------------------------------------------------------------
Materialised edges are PREDICTIONS. Some are correct. If the rules to
materialise are chosen using the same set the new rules are later scored on,
then correct test answers get written into the training graph and any round-1
rule that reconstructs them scores perfectly for no reason.

    train (70%)  bodies are mined here; derived edges are a deterministic
                 function of train and the chosen rule set, and contain no
                 information from anywhere else
    dev   (15%)  used ONLY to rank round-0 rules and pick which to materialise
    test  (15%)  never touched until round-1 rules are scored

Because derived = f(train, rules(dev)), the test set is causally upstream of
nothing. Any correlation between derived edges and test is real predictive
structure rather than leakage.

--------------------------------------------------------------------------
CONTROLS
--------------------------------------------------------------------------
NEGATIVE (the one that can kill the result). Adding 50k edges to a graph
creates new 2-hop paths whatever those edges are, so "new rules appeared" is
worthless on its own. The control materialises the SAME derived edges with
their objects permuted within predicate — identical count, identical predicate
marginals, identical subject out-degrees, composition alignment destroyed. If
the control also yields good new rules, the effect is edge-count and the spike
is dead.

POSITIVE, A15 (the one that makes a null result mean anything). A synthetic
second-order chain is planted whose body has support ONLY after materialisation.
If the pipeline cannot recover a rule that is there by construction, it is blind
and "no discovery" would be an instrument failure, not a finding.

Both controls report the SIZE of the intervention they applied, not only a
verdict — see G17's A20, which twice printed a clean "NOT DETECTED" while
having planted nothing at all.
"""

import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "G17_composition_redo"))
import redo as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

MIN_PAIRS = R.MIN_PAIRS      # 30
INV_MAX = R.INV_MAX          # 0.30
TOP_N = R.TOP_N              # 12

MATERIALISE_TOP = 12         # round-0 rules whose conclusions get written back
MAX_BODY = 20_000            # per-rule cap on materialised edges
DERIVED_CAP = 60_000         # total cap; both caps are REPORTED, never silent
SEED = 0xC0FFEE


def mine(graph, exclude_pair, score_pair):
    """Rules from `graph`, excluding pairs already answered in `exclude_pair`,
    scored against `score_pair`. Same exclusions as redo.py, which are the ones
    that killed G15: pair-level denominators, no inverse bodies, no
    restatements, no self-loops."""
    body, head = R.mine_pairs(graph)
    byp, rev = R.inverse_rate(graph)
    rules = []
    for (p, q, r), _ in head.items():
        bp = body[(p, q)]
        if len(bp) < MIN_PAIRS:
            continue
        if byp[p] and len(rev[q] & byp[p]) / len(byp[p]) > INV_MAX:
            continue
        if r == p or r == q:
            continue
        cand = [ac for ac in bp if r not in exclude_pair.get(ac, ())]
        if len(cand) < MIN_PAIRS:
            continue
        hits = sum(1 for ac in cand if r in score_pair.get(ac, ()))
        rules.append({"p": p, "q": q, "r": r, "body": len(bp),
                      "n": len(cand), "hits": hits, "conf": hits / len(cand)})
    rules.sort(key=lambda x: (-x["conf"], -x["n"]))
    return rules, body


def materialise(rules, body, exclude_pair, top, rng=None):
    """Write the top rules' conclusions back into the graph as real edges.

    Returns (edges, log). The log records what each rule contributed and what
    the caps dropped, because a cap that is not printed reads as coverage.
    """
    edges, log, total = [], [], 0
    for rl in rules[:top]:
        bp = body[(rl["p"], rl["q"])]
        cand = [ac for ac in sorted(bp)
                if rl["r"] not in exclude_pair.get(ac, ())]
        wanted = len(cand)
        if wanted > MAX_BODY:
            cand = cand[:MAX_BODY]
        if total + len(cand) > DERIVED_CAP:
            cand = cand[:max(0, DERIVED_CAP - total)]
        new = [(rl["r"], a, c) for a, c in cand]
        edges += new
        total += len(new)
        log.append({"rule": [rl["p"], rl["q"], rl["r"]], "conf": rl["conf"],
                    "eligible": wanted, "written": len(new)})
        if total >= DERIVED_CAP:
            break
    return edges, log


def shuffle_derived(edges, seed):
    """NEGATIVE CONTROL. Permute objects within predicate across the derived
    set: same count, same predicate marginals, same subject degrees, the
    composition alignment destroyed. Matches G17's degree-preserving null."""
    rng = random.Random(seed)
    byp = defaultdict(list)
    for p, s, o in edges:
        byp[p].append((s, o))
    out = []
    for p in sorted(byp):
        prs = byp[p]
        objs = [o for _, o in prs]
        rng.shuffle(objs)
        out += [(p, s, objs[i]) for i, (s, _) in enumerate(prs)]
    return out


def plant_second_order(derived, train, npred, nent, rng):
    """POSITIVE CONTROL (A15). Build a rule that is minable ONLY after the
    rewrite, so a pipeline that misses it is proven blind.

    For derived edges (r, a, c) -- which by construction do not exist in train
    -- add (s, c, d) with a fresh predicate s and fresh entities d, and put the
    conclusion (t, a, d) in the scored set. The body (r, s) then has support
    only via materialised edges: in train, no r-edge joins a to c at all.
    """
    s_pred, t_pred = npred + 1, npred + 2
    use = derived[:400]
    extra_train, extra_score = [], []
    for i, (r, a, c) in enumerate(use):
        d = nent + 1 + i
        extra_train.append((s_pred, c, d))
        extra_score.append((t_pred, a, d))
    return (s_pred, t_pred), extra_train, extra_score


def pairs_of(triples):
    return R.index(triples)[1]


def main():
    nt, npred, nent, tri = R.load()
    idx = list(range(nt))
    random.Random(SEED).shuffle(idx)
    a, b = int(nt * 0.70), int(nt * 0.85)
    train = [tri[i] for i in idx[:a]]
    dev = [tri[i] for i in idx[a:b]]
    test = [tri[i] for i in idx[b:]]
    p_tr, p_dev, p_te = pairs_of(train), pairs_of(dev), pairs_of(test)
    print(f"split  train {len(train)}  dev {len(dev)}  test {len(test)}"
          f"   ({npred} predicates, {nent} entities)\n")

    # ---------------- round 0 -------------------------------------------
    r0_dev, body0 = mine(train, p_tr, p_dev)
    r0_test, _ = mine(train, p_tr, p_te)
    base0 = sum(x["conf"] for x in r0_test[:TOP_N]) / TOP_N
    known = {(x["p"], x["q"], x["r"]) for x in r0_dev}
    print(f"ROUND 0   {len(r0_dev)} rules minable from train")
    print(f"          top-{TOP_N} conf on test {base0:.4f}  (the G17 statistic)")

    # ---------------- rewrite -------------------------------------------
    derived, mlog = materialise(r0_dev, body0, p_tr, MATERIALISE_TOP)
    elig = sum(m["eligible"] for m in mlog)
    print(f"\nREWRITE   {len(derived)} edges written from "
          f"{len(mlog)} rules")
    print(f"          {elig} were eligible; caps dropped {elig - len(derived)}"
          f"  (MAX_BODY={MAX_BODY}, DERIVED_CAP={DERIVED_CAP})")
    for m in mlog[:5]:
        print(f"            rule {tuple(m['rule'])}  conf {m['conf']:.3f}  "
              f"eligible {m['eligible']:6d}  written {m['written']:6d}")
    if not derived:
        print("\nNOTHING WAS WRITTEN — the rewrite is empty and every result "
              "below would be vacuous. Stopping.")
        return 2

    # ---------------- round 1, treatment --------------------------------
    aug = train + derived
    p_aug = pairs_of(aug)
    r1, _ = mine(aug, p_aug, p_te)
    new = [x for x in r1 if (x["p"], x["q"], x["r"]) not in known]
    print(f"\nROUND 1   {len(r1)} rules minable from train+derived")
    print(f"          {len(new)} of them were NOT minable in round 0")
    if new:
        top = new[:TOP_N]
        print(f"          new-rule top-{len(top)} conf on test "
              f"{sum(x['conf'] for x in top) / len(top):.4f}")
        for x in top[:5]:
            print(f"            ({x['p']},{x['q']})=>{x['r']}  n={x['n']:5d}  "
                  f"conf {x['conf']:.3f}")

    # ---------------- round 1, negative control -------------------------
    ctrl_edges = shuffle_derived(derived, 7)
    aug_c = train + ctrl_edges
    r1c, _ = mine(aug_c, pairs_of(aug_c), p_te)
    new_c = [x for x in r1c if (x["p"], x["q"], x["r"]) not in known]
    print(f"\nCONTROL   same {len(ctrl_edges)} edges, objects permuted within "
          f"predicate")
    print(f"          {len(new_c)} rules not minable in round 0")
    conf_c = (sum(x["conf"] for x in new_c[:TOP_N]) / min(TOP_N, len(new_c))
              if new_c else 0.0)
    if new_c:
        print(f"          new-rule top-{min(TOP_N, len(new_c))} conf on test "
              f"{conf_c:.4f}")

    # ---------------- positive control ----------------------------------
    rng = random.Random(99)
    (s_pred, t_pred), ex_tr, ex_sc = plant_second_order(derived, train, npred,
                                                        nent, rng)
    aug_p = aug + ex_tr
    p_te_p = pairs_of(test + ex_sc)
    r1p, _ = mine(aug_p, pairs_of(aug_p), p_te_p)
    found = [x for x in r1p if x["r"] == t_pred]
    print(f"\nA15       planted a second-order chain: {len(ex_tr)} (s,c,d) "
          f"edges into train,\n          {len(ex_sc)} (t,a,d) conclusions into "
          f"the scored set. Body (r,s) has\n          support only via "
          f"materialised r-edges.")
    if found:
        f0 = max(found, key=lambda x: x["conf"])
        print(f"          RECOVERED ({f0['p']},{f0['q']})=>{f0['r']}  "
              f"n={f0['n']}  conf {f0['conf']:.3f}  -- machinery is not blind")
    else:
        print(f"          NOT RECOVERED — the pipeline cannot see a "
              f"second-order rule that\n          is present by construction. "
              f"Every null result above is void.")

    # ---------------- verdict -------------------------------------------
    conf_new = (sum(x["conf"] for x in new[:TOP_N]) / min(TOP_N, len(new))
                if new else 0.0)
    if not found:
        v = "VOID — positive control failed; the machinery is blind"
    elif not new:
        v = "NO DISCOVERY — the rewrite exposed no rule that was not already minable"
    elif conf_new <= conf_c:
        v = (f"NO DISCOVERY — new rules ({conf_new:.4f}) do not beat the "
             f"shuffled-edge control ({conf_c:.4f}); the effect is edge count")
    else:
        v = (f"DISCOVERY — {len(new)} rules minable only after the rewrite, "
             f"test conf {conf_new:.4f} vs control {conf_c:.4f}")
    print(f"\nVERDICT: {v}")

    json.dump({"split": [len(train), len(dev), len(test)],
               "round0_rules": len(r0_dev), "round0_top_conf": base0,
               "derived": len(derived), "eligible": elig,
               "caps": {"max_body": MAX_BODY, "derived_cap": DERIVED_CAP},
               "materialised": mlog,
               "round1_rules": len(r1), "new_rules": len(new),
               "new_conf": conf_new,
               "control_new_rules": len(new_c), "control_conf": conf_c,
               "a15_recovered": bool(found), "verdict": v,
               "conditions": {"data": "real:FB15k-237", "split_seed": SEED,
                              "platforms": [["macos", "aarch64"]],
                              "concurrency": "single-process"},
               "cites": ["G17_composition_redo", "G21_null_rust"]},
              open(os.path.join(HERE, "evolve.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
