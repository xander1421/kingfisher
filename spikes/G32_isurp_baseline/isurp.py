#!/usr/bin/env python3
"""G32 — hyperon-miner's baseline is INSIDE the statistic. Mine needs 500 shuffles.
Do they agree, and is my null even measuring what I think it measures?

`elders/hyperon-miner/experiments/surprisingness/isurp.metta`:

    (= (isurp $pattern $db $normalize $db_ratio)
       (let* ((($emin $emax) (ji_prob_est_interval $pattern $db $db_ratio))
              ($emp        (emp-prob-pbs $pattern $db $emax $db_ratio))
              ($dst        (dst_from_interval $emin $emax $emp))
              ($maxprb     (max-atom ($emp $emax))))
         (min-atom ((if $normalize (// $dst $maxprb) $dst) 1.0))))

Surprisingness is the DISTANCE of the empirical probability from the interval an
independence assumption predicts (`pro-prob-wout-joint` multiplies subpattern
probabilities, treating components as independent). The chance-structure baseline
is subtracted inside the measure, analytically. The whole G-series instead
estimates that baseline afterwards by shuffling the graph 500 times, which is why
every p-value we publish is floored at 1/501.

THE OBSERVATION THAT MAKES THIS CHEAP: `redo.shuffled` permutes the OBJECTS within
each predicate. Out-degree per (subject, predicate) is preserved exactly, and the
multiset of objects is a permutation of itself so in-degree per (object,
predicate) is preserved too. Only the PAIRING is randomised. A null that
preserves both degree sequences and randomises pairing has a closed form: for a
candidate pair (a, c) and head predicate r with m_r edges,

    E[# r-edges landing on (a,c)] = d_out_r(a) * d_in_r(c) / m_r

so the expected confidence of a rule over its candidate set C is the mean of
min(1, that) over C -- arithmetic, no sampling, no floor.

AND A SECOND QUESTION I DID NOT SET OUT TO ASK. The G-series null shuffles the
WHOLE graph and re-scores, so the body's candidate set changes too. That conflates
"is the head independent of the body" with "does the body itself have unusual
structure". The closed form holds the body fixed and randomises only the head. If
those two nulls disagree, the 500-shuffle null has been answering a different
question from the one its RESULT.md sentences claim.

SETTING. `isurp` scores a pattern's surprisingness WITHIN a database, not its
held-out accuracy, so this measures association inside the train graph and there
is no test split. The first version of this script excluded from the candidate set
every pair where the head already held in train -- copying redo.evaluate's
held-out construction -- and then scored confidence against train, so conf was
0.0000 BY CONSTRUCTION on every rule. Recorded rather than quietly fixed: a
number that cannot be nonzero is not a measurement.

Four quantities per rule:
  conf        empirical confidence: fraction of body-matched pairs carrying r
  E_closed    closed-form degree-preserving expectation (arithmetic, no sampling)
  E_head      mean over K shuffles of r's edges ONLY, body held fixed -- the
              matched empirical version of E_closed
  E_whole     mean over K shuffles of the WHOLE graph with the body RE-WALKED --
              this is the G-series null. If E_head and E_whole differ, the
              500-shuffle null has been answering a different question from the
              one its sentences claim, because it randomises the body too.

CONTROLS, each with the input that would make it fail:
  C1 INDEPENDENT HEAD   a synthetic head predicate placed at random over the same
                        entities with matched edge count. Excess must be ~0 under
                        every baseline. FAILS if a baseline reports structure
                        where none was planted -- which would make every excess
                        it has ever scored suspect.
  C2 PERFECT DEPENDENCE a synthetic head placed exactly on the body's endpoint
                        pairs. Excess must be large under every baseline. FAILS if
                        a baseline explains away a dependence that is real by
                        construction -- the A20 direction: a null that can contain
                        the effect it is meant to exclude.
  C3 AGREEMENT          closed form vs head-only shuffle. FAILS if they differ by
                        more than sampling error, which would mean the closed form
                        is wrong and the sampling is load-bearing after all.
"""

import json
import math
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G17_composition_redo"))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import redo as R  # noqa: E402
import provenance as P  # noqa: E402

MIN_PAIRS = 30
MAX_PAIRS = 40_000     # G24's stated exclusion: a rule whose body matches more
                       # than this is EXCLUDED, not truncated, because a
                       # confidence measured on an arbitrary iteration-order
                       # subset is not a confidence. The first run of this spike
                       # scored the top rules by raw support -- 1.16M candidate
                       # pairs, conf 0.0000 -- i.e. exactly the rules G24 had
                       # already ruled unscoreable. Same band or the comparison
                       # is not about the same objects.
TOP_N = 30           # rules scored, by support
K = 50               # shuffles per rule for the sampled nulls
SEED = 0xC0FFEE


def degrees(triples):
    """(pred -> out-degree map), (pred -> in-degree map), (pred -> edge count)."""
    dout = defaultdict(lambda: defaultdict(int))
    din = defaultdict(lambda: defaultdict(int))
    m = defaultdict(int)
    for p, s, o in triples:
        if s == o:
            continue
        dout[p][s] += 1
        din[p][o] += 1
        m[p] += 1
    return dout, din, m


def closed_form(cand, r, dout, din, m):
    """Expected confidence under degree-preserving pairing randomisation.

    P(at least one r-edge on (a,c)) = 1 - exp(-lambda) with lambda the expected
    count; the linear approximation lambda is used where lambda is small, and the
    exponential form keeps it a probability when it is not. Both are reported so
    the approximation cannot hide inside the number.
    """
    if not m.get(r):
        return 0.0, 0.0
    lin = exp = 0.0
    for a, c in cand:
        lam = dout[r].get(a, 0) * din[r].get(c, 0) / m[r]
        lin += min(1.0, lam)
        exp += 1.0 - math.exp(-lam)
    return lin / len(cand), exp / len(cand)


def conf_of(cand_set, r_pairs):
    """Only predicate r's edge set matters, so intersect two sets instead of
    rebuilding a 190k-entry pair index per shuffle. The first version did the
    latter: 50 rebuilds per rule, 4 rules in 13 minutes."""
    return len(cand_set & r_pairs) / len(cand_set)


def shuffle_pairs(edges, rng):
    """Degree-preserving pairing randomisation of ONE predicate: permute the
    objects, keep every subject slot. Same null `redo.shuffled` applies per
    predicate, isolated to r."""
    objs = [o for _, o in edges]
    rng.shuffle(objs)
    return {(s, objs[i]) for i, (s, _) in enumerate(edges)}


def body_pairs_from(out_adj, p, q, cap):
    """Endpoint pairs of body (p,q) over an arbitrary adjacency -- needed because
    the whole-graph null moves the body as well as the head."""
    out = set()
    for a, edges in out_adj.items():
        for pp, b in edges:
            if pp != p or b == a:
                continue
            for qq, c in out_adj.get(b, ()):
                if qq == q and c != a and c != b:
                    out.add((a, c))
                    if len(out) > cap:
                        return None
    return out


def adj_of(triples):
    adj = defaultdict(list)
    for p, s, o in triples:
        if s != o:
            adj[s].append((p, o))
    return adj


def pairs_of(triples):
    pair = defaultdict(set)
    for p, s, o in triples:
        if s != o:
            pair[(s, o)].add(p)
    return pair


def main():
    nt, npred, nent, tri = R.load()
    idx = list(range(nt))
    random.Random(SEED).shuffle(idx)
    train = [tri[i] for i in idx[:int(nt * 0.70)]]
    print(f"corpus {nt} triples, train {len(train)}, preds {npred}", flush=True)

    body, head = R.mine_pairs(train)
    dout, din, m = degrees(train)
    by_pred = defaultdict(list)
    for p, s, o in train:
        if s != o:
            by_pred[p].append((s, o))
    r_pairs_of = {p: set(v) for p, v in by_pred.items()}
    adj = adj_of(train)

    cands = []
    for (p, q, r), _hp in head.items():
        if r == p or r == q:
            continue
        bp = body[(p, q)]
        if not MIN_PAIRS <= len(bp) <= MAX_PAIRS:
            continue
        cands.append(((p, q, r), set(bp)))
    # TWO STRATA. Top-by-support rules turn out to have conf ~0.0002, so both
    # baselines sit at ~0.0000 and "the closed form agrees with the shuffle mean"
    # would pass without either estimator having any dynamic range -- a control
    # that cannot fail. The by-confidence stratum is where the two baselines can
    # actually disagree, and the max baseline value per stratum is reported so a
    # vacuous pass is visible rather than inferred.
    with_conf = [((p, q, r), cand, conf_of(cand, r_pairs_of[r]))
                 for (p, q, r), cand in cands]
    by_support = sorted(with_conf, key=lambda x: -len(x[1]))[:TOP_N]
    by_conf = sorted(with_conf, key=lambda x: -x[2])[:TOP_N]
    seen, cands = set(), []
    for (key, cand, cf), stratum in ([(x, "support") for x in by_support]
                                     + [(x, "conf") for x in by_conf]):
        if key in seen:
            continue
        seen.add(key)
        cands.append((key, cand, stratum))
    print(f"{len(cands)} rules: {len(by_support)} by support + {len(by_conf)} by "
          f"confidence within [{MIN_PAIRS}, {MAX_PAIRS}], "
          f"{len(by_support) + len(by_conf) - len(cands)} overlapping\n",
          flush=True)

    cache = os.path.join(HERE, "isurp_rows.json")
    if os.path.exists(cache):
        rows = json.load(open(cache))
        print(f"loaded {len(rows)} scored rows from cache", flush=True)
        cands_iter = []
    else:
        rows, cands_iter = [], cands
    for (p, q, r), cand, stratum in cands_iter:
        cl = sorted(cand)
        conf = conf_of(cand, r_pairs_of[r])
        c_lin, c_exp = closed_form(cl, r, dout, din, m)
        rng = random.Random(4242)
        hs = [conf_of(cand, shuffle_pairs(by_pred[r], rng)) for _ in range(K)]
        e_head = sum(hs) / len(hs)
        sd = (sum((x - e_head) ** 2 for x in hs) / (len(hs) - 1)) ** 0.5
        # whole-graph null: the G-series one. Body is RE-WALKED on the shuffled
        # graph, so the candidate set moves too -- that is the difference being
        # measured, not an implementation detail.
        rng2 = random.Random(4242)
        ws = []
        for _ in range(K):
            sh = R.shuffled(train, rng2.randrange(1 << 30))
            a2 = adj_of(sh)
            bp2 = body_pairs_from(a2, p, q, MAX_PAIRS * 4)
            if not bp2:
                continue
            rp2 = {(s, o) for pp, s, o in sh if pp == r and s != o}
            ws.append(len(bp2 & rp2) / len(bp2))
        e_whole = sum(ws) / len(ws) if ws else float("nan")
        rows.append({"rule": [p, q, r], "stratum": stratum,
                     "n_cand": len(cand), "conf": conf,
                     "closed_lin": c_lin, "closed_exp": c_exp,
                     "head_shuffle_mean": e_head, "head_shuffle_sd": sd,
                     "whole_shuffle_mean": e_whole, "n_whole": len(ws),
                     "excess_closed": conf - c_exp,
                     "excess_head": conf - e_head,
                     "excess_whole": conf - e_whole})
        print(f"  [{stratum:<7}] ({p:>3},{q:>3})=>{r:<4} n {len(cand):>6}  conf {conf:.4f}  "
              f"closed {c_exp:.4f}  head-shuf {e_head:.4f}+-{sd:.4f}  "
              f"whole-shuf {e_whole:.4f}", flush=True)

    json.dump(rows, open(cache, "w"), indent=1)
    for st in ("support", "conf"):
        sr = [x for x in rows if x["stratum"] == st]
        if sr:
            md = max(abs(x["closed_exp"] - x["head_shuffle_mean"]) for x in sr)
            print(f"  stratum {st:<8} n={len(sr):<3} conf up to "
                  f"{max(x['conf'] for x in sr):.4f}, baseline up to "
                  f"{max(x['closed_exp'] for x in sr):.4f}  -> worst "
                  f"|closed-shuffle| {md:.5f}"
                  + ("   (RANGE TOO SMALL TO TEST ANYTHING)"
                     if max(x['closed_exp'] for x in sr) < 1e-4 else ""))
    diffs = [abs(x["closed_exp"] - x["head_shuffle_mean"]) for x in rows]
    wdiffs = [abs(x["head_shuffle_mean"] - x["whole_shuffle_mean"])
              for x in rows if x["whole_shuffle_mean"] == x["whole_shuffle_mean"]]
    within = sum(1 for x in rows
                 if abs(x["closed_exp"] - x["head_shuffle_mean"])
                 <= 2 * (x["head_shuffle_sd"] / K ** 0.5 + 1e-9))
    print(f"\nC3 AGREEMENT closed vs head-shuffle: max {max(diffs):.5f}, mean "
          f"{sum(diffs) / len(diffs):.5f}; {within}/{len(rows)} within 2 SE")
    if wdiffs:
        print(f"C4 head-shuffle vs WHOLE-graph shuffle: max {max(wdiffs):.5f}, "
              f"mean {sum(wdiffs) / len(wdiffs):.5f}")

    ents = sorted({e for _, s, o in train for e in (s, o)})
    bp_key, bp_cand, _st = cands[0]   # largest-support rule's pair set
    r_ind, r_dep = npred + 101, npred + 102
    rng = random.Random(77)
    ind = [(r_ind, rng.choice(ents), rng.choice(ents)) for _ in range(len(bp_cand))]
    dep = [(r_dep, a_, c_) for a_, c_ in bp_cand]
    ctrl = {}
    for name, r_, extra in (("C1_independent", r_ind, ind),
                            ("C2_dependent", r_dep, dep)):
        t2 = train + extra
        d2o, d2i, m2 = degrees(t2)
        ed2 = [(s, o) for _p, s, o in extra if s != o]
        rp2 = set(ed2)
        conf2 = conf_of(bp_cand, rp2)
        _l, c2 = closed_form(sorted(bp_cand), r_, d2o, d2i, m2)
        rng2 = random.Random(99)
        hs2 = [conf_of(bp_cand, shuffle_pairs(ed2, rng2)) for _ in range(K)]
        s2 = sum(hs2) / len(hs2)
        ctrl[name] = {"conf": conf2, "closed": c2, "head_shuffle": s2,
                      "excess_closed": conf2 - c2, "excess_head": conf2 - s2,
                      "n_cand": len(bp_cand), "n_edges": len(ed2)}
        print(f"{name}: conf {conf2:.4f}  closed {c2:.4f}  head-shuf {s2:.4f}  "
              f"excess_closed {conf2 - c2:+.4f}  excess_head {conf2 - s2:+.4f}")

    c1_ok = (abs(ctrl["C1_independent"]["excess_closed"]) < 0.02
             and abs(ctrl["C1_independent"]["excess_head"]) < 0.02)
    c2_ok = (ctrl["C2_dependent"]["excess_closed"] > 0.5
             and ctrl["C2_dependent"]["excess_head"] > 0.5)
    c3_ok = max(diffs) < 0.01

    v = [f"C1 {'PASS' if c1_ok else 'FAIL'}: randomly-placed head scores excess "
         f"{ctrl['C1_independent']['excess_closed']:+.4f} closed / "
         f"{ctrl['C1_independent']['excess_head']:+.4f} sampled",
         f"C2 {'PASS' if c2_ok else 'FAIL'}: head planted on the body's own pairs "
         f"scores excess {ctrl['C2_dependent']['excess_closed']:+.4f} closed / "
         f"{ctrl['C2_dependent']['excess_head']:+.4f} sampled",
         f"C3 {'PASS' if c3_ok else 'FAIL'}: closed form matches the {K}-shuffle "
         f"mean to {max(diffs):.5f} worst case over {len(rows)} rules"]
    if wdiffs:
        v.append(f"C4 MEASURED: the whole-graph null differs from the head-only "
                 f"null by up to {max(wdiffs):.5f} (mean "
                 f"{sum(wdiffs) / len(wdiffs):.5f}) -- it randomises the body as "
                 f"well, so it is not the same question")
    if c1_ok and c2_ok and c3_ok:
        v.append(f"VERDICT: THE SAMPLING IS REPLACEABLE for the degree-preserving "
                 f"null. Closed form matches the sampled mean to {max(diffs):.5f}, "
                 f"costs one pass instead of {K}, and has NO p-floor -- the 1/501 "
                 f"floor was an artefact of estimating analytically-available "
                 f"marginals by sampling. hyperon-miner's design validated "
                 f"against ours, not adopted on authority.")
    else:
        v.append("VERDICT: NOT ESTABLISHED - a control failed, so the closed form "
                 "does not stand in for the sampled null on this corpus.")
    print("\n" + "\n".join(v))

    controls = []
    c = P.Control("C1_independent_head",
                  "a baseline that reports structure for a randomly placed head "
                  "makes every excess it has ever scored suspect",
                  null_must_contain="a nonzero excess for a head placed at random "
                  "over the same entities with matched edge count",
                  can_fail_because="placement is rng.choice over real entities, so "
                  "degree-correlated placement could produce a spurious excess")
    c.observe(c1_ok, ctrl["C1_independent"])
    controls.append(c)
    c = P.Control("C2_dependent_head",
                  "a null that explains away a dependence planted by construction "
                  "cannot exclude chance structure (A20)",
                  null_must_contain="a near-zero excess for a head planted exactly "
                  "on the body's endpoint pairs",
                  can_fail_because="the planted head raises r's degrees on exactly "
                  "those endpoints, so a degree-preserving baseline could absorb "
                  "the entire effect -- that is the failure mode under test")
    c.observe(c2_ok, ctrl["C2_dependent"])
    controls.append(c)
    c = P.Control("C3_closed_form_agreement",
                  "the closed form replaces the sampled null only if it "
                  "reproduces it",
                  null_must_contain="a disagreement larger than sampling error",
                  can_fail_because="the closed form treats candidate pairs as "
                  "independent and ignores the permutation's exchange constraint; "
                  "if that matters the two diverge here")
    c.observe(c3_ok, {"max_abs_diff": max(diffs),
                      "mean_abs_diff": sum(diffs) / len(diffs),
                      "within_2se": within, "n_rules": len(rows), "K": K,
                      "head_vs_whole_max": max(wdiffs) if wdiffs else None})
    controls.append(c)

    json.dump({"rows": rows, "controls_summary": ctrl, "verdict": v,
               "conditions": {"data": "real:FB15k-237", "train_frac": 0.70,
                              "split_seed": "0xC0FFEE", "K": K, "top_n": TOP_N,
                              "min_pairs": MIN_PAIRS, "max_pairs": MAX_PAIRS,
                              "platforms": [["macos", "aarch64"]]},
               "cites": ["elders/hyperon-miner isurp.metta",
                         "G17_composition_redo", "G21_null_rust", "G23_depth"]},
              open(os.path.join(HERE, "isurp.json"), "w"), indent=1)
    ok, _ = P.record(HERE, deps=[os.path.join(HERE, "..", "G17_composition_redo")],
                     artifacts=[os.path.join(HERE, "isurp.py"),
                                os.path.join(HERE, "isurp.json")],
                     controls=controls, allow_dirty=True,
                     note="G32: closed-form degree-preserving baseline vs the "
                          "shuffle null, after reading hyperon-miner's isurp")
    print(f"provenance ok={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
