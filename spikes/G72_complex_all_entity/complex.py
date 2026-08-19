#!/usr/bin/env python3
"""G72 — ComplEx, filtered ALL-ENTITY ranking, official FB15k-237.

Score: Re(<h, r, conjugate(t)>). Higher better.
Train on official TRAIN only. Valid used only after epoch 10 for patience
(not γ/β, A26). Do not early-stop before epoch 10. Best checkpoint is the
best valid MRR among epochs ≥ 10.

G51/prior scored with support of p (and rule firings) and −∞ elsewhere —
same rank_from_scores as G59 — so the comparison is not A18.

Do not quote Bordes/RotatE/AMIE (G35). literature_compare=unavailable.

F1: ComplEx all-entity MRR does not beat G51 (support−∞) by >= +0.005.
    fires_when complex - g51 < 0.005
F2: ComplEx MRR < 0.2334 (official prior) → broken/undertrained.
    fires_when complex < 0.2334

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G72_complex_all_entity/complex.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)


def _numpy_pythons():
    out = [os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")]
    parent = os.path.dirname(ROOT)
    try:
        names = os.listdir(parent)
    except OSError:
        names = []
    for name in names:
        out.append(os.path.join(
            parent, name, "spikes", "S5_hdc_prototype", ".venv", "bin", "python"))
    return out


def _reexec_with_numpy():
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    here = os.path.abspath(sys.executable)
    for py in _numpy_pythons():
        if os.path.isfile(py) and os.path.abspath(py) != here:
            os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:])
    sys.stderr.write("numpy required (S5 venv missing)\n")
    sys.exit(2)


_reexec_with_numpy()

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
RULES_CACHE = os.path.join(HERE, "rules_cache.json")
G66_RULES = os.path.join(SPIKES, "G66_all_entity_distmult", "rules_cache.json")

# Pre-registered. Not searched on test (A26). Valid only for selection after 10.
SEED = 72
DIM = 64
MAX_EPOCHS = 40
MIN_EPOCH = 10
PATIENCE = 8
LR = 0.1
BATCH = 1024
REG = 1e-5
VALID_SAMPLE = 2500
OFFICIAL_PRIOR = 0.2334
G51_BAR = 0.005
NENT_OFFICIAL = 14541
NPRED_OFFICIAL = 237
TEST_N = 20466


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics(ranks):
    n = len(ranks)
    if n == 0:
        return {"mrr": 0.0, "hits1": 0.0, "hits3": 0.0, "hits10": 0.0, "n_queries": 0}
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


def slice_metrics(ranks, directions):
    out = {}
    for d in ("tail", "head"):
        out[d] = metrics([r for r, dir_ in zip(ranks, directions) if dir_ == d])
    return out


def build_true_lists(triples):
    sp, po = defaultdict(list), defaultdict(list)
    for p, s, o in triples:
        sp[(int(s), int(p))].append(int(o))
        po[(int(p), int(o))].append(int(s))
    sp_a = {k: np.asarray(v, dtype=np.int32) for k, v in sp.items()}
    po_a = {k: np.asarray(v, dtype=np.int32) for k, v in po.items()}
    return sp_a, po_a


def softmax_grad(scores, target):
    """1-N softmax NLL. scores (B, nent), target (B,)."""
    bsz = scores.shape[0]
    m = np.max(scores, axis=1, keepdims=True)
    exp = np.exp(scores - m)
    z = exp.sum(axis=1, keepdims=True)
    prob = exp / np.maximum(z, 1e-12)
    nll = -np.log(np.maximum(prob[np.arange(bsz), target], 1e-12)).mean()
    g = prob / bsz
    g[np.arange(bsz), target] -= 1.0 / bsz
    return g, float(nll)


def adagrad_step(param, acc, grad, lr):
    acc += grad * grad
    param -= lr * grad / (np.sqrt(acc) + 1e-10)


def complex_tail_scores(E_re, E_im, R_re, R_im, s, p):
    """All-entity tail scores: Re(<h, r, conj(t)>) for every t."""
    h_re, h_im = E_re[s], E_im[s]
    r_re, r_im = R_re[p], R_im[p]
    inner_re = h_re * r_re - h_im * r_im
    inner_im = h_re * r_im + h_im * r_re
    return inner_re @ E_re.T + inner_im @ E_im.T, inner_re, inner_im, h_re, h_im, r_re, r_im


def complex_head_scores(E_re, E_im, R_re, R_im, o, p):
    """All-entity head scores: Re(<h, r, conj(t)>) for every h."""
    t_re, t_im = E_re[o], E_im[o]
    r_re, r_im = R_re[p], R_im[p]
    rhs_re = r_re * t_re + r_im * t_im
    rhs_im = r_re * t_im - r_im * t_re
    return rhs_re @ E_re.T + rhs_im @ E_im.T, rhs_re, rhs_im, t_re, t_im, r_re, r_im


def _assert_score_identity():
    """Re(<h,r,conj(t)>) vs the factored all-entity form, one triple."""
    rng = np.random.default_rng(0)
    d = 8
    h_re, h_im = rng.normal(size=d), rng.normal(size=d)
    r_re, r_im = rng.normal(size=d), rng.normal(size=d)
    t_re, t_im = rng.normal(size=d), rng.normal(size=d)
    direct = float(np.sum(
        h_re * r_re * t_re - h_im * r_im * t_re
        + h_re * r_im * t_im + h_im * r_re * t_im
    ))
    E_re = np.stack([t_re, h_re])
    E_im = np.stack([t_im, h_im])
    R_re = r_re[None, :]
    R_im = r_im[None, :]
    sc_t, *_ = complex_tail_scores(E_re, E_im, R_re, R_im, np.array([1]), np.array([0]))
    sc_h, *_ = complex_head_scores(E_re, E_im, R_re, R_im, np.array([0]), np.array([0]))
    if abs(float(sc_t[0, 0]) - direct) > 1e-5 or abs(float(sc_h[0, 1]) - direct) > 1e-5:
        raise RuntimeError(
            f"ComplEx score identity failed: direct={direct} "
            f"tail={sc_t[0, 0]} head={sc_h[0, 1]}"
        )


def train_complex(train, nent, npred, rng, valid_q=None, eval_sp=None, eval_po=None):
    """Unfiltered 1-N ComplEx. Selection only among epochs >= MIN_EPOCH."""
    scale = 1.0 / np.sqrt(DIM)
    E_re = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    E_im = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    R_re = rng.uniform(-scale, scale, size=(npred, DIM)).astype(np.float32)
    R_im = rng.uniform(-scale, scale, size=(npred, DIM)).astype(np.float32)
    acc = [np.zeros_like(x) for x in (E_re, E_im, R_re, R_im)]
    tri = np.asarray(train, dtype=np.int32)
    n = len(tri)
    hist = []
    pack = lambda: (E_re.copy(), E_im.copy(), R_re.copy(), R_im.copy())
    best = {"mrr": -1.0, "epoch": None, "emb": None}
    stale = 0

    for ep in range(1, MAX_EPOCHS + 1):
        t0 = time.time()
        perm = rng.permutation(n)
        loss_acc = 0.0
        n_batches = 0
        for start in range(0, n, BATCH):
            batch = tri[perm[start:start + BATCH]]
            p, s, o = batch[:, 0], batch[:, 1], batch[:, 2]

            sc_t, ire, iim, h_re, h_im, r_re, r_im = complex_tail_scores(
                E_re, E_im, R_re, R_im, s, p)
            g_t, nll_t = softmax_grad(sc_t, o)
            g_ire = g_t @ E_re
            g_iim = g_t @ E_im
            gE_re = g_t.T @ ire
            gE_im = g_t.T @ iim
            gR_re = np.zeros_like(R_re)
            gR_im = np.zeros_like(R_im)
            np.add.at(gE_re, s, g_ire * r_re + g_iim * r_im)
            np.add.at(gE_im, s, -g_ire * r_im + g_iim * r_re)
            np.add.at(gR_re, p, g_ire * h_re + g_iim * h_im)
            np.add.at(gR_im, p, -g_ire * h_im + g_iim * h_re)

            sc_h, rre, rim, t_re, t_im, r_re, r_im = complex_head_scores(
                E_re, E_im, R_re, R_im, o, p)
            g_h, nll_h = softmax_grad(sc_h, s)
            g_rre = g_h @ E_re
            g_rim = g_h @ E_im
            gE_re += g_h.T @ rre
            gE_im += g_h.T @ rim
            np.add.at(gE_re, o, g_rre * r_re + g_rim * r_im)
            np.add.at(gE_im, o, g_rre * r_im - g_rim * r_re)
            np.add.at(gR_re, p, g_rre * t_re + g_rim * t_im)
            np.add.at(gR_im, p, g_rre * t_im - g_rim * t_re)

            if REG:
                gE_re += REG * E_re
                gE_im += REG * E_im
                gR_re += REG * R_re
                gR_im += REG * R_im
            adagrad_step(E_re, acc[0], gE_re, LR)
            adagrad_step(E_im, acc[1], gE_im, LR)
            adagrad_step(R_re, acc[2], gR_re, LR)
            adagrad_step(R_im, acc[3], gR_im, LR)
            loss_acc += nll_t + nll_h
            n_batches += 1
            if ep == 1 and n_batches == 1:
                print(
                    f"  first-batch nll={nll_t + nll_h:.4f} "
                    f"(uniform~{2.0 * np.log(nent):.4f}) ||E||={np.linalg.norm(E_re):.3f}",
                    flush=True,
                )

        row = {
            "epoch": ep,
            "nll": round(loss_acc / max(1, n_batches), 4),
            "sec": round(time.time() - t0, 2),
            "eligible": ep >= MIN_EPOCH,
        }
        # History on valid before 10 is recorded; it cannot win (G66 epoch-1 trap).
        do_valid = valid_q is not None and (
            ep >= MIN_EPOCH or ep == 1 or ep == 5 or ep == MAX_EPOCHS)
        if do_valid:
            vr, _, _ = rank_complex(valid_q, E_re, E_im, R_re, R_im, eval_sp, eval_po)
            vm = metrics(vr)
            row["valid_sample_mrr"] = vm["mrr"]
            if ep >= MIN_EPOCH and vm["mrr"] > best["mrr"]:
                best = {"mrr": vm["mrr"], "epoch": ep, "emb": pack()}
                row["best"] = True
                stale = 0
            elif ep >= MIN_EPOCH:
                stale += 1
                row["stale"] = stale
        hist.append(row)
        extra = f" valid_mrr={row['valid_sample_mrr']:.4f}" if "valid_sample_mrr" in row else ""
        extra += " BEST" if row.get("best") else ""
        print(
            f"  epoch {ep}/{MAX_EPOCHS} nll={row['nll']:.4f} {row['sec']:.1f}s"
            f"{extra} eligible={row['eligible']}",
            flush=True,
        )
        if ep >= MIN_EPOCH and stale >= PATIENCE:
            print(
                f"  patience {PATIENCE} after best_epoch={best['epoch']} "
                f"(min_epoch={MIN_EPOCH}); stop",
                flush=True,
            )
            break

    if best["emb"] is None:
        best = {"mrr": None, "epoch": max(MIN_EPOCH, ep), "emb": pack()}
    return best["emb"], hist, best["epoch"], best["mrr"]


def _rank_from_scores(sc, targets, chunk, true_map, key_fn, keep_fn, direction, ranks, directions):
    p = [t[0] for t in chunk]
    s = [t[1] for t in chunk]
    o = [t[2] for t in chunk]
    for i, (pi, si, oi) in enumerate(zip(p, s, o)):
        filt = true_map.get(key_fn(pi, si, oi))
        keep = keep_fn(si, oi)
        if filt is not None:
            mask = filt[filt != keep]
            if len(mask):
                sc[i, mask] = -np.inf
    tgt = sc[np.arange(len(chunk)), targets]
    higher = np.sum(sc > tgt[:, None], axis=1)
    equal = np.sum(sc == tgt[:, None], axis=1) - 1
    for h, e in zip(higher.tolist(), equal.tolist()):
        ranks.append(1.0 + h + 0.5 * e)
        directions.append(direction)


def rank_complex(queries, E_re, E_im, R_re, R_im, true_sp, true_po, batch=256):
    ranks, directions = [], []
    nent = E_re.shape[0]
    q = list(queries)
    for start in range(0, len(q), batch):
        chunk = q[start:start + batch]
        p = np.array([t[0] for t in chunk], dtype=np.int32)
        s = np.array([t[1] for t in chunk], dtype=np.int32)
        o = np.array([t[2] for t in chunk], dtype=np.int32)
        sc_t, *_ = complex_tail_scores(E_re, E_im, R_re, R_im, s, p)
        _rank_from_scores(
            sc_t, o, chunk, true_sp,
            lambda pi, si, oi: (si, pi), lambda si, oi: oi,
            "tail", ranks, directions,
        )
        sc_h, *_ = complex_head_scores(E_re, E_im, R_re, R_im, o, p)
        _rank_from_scores(
            sc_h, s, chunk, true_po,
            lambda pi, si, oi: (pi, oi), lambda si, oi: si,
            "head", ranks, directions,
        )
    assert len(ranks) == 2 * len(q)
    return ranks, directions, nent


def score_support_neginf(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx):
    """G59/G51 protocol: score train support of p (and rule firings); rest −∞."""
    rows = G59.score_split(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    prior = [r["ranks"]["prior"] for r in rows]
    g51 = [r["ranks"]["g51"] for r in rows]
    dirs = [r["direction"] for r in rows]
    return prior, g51, dirs


def load_or_mine_rules(out_adj, pair_tr, byp, rev):
    for path in (RULES_CACHE, G66_RULES):
        if os.path.isfile(path):
            raw = json.loads(open(path, encoding="utf-8").read())
            if path != RULES_CACHE:
                with open(RULES_CACHE, "w", encoding="utf-8") as f:
                    json.dump(raw, f)
            print(f"loaded {len(raw)} rules from {path}", flush=True)
            return raw
    print("mining 2-hop on official train ...", flush=True)
    t0 = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    slim = [{"head": r["head"], "body": list(r["body"]), "conf": r["conf"]} for r in rules]
    with open(RULES_CACHE, "w", encoding="utf-8") as f:
        json.dump(slim, f)
    print(f"mined {len(slim)} in {time.time() - t0:.1f}s", flush=True)
    return slim


def field_order_ok(train, npred, nent):
    max_p = max(p for p, s, o in train)
    max_s = max(s for p, s, o in train)
    max_o = max(o for p, s, o in train)
    ok = max_p < npred and max_s < nent and max_o < nent
    return ok, {
        "declared_order": "p,s,o",
        "npred": npred,
        "nent": nent,
        "max_p": max_p,
        "max_s": max_s,
        "max_o": max_o,
    }


def main():
    t0 = time.time()
    _assert_score_identity()
    hashes = {name: sha256_file(os.path.join(CORPUS, name))
              for name in ("train.txt", "valid.txt", "test.txt")}
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(
        f"official n train={len(train)} valid={len(valid)} test={len(test)} "
        f"npred={npred} nent={nent}",
        flush=True,
    )
    print(f"hashes { {k: v[:12] for k, v in hashes.items()} }", flush=True)

    order_ok, order_obs = field_order_ok(train, npred, nent)
    leak = G51.count_same_pair_leak(train, test)
    print(f"field_order_ok={order_ok} leak={leak}", flush=True)

    all_tri = train + valid + test
    true_sp_set, true_po_set = G51.build_filter_index(all_tri)
    eval_sp, eval_po = build_true_lists(all_tri)

    rng = np.random.default_rng(SEED)
    valid_idx = rng.choice(len(valid), size=min(VALID_SAMPLE, len(valid)), replace=False)
    valid_sample = [valid[int(i)] for i in valid_idx]

    print(
        f"training ComplEx (unfiltered 1-N, AdaGrad, dim={DIM}, "
        f"min_epoch={MIN_EPOCH}, patience={PATIENCE} on valid) ...",
        flush=True,
    )
    t_cx = time.time()
    (E_re, E_im, R_re, R_im), hist, best_ep, best_valid = train_complex(
        train, nent, npred, rng,
        valid_q=valid_sample, eval_sp=eval_sp, eval_po=eval_po,
    )
    print(
        f"trained ComplEx in {time.time() - t_cx:.1f}s "
        f"best_valid_epoch={best_ep} best_valid_sample_mrr={best_valid}",
        flush=True,
    )
    if best_ep is None or best_ep < MIN_EPOCH:
        raise RuntimeError(
            f"selection violated min_epoch={MIN_EPOCH}: best_epoch={best_ep}"
        )

    print("ranking ComplEx ALL entities (filtered) on official TEST ...", flush=True)
    t_ev = time.time()
    cx_ranks, cx_dirs, _ = rank_complex(test, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    cx_arm = metrics(cx_ranks)
    cx_slices = slice_metrics(cx_ranks, cx_dirs)
    print(f"ComplEx MRR={cx_arm['mrr']:.4f} H@10={cx_arm['hits10']:.4f} "
          f"in {time.time() - t_ev:.1f}s", flush=True)

    print("scoring prior + G51 under support−∞ (same rank_from_scores as G59) ...", flush=True)
    t_g = time.time()
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    raw_rules = load_or_mine_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in raw_rules:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))
    idx = G59.slim_index(train)
    prior_ranks, g51_ranks, pg_dirs = score_support_neginf(
        test, nent, rules_by_head, out_adj, in_adj, true_sp_set, true_po_set, idx,
    )
    prior_arm = metrics(prior_ranks)
    g51_arm = metrics(g51_ranks)
    print(
        f"prior={prior_arm['mrr']:.4f} G51={g51_arm['mrr']:.4f} "
        f"in {time.time() - t_g:.1f}s",
        flush=True,
    )

    delta = round(cx_arm["mrr"] - g51_arm["mrr"], 4)
    f1_fired = (cx_arm["mrr"] - g51_arm["mrr"]) < G51_BAR
    f2_fired = cx_arm["mrr"] < OFFICIAL_PRIOR

    c1_ok = len(test) == TEST_N
    c2_ok = leak == 0
    c3_ok = nent == NENT_OFFICIAL
    c4_ok = order_ok and npred == NPRED_OFFICIAL
    lit = "unavailable"
    c5_ok = lit == "unavailable"

    res = {
        "spike": "G72",
        "split": "official FB15k-237 train/valid/test",
        "source_git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
        "source_commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
        "field_order": "p,s,o",
        "headline_arm": "C_complex_all_entity",
        "headline_is_test_grid": False,
        "literature_compare": lit,
        "literature_note": "do not quote Bordes/RotatE/AMIE MRR; no excerpt under corpus/",
        "candidate_set": "all 14541 entities, filtered train+valid+test",
        "protocol": "filtered_all_entity",
        "scoreboard_note": (
            "pair-disjoint G54 0.2313 and official G59 0.2679 stay; "
            "G66 DistMult 0.2195 is the other all-entity column; "
            "G72 is ComplEx on the same protocol"
        ),
        "model": "ComplEx",
        "score_fn": "Re(sum_k h_k * r_k * conj(t_k))",
        "train_objective": "unfiltered softmax 1-N (both directions), AdaGrad",
        "seed": SEED,
        "dim": DIM,
        "max_epochs": MAX_EPOCHS,
        "min_epoch": MIN_EPOCH,
        "patience": PATIENCE,
        "lr": LR,
        "batch": BATCH,
        "reg": REG,
        "valid_select": {
            "every_after_min_epoch": 1,
            "also_recorded_epochs": [1, 5],
            "n_sample": VALID_SAMPLE,
            "best_epoch": best_ep,
            "best_valid_sample_mrr": best_valid,
            "min_epoch": MIN_EPOCH,
            "patience": PATIENCE,
            "note": "valid only; no test grid (A26); epochs < 10 ineligible",
        },
        "train_hist": hist,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "npred": npred,
        "nent": nent,
        "n_rules_2hop": len(raw_rules),
        "file_sha256": hashes,
        "same_pair_leak": {"n": leak, "n_test": len(test)},
        "field_order_obs": order_obs,
        "n_filter_triples": len(all_tri),
        "arms": {
            "A_prior_support_neginf": prior_arm,
            "B_g51_support_neginf": g51_arm,
            "C_complex_all_entity": cx_arm,
        },
        "slices": {
            "prior": slice_metrics(prior_ranks, pg_dirs),
            "g51": slice_metrics(g51_ranks, pg_dirs),
            "complex": cx_slices,
        },
        "complex_minus_g51": delta,
        "controls": {
            "C1_test_n": {"n": len(test), "expected": TEST_N, "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_nent": {"nent": nent, "expected": NENT_OFFICIAL, "ok": c3_ok},
            "C4_field_order": {"ok": c4_ok, **order_obs},
            "C5_literature_compare": {"value": lit, "ok": c5_ok},
        },
        "falsifiers": {
            "F1_complex_does_not_beat_g51": {
                "complex_mrr": cx_arm["mrr"],
                "g51_mrr": g51_arm["mrr"],
                "delta": delta,
                "bar": G51_BAR,
                "fired": f1_fired,
                "fires_when": "complex - g51 < 0.005",
                "description": (
                    "Fires if ComplEx all-entity MRR does not beat G51 "
                    "(support−∞ / all-entity) by >= +0.005"
                ),
            },
            "F2_complex_below_official_prior": {
                "complex_mrr": cx_arm["mrr"],
                "prior_bar": OFFICIAL_PRIOR,
                "prior_observed": prior_arm["mrr"],
                "fired": f2_fired,
                "fires_when": "complex < 0.2334",
                "description": (
                    "Fires if ComplEx MRR < 0.2334 (official prior) "
                    "→ broken/undertrained"
                ),
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out_json = os.path.join(HERE, "complex.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G72 filtered all-entity ComplEx ===", flush=True)
    print(f"  prior  support−∞  MRR={prior_arm['mrr']:.4f} H@10={prior_arm['hits10']:.4f}", flush=True)
    print(f"  G51    support−∞  MRR={g51_arm['mrr']:.4f} H@10={g51_arm['hits10']:.4f}", flush=True)
    print(
        f"  ComplEx ALL-ent MRR={cx_arm['mrr']:.4f} H@10={cx_arm['hits10']:.4f} "
        f"H@1={cx_arm['hits1']:.4f} best_epoch={best_ep}",
        flush=True,
    )
    print(f"  Δ ComplEx-G51 = {delta:+.4f}", flush=True)
    print(f"  F1={f1_fired} F2={f2_fired}", flush=True)
    print(
        f"  ComplEx tail={cx_slices['tail']['mrr']:.4f} head={cx_slices['head']['mrr']:.4f}",
        flush=True,
    )
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test is 20466",
                can_fail_because="wrong test.txt",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="official test same-pair leak with train is 0",
                can_fail_because="wrong split or leak detector",
                null_must_contain="leak>0"),
        Control("C3_nent", why="train+valid+test entities = 14541",
                can_fail_because="pack_ids over train only (14505)",
                null_must_contain="nent!=14541"),
        Control("C4_field_order", why="(p,s,o) after pack_ids; 237 relations",
                can_fail_because="(s,p,o) swap or truncated relations",
                null_must_contain="max_p>=npred"),
        Control("C5_literature_compare", why="no RotatE/Bordes excerpt under corpus/",
                can_fail_because="a quoted 0.338 or similar was invented",
                null_must_contain="a literature MRR"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_test_n"])
    controls[1].observe(c2_ok, res["controls"]["C2_leak"])
    controls[2].observe(c3_ok, res["controls"]["C3_nent"])
    controls[3].observe(c4_ok, res["controls"]["C4_field_order"])
    controls[4].observe(c5_ok, res["controls"]["C5_literature_compare"])

    falsifiers = [
        Falsifier(
            "F1_complex_does_not_beat_g51",
            refutes="that ComplEx all-entity is a +0.005 lift over G51 on this protocol",
            fires_when="complex - g51 < 0.005",
            null_must_contain="a signed delta vs G51, including a loss",
        ),
        Falsifier(
            "F2_complex_below_official_prior",
            refutes="that the latent arm is a working ComplEx",
            fires_when="complex < 0.2334",
            null_must_contain="an MRR on either side of the official prior 0.2334",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_complex_does_not_beat_g51"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_complex_below_official_prior"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G59_official_split")],
        artifacts=[os.path.join(HERE, "complex.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("complex_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "ComplEx all-entity MRR does not beat G51 (support−∞) by >= +0.005, "
            "OR ComplEx MRR < 0.2334 official prior (broken/undertrained)"
        ),
        allow_dirty=True,
        note=(
            "G72: ComplEx filtered all-entity on official FB15k-237. "
            "No early-stop before epoch 10; patience on valid. "
            "G51/prior under support−∞ so the comparison is not A18. "
            "No literature MRR."
        ),
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
