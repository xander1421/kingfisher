#!/usr/bin/env python3
"""G23 — was materialisation a bad way of buying depth, and is depth worth it?

G22 found that writing mined rules back into the graph exposes new rules that
lose to randomly-rewired edges. The explanation offered there was that a
materialised deduction carries no information: `derived` is a function of
`train`, so a 2-hop rule over `train + derived` is a longer-path rule over
`train` alone, reached badly.

That explanation was fitted to a result. G18's withdrawn "exact bound 1021, head
plus wrapper" was fitted the same way and was wrong. So it gets tested.

    depth 2   (p,q) => r          the G17 / G22-round-0 miner
    depth 3   (p,q,s) => r        the same rules materialisation was groping at,
                                  mined directly, with the chain kept explicit
                                  instead of collapsed into a derived predicate

--------------------------------------------------------------------------
THE COMPARISON THAT MATTERS, AND THE ONE THAT WOULD BE WRONG
--------------------------------------------------------------------------
Comparing depth-3's top-12 confidence against depth-2's directly is invalid.
Depth 3 searches a far larger rule space, and a top-12 taken from more
candidates is inflated by selection alone. That is the same lenient comparison
that has fired on noise three times in this workspace already.

So EACH DEPTH IS COMPARED TO ITS OWN NULL: degree-preserving shuffles of train,
mined at that same depth, with the identical exclusions. What is compared across
depths is the GAP between real and its own null -- never the raw statistic.

G21 is the reason this is not optional: at depth 2 the shuffle alone reproduces
74% of the real statistic. An unnulled depth-3 number would be mostly baseline
and would look like progress.

--------------------------------------------------------------------------
RESTRICTION, STATED UP FRONT
--------------------------------------------------------------------------
Full depth-3 mining over 190k edges is not affordable here, so the depth-3 body
prefix (p,q) is restricted to the top PREFIX_TOP depth-2 bodies by support.
This is a real limitation and it BIASES TOWARD DEPTH 3 FINDING SOMETHING: it
searches extensions of the prefixes that already work best. If depth 3 fails to
beat its null even with that advantage, the failure is the stronger result.
"""

import json
import os
import random
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "G17_composition_redo"))
import redo as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_PAIRS = R.MIN_PAIRS
INV_MAX = R.INV_MAX
TOP_N = R.TOP_N
SEED = 0xC0FFEE
PREFIX_TOP = 60          # depth-3 prefixes, by depth-2 body support
NULLS = 20               # per depth; the p is floor-limited and reported as such


def rules2(graph, p_ex, p_sc):
    body, head = R.mine_pairs(graph)
    byp, rev = R.inverse_rate(graph)
    out = []
    for (p, q, r), _ in head.items():
        bp = body[(p, q)]
        if len(bp) < MIN_PAIRS or r == p or r == q:
            continue
        if byp[p] and len(rev[q] & byp[p]) / len(byp[p]) > INV_MAX:
            continue
        cand = [ac for ac in bp if r not in p_ex.get(ac, ())]
        if len(cand) < MIN_PAIRS:
            continue
        h = sum(1 for ac in cand if r in p_sc.get(ac, ()))
        out.append({"body": (p, q), "r": r, "n": len(cand),
                    "conf": h / len(cand)})
    out.sort(key=lambda x: (-x["conf"], -x["n"]))
    return out, body


def rules3(graph, p_ex, p_sc, prefixes):
    """(p,q,s) => r. Same exclusions as depth 2, extended one hop.

    Guards: a!=d and c!=d, matching depth 2's a!=b, b!=c, c!=a -- an endpoint
    pair that is the same node is not a prediction. `r` equal to ANY body
    predicate is a restatement.
    """
    out_, pair = R.index(graph)
    body3 = defaultdict(set)
    head3 = defaultdict(set)
    for (p, q), pairs in prefixes.items():
        for a, c in pairs:
            for s, d in out_.get(c, ()):
                if d == a or d == c:
                    continue
                body3[(p, q, s)].add((a, d))
                for r in pair.get((a, d), ()):
                    head3[(p, q, s, r)].add((a, d))
    res = []
    for (p, q, s, r), _ in head3.items():
        bp = body3[(p, q, s)]
        if len(bp) < MIN_PAIRS or r in (p, q, s):
            continue
        cand = [ad for ad in bp if r not in p_ex.get(ad, ())]
        if len(cand) < MIN_PAIRS:
            continue
        h = sum(1 for ad in cand if r in p_sc.get(ad, ()))
        res.append({"body": (p, q, s), "r": r, "n": len(cand),
                    "conf": h / len(cand)})
    res.sort(key=lambda x: (-x["conf"], -x["n"]))
    return res


def topconf(rules):
    if not rules:
        return 0.0
    k = min(TOP_N, len(rules))
    return sum(x["conf"] for x in rules[:k]) / k


def prefixes_from(body, top):
    best = sorted(body.items(), key=lambda kv: -len(kv[1]))[:top]
    return {k: v for k, v in best}


def main():
    nt, npred, nent, tri = R.load()
    idx = list(range(nt))
    random.Random(SEED).shuffle(idx)
    cut = int(nt * 0.8)
    train = [tri[i] for i in idx[:cut]]
    test = [tri[i] for i in idx[cut:]]
    p_tr, p_te = R.index(train)[1], R.index(test)[1]
    print(f"split  train {len(train)}  test {len(test)}\n")

    r2, body2 = rules2(train, p_tr, p_te)
    d2 = topconf(r2)
    pre = prefixes_from(body2, PREFIX_TOP)
    print(f"DEPTH 2   {len(r2)} rules   top-{TOP_N} conf {d2:.4f}")
    r3 = rules3(train, p_tr, p_te, pre)
    d3 = topconf(r3)
    print(f"DEPTH 3   {len(r3)} rules   top-{TOP_N} conf {d3:.4f}   "
          f"(prefixes: top {PREFIX_TOP} depth-2 bodies, "
          f"{sum(len(v) for v in pre.values())} prefix pairs)")
    for x in r3[:5]:
        print(f"            {x['body']}=>{x['r']}  n={x['n']:5d}  "
              f"conf {x['conf']:.3f}")

    print(f"\nNULLS  {NULLS} degree-preserving shuffles per depth. Each depth "
          f"is compared to\n       its own null; the raw statistics are NOT "
          f"compared across depths.")
    n2, n3 = [], []
    for i in range(NULLS):
        sh = R.shuffled(train, 3000 + i)
        p_sh = R.index(sh)[1]
        s2, b2 = rules2(sh, p_sh, p_te)
        n2.append(topconf(s2))
        s3 = rules3(sh, p_sh, p_te, prefixes_from(b2, PREFIX_TOP))
        n3.append(topconf(s3))
        print(f"       draw {i + 1:2d}/{NULLS}   depth2 {n2[-1]:.4f}   "
              f"depth3 {n3[-1]:.4f}")

    m2, sd2 = st.mean(n2), st.pstdev(n2)
    m3, sd3 = st.mean(n3), st.pstdev(n3)
    g2, g3 = d2 - m2, d3 - m3
    z2 = g2 / sd2 if sd2 else float("inf")
    z3 = g3 / sd3 if sd3 else float("inf")
    print(f"\n{'':10}{'real':>9}{'null mean':>11}{'null sd':>9}{'gap':>9}"
          f"{'gap/sd':>8}{'>=real':>8}")
    for nm, real, m, sd, g, z, ns in (("depth 2", d2, m2, sd2, g2, z2, n2),
                                      ("depth 3", d3, m3, sd3, g3, z3, n3)):
        ge = sum(1 for x in ns if x >= real)
        print(f"{nm:<10}{real:>9.4f}{m:>11.4f}{sd:>9.4f}{g:>+9.4f}"
              f"{z:>8.1f}{ge:>5}/{len(ns)}")

    print(f"\nG22 for comparison: materialisation reached 0.0956 against its "
          f"own\nshuffled-edge control at 0.1222 — a gap of -0.0266.")

    if g3 <= 0:
        v = ("DEPTH DOES NOT PAY — depth 3 does not beat its own null even "
             "with prefixes chosen to favour it")
    elif g3 > g2:
        v = (f"DEPTH PAYS — depth-3 gap {g3:+.4f} exceeds depth-2 {g2:+.4f}; "
             f"materialisation was a bad way to buy it")
    else:
        v = (f"DEPTH PAYS LESS THAN WIDTH — depth-3 gap {g3:+.4f} is below "
             f"depth-2 {g2:+.4f}; deeper search finds weaker structure")
    print(f"\nVERDICT: {v}")

    json.dump({"depth2": {"real": d2, "null_mean": m2, "null_sd": sd2,
                          "gap": g2, "n_rules": len(r2)},
               "depth3": {"real": d3, "null_mean": m3, "null_sd": sd3,
                          "gap": g3, "n_rules": len(r3)},
               "nulls": {"depth2": n2, "depth3": n3, "n": NULLS},
               "g22_materialisation": {"real": 0.0956, "control": 0.1222},
               "verdict": v,
               "conditions": {"data": "real:FB15k-237", "split_seed": SEED,
                              "split": "80/20", "prefix_top": PREFIX_TOP,
                              "platforms": [["macos", "aarch64"]],
                              "concurrency": "single-process",
                              "swept": {"depth": [2, 3]}},
               "cites": ["G17_composition_redo", "G21_null_rust",
                         "G22_evolve"]},
              open(os.path.join(HERE, "depth.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
