#!/usr/bin/env python3
"""G66 — DistMult, filtered ALL-ENTITY ranking, official FB15k-237.

Kitchen G51/G59 rank only the train support of p (everyone else −∞).
Papers score every entity. This spike is that third PROTOCOL column.

Score: <h, r, t> = sum_k h_k * r_k * t_k. Higher better.
Train on official TRAIN only. Valid used only for early-stop (not γ/β, A26).
Do not quote Bordes/RotatE/AMIE (G35). literature_compare=unavailable.

F1: DistMult all-entity MRR does not beat G51 (support−∞) by >= +0.005.
    fires_when distmult - g51 < 0.005
F2: DistMult MRR < 0.2334 (official prior) → broken/undertrained.
    fires_when distmult < 0.2334

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G66_all_entity_distmult/distmult.py
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
VENV_PY = os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")

# Prefer the S5 venv (numpy lives there). Re-exec once if needed.
if os.path.isfile(VENV_PY) and os.path.abspath(sys.executable) != os.path.abspath(VENV_PY):
    os.execv(VENV_PY, [VENV_PY, os.path.abspath(__file__)] + sys.argv[1:])

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

# Pre-registered. Not searched on test (A26). Valid only for early-stop.
SEED = 66
DIM = 50
EPOCHS = 25
LR = 0.1
BATCH = 1024
REG = 1e-5
VALID_EVERY = 5
VALID_SAMPLE = 1500
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


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def build_true_lists(triples):
    sp, po = defaultdict(list), defaultdict(list)
    for p, s, o in triples:
        sp[(int(s), int(p))].append(int(o))
        po[(int(p), int(o))].append(int(s))
    sp_a = {k: np.asarray(v, dtype=np.int32) for k, v in sp.items()}
    po_a = {k: np.asarray(v, dtype=np.int32) for k, v in po.items()}
    return sp_a, po_a


def softmax_grad(scores, target):
    """Filtered-ready softmax NLL. scores (B, nent), target (B,)."""
    bsz = scores.shape[0]
    m = np.max(scores, axis=1, keepdims=True)
    exp = np.exp(scores - m)
    z = exp.sum(axis=1, keepdims=True)
    prob = exp / np.maximum(z, 1e-12)
    nll = -np.log(np.maximum(prob[np.arange(bsz), target], 1e-12)).mean()
    g = prob / bsz
    g[np.arange(bsz), target] -= 1.0 / bsz
    return g, float(nll)


def filter_scores(scores, keys, true_map, keep):
    """Set other true entities to -inf so softmax matches filtered ranking."""
    for i, k in enumerate(keys):
        idx = true_map.get(k)
        if idx is None:
            continue
        mask = idx[idx != keep[i]]
        if len(mask):
            scores[i, mask] = -1e9


def adagrad_step(param, acc, grad, lr):
    acc += grad * grad
    param -= lr * grad / (np.sqrt(acc) + 1e-10)


def train_distmult(train, nent, npred, rng, train_sp, train_po, valid_q=None,
                   eval_sp=None, eval_po=None):
    """Filtered softmax 1-N DistMult (both directions). Valid only for early-stop."""
    scale = 1.0 / np.sqrt(DIM)
    E = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    R = rng.uniform(-scale, scale, size=(npred, DIM)).astype(np.float32)
    Eg = np.zeros_like(E)
    Rg = np.zeros_like(R)
    tri = np.asarray(train, dtype=np.int32)
    n = len(tri)
    hist = []
    best = {"mrr": -1.0, "epoch": 0, "E": E.copy(), "R": R.copy()}

    for ep in range(1, EPOCHS + 1):
        t0 = time.time()
        perm = rng.permutation(n)
        loss_acc = 0.0
        n_batches = 0
        for start in range(0, n, BATCH):
            batch = tri[perm[start:start + BATCH]]
            p, s, o = batch[:, 0], batch[:, 1], batch[:, 2]
            bsz = len(batch)

            hr = E[s] * R[p]
            scores_t = hr @ E.T
            filter_scores(scores_t, list(zip(s.tolist(), p.tolist())), train_sp, o)
            g_t, nll_t = softmax_grad(scores_t, o)
            g_hr = g_t @ E
            gE = g_t.T @ hr
            np.add.at(gE, s, g_hr * R[p])
            gR = np.zeros_like(R)
            np.add.at(gR, p, g_hr * E[s])

            tr = E[o] * R[p]
            scores_h = tr @ E.T
            filter_scores(scores_h, list(zip(p.tolist(), o.tolist())), train_po, s)
            g_h, nll_h = softmax_grad(scores_h, s)
            g_tr = g_h @ E
            gE += g_h.T @ tr
            np.add.at(gE, o, g_tr * R[p])
            np.add.at(gR, p, g_tr * E[o])

            if REG:
                gE += REG * E
                gR += REG * R

            adagrad_step(E, Eg, gE, LR)
            adagrad_step(R, Rg, gR, LR)
            loss_acc += nll_t + nll_h
            n_batches += 1

        row = {
            "epoch": ep,
            "nll": round(loss_acc / max(1, n_batches), 4),
            "sec": round(time.time() - t0, 2),
        }
        if valid_q is not None and (ep % VALID_EVERY == 0 or ep == EPOCHS or ep == 1):
            vr, _, _ = rank_all_entity(valid_q, E, R, eval_sp, eval_po)
            vm = metrics(vr)
            row["valid_sample_mrr"] = vm["mrr"]
            if vm["mrr"] > best["mrr"]:
                best = {"mrr": vm["mrr"], "epoch": ep, "E": E.copy(), "R": R.copy()}
                row["best"] = True
        hist.append(row)
        extra = f" valid_mrr={row['valid_sample_mrr']:.4f}" if "valid_sample_mrr" in row else ""
        print(
            f"  epoch {ep}/{EPOCHS} nll={row['nll']:.4f} {row['sec']:.1f}s{extra}",
            flush=True,
        )

    if best["mrr"] < 0:
        best = {"mrr": None, "epoch": EPOCHS, "E": E, "R": R}
    return best["E"], best["R"], hist, best["epoch"], best["mrr"]


def complex_tail_scores(E_re, E_im, R_re, R_im, s, p):
    h_re, h_im = E_re[s], E_im[s]
    r_re, r_im = R_re[p], R_im[p]
    inner_re = h_re * r_re - h_im * r_im
    inner_im = h_re * r_im + h_im * r_re
    return inner_re @ E_re.T + inner_im @ E_im.T, inner_re, inner_im, h_re, h_im, r_re, r_im


def complex_head_scores(E_re, E_im, R_re, R_im, o, p):
    t_re, t_im = E_re[o], E_im[o]
    r_re, r_im = R_re[p], R_im[p]
    rhs_re = r_re * t_re + r_im * t_im
    rhs_im = r_re * t_im - r_im * t_re
    return rhs_re @ E_re.T + rhs_im @ E_im.T, rhs_re, rhs_im, t_re, t_im, r_re, r_im


def train_complex(train, nent, npred, rng, train_sp, train_po, valid_q=None,
                  eval_sp=None, eval_po=None):
    """Filtered softmax 1-N ComplEx. DistMult F2 fired (too weak); same protocol."""
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
    best = {"mrr": -1.0, "epoch": 0, "emb": pack()}

    for ep in range(1, EPOCHS + 1):
        t0 = time.time()
        perm = rng.permutation(n)
        loss_acc = 0.0
        n_batches = 0
        for start in range(0, n, BATCH):
            batch = tri[perm[start:start + BATCH]]
            p, s, o = batch[:, 0], batch[:, 1], batch[:, 2]
            bsz = len(batch)

            sc_t, ire, iim, h_re, h_im, r_re, r_im = complex_tail_scores(
                E_re, E_im, R_re, R_im, s, p)
            filter_scores(sc_t, list(zip(s.tolist(), p.tolist())), train_sp, o)
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
            filter_scores(sc_h, list(zip(p.tolist(), o.tolist())), train_po, s)
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

        row = {
            "epoch": ep,
            "nll": round(loss_acc / max(1, n_batches), 4),
            "sec": round(time.time() - t0, 2),
        }
        do_valid = valid_q is not None and (
            ep % VALID_EVERY == 0 or ep == EPOCHS or ep <= 5)
        if do_valid:
            vr, _, _ = rank_complex(valid_q, E_re, E_im, R_re, R_im, eval_sp, eval_po)
            vm = metrics(vr)
            row["valid_sample_mrr"] = vm["mrr"]
            if vm["mrr"] > best["mrr"]:
                best = {"mrr": vm["mrr"], "epoch": ep, "emb": pack()}
                row["best"] = True
        hist.append(row)
        extra = f" valid_mrr={row['valid_sample_mrr']:.4f}" if "valid_sample_mrr" in row else ""
        print(
            f"  epoch {ep}/{EPOCHS} nll={row['nll']:.4f} {row['sec']:.1f}s{extra}",
            flush=True,
        )

    if best["mrr"] < 0:
        best = {"mrr": None, "epoch": EPOCHS, "emb": pack()}
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


def rank_all_entity(queries, E, R, true_sp, true_po, batch=256):
    """Filtered all-entity ranks. Expected rank: 1 + higher + equal/2."""
    ranks = []
    directions = []
    nent = E.shape[0]
    q = list(queries)
    for start in range(0, len(q), batch):
        chunk = q[start:start + batch]
        p = np.array([t[0] for t in chunk], dtype=np.int32)
        s = np.array([t[1] for t in chunk], dtype=np.int32)
        o = np.array([t[2] for t in chunk], dtype=np.int32)
        # tail
        hr = E[s] * R[p]
        sc = hr @ E.T
        for i, (pi, si, oi) in enumerate(zip(p.tolist(), s.tolist(), o.tolist())):
            filt = true_sp.get((si, pi))
            if filt is not None:
                mask = filt[filt != oi]
                if len(mask):
                    sc[i, mask] = -np.inf
        tgt = sc[np.arange(len(chunk)), o]
        higher = np.sum(sc > tgt[:, None], axis=1)
        equal = np.sum(sc == tgt[:, None], axis=1) - 1
        for h, e in zip(higher.tolist(), equal.tolist()):
            ranks.append(1.0 + h + 0.5 * e)
            directions.append("tail")
        # head
        tr = E[o] * R[p]
        sc = tr @ E.T
        for i, (pi, si, oi) in enumerate(zip(p.tolist(), s.tolist(), o.tolist())):
            filt = true_po.get((pi, oi))
            if filt is not None:
                mask = filt[filt != si]
                if len(mask):
                    sc[i, mask] = -np.inf
        tgt = sc[np.arange(len(chunk)), s]
        higher = np.sum(sc > tgt[:, None], axis=1)
        equal = np.sum(sc == tgt[:, None], axis=1) - 1
        for h, e in zip(higher.tolist(), equal.tolist()):
            ranks.append(1.0 + h + 0.5 * e)
            directions.append("head")
        del sc
    assert len(ranks) == 2 * len(q)
    return ranks, directions, nent


def score_support_neginf(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx):
    """G59/G51 protocol: score train support of p (and rule firings); rest −∞."""
    rows = G59.score_split(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    prior = [r["ranks"]["prior"] for r in rows]
    g51 = [r["ranks"]["g51"] for r in rows]
    dirs = [r["direction"] for r in rows]
    return prior, g51, dirs


def load_or_mine_rules(train, out_adj, pair_tr, byp, rev):
    if os.path.isfile(RULES_CACHE):
        raw = json.loads(open(RULES_CACHE, encoding="utf-8").read())
        print(f"loaded {len(raw)} rules from cache", flush=True)
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
    train_sp, train_po = build_true_lists(train)

    rng = np.random.default_rng(SEED)
    valid_idx = rng.choice(len(valid), size=min(VALID_SAMPLE, len(valid)), replace=False)
    valid_sample = [valid[int(i)] for i in valid_idx]

    out_json = os.path.join(HERE, "distmult.json")
    cached = json.loads(open(out_json, encoding="utf-8").read()) if os.path.isfile(out_json) else {}
    cached_dm = (cached.get("arms") or {}).get("C_distmult_all_entity")
    # DistMult already run this session (F2 fired). Do not retrain on test (A26).
    if cached_dm and cached.get("model") in (None, "DistMult", "ComplEx"):
        dm_arm = cached_dm
        dm_slices = (cached.get("slices") or {}).get("distmult") or {}
        hist_dm = cached.get("train_hist") or cached.get("distmult_train_hist") or []
        best_ep_dm = (cached.get("valid_early_stop") or {}).get("best_epoch")
        best_valid_dm = (cached.get("valid_early_stop") or {}).get("best_valid_sample_mrr")
        if cached.get("distmult_valid_early_stop"):
            best_ep_dm = cached["distmult_valid_early_stop"]["best_epoch"]
            best_valid_dm = cached["distmult_valid_early_stop"]["best_valid_sample_mrr"]
            hist_dm = cached.get("distmult_train_hist") or hist_dm
        print(
            f"cached DistMult MRR={dm_arm['mrr']:.4f} "
            f"(best_valid_epoch={best_ep_dm})",
            flush=True,
        )
    else:
        print("training DistMult (filtered softmax 1-N, train only) ...", flush=True)
        t_tr = time.time()
        E, R, hist_dm, best_ep_dm, best_valid_dm = train_distmult(
            train, nent, npred, rng, train_sp, train_po,
            valid_q=valid_sample, eval_sp=eval_sp, eval_po=eval_po,
        )
        print(
            f"trained DistMult in {time.time() - t_tr:.1f}s "
            f"best_valid_epoch={best_ep_dm} best_valid_sample_mrr={best_valid_dm}",
            flush=True,
        )
        print("ranking DistMult ALL entities (filtered) on official TEST ...", flush=True)
        t_ev = time.time()
        dm_ranks, dm_dirs, _ = rank_all_entity(test, E, R, eval_sp, eval_po)
        dm_arm = metrics(dm_ranks)
        dm_slices = slice_metrics(dm_ranks, dm_dirs)
        print(f"DistMult MRR={dm_arm['mrr']:.4f} H@10={dm_arm['hits10']:.4f} "
              f"in {time.time() - t_ev:.1f}s", flush=True)

    print("training ComplEx (DistMult F2: too weak to train) ...", flush=True)
    t_cx = time.time()
    (E_re, E_im, R_re, R_im), hist_cx, best_ep_cx, best_valid_cx = train_complex(
        train, nent, npred, rng, train_sp, train_po,
        valid_q=valid_sample, eval_sp=eval_sp, eval_po=eval_po,
    )
    print(
        f"trained ComplEx in {time.time() - t_cx:.1f}s "
        f"best_valid_epoch={best_ep_cx} best_valid_sample_mrr={best_valid_cx}",
        flush=True,
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
    raw_rules = load_or_mine_rules(train, out_adj, pair_tr, byp, rev)
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

    delta_dm = round(dm_arm["mrr"] - g51_arm["mrr"], 4)
    delta_cx = round(cx_arm["mrr"] - g51_arm["mrr"], 4)
    # F1/F2 are the DistMult falsifiers stated before the run.
    f1_fired = (dm_arm["mrr"] - g51_arm["mrr"]) < G51_BAR
    f2_fired = dm_arm["mrr"] < OFFICIAL_PRIOR
    headline = "D_complex_all_entity" if f2_fired else "C_distmult_all_entity"
    headline_arm = cx_arm if f2_fired else dm_arm

    c1_ok = len(test) == TEST_N
    c2_ok = leak == 0
    c3_ok = nent == NENT_OFFICIAL
    c4_ok = order_ok and npred == NPRED_OFFICIAL
    lit = "unavailable"
    c5_ok = lit == "unavailable"

    res = {
        "spike": "G66",
        "split": "official FB15k-237 train/valid/test",
        "source_git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
        "source_commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
        "field_order": "p,s,o",
        "headline_arm": headline,
        "headline_is_test_grid": False,
        "literature_compare": lit,
        "literature_note": "do not quote Bordes/RotatE/AMIE MRR; no excerpt under corpus/",
        "candidate_set": "all 14541 entities, filtered train+valid+test",
        "protocol": "filtered_all_entity",
        "scoreboard_note": (
            "pair-disjoint G54 0.2313 and official G59 0.2679 stay; "
            "G66 is a third PROTOCOL column"
        ),
        "model": "ComplEx" if f2_fired else "DistMult",
        "distmult_too_weak": f2_fired,
        "score_fn_distmult": "sum_k h_k * r_k * t_k",
        "score_fn_complex": "Re(sum_k h_k * r_k * conj(t_k))",
        "train_objective": "filtered softmax 1-N (both directions), AdaGrad",
        "seed": SEED,
        "dim": DIM,
        "epochs": EPOCHS,
        "lr": LR,
        "batch": BATCH,
        "reg": REG,
        "distmult_valid_early_stop": {
            "every": VALID_EVERY,
            "n_sample": VALID_SAMPLE,
            "best_epoch": best_ep_dm,
            "best_valid_sample_mrr": best_valid_dm,
            "note": "valid only; no test grid (A26)",
        },
        "complex_valid_early_stop": {
            "every": VALID_EVERY,
            "also_epochs_1_to_5": True,
            "n_sample": VALID_SAMPLE,
            "best_epoch": best_ep_cx,
            "best_valid_sample_mrr": best_valid_cx,
            "note": "valid only; no test grid (A26)",
        },
        "distmult_train_hist": hist_dm,
        "complex_train_hist": hist_cx,
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
            "C_distmult_all_entity": dm_arm,
            "D_complex_all_entity": cx_arm,
        },
        "slices": {
            "prior": slice_metrics(prior_ranks, pg_dirs),
            "g51": slice_metrics(g51_ranks, pg_dirs),
            "distmult": dm_slices,
            "complex": cx_slices,
        },
        "distmult_minus_g51": delta_dm,
        "complex_minus_g51": delta_cx,
        "controls": {
            "C1_test_n": {"n": len(test), "expected": TEST_N, "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_nent": {"nent": nent, "expected": NENT_OFFICIAL, "ok": c3_ok},
            "C4_field_order": {"ok": c4_ok, **order_obs},
            "C5_literature_compare": {"value": lit, "ok": c5_ok},
        },
        "falsifiers": {
            "F1_distmult_does_not_beat_g51": {
                "distmult_mrr": dm_arm["mrr"],
                "complex_mrr": cx_arm["mrr"],
                "g51_mrr": g51_arm["mrr"],
                "delta": delta_dm,
                "complex_delta": delta_cx,
                "bar": G51_BAR,
                "fired": f1_fired,
                "fires_when": "distmult - g51 < 0.005",
                "description": (
                    "Fires if DistMult all-entity MRR does not beat G51 "
                    "(support−∞ / all-entity) by >= +0.005"
                ),
            },
            "F2_distmult_below_official_prior": {
                "distmult_mrr": dm_arm["mrr"],
                "complex_mrr": cx_arm["mrr"],
                "prior_bar": OFFICIAL_PRIOR,
                "prior_observed": prior_arm["mrr"],
                "fired": f2_fired,
                "fires_when": "distmult < 0.2334",
                "description": (
                    "Fires if DistMult MRR < 0.2334 (official prior) "
                    "→ broken/undertrained"
                ),
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G66 filtered all-entity ===", flush=True)
    print(f"  prior  support−∞  MRR={prior_arm['mrr']:.4f} H@10={prior_arm['hits10']:.4f}", flush=True)
    print(f"  G51    support−∞  MRR={g51_arm['mrr']:.4f} H@10={g51_arm['hits10']:.4f}", flush=True)
    print(
        f"  DistMult ALL-ent MRR={dm_arm['mrr']:.4f} H@10={dm_arm['hits10']:.4f} "
        f"H@1={dm_arm['hits1']:.4f}",
        flush=True,
    )
    print(
        f"  ComplEx  ALL-ent MRR={cx_arm['mrr']:.4f} H@10={cx_arm['hits10']:.4f} "
        f"H@1={cx_arm['hits1']:.4f}",
        flush=True,
    )
    print(
        f"  Δ DistMult-G51 = {delta_dm:+.4f}  Δ ComplEx-G51 = {delta_cx:+.4f}",
        flush=True,
    )
    print(f"  F1={f1_fired} F2={f2_fired} headline={headline}", flush=True)
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
            "F1_distmult_does_not_beat_g51",
            refutes="that DistMult all-entity is a +0.005 lift over G51 on this protocol",
            fires_when="distmult - g51 < 0.005",
            null_must_contain="a signed delta vs G51, including a loss",
        ),
        Falsifier(
            "F2_distmult_below_official_prior",
            refutes="that the latent arm is a working DistMult",
            fires_when="distmult < 0.2334",
            null_must_contain="an MRR on either side of the official prior 0.2334",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_distmult_does_not_beat_g51"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_distmult_below_official_prior"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G59_official_split")],
        artifacts=[os.path.join(HERE, "distmult.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("distmult_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "DistMult all-entity MRR does not beat G51 (support−∞) by >= +0.005, "
            "OR DistMult MRR < 0.2334 official prior (broken/undertrained)"
        ),
        allow_dirty=True,
        note=(
            "G66: DistMult filtered all-entity on official FB15k-237. "
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
