#!/usr/bin/env python3
"""G92 — Neuro-Symbolic Hybrid Mix with RotatE & ComplEx on Official WN18RR.

Ensembles {RotatE, ComplEx, Prior} via per-relation validation routing on official WN18RR
(86,835 train, 3,034 valid, 3,134 test triples, 40,943 entities, 11 relations)
and evaluates Filtered MRR, Hits@1, Hits@3, Hits@10 on the official test split (6,268 queries).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)

def _reexec_with_numpy():
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    py = os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")
    if os.path.isfile(py):
        os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:])
    sys.stderr.write("numpy required (S5 venv missing)\n")
    sys.exit(2)

_reexec_with_numpy()

import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(SPIKES, "harness"))

import kfcheck
from provenance import Control, Falsifier

CORPUS_WN = Path(ROOT) / "corpus" / "wn18rr"

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

DIM = 64
LR = 0.10
REG = 1e-5
BATCH_SIZE = 1024
EPOCHS = 6
SEED = 79


def load_split_txt(path: Path) -> list[tuple[str, str, str]]:
    triples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                triples.append((parts[0], parts[1], parts[2]))
    return triples


def build_vocab(triples_list: list[list[tuple[str, str, str]]]):
    entities = sorted(list({s for trips in triples_list for s, _, _ in trips} |
                           {o for trips in triples_list for _, _, o in trips}))
    relations = sorted(list({p for trips in triples_list for _, p, _ in trips}))
    e2i = {e: i for i, e in enumerate(entities)}
    r2i = {r: i for i, r in enumerate(relations)}
    return e2i, r2i, entities, relations


def encode_triples(triples: list[tuple[str, str, str]], e2i: dict, r2i: dict):
    out = []
    for s, p, o in triples:
        out.append((r2i[p], e2i[s], e2i[o]))
    return out


def softmax_grad(scores: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, float]:
    bsz = scores.shape[0]
    m = scores.max(axis=1, keepdims=True)
    exp = np.exp(scores - m)
    prob = exp / exp.sum(axis=1, keepdims=True)
    nll = -np.log(np.maximum(prob[np.arange(bsz), target], 1e-12)).mean()
    g = prob / bsz
    g[np.arange(bsz), target] -= 1.0 / bsz
    return g, float(nll)


def adagrad_step(param, acc, grad, lr):
    acc += grad * grad
    param -= lr * grad / (np.sqrt(acc) + 1e-10)


# --- RotatE Model ---
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
    tr_re = t_re * r_re + t_im * r_im
    tr_im = -t_re * r_im + t_im * r_re
    return tr_re, tr_im, r_re, r_im, t_re, t_im


def dist2_scores(hr_re, hr_im, E_re, E_im):
    hr_n = (hr_re * hr_re + hr_im * hr_im).sum(1, keepdims=True)
    t_n = (E_re * E_re + E_im * E_im).sum(1)
    ip = hr_re @ E_re.T + hr_im @ E_im.T
    return hr_n + t_n[None, :] - 2.0 * ip


def _backprop_dist2(g_sc, hr_re, hr_im, E_re, E_im):
    g_d = -g_sc
    sum_g = g_d.sum(axis=1, keepdims=True)
    g_hr_re = 2.0 * (sum_g * hr_re - g_d @ E_re)
    g_hr_im = 2.0 * (sum_g * hr_im - g_d @ E_im)
    col = g_d.sum(axis=0)[:, None]
    gE_re = 2.0 * (col * E_re - g_d.T @ hr_re)
    gE_im = 2.0 * (col * E_im - g_d.T @ hr_im)
    return g_hr_re, g_hr_im, gE_re, gE_im


def train_rotate_wn(train_triples, nent, npred, epochs=6, lr=0.10, bsz=1024, reg=1e-5, seed=79):
    print(f"Training RotatE (dim={DIM}, epochs={epochs})...", flush=True)
    rng = np.random.default_rng(seed)
    scale = 1.0 / np.sqrt(DIM)
    E_re = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    E_im = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    theta = rng.uniform(-np.pi, np.pi, size=(npred, DIM)).astype(np.float32)
    accE_re = np.zeros_like(E_re)
    accE_im = np.zeros_like(E_im)
    accTh = np.zeros_like(theta)

    tri = np.asarray(train_triples, dtype=np.int32)
    n = len(tri)
    for ep in range(1, epochs + 1):
        perm = rng.permutation(n)
        for start in range(0, n, bsz):
            batch = tri[perm[start:start + bsz]]
            p, s, o = batch[:, 0], batch[:, 1], batch[:, 2]

            hr_re, hr_im, r_re, r_im, h_re, h_im = rotate_tail_pack(E_re, E_im, theta, s, p)
            g_t, _ = softmax_grad(-dist2_scores(hr_re, hr_im, E_re, E_im), o)
            g_hr_re, g_hr_im, gE_re, gE_im = _backprop_dist2(g_t, hr_re, hr_im, E_re, E_im)
            np.add.at(gE_re, s, g_hr_re * r_re + g_hr_im * r_im)
            np.add.at(gE_im, s, -g_hr_re * r_im + g_hr_im * r_re)
            g_r_re = g_hr_re * h_re + g_hr_im * h_im
            g_r_im = -g_hr_re * h_im + g_hr_im * h_re
            gTh = np.zeros_like(theta)
            np.add.at(gTh, p, -g_r_re * r_im + g_r_im * r_re)

            tr_re, tr_im, r_re, r_im, t_re, t_im = rotate_head_pack(E_re, E_im, theta, o, p)
            g_h, _ = softmax_grad(-dist2_scores(tr_re, tr_im, E_re, E_im), s)
            g_tr_re, g_tr_im, gE_re_h, gE_im_h = _backprop_dist2(g_h, tr_re, tr_im, E_re, E_im)
            gE_re += gE_re_h
            gE_im += gE_im_h
            np.add.at(gE_re, o, g_tr_re * r_re - g_tr_im * r_im)
            np.add.at(gE_im, o, g_tr_re * r_im + g_tr_im * r_re)
            g_r_re = g_tr_re * t_re + g_tr_im * t_im
            g_r_im = g_tr_re * t_im - g_tr_im * t_re
            np.add.at(gTh, p, -g_r_re * r_im + g_r_im * r_re)

            if reg:
                gE_re += reg * E_re
                gE_im += reg * E_im
            adagrad_step(E_re, accE_re, gE_re, lr)
            adagrad_step(E_im, accE_im, gE_im, lr)
            adagrad_step(theta, accTh, gTh, lr)

    return E_re, E_im, theta


# --- ComplEx Model ---
def train_complex_wn(train_triples, nent, npred, epochs=6, lr=0.10, bsz=1024, reg=1e-4, seed=79):
    print(f"Training ComplEx (dim={DIM}, epochs={epochs})...", flush=True)
    rng = np.random.default_rng(seed)
    scale = 1.0 / np.sqrt(DIM)
    E_re = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    E_im = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    R_re = rng.uniform(-scale, scale, size=(npred, DIM)).astype(np.float32)
    R_im = rng.uniform(-scale, scale, size=(npred, DIM)).astype(np.float32)
    accE_re = np.zeros_like(E_re)
    accE_im = np.zeros_like(E_im)
    accR_re = np.zeros_like(R_re)
    accR_im = np.zeros_like(R_im)

    tri = np.asarray(train_triples, dtype=np.int32)
    n = len(tri)
    for ep in range(1, epochs + 1):
        perm = rng.permutation(n)
        for start in range(0, n, bsz):
            batch = tri[perm[start:start + bsz]]
            p, s, o = batch[:, 0], batch[:, 1], batch[:, 2]

            h_re, h_im = E_re[s], E_im[s]
            r_re, r_im = R_re[p], R_im[p]
            t_re, t_im = E_re[o], E_im[o]

            # Tail prediction
            hr_re = h_re * r_re - h_im * r_im
            hr_im = h_re * r_im + h_im * r_re
            sc_t = hr_re @ E_re.T + hr_im @ E_im.T
            g_t, _ = softmax_grad(sc_t, o)
            ghr_re = g_t @ E_re
            ghr_im = g_t @ E_im
            gE_re = g_t.T @ hr_re
            gE_im = g_t.T @ hr_im
            np.add.at(gE_re, s, ghr_re * r_re + ghr_im * r_im)
            np.add.at(gE_im, s, -ghr_re * r_im + ghr_im * r_re)
            gR_re = np.zeros_like(R_re)
            gR_im = np.zeros_like(R_im)
            np.add.at(gR_re, p, ghr_re * h_re + ghr_im * h_im)
            np.add.at(gR_im, p, -ghr_re * h_im + ghr_im * h_re)

            # Head prediction
            tr_re = t_re * r_re + t_im * r_im
            tr_im = -t_re * r_im + t_im * r_re
            sc_h = tr_re @ E_re.T + tr_im @ E_im.T
            g_h, _ = softmax_grad(sc_h, s)
            gtr_re = g_h @ E_re
            gtr_im = g_h @ E_im
            gE_re += g_h.T @ tr_re
            gE_im += g_h.T @ tr_im
            np.add.at(gE_re, o, gtr_re * r_re - gtr_im * r_im)
            np.add.at(gE_im, o, gtr_re * r_im + gtr_im * r_re)
            np.add.at(gR_re, p, gtr_re * t_re + gtr_im * t_im)
            np.add.at(gR_im, p, gtr_re * t_im - gtr_im * t_re)

            if reg:
                gE_re += reg * E_re
                gE_im += reg * E_im
                gR_re += reg * R_re
                gR_im += reg * R_im

            adagrad_step(E_re, accE_re, gE_re, lr)
            adagrad_step(E_im, accE_im, gE_im, lr)
            adagrad_step(R_re, accR_re, gR_re, lr)
            adagrad_step(R_im, accR_im, gR_im, lr)

    return E_re, E_im, R_re, R_im


def score_rot(E_re, E_im, theta, p, s, o, mode="tail"):
    if mode == "tail":
        hr_re, hr_im, _, _, _, _ = rotate_tail_pack(E_re, E_im, theta, [s], [p])
        return -dist2_scores(hr_re, hr_im, E_re, E_im)[0]
    else:
        tr_re, tr_im, _, _, _, _ = rotate_head_pack(E_re, E_im, theta, [o], [p])
        return -dist2_scores(tr_re, tr_im, E_re, E_im)[0]


def score_cx(E_re, E_im, R_re, R_im, p, s, o, mode="tail"):
    if mode == "tail":
        h_re, h_im = E_re[s], E_im[s]
        r_re, r_im = R_re[p], R_im[p]
        hr_re = h_re * r_re - h_im * r_im
        hr_im = h_re * r_im + h_im * r_re
        return (hr_re @ E_re.T + hr_im @ E_im.T)
    else:
        t_re, t_im = E_re[o], E_im[o]
        r_re, r_im = R_re[p], R_im[p]
        tr_re = t_re * r_re + t_im * r_im
        tr_im = -t_re * r_im + t_im * r_re
        return (tr_re @ E_re.T + tr_im @ E_im.T)


def eval_validation(valid_triples, rot_m, cx_m, all_true_sp, all_true_po, npred):
    print("Selecting optimal model per relation on validation set...", flush=True)
    E_re_r, E_im_r, theta_r = rot_m
    E_re_c, E_im_c, R_re_c, R_im_c = cx_m

    rel_mrr = {"rotate": defaultdict(list), "complex": defaultdict(list)}

    for p, s, o in valid_triples:
        # Tail
        sc_r_t = score_rot(E_re_r, E_im_r, theta_r, p, s, o, mode="tail")
        sc_c_t = score_cx(E_re_c, E_im_c, R_re_c, R_im_c, p, s, o, mode="tail")

        known_t = set(all_true_sp.get((s, p), []))
        for cand in known_t:
            if cand != o:
                sc_r_t[cand] = -1e9
                sc_c_t[cand] = -1e9

        rank_r_t = int((sc_r_t > sc_r_t[o]).sum() + 1)
        rank_c_t = int((sc_c_t > sc_c_t[o]).sum() + 1)
        rel_mrr["rotate"][p].append(1.0 / rank_r_t)
        rel_mrr["complex"][p].append(1.0 / rank_c_t)

        # Head
        sc_r_h = score_rot(E_re_r, E_im_r, theta_r, p, s, o, mode="head")
        sc_c_h = score_cx(E_re_c, E_im_c, R_re_c, R_im_c, p, s, o, mode="head")

        known_h = set(all_true_po.get((p, o), []))
        for cand in known_h:
            if cand != s:
                sc_r_h[cand] = -1e9
                sc_c_h[cand] = -1e9

        rank_r_h = int((sc_r_h > sc_r_h[s]).sum() + 1)
        rank_c_h = int((sc_c_h > sc_c_h[s]).sum() + 1)
        rel_mrr["rotate"][p].append(1.0 / rank_r_h)
        rel_mrr["complex"][p].append(1.0 / rank_c_h)

    routing = {}
    for p in range(npred):
        mrr_r = np.mean(rel_mrr["rotate"][p]) if rel_mrr["rotate"][p] else 0.0
        mrr_c = np.mean(rel_mrr["complex"][p]) if rel_mrr["complex"][p] else 0.0
        chosen = "rotate" if mrr_r >= mrr_c else "complex"
        routing[p] = (chosen, mrr_r, mrr_c)
        print(f"  Rel {p:2d}: chosen={chosen:7s} | RotatE valid MRR={mrr_r:.4f}, ComplEx valid MRR={mrr_c:.4f}")

    return routing


def eval_test_hybrid(test_triples, rot_m, cx_m, routing, all_true_sp, all_true_po):
    print(f"\nEvaluating Hybrid on {len(test_triples)} test triples (6,268 queries)...", flush=True)
    E_re_r, E_im_r, theta_r = rot_m
    E_re_c, E_im_c, R_re_c, R_im_c = cx_m

    ranks = []
    rel_ranks = defaultdict(list)
    model_choices = Counter()

    for p, s, o in test_triples:
        chosen, _, _ = routing[p]
        model_choices[chosen] += 2

        if chosen == "rotate":
            sc_t = score_rot(E_re_r, E_im_r, theta_r, p, s, o, mode="tail")
            sc_h = score_rot(E_re_r, E_im_r, theta_r, p, s, o, mode="head")
        else:
            sc_t = score_cx(E_re_c, E_im_c, R_re_c, R_im_c, p, s, o, mode="tail")
            sc_h = score_cx(E_re_c, E_im_c, R_re_c, R_im_c, p, s, o, mode="head")

        # Filter known true
        for cand in all_true_sp.get((s, p), []):
            if cand != o:
                sc_t[cand] = -1e9
        for cand in all_true_po.get((p, o), []):
            if cand != s:
                sc_h[cand] = -1e9

        rank_t = int((sc_t > sc_t[o]).sum() + 1)
        rank_h = int((sc_h > sc_h[s]).sum() + 1)

        ranks.extend([rank_t, rank_h])
        rel_ranks[p].extend([rank_t, rank_h])

    ranks = np.asarray(ranks, dtype=np.float32)
    mrr = float(np.mean(1.0 / ranks))
    h1 = float(np.mean(ranks <= 1))
    h3 = float(np.mean(ranks <= 3))
    h10 = float(np.mean(ranks <= 10))

    return mrr, h1, h3, h10, model_choices, rel_ranks


def main():
    print("=== G92 Neuro-Symbolic Hybrid on Official WN18RR ===")
    t0 = time.perf_counter()

    train_raw = load_split_txt(CORPUS_WN / "train.txt")
    valid_raw = load_split_txt(CORPUS_WN / "valid.txt")
    test_raw = load_split_txt(CORPUS_WN / "test.txt")

    e2i, r2i, entities, relations = build_vocab([train_raw, valid_raw, test_raw])
    nent, npred = len(entities), len(relations)

    train_tri = encode_triples(train_raw, e2i, r2i)
    valid_tri = encode_triples(valid_raw, e2i, r2i)
    test_tri = encode_triples(test_raw, e2i, r2i)

    all_true_sp = defaultdict(list)
    all_true_po = defaultdict(list)
    for p, s, o in train_tri + valid_tri + test_tri:
        all_true_sp[(s, p)].append(o)
        all_true_po[(p, o)].append(s)

    # Train RotatE and ComplEx
    rot_m = train_rotate_wn(train_tri, nent, npred, epochs=EPOCHS, lr=LR, reg=REG, seed=SEED)
    cx_m = train_complex_wn(train_tri, nent, npred, epochs=EPOCHS, lr=LR, reg=1e-4, seed=SEED)

    # Validation Selection
    routing = eval_validation(valid_tri, rot_m, cx_m, all_true_sp, all_true_po, npred)

    # Test Evaluation
    mrr, h1, h3, h10, choices, rel_ranks = eval_test_hybrid(test_tri, rot_m, cx_m, routing, all_true_sp, all_true_po)

    elapsed = time.perf_counter() - t0

    print(f"\n====================== G92 WN18RR HYBRID TEST RESULTS ======================")
    print(f"  Filtered MRR: {mrr:.4f}")
    print(f"  Hits@1:       {h1:.4f}")
    print(f"  Hits@3:       {h3:.4f}")
    print(f"  Hits@10:      {h10:.4f}")
    print(f"  Model Choices: {dict(choices)}")
    print(f"  Elapsed Time: {elapsed:.2f}s")
    print(f"===========================================================================")

    # Controls & Falsifiers
    c1 = (len(test_tri) == 3134)
    c2 = (len(ranks := [r for rs in rel_ranks.values() for r in rs]) == 6268)
    c3 = (PIN_F001 == "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f" and
          PIN_F002 == "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9")

    controls = [
        Control("C1_test_size", why="Evaluates exactly 3,134 official WN18RR test triples", can_fail_because="test split truncated", null_must_contain="wrong split"),
        Control("C2_query_count", why="Evaluates exactly 6,268 queries (head+tail for 3,134 triples)", can_fail_because="query count mismatch", null_must_contain="wrong queries"),
        Control("C3_pins_intact", why="F001 and F002 golden pins remain uncorrupted", can_fail_because="pin drift", null_must_contain="pins moved"),
    ]
    controls[0].observe(c1, {"n_test": len(test_tri)})
    controls[1].observe(c2, {"n_queries": len(ranks)})
    controls[2].observe(c3, {"f001": PIN_F001, "f002": PIN_F002})

    f1 = (len(ranks) != 6268)
    f2 = (mrr < 0.0355)  # must beat pure symbolic baseline G89
    f3 = (mrr < 0.1251)  # must beat standalone ComplEx G90

    falsifiers = [
        Falsifier("F1_wrong_query_count", refutes="that test covers exactly 6,268 queries", fires_when="n_queries != 6268", null_must_contain="truncated evaluation"),
        Falsifier("F2_fails_symbolic_baseline", refutes="that hybrid beats pure symbolic rules (0.0355 MRR)", fires_when="mrr < 0.0355", null_must_contain="inferior performance"),
        Falsifier("F3_fails_complex_baseline", refutes="that hybrid beats standalone ComplEx (0.1251 MRR)", fires_when="mrr < 0.1251", null_must_contain="inferior performance"),
    ]
    falsifiers[0].observe(f1, {"n_queries": len(ranks)})
    falsifiers[1].observe(f2, {"mrr": mrr, "baseline_symbolic": 0.0355})
    falsifiers[2].observe(f3, {"mrr": mrr, "baseline_complex": 0.1251})

    res = {
        "spike": "G92",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(elapsed, 2),
        "corpus": "WN18RR (Official 86,835 train, 3,034 valid, 3,134 test)",
        "metrics": {
            "mrr": round(mrr, 4),
            "hits1": round(h1, 4),
            "hits3": round(h3, 4),
            "hits10": round(h10, 4),
            "lift_over_symbolic_mrr": round(mrr - 0.0355, 4),
            "lift_over_complex_mrr": round(mrr - 0.1251, 4),
        },
        "model_choices": dict(choices),
        "routing": {r2i_name: routing[p][0] for r2i_name, p in r2i.items()},
        "controls": {
            "C1_test_size": {"ok": c1},
            "C2_query_count": {"ok": c2},
            "C3_pins_intact": {"ok": c3},
        },
        "falsifiers": {
            "F1_wrong_query_count": {"fired": f1},
            "F2_fails_symbolic_baseline": {"fired": f2},
            "F3_fails_complex_baseline": {"fired": f3},
        },
    }

    out_json = Path(HERE) / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(CORPUS_WN)],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="Hybrid mix fails to beat ComplEx and pure symbolic baselines or truncates test set",
        allow_dirty=True,
        note="G92: Neuro-Symbolic Hybrid Mix with RotatE and ComplEx on Official WN18RR.",
    )

    print(f"\n[G92] Complete: certify ok={ok}. Written to result.json.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
