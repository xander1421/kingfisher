#!/usr/bin/env python3
"""G76 — DistMult all-entity with G72's training protocol (min_epoch=10).

G66 DistMult 0.2195 lost to the official prior 0.2334 because valid
early-stop picked epoch 1. That is not a DistMult verdict. This row
uses G72's protocol: dim=64, unfiltered 1-N softmax, AdaGrad, no
eligible checkpoint before epoch 10, patience 8 on valid.

Score: <h, r, t> = sum_k h_k r_k t_k. Only the bilinear form changes
relative to G72 ComplEx.

F1: DistMult − G51 < +0.005.
F2: DistMult < 0.2334 (still undertrained / broken).
F3: DistMult < ComplEx 0.2755.

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G76_distmult_min10/distmult.py
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
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
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
EMB_PATH = os.path.join(HERE, "distmult_emb.npz")
HIST_PATH = os.path.join(HERE, "train_hist.json")

SEED = 76
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
G51_BAR = 0.005
NENT_OFFICIAL = 14541
NPRED_OFFICIAL = 237
TEST_N = 20466
G66_REF = 0.2195


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def distmult_tail_scores(E, R, s, p):
    hr = E[s] * R[p]
    return hr @ E.T, hr


def distmult_head_scores(E, R, o, p):
    tr = E[o] * R[p]
    return tr @ E.T, tr


def _assert_score_identity():
    rng = np.random.default_rng(0)
    d = 8
    h, r, t = rng.normal(size=d), rng.normal(size=d), rng.normal(size=d)
    direct = float(np.sum(h * r * t))
    E = np.stack([t, h]).astype(np.float32)
    R = r[None, :].astype(np.float32)
    sc_t, _ = distmult_tail_scores(E, R, np.array([1]), np.array([0]))
    sc_h, _ = distmult_head_scores(E, R, np.array([0]), np.array([0]))
    if abs(float(sc_t[0, 0]) - direct) > 1e-4 or abs(float(sc_h[0, 1]) - direct) > 1e-4:
        raise RuntimeError(
            f"DistMult score identity failed: direct={direct} "
            f"tail={sc_t[0, 0]} head={sc_h[0, 1]}"
        )


def train_distmult(train, nent, npred, rng, valid_q=None, eval_sp=None, eval_po=None):
    """Unfiltered 1-N DistMult. Selection only among epochs >= MIN_EPOCH."""
    scale = 1.0 / np.sqrt(DIM)
    E = rng.uniform(-scale, scale, size=(nent, DIM)).astype(np.float32)
    R = rng.uniform(-scale, scale, size=(npred, DIM)).astype(np.float32)
    accE = np.zeros_like(E)
    accR = np.zeros_like(R)
    tri = np.asarray(train, dtype=np.int32)
    n = len(tri)
    hist = []
    best = {"mrr": -1.0, "epoch": None, "E": None, "R": None}
    stale = 0

    for ep in range(1, MAX_EPOCHS + 1):
        t0 = time.time()
        perm = rng.permutation(n)
        loss_acc = 0.0
        n_batches = 0
        for start in range(0, n, BATCH):
            batch = tri[perm[start:start + BATCH]]
            p, s, o = batch[:, 0], batch[:, 1], batch[:, 2]

            sc_t, hr = distmult_tail_scores(E, R, s, p)
            g_t, nll_t = G72.softmax_grad(sc_t, o)
            g_hr = g_t @ E
            gE = g_t.T @ hr
            gR = np.zeros_like(R)
            np.add.at(gE, s, g_hr * R[p])
            np.add.at(gR, p, g_hr * E[s])

            sc_h, tr = distmult_head_scores(E, R, o, p)
            g_h, nll_h = G72.softmax_grad(sc_h, s)
            g_tr = g_h @ E
            gE += g_h.T @ tr
            np.add.at(gE, o, g_tr * R[p])
            np.add.at(gR, p, g_tr * E[o])

            if REG:
                gE += REG * E
                gR += REG * R
            G72.adagrad_step(E, accE, gE, LR)
            G72.adagrad_step(R, accR, gR, LR)
            loss_acc += nll_t + nll_h
            n_batches += 1
            if ep == 1 and n_batches == 1:
                print(
                    f"  first-batch nll={nll_t + nll_h:.4f} "
                    f"(uniform~{2.0 * np.log(nent):.4f}) ||E||={np.linalg.norm(E):.3f}",
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
            vr, _, _ = rank_distmult(valid_q, E, R, eval_sp, eval_po)
            vm = G72.metrics(vr)
            row["valid_sample_mrr"] = vm["mrr"]
            if ep >= MIN_EPOCH and vm["mrr"] > best["mrr"]:
                best = {"mrr": vm["mrr"], "epoch": ep, "E": E.copy(), "R": R.copy()}
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

    if best["E"] is None:
        best = {"mrr": None, "epoch": max(MIN_EPOCH, ep), "E": E.copy(), "R": R.copy()}
    return best["E"], best["R"], hist, best["epoch"], best["mrr"]


def rank_distmult(queries, E, R, true_sp, true_po, batch=256):
    ranks, directions = [], []
    nent = E.shape[0]
    q = list(queries)
    for start in range(0, len(q), batch):
        chunk = q[start:start + batch]
        p = np.array([t[0] for t in chunk], dtype=np.int32)
        s = np.array([t[1] for t in chunk], dtype=np.int32)
        o = np.array([t[2] for t in chunk], dtype=np.int32)
        sc_t, _ = distmult_tail_scores(E, R, s, p)
        G72._rank_from_scores(
            sc_t, o, chunk, true_sp,
            lambda pi, si, oi: (si, pi), lambda si, oi: oi,
            "tail", ranks, directions,
        )
        sc_h, _ = distmult_head_scores(E, R, o, p)
        G72._rank_from_scores(
            sc_h, s, chunk, true_po,
            lambda pi, si, oi: (pi, oi), lambda si, oi: si,
            "head", ranks, directions,
        )
    assert len(ranks) == 2 * len(q)
    return ranks, directions, nent


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
        E, R = z["E"], z["R"]
        best_ep = int(z["best_epoch"])
        best_valid = float(z["best_valid_sample_mrr"])
        hist = json.loads(open(HIST_PATH, encoding="utf-8").read()) if os.path.isfile(HIST_PATH) else []
        print(
            f"loaded DistMult embeddings {EMB_PATH} "
            f"best_epoch={best_ep} valid_sample_mrr={best_valid}",
            flush=True,
        )
        if best_ep < MIN_EPOCH:
            raise RuntimeError(f"cached best_epoch={best_ep} < min_epoch={MIN_EPOCH}")
        return E, R, hist, best_ep, best_valid, True
    print(
        f"training DistMult (unfiltered 1-N, AdaGrad, dim={DIM}, "
        f"min_epoch={MIN_EPOCH}, patience={PATIENCE}) ...",
        flush=True,
    )
    t0 = time.time()
    E, R, hist, best_ep, best_valid = train_distmult(
        train, nent, npred, rng,
        valid_q=valid_sample, eval_sp=eval_sp, eval_po=eval_po,
    )
    np.savez(
        EMB_PATH, E=E, R=R,
        best_epoch=np.int32(best_ep),
        best_valid_sample_mrr=np.float64(best_valid if best_valid is not None else -1.0),
    )
    with open(HIST_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    print(
        f"trained DistMult in {time.time() - t0:.1f}s "
        f"best_epoch={best_ep} valid_sample_mrr={best_valid}",
        flush=True,
    )
    if best_ep is None or best_ep < MIN_EPOCH:
        raise RuntimeError(f"selection violated min_epoch={MIN_EPOCH}: {best_ep}")
    return E, R, hist, best_ep, best_valid, False


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
    order_ok, order_obs = G72.field_order_ok(train, npred, nent)
    leak = G51.count_same_pair_leak(train, test)
    print(f"field_order_ok={order_ok} leak={leak}", flush=True)

    all_tri = train + valid + test
    true_sp_set, true_po_set = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)

    rng = np.random.default_rng(SEED)
    valid_idx = rng.choice(len(valid), size=min(VALID_SAMPLE, len(valid)), replace=False)
    valid_sample = [valid[int(i)] for i in valid_idx]

    E, R, hist, best_ep, best_valid, used_cache = train_or_load(
        train, nent, npred, rng, valid_sample, eval_sp, eval_po,
    )

    print("ranking DistMult ALL entities (filtered) on official TEST ...", flush=True)
    t_ev = time.time()
    dm_ranks, dm_dirs, _ = rank_distmult(test, E, R, eval_sp, eval_po)
    dm_arm = G72.metrics(dm_ranks)
    dm_slices = G72.slice_metrics(dm_ranks, dm_dirs)
    print(
        f"DistMult MRR={dm_arm['mrr']:.4f} H@10={dm_arm['hits10']:.4f} "
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

    delta_g51 = round(dm_arm["mrr"] - g51_arm["mrr"], 4)
    delta_cx = round(dm_arm["mrr"] - COMPLEX_REF, 4)
    f1_fired = (dm_arm["mrr"] - g51_arm["mrr"]) < G51_BAR
    f2_fired = dm_arm["mrr"] < OFFICIAL_PRIOR
    f3_fired = dm_arm["mrr"] < COMPLEX_REF

    c1_ok = len(test) == TEST_N
    c2_ok = leak == 0
    c3_ok = nent == NENT_OFFICIAL
    c4_ok = order_ok and npred == NPRED_OFFICIAL
    c5_ok = best_ep is not None and best_ep >= MIN_EPOCH
    c6_ok = abs(prior_arm["mrr"] - OFFICIAL_PRIOR) <= 0.0005
    lit = "unavailable"

    res = {
        "spike": "G76",
        "split": "official FB15k-237 train/valid/test",
        "source_git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
        "source_commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
        "field_order": "p,s,o",
        "headline_arm": "C_distmult_min10",
        "headline_is_test_grid": False,
        "literature_compare": lit,
        "literature_note": "do not quote Bordes/RotatE/AMIE MRR; no excerpt under corpus/",
        "candidate_set": "all 14541 entities, filtered train+valid+test",
        "protocol": "filtered_all_entity",
        "scoreboard_note": (
            "G66 DistMult 0.2195 was epoch-1; this row is the same bilinear "
            "form under G72's min_epoch=10 protocol. G72 ComplEx 0.2755 and "
            "G59 gated 0.2679 stay."
        ),
        "model": "DistMult",
        "score_fn": "sum_k h_k * r_k * t_k",
        "train_objective": "unfiltered softmax 1-N (both directions), AdaGrad",
        "g66_was": {"mrr": G66_REF, "best_epoch": 1, "note": "undertrained; not this row"},
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
            "note": "valid only; epochs < 10 ineligible (G66 trap)",
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
            "C_distmult_min10": dm_arm,
        },
        "slices": {
            "prior": G72.slice_metrics(prior_ranks, pg_dirs),
            "g51": G72.slice_metrics(g51_ranks, pg_dirs),
            "distmult": dm_slices,
        },
        "distmult_minus_g51": delta_g51,
        "distmult_minus_complex_ref": delta_cx,
        "controls": {
            "C1_test_n": {"n": len(test), "expected": TEST_N, "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_nent": {"nent": nent, "expected": NENT_OFFICIAL, "ok": c3_ok},
            "C4_field_order": {"ok": c4_ok, **order_obs},
            "C5_min_epoch": {"best_epoch": best_ep, "min_epoch": MIN_EPOCH, "ok": c5_ok},
            "C6_prior_identity": {
                "prior": prior_arm["mrr"], "ref": OFFICIAL_PRIOR, "ok": c6_ok,
            },
            "C7_literature_compare": {"value": lit, "ok": lit == "unavailable"},
        },
        "falsifiers": {
            "F1_distmult_does_not_beat_g51": {
                "distmult_mrr": dm_arm["mrr"],
                "g51_mrr": g51_arm["mrr"],
                "delta": delta_g51,
                "bar": G51_BAR,
                "fired": f1_fired,
                "fires_when": "distmult - g51 < 0.005",
            },
            "F2_distmult_below_official_prior": {
                "distmult_mrr": dm_arm["mrr"],
                "prior_bar": OFFICIAL_PRIOR,
                "prior_observed": prior_arm["mrr"],
                "fired": f2_fired,
                "fires_when": "distmult < 0.2334",
            },
            "F3_distmult_below_complex": {
                "distmult_mrr": dm_arm["mrr"],
                "complex_ref": COMPLEX_REF,
                "delta": delta_cx,
                "fired": f3_fired,
                "fires_when": "distmult < 0.2755",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out_json = os.path.join(HERE, "distmult.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

        f.write("\n")

    # ---- G94 ADDITION (not in the G76 original) -------------------------------
    # Persist PER-QUERY ranks so the ensemble selector and its F3 null can be
    # built without retraining. The original dumps summary metrics only, so a
    # mix would have to recompute every arm — and recomputing scoring code is
    # how two "identical" pipelines drift.
    import numpy as _np
    _np.savez_compressed(
        os.path.join(HERE, "ranks_pd.npz"),
        dm=_np.asarray(dm_ranks, dtype=_np.int32),
        dm_dirs=_np.asarray(dm_dirs),
        prior=_np.asarray(prior_ranks, dtype=_np.int32),
        g51=_np.asarray(g51_ranks, dtype=_np.int32),
        pg_dirs=_np.asarray(pg_dirs),
        test_p=_np.asarray([t[0] for t in test], dtype=_np.int32))
    print(f"[G94] wrote ranks_pd.npz  dm={len(dm_ranks)} prior={len(prior_ranks)} "
          f"g51={len(g51_ranks)}", flush=True)

    print("\n=== G76 DistMult min_epoch=10 ===", flush=True)
    print(f"  prior    {prior_arm['mrr']:.4f}", flush=True)
    print(f"  G51      {g51_arm['mrr']:.4f}", flush=True)
    print(
        f"  DistMult {dm_arm['mrr']:.4f} H@10={dm_arm['hits10']:.4f} "
        f"best_epoch={best_ep} (G66 was {G66_REF} epoch-1)",
        flush=True,
    )
    print(f"  Δ vs G51 {delta_g51:+.4f}  Δ vs ComplEx {delta_cx:+.4f}", flush=True)
    print(f"  F1={f1_fired} F2={f2_fired} F3={f3_fired}", flush=True)
    print(
        f"  tail={dm_slices['tail']['mrr']:.4f} head={dm_slices['head']['mrr']:.4f}",
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
        Control("C7_literature_compare", why="no RotatE excerpt",
                can_fail_because="invented literature MRR",
                null_must_contain="a literature MRR"),
    ]
    keys = [
        "C1_test_n", "C2_leak", "C3_nent", "C4_field_order",
        "C5_min_epoch", "C6_prior_identity", "C7_literature_compare",
    ]
    oks = [c1_ok, c2_ok, c3_ok, c4_ok, c5_ok, c6_ok, True]
    for ctl, key, okv in zip(controls, keys, oks):
        ctl.observe(okv, res["controls"][key])

    falsifiers = [
        Falsifier(
            "F1_distmult_does_not_beat_g51",
            refutes="that DistMult min_epoch=10 is a +0.005 lift over G51",
            fires_when="distmult - g51 < 0.005",
            null_must_contain="a signed delta vs G51, including a loss",
        ),
        Falsifier(
            "F2_distmult_below_official_prior",
            refutes="that the latent arm is a working DistMult",
            fires_when="distmult < 0.2334",
            null_must_contain="an MRR on either side of the official prior 0.2334",
        ),
        Falsifier(
            "F3_distmult_below_complex",
            refutes="that DistMult under this protocol matches ComplEx 0.2755",
            fires_when="distmult < 0.2755",
            null_must_contain="DistMult on either side of 0.2755",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_distmult_does_not_beat_g51"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_distmult_below_official_prior"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_distmult_below_complex"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G72_complex_all_entity")],
        artifacts=[os.path.join(HERE, "distmult.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("distmult_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "DistMult min_epoch=10 does not beat G51 by +0.005, "
            "OR DistMult < 0.2334, OR DistMult < ComplEx 0.2755"
        ),
        allow_dirty=True,
        note=(
            "G76: DistMult filtered all-entity on official FB15k-237 "
            "with G72 min_epoch=10. G66 0.2195 was epoch-1. No literature MRR."
        ),
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
