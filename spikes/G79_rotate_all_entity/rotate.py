#!/usr/bin/env python3
"""G79 — RotatE all-entity, G72 protocol (min_epoch=10).

Score: −||h ◦ r − t||² with |r_i|=1 (r = exp(iθ)). Higher better.
Same trainer as G72/G76: unfiltered 1-N softmax, AdaGrad, dim=64,
no eligible checkpoint before epoch 10. The paper's self-adversarial
dim=1000 run is a different protocol; 0.338 is in
corpus/refs/sun-2019-rotate-fb15k237.txt and is NOT a falsifier bar.

F1: RotatE − DistMult 0.2852 < +0.005.
F2: RotatE < 0.2334 (broken/undertrained).
F3: RotatE < ComplEx 0.2755.

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G79_rotate_all_entity/rotate.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
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
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G72_complex_all_entity"))

import bayesian_lift as G51  # noqa: E402
import complex as G72  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
RULES_CACHE = os.path.join(HERE, "rules_cache.json")
G72_RULES = os.path.join(SPIKES, "G72_complex_all_entity", "rules_cache.json")
EMB_PATH = os.path.join(HERE, "rotate_emb.npz")
HIST_PATH = os.path.join(HERE, "train_hist.json")
EXCERPT = os.path.join(ROOT, "corpus", "refs", "sun-2019-rotate-fb15k237.txt")

SEED = 79
DIM = 64
MAX_EPOCHS = 40
MIN_EPOCH = 10
PATIENCE = 8
LR = 0.1
BATCH = 1024
REG = 1e-5
VALID_SAMPLE = 2500
OFFICIAL_PRIOR = 0.2334
G51_REF = 0.2585
COMPLEX_REF = 0.2755
DISTMULT_REF = 0.2852
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


def parse_excerpt(path):
    """Read stored numbers. Refuse if the file is missing or lacks RotatE."""
    if not os.path.isfile(path):
        return {"ok": False, "why": "excerpt missing"}
    text = open(path, encoding="utf-8").read()
    need = ("Sun 2019", "Trouillon 2016", ".338", ".337", "HITS@10   .533", "DistMult")
    missing = [s for s in need if s not in text]
    return {
        "ok": not missing,
        "why": None if not missing else f"missing {missing}",
        "sha256": sha256_file(path),
        "readme_rotate_mrr": 0.337 if ".337 ± .001" in text else None,
        "table5_rotate_mrr": 0.338 if ".338" in text else None,
        "table5_complex_mrr": 0.247 if ".247" in text else None,
        "table5_distmult_mrr": 0.241 if ".241" in text else None,
        "protocol_note": "self-adversarial dim=1000 100k steps; not this trainer",
    }


def rotate_tail_pack(E_re, E_im, theta, s, p):
    h_re, h_im = E_re[s], E_im[s]
    r_re = np.cos(theta[p])
    r_im = np.sin(theta[p])
    hr_re = h_re * r_re - h_im * r_im
    hr_im = h_re * r_im + h_im * r_re
    return hr_re, hr_im, r_re, r_im, h_re, h_im


def rotate_head_pack(E_re, E_im, theta, o, p):
    t_re, t_im = E_re[o], E_im[o]
    r_re = np.cos(theta[p])
    r_im = np.sin(theta[p])
    # t ◦ conj(r)
    tr_re = t_re * r_re + t_im * r_im
    tr_im = -t_re * r_im + t_im * r_re
    return tr_re, tr_im, r_re, r_im, t_re, t_im


def dist2_scores(hr_re, hr_im, E_re, E_im):
    hr_n = (hr_re * hr_re + hr_im * hr_im).sum(1, keepdims=True)
    t_n = (E_re * E_re + E_im * E_im).sum(1)
    ip = hr_re @ E_re.T + hr_im @ E_im.T
    return hr_n + t_n[None, :] - 2.0 * ip


def _assert_score_identity():
    rng = np.random.default_rng(0)
    d = 8
    h_re, h_im = rng.normal(size=d), rng.normal(size=d)
    th = rng.normal(size=d)
    r_re, r_im = np.cos(th), np.sin(th)
    t_re, t_im = rng.normal(size=d), rng.normal(size=d)
    hr_re = h_re * r_re - h_im * r_im
    hr_im = h_re * r_im + h_im * r_re
    direct = float(np.sum((hr_re - t_re) ** 2 + (hr_im - t_im) ** 2))
    E_re = np.stack([t_re, h_re]).astype(np.float64)
    E_im = np.stack([t_im, h_im]).astype(np.float64)
    theta = th[None, :].astype(np.float64)
    pck = rotate_tail_pack(E_re, E_im, theta, np.array([1]), np.array([0]))
    sc = dist2_scores(pck[0], pck[1], E_re, E_im)
    pck_h = rotate_head_pack(E_re, E_im, theta, np.array([0]), np.array([0]))
    sc_h = dist2_scores(pck_h[0], pck_h[1], E_re, E_im)
    if abs(float(sc[0, 0]) - direct) > 1e-6:
        raise RuntimeError(f"RotatE tail identity failed: {sc[0, 0]} vs {direct}")
    if abs(float(sc_h[0, 1]) - direct) > 1e-5:
        raise RuntimeError(f"RotatE head identity failed: {sc_h[0, 1]} vs {direct}")
    if abs(float(r_re[0] ** 2 + r_im[0] ** 2) - 1.0) > 1e-6:
        raise RuntimeError("unit-modulus failed")


def _backprop_dist2(g_sc, hr_re, hr_im, E_re, E_im):
    """scores = -dist2; g_sc = dL/d scores. Returns g_hr_re, g_hr_im, gE_re, gE_im."""
    g_d = -g_sc
    sum_g = g_d.sum(axis=1, keepdims=True)
    g_hr_re = 2.0 * (sum_g * hr_re - g_d @ E_re)
    g_hr_im = 2.0 * (sum_g * hr_im - g_d @ E_im)
    col = g_d.sum(axis=0)[:, None]
    gE_re = 2.0 * (col * E_re - g_d.T @ hr_re)
    gE_im = 2.0 * (col * E_im - g_d.T @ hr_im)
    return g_hr_re, g_hr_im, gE_re, gE_im


def train_rotate(train, nent, npred, rng, valid_q=None, eval_sp=None, eval_po=None):
    scale = 1.0 / np.sqrt(DIM)
    E_re = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    E_im = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    theta = rng.uniform(-np.pi, np.pi, size=(npred, DIM)).astype(np.float32)
    accE_re = np.zeros_like(E_re)
    accE_im = np.zeros_like(E_im)
    accTh = np.zeros_like(theta)
    tri = np.asarray(train, dtype=np.int32)
    n = len(tri)
    hist = []
    pack = lambda: (E_re.copy(), E_im.copy(), theta.copy())
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

            hr_re, hr_im, r_re, r_im, h_re, h_im = rotate_tail_pack(
                E_re, E_im, theta, s, p)
            sc_t = -dist2_scores(hr_re, hr_im, E_re, E_im)
            g_t, nll_t = G72.softmax_grad(sc_t, o)
            g_hr_re, g_hr_im, gE_re, gE_im = _backprop_dist2(
                g_t, hr_re, hr_im, E_re, E_im)
            np.add.at(gE_re, s, g_hr_re * r_re + g_hr_im * r_im)
            np.add.at(gE_im, s, -g_hr_re * r_im + g_hr_im * r_re)
            g_r_re = g_hr_re * h_re + g_hr_im * h_im
            g_r_im = -g_hr_re * h_im + g_hr_im * h_re
            gTh = np.zeros_like(theta)
            np.add.at(gTh, p, -g_r_re * r_im + g_r_im * r_re)

            tr_re, tr_im, r_re, r_im, t_re, t_im = rotate_head_pack(
                E_re, E_im, theta, o, p)
            sc_h = -dist2_scores(tr_re, tr_im, E_re, E_im)
            g_h, nll_h = G72.softmax_grad(sc_h, s)
            g_tr_re, g_tr_im, gE_re_h, gE_im_h = _backprop_dist2(
                g_h, tr_re, tr_im, E_re, E_im)
            gE_re += gE_re_h
            gE_im += gE_im_h
            np.add.at(gE_re, o, g_tr_re * r_re - g_tr_im * r_im)
            np.add.at(gE_im, o, g_tr_re * r_im + g_tr_im * r_re)
            g_r_re = g_tr_re * t_re + g_tr_im * t_im
            g_r_im = g_tr_re * t_im - g_tr_im * t_re
            np.add.at(gTh, p, -g_r_re * r_im + g_r_im * r_re)

            if REG:
                gE_re += REG * E_re
                gE_im += REG * E_im
            G72.adagrad_step(E_re, accE_re, gE_re, LR)
            G72.adagrad_step(E_im, accE_im, gE_im, LR)
            G72.adagrad_step(theta, accTh, gTh, LR)
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
        do_valid = valid_q is not None and (
            ep >= MIN_EPOCH or ep == 1 or ep == 5 or ep == MAX_EPOCHS)
        if do_valid:
            vr, _, _ = rank_rotate(valid_q, E_re, E_im, theta, eval_sp, eval_po)
            vm = G72.metrics(vr)
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


def rank_rotate(queries, E_re, E_im, theta, true_sp, true_po, batch=256):
    ranks, directions = [], []
    q = list(queries)
    for start in range(0, len(q), batch):
        chunk = q[start:start + batch]
        p = np.array([t[0] for t in chunk], dtype=np.int32)
        s = np.array([t[1] for t in chunk], dtype=np.int32)
        o = np.array([t[2] for t in chunk], dtype=np.int32)
        hr_re, hr_im, *_ = rotate_tail_pack(E_re, E_im, theta, s, p)
        sc_t = -dist2_scores(hr_re, hr_im, E_re, E_im)
        G72._rank_from_scores(
            sc_t, o, chunk, true_sp,
            lambda pi, si, oi: (si, pi), lambda si, oi: oi,
            "tail", ranks, directions,
        )
        tr_re, tr_im, *_ = rotate_head_pack(E_re, E_im, theta, o, p)
        sc_h = -dist2_scores(tr_re, tr_im, E_re, E_im)
        G72._rank_from_scores(
            sc_h, s, chunk, true_po,
            lambda pi, si, oi: (pi, oi), lambda si, oi: si,
            "head", ranks, directions,
        )
    assert len(ranks) == 2 * len(q)
    return ranks, directions, E_re.shape[0]


def load_or_mine_rules(out_adj, pair_tr, byp, rev):
    for path, label in ((RULES_CACHE, "local"), (G72_RULES, "G72")):
        if os.path.isfile(path):
            raw = json.loads(open(path, encoding="utf-8").read())
            if path != RULES_CACHE:
                os.makedirs(HERE, exist_ok=True)
                shutil.copy2(path, RULES_CACHE)
            print(f"loaded {len(raw)} rules ({label})", flush=True)
            return raw
    print("mining 2-hop on official train ...", flush=True)
    t0 = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    slim = [{"head": r["head"], "body": list(r["body"]), "conf": r["conf"]} for r in rules]
    os.makedirs(HERE, exist_ok=True)
    with open(RULES_CACHE, "w", encoding="utf-8") as f:
        json.dump(slim, f)
    print(f"mined {len(slim)} in {time.time() - t0:.1f}s", flush=True)
    return slim


def train_or_load(train, nent, npred, rng, valid_sample, eval_sp, eval_po):
    if os.path.isfile(EMB_PATH):
        z = np.load(EMB_PATH)
        E_re, E_im, theta = z["E_re"], z["E_im"], z["theta"]
        best_ep = int(z["best_epoch"])
        best_valid = float(z["best_valid_sample_mrr"])
        hist = json.loads(open(HIST_PATH, encoding="utf-8").read()) if os.path.isfile(HIST_PATH) else []
        print(
            f"loaded RotatE embeddings {EMB_PATH} "
            f"best_epoch={best_ep} valid_sample_mrr={best_valid}",
            flush=True,
        )
        if best_ep < MIN_EPOCH:
            raise RuntimeError(f"cached best_epoch={best_ep} < min_epoch={MIN_EPOCH}")
        return (E_re, E_im, theta), hist, best_ep, best_valid, True
    print(
        f"training RotatE (unfiltered 1-N, AdaGrad, dim={DIM}, "
        f"min_epoch={MIN_EPOCH}, |r_i|=1) ...",
        flush=True,
    )
    t0 = time.time()
    emb, hist, best_ep, best_valid = train_rotate(
        train, nent, npred, rng,
        valid_q=valid_sample, eval_sp=eval_sp, eval_po=eval_po,
    )
    E_re, E_im, theta = emb
    np.savez(
        EMB_PATH, E_re=E_re, E_im=E_im, theta=theta,
        best_epoch=np.int32(best_ep),
        best_valid_sample_mrr=np.float64(best_valid if best_valid is not None else -1.0),
    )
    with open(HIST_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    print(
        f"trained RotatE in {time.time() - t0:.1f}s "
        f"best_epoch={best_ep} valid_sample_mrr={best_valid}",
        flush=True,
    )
    if best_ep is None or best_ep < MIN_EPOCH:
        raise RuntimeError(f"selection violated min_epoch={MIN_EPOCH}: {best_ep}")
    return emb, hist, best_ep, best_valid, False


def main():
    t0 = time.time()
    _assert_score_identity()
    excerpt = parse_excerpt(EXCERPT)
    print(f"excerpt ok={excerpt['ok']} sha={(excerpt.get('sha256') or '')[:12]}", flush=True)
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
    order_ok, order_obs = G72.field_order_ok(train, npred, nent)
    leak = G51.count_same_pair_leak(train, test)
    print(f"field_order_ok={order_ok} leak={leak}", flush=True)

    all_tri = train + valid + test
    true_sp_set, true_po_set = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)

    rng = np.random.default_rng(SEED)
    valid_idx = rng.choice(len(valid), size=min(VALID_SAMPLE, len(valid)), replace=False)
    valid_sample = [valid[int(i)] for i in valid_idx]

    (E_re, E_im, theta), hist, best_ep, best_valid, used_cache = train_or_load(
        train, nent, npred, rng, valid_sample, eval_sp, eval_po,
    )

    print("ranking RotatE ALL entities (filtered) on official TEST ...", flush=True)
    t_ev = time.time()
    rt_ranks, rt_dirs, _ = rank_rotate(test, E_re, E_im, theta, eval_sp, eval_po)
    rt_arm = G72.metrics(rt_ranks)
    rt_slices = G72.slice_metrics(rt_ranks, rt_dirs)
    print(
        f"RotatE MRR={rt_arm['mrr']:.4f} H@10={rt_arm['hits10']:.4f} "
        f"in {time.time() - t_ev:.1f}s",
        flush=True,
    )

    print("scoring prior + G51 under support−∞ ...", flush=True)
    t_g = time.time()
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    raw_rules = load_or_mine_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in raw_rules:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))
    idx = G59.slim_index(train)
    prior_ranks, g51_ranks, pg_dirs = G72.score_support_neginf(
        test, nent, rules_by_head, out_adj, in_adj, true_sp_set, true_po_set, idx,
    )
    prior_arm = G72.metrics(prior_ranks)
    g51_arm = G72.metrics(g51_ranks)
    print(
        f"prior={prior_arm['mrr']:.4f} G51={g51_arm['mrr']:.4f} "
        f"in {time.time() - t_g:.1f}s",
        flush=True,
    )

    delta_dm = round(rt_arm["mrr"] - DISTMULT_REF, 4)
    delta_cx = round(rt_arm["mrr"] - COMPLEX_REF, 4)
    f1_fired = (rt_arm["mrr"] - DISTMULT_REF) < G51_BAR
    f2_fired = rt_arm["mrr"] < OFFICIAL_PRIOR
    f3_fired = rt_arm["mrr"] < COMPLEX_REF

    c1_ok = len(test) == TEST_N
    c2_ok = leak == 0
    c3_ok = nent == NENT_OFFICIAL
    c4_ok = order_ok and npred == NPRED_OFFICIAL
    c5_ok = best_ep is not None and best_ep >= MIN_EPOCH
    c6_ok = abs(prior_arm["mrr"] - OFFICIAL_PRIOR) <= 0.0005
    c7_ok = bool(excerpt.get("ok"))
    lit = "unavailable"

    res = {
        "spike": "G79",
        "split": "official FB15k-237 train/valid/test",
        "source_git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
        "source_commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
        "field_order": "p,s,o",
        "headline_arm": "C_rotate_min10",
        "headline_is_test_grid": False,
        "literature_compare": lit,
        "literature_note": (
            "excerpt stored at corpus/refs/sun-2019-rotate-fb15k237.txt; "
            "0.338 is their self-adversarial dim=1000 protocol, not this row"
        ),
        "literature_excerpt": excerpt,
        "candidate_set": "all 14541 entities, filtered train+valid+test",
        "protocol": "filtered_all_entity",
        "scoreboard_note": (
            "G59 0.2679 stays observed+gate. G76 DistMult 0.2852 and G72 "
            "ComplEx 0.2755 are the same-protocol latent columns. G77 0.3101 "
            "is the mix. Do not headline against Sun 2019 0.338."
        ),
        "model": "RotatE",
        "score_fn": "-||h ◦ r - t||^2, |r_i|=1",
        "train_objective": "unfiltered softmax 1-N (both directions), AdaGrad",
        "seed": SEED,
        "dim": DIM,
        "max_epochs": MAX_EPOCHS,
        "min_epoch": MIN_EPOCH,
        "patience": PATIENCE,
        "lr": LR,
        "batch": BATCH,
        "reg": REG,
        "used_cached_embeddings": used_cache,
        "valid_select": {
            "n_sample": VALID_SAMPLE,
            "best_epoch": best_ep,
            "best_valid_sample_mrr": best_valid,
            "min_epoch": MIN_EPOCH,
            "patience": PATIENCE,
            "note": "valid only; epochs < 10 ineligible",
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
        "arms": {
            "A_prior_support_neginf": prior_arm,
            "B_g51_support_neginf": g51_arm,
            "C_rotate_min10": rt_arm,
        },
        "slices": {
            "prior": G72.slice_metrics(prior_ranks, pg_dirs),
            "g51": G72.slice_metrics(g51_ranks, pg_dirs),
            "rotate": rt_slices,
        },
        "rotate_minus_distmult_ref": delta_dm,
        "rotate_minus_complex_ref": delta_cx,
        "controls": {
            "C1_test_n": {"n": len(test), "expected": TEST_N, "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_nent": {"nent": nent, "expected": NENT_OFFICIAL, "ok": c3_ok},
            "C4_field_order": {"ok": c4_ok, **order_obs},
            "C5_min_epoch": {"best_epoch": best_ep, "min_epoch": MIN_EPOCH, "ok": c5_ok},
            "C6_prior_identity": {
                "prior": prior_arm["mrr"], "ref": OFFICIAL_PRIOR, "ok": c6_ok,
            },
            "C7_excerpt_present": excerpt,
            "C8_literature_compare": {"value": lit, "ok": lit == "unavailable"},
        },
        "falsifiers": {
            "F1_rotate_does_not_beat_distmult": {
                "rotate_mrr": rt_arm["mrr"],
                "distmult_ref": DISTMULT_REF,
                "delta": delta_dm,
                "bar": G51_BAR,
                "fired": f1_fired,
                "fires_when": "rotate - 0.2852 < 0.005",
            },
            "F2_rotate_below_official_prior": {
                "rotate_mrr": rt_arm["mrr"],
                "prior_bar": OFFICIAL_PRIOR,
                "prior_observed": prior_arm["mrr"],
                "fired": f2_fired,
                "fires_when": "rotate < 0.2334",
            },
            "F3_rotate_below_complex": {
                "rotate_mrr": rt_arm["mrr"],
                "complex_ref": COMPLEX_REF,
                "delta": delta_cx,
                "fired": f3_fired,
                "fires_when": "rotate < 0.2755",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out_json = os.path.join(HERE, "rotate.json")
    os.makedirs(HERE, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G79 RotatE min_epoch=10 ===", flush=True)
    print(f"  prior    {prior_arm['mrr']:.4f}", flush=True)
    print(f"  G51      {g51_arm['mrr']:.4f}", flush=True)
    print(
        f"  RotatE   {rt_arm['mrr']:.4f} H@10={rt_arm['hits10']:.4f} "
        f"best_epoch={best_ep}",
        flush=True,
    )
    print(
        f"  Δ vs DistMult {delta_dm:+.4f}  Δ vs ComplEx {delta_cx:+.4f} "
        f"(excerpt RotatE 0.338 is NOT this protocol)",
        flush=True,
    )
    print(f"  F1={f1_fired} F2={f2_fired} F3={f3_fired}", flush=True)
    print(
        f"  tail={rt_slices['tail']['mrr']:.4f} head={rt_slices['head']['mrr']:.4f}",
        flush=True,
    )
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test is 20466",
                can_fail_because="wrong test.txt",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="official leak is 0",
                can_fail_because="wrong split",
                null_must_contain="leak>0"),
        Control("C3_nent", why="14541 entities",
                can_fail_because="pack_ids over train only",
                null_must_contain="nent!=14541"),
        Control("C4_field_order", why="(p,s,o); 237 relations",
                can_fail_because="(s,p,o) swap",
                null_must_contain="max_p>=npred"),
        Control("C5_min_epoch", why="best_epoch >= 10",
                can_fail_because="G66 epoch-1 trap",
                null_must_contain="best_epoch<10"),
        Control("C6_prior_identity", why="prior 0.2334",
                can_fail_because="score_split drift",
                null_must_contain="prior!=0.2334"),
        Control("C7_excerpt_present", why="Sun 2019 table stored under corpus/",
                can_fail_because="G35 unsourced recall",
                null_must_contain="excerpt missing"),
        Control("C8_literature_compare", why="headline stays unavailable (protocol)",
                can_fail_because="quoted 0.338 as our bar",
                null_must_contain="a literature MRR headline"),
    ]
    keys = [
        "C1_test_n", "C2_leak", "C3_nent", "C4_field_order",
        "C5_min_epoch", "C6_prior_identity", "C7_excerpt_present",
        "C8_literature_compare",
    ]
    oks = [c1_ok, c2_ok, c3_ok, c4_ok, c5_ok, c6_ok, c7_ok, True]
    for ctl, key, okv in zip(controls, keys, oks):
        ctl.observe(okv, res["controls"][key])

    falsifiers = [
        Falsifier(
            "F1_rotate_does_not_beat_distmult",
            refutes="that RotatE under G72 protocol is a +0.005 lift over DistMult 0.2852",
            fires_when="rotate - 0.2852 < 0.005",
            null_must_contain="a signed delta vs DistMult, including a loss",
        ),
        Falsifier(
            "F2_rotate_below_official_prior",
            refutes="that the latent arm is a working RotatE",
            fires_when="rotate < 0.2334",
            null_must_contain="an MRR on either side of the official prior 0.2334",
        ),
        Falsifier(
            "F3_rotate_below_complex",
            refutes="that RotatE under this protocol beats ComplEx 0.2755",
            fires_when="rotate < 0.2755",
            null_must_contain="RotatE on either side of 0.2755",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_rotate_does_not_beat_distmult"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_rotate_below_official_prior"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_rotate_below_complex"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G72_complex_all_entity"),
              os.path.join(ROOT, "corpus", "refs")],
        artifacts=[os.path.join(HERE, "rotate.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("rotate_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "RotatE min_epoch=10 does not beat DistMult 0.2852 by +0.005, "
            "OR RotatE < 0.2334, OR RotatE < ComplEx 0.2755"
        ),
        allow_dirty=True,
        note=(
            "G79: RotatE filtered all-entity on official FB15k-237 "
            "with G72 min_epoch=10. Sun 2019 0.338 is excerpted, not a bar. "
            "No literature headline."
        ),
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
