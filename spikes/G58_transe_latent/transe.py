#!/usr/bin/env python3
"""G58 — TransE on the same leak-free split, same candidate set as G51.

Setup enhancement, not a literature bake-off. Toutanova & Chen (MSR 2015)
compared observed features to latent embeddings after stripping inverses.
We have the observed side (prior / G51 / G54 gate) and no latent arm.

Protocol:
  * pair-disjoint split (G48), field order (p,s,o).
  * Rank TransE only on the predicate's train support — the same set
    G51.rank_from_scores sees. Full-entity ranking is a different
    candidate set (A18) and is not the headline.
  * Official test is detected, not fetched. literature_compare=unavailable.

F1: TransE_support >= G54 gated 0.2313 + 0.005 → latent wins here.
F2: TransE_support < prior 0.1732 → arm is broken/undertrained.

  python3 spikes/G58_transe_latent/transe.py
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))

import bayesian_lift as G51  # noqa: E402
import kg_split  # noqa: E402
import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

SEED = G51.SEED
DIM = 32
EPOCHS = 8
LR = 0.05
MARGIN = 1.0
G54_GATED = 0.2313


def zeros(n):
    return [0.0] * n


def rand_vec(rng, n, scale=0.01):
    return [rng.uniform(-scale, scale) for _ in range(n)]


def l2(v):
    return math.sqrt(sum(x * x for x in v)) or 1.0


def normed(v):
    n = l2(v)
    return [x / n for x in v]


def dist2(s, r, o):
    # ||s + r - o||^2
    acc = 0.0
    for i in range(len(s)):
        d = s[i] + r[i] - o[i]
        acc += d * d
    return acc


def train_transe(train, nent, npred, rng):
    E = [normed(rand_vec(rng, DIM)) for _ in range(nent)]
    R = [normed(rand_vec(rng, DIM)) for _ in range(npred)]
    triples = list(train)
    n_up = 0
    for ep in range(EPOCHS):
        rng.shuffle(triples)
        hits = 0
        for p, s, o in triples:
            if rng.random() < 0.5:
                sc, oc = rng.randrange(nent), o
                while sc == s:
                    sc = rng.randrange(nent)
            else:
                sc, oc = s, rng.randrange(nent)
                while oc == o:
                    oc = rng.randrange(nent)
            dpos = dist2(E[s], R[p], E[o])
            dneg = dist2(E[sc], R[p], E[oc])
            if MARGIN + dpos - dneg <= 0:
                continue
            hits += 1
            g = [2.0 * (E[s][i] + R[p][i] - E[o][i]) for i in range(DIM)]
            gn = [2.0 * (E[sc][i] + R[p][i] - E[oc][i]) for i in range(DIM)]
            for i in range(DIM):
                E[s][i] -= LR * g[i]
                R[p][i] -= LR * g[i]
                E[o][i] += LR * g[i]
                E[sc][i] += LR * gn[i]
                E[oc][i] -= LR * gn[i]
            E[s] = normed(E[s])
            E[o] = normed(E[o])
            E[sc] = normed(E[sc])
            E[oc] = normed(E[oc])
            R[p] = normed(R[p])
        n_up += hits
        print(f"  epoch {ep+1}/{EPOCHS} hinge_fires={hits}/{len(triples)}", flush=True)
    return E, R, n_up


def score_support(test, E, R, obj_freq, sub_freq, true_sp, true_po, nent):
    """Rank TransE on the same support G51 uses (train objects/subjects of p)."""
    ranks = []
    for p, s, o in test:
        # tail
        support = obj_freq[p]
        scores = {}
        rv = R[p]
        sv = E[s]
        for cand in support:
            scores[cand] = -dist2(sv, rv, E[cand])
        ranks.append(G51.rank_from_scores(scores, o, true_sp.get((s, p), set()), nent))
        # head
        support = sub_freq[p]
        scores = {}
        ov = E[o]
        for cand in support:
            # ||cand + r - o|| ; query is (?, p, o)
            scores[cand] = -dist2(E[cand], rv, ov)
        ranks.append(G51.rank_from_scores(scores, s, true_po.get((p, o), set()), nent))
    return ranks


def metrics(ranks):
    n = len(ranks)
    rr = h1 = h3 = h10 = 0.0
    for r in ranks:
        rr += 1.0 / r
        h1 += r <= 1.0
        h3 += r <= 3.0
        h10 += r <= 10.0
    return {
        "mrr": round(rr / n, 4),
        "hits1": round(h1 / n, 4),
        "hits3": round(h3 / n, 4),
        "hits10": round(h10 / n, 4),
        "n_queries": n,
    }


def main():
    t0 = time.time()
    official = kg_split.official_test_status()
    print("official_test", official, flush=True)
    nt, npred, nent, tri = G51.load_raw_triples()
    order_ok, order_obs = kg_split.field_order_ok(tri, npred, nent)
    rng = random.Random(SEED)
    train, dev, test, n_groups = G51.pair_disjoint_split(tri, SEED)
    leak = G51.count_same_pair_leak(train, test)
    print(
        f"nt={nt} npred={npred} nent={nent} order_ok={order_ok} "
        f"train={len(train)} test={len(test)} leak={leak}",
        flush=True,
    )
    obj_freq = defaultdict(dict)
    sub_freq = defaultdict(dict)
    for p, s, o in train:
        obj_freq[p][o] = obj_freq[p].get(o, 0) + 1
        sub_freq[p][s] = sub_freq[p].get(s, 0) + 1
    true_sp, true_po = G51.build_filter_index(tri)

    print("training TransE ...", flush=True)
    t_tr = time.time()
    E, R, n_up = train_transe(train, nent, npred, rng)
    print(f"trained in {time.time() - t_tr:.1f}s hinge_updates={n_up}", flush=True)

    print("ranking on prior support ...", flush=True)
    t_sc = time.time()
    ranks = score_support(test, E, R, obj_freq, sub_freq, true_sp, true_po, nent)
    arm = metrics(ranks)
    print(f"scored {len(ranks)} in {time.time() - t_sc:.1f}s MRR={arm['mrr']}", flush=True)

    # prior on the same support, same rank function
    prior_ranks = []
    for p, s, o in test:
        prior_ranks.append(
            G51.rank_from_scores(
                {c: float(n) for c, n in obj_freq[p].items()},
                o, true_sp.get((s, p), set()), nent,
            )
        )
        prior_ranks.append(
            G51.rank_from_scores(
                {c: float(n) for c, n in sub_freq[p].items()},
                s, true_po.get((p, o), set()), nent,
            )
        )
    prior_arm = metrics(prior_ranks)

    vs_gated = round(arm["mrr"] - G54_GATED, 4)
    vs_prior = round(arm["mrr"] - prior_arm["mrr"], 4)
    f1_fired = vs_gated >= 0.005
    f2_fired = arm["mrr"] < 0.1732

    c1_ok = abs(prior_arm["mrr"] - 0.1732) <= 0.0005
    c3_ok = leak == 0
    c4_ok = order_ok
    c5_ok = official["official_test_available"] is False

    res = {
        "spike": "G58",
        "seed": f"0x{SEED:X}",
        "split": "pair_disjoint (0 leak by construction)",
        "field_order": "p,s,o",
        "headline_arm": "B_transe_on_prior_support",
        "headline_is_test_grid": False,
        "candidate_set": "train_support_of_p (same as G51)",
        "not_full_entity_ranking": True,
        "official_test": official,
        "literature_compare": "unavailable",
        "literature_note": "do not quote Bordes/RotatE MRR against this split",
        "dim": DIM,
        "epochs": EPOCHS,
        "lr": LR,
        "margin": MARGIN,
        "n_train": len(train),
        "n_dev_unused": len(dev),
        "n_test": len(test),
        "n_groups": n_groups,
        "hinge_updates": n_up,
        "g54_gated_mrr_reference": G54_GATED,
        "arms": {
            "A_prior_support": prior_arm,
            "B_transe_on_prior_support": arm,
        },
        "transe_minus_gated": vs_gated,
        "transe_minus_prior": vs_prior,
        "field_order_obs": order_obs,
        "controls": {
            "C1_prior": {"ok": c1_ok, "mrr": prior_arm["mrr"]},
            "C3_leak": {"ok": c3_ok, "leak": leak},
            "C4_field_order": {"ok": c4_ok, **order_obs},
            "C5_official_test_absent": {
                "ok": c5_ok,
                **official,
            },
        },
        "falsifiers": {
            "F1_latent_beats_gated": {
                "transe_mrr": arm["mrr"],
                "gated_ref": G54_GATED,
                "delta": vs_gated,
                "bar": 0.005,
                "fired": f1_fired,
                "description": "Fires if TransE_support beats G54 gated by >=+0.005",
            },
            "F2_transe_below_prior": {
                "transe_mrr": arm["mrr"],
                "prior_mrr": prior_arm["mrr"],
                "fired": f2_fired,
                "description": "Fires if TransE_support < 0.1732 (broken/undertrained)",
            },
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }
    out = os.path.join(HERE, "transe.json")
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G58 ===", flush=True)
    print(f"  prior   MRR={prior_arm['mrr']:.4f}", flush=True)
    print(f"  transe  MRR={arm['mrr']:.4f} vs gated {vs_gated:+.4f} vs prior {vs_prior:+.4f}", flush=True)
    print(f"F1 fired={f1_fired} F2 fired={f2_fired}", flush=True)
    print(f"official_test_available={official['official_test_available']}", flush=True)

    controls = [
        Control("C1_prior", why="same-support prior reproduces 0.1732",
                can_fail_because="split or rank drifted",
                null_must_contain="unexpected prior"),
        Control("C3_leak", why="leak 0", can_fail_because="partition broken",
                null_must_contain="leak>0"),
        Control("C4_field_order", why="(p,s,o)", can_fail_because="G52 swap",
                null_must_contain="max_p>=npred"),
        Control("C5_official_test_absent", why="setup must see that official test is missing",
                can_fail_because="a test.txt appeared or detector always-true",
                null_must_contain="official_test_available true"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_prior"])
    controls[1].observe(c3_ok, res["controls"]["C3_leak"])
    controls[2].observe(c4_ok, res["controls"]["C4_field_order"])
    controls[3].observe(c5_ok, res["controls"]["C5_official_test_absent"])

    falsifiers = [
        Falsifier(
            "F1_latent_beats_gated",
            refutes="that observed+DEV-gate is the better class on this split",
            fires_when="transe_support - 0.2313 >= 0.005",
            null_must_contain="a signed delta vs 0.2313",
        ),
        Falsifier(
            "F2_transe_below_prior",
            refutes="that the latent arm is a working TransE",
            fires_when="transe_support < 0.1732",
            null_must_contain="an MRR on either side of the prior",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_latent_beats_gated"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_transe_below_prior"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G51.DEP_DIR, os.path.join(SPIKES, "G51_bayesian_lift_scoring")],
        artifacts=[os.path.join(HERE, "transe.py"), out],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("transe_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "TransE on prior support beats G54 gated by +0.005, "
            "OR TransE scores below the frequency prior"
        ),
        allow_dirty=True,
        note="G58: TransE latent arm on pair-disjoint split, same candidate set as G51. Official test not fetched.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
