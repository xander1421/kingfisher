#!/usr/bin/env python3
"""G75 — valid-select {ComplEx, G51, prior} per (predicate, direction).

G72 ComplEx all-entity 0.2755 beat G51 support−∞ 0.2585. G59 gated 0.2679
is G51-or-prior, still support−∞. This row asks whether a frozen valid
choice of which *scorer* to use per (p, dir) beats ComplEx alone.

No additive residual. No global override. Train is G72 (seed 72,
min_epoch 10) so the ComplEx column is instrument-identical, not a new
fit. Selector uses FULL official valid; early-stop still uses G72's
2500-sample (A26: valid for selection, test scored once).

F1: hybrid − 0.2755 < +0.005 (not a new latent high).
F2: hybrid < 0.2755 (selection hurts vs ComplEx).
F3: on keys valid picked G51 (n≥20), TEST G51 ≤ TEST ComplEx.

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G75_complex_gate/hybrid.py
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
EMB_PATH = os.path.join(HERE, "complex_emb.npz")
HIST_PATH = os.path.join(HERE, "train_hist.json")
KEYS = ("complex", "g51", "prior")
MIN_N = 20
COMPLEX_REF = 0.2755
G51_REF = 0.2585
PRIOR_REF = 0.2334
GATED_REF = 0.2679
BAR = 0.005
NENT_OFFICIAL = 14541
NPRED_OFFICIAL = 237
TEST_N = 20466
COMPLEX_TOL = 0.002


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def unbatch_complex_ranks(cx_ranks, cx_dirs, n_queries, batch=256):
    """G72.rank_complex emits [chunk tails..., chunk heads...] not per-query.

    score_split is interleaved (tail, head) per query. Reorder ComplEx ranks
    to that layout. batch must match rank_complex's default (256).
    """
    if len(cx_ranks) != 2 * n_queries:
        raise RuntimeError(
            f"ComplEx rank length {len(cx_ranks)} != 2*{n_queries}"
        )
    out_r = [None] * (2 * n_queries)
    out_d = [None] * (2 * n_queries)
    i = 0
    for start in range(0, n_queries, batch):
        chunk_n = min(batch, n_queries - start)
        for j in range(chunk_n):
            q = start + j
            out_r[2 * q] = cx_ranks[i]
            out_d[2 * q] = cx_dirs[i]
            i += 1
        for j in range(chunk_n):
            q = start + j
            out_r[2 * q + 1] = cx_ranks[i]
            out_d[2 * q + 1] = cx_dirs[i]
            i += 1
    if i != len(cx_ranks):
        raise RuntimeError(f"unbatch consumed {i} of {len(cx_ranks)}")
    return out_r, out_d


def attach_complex(rows, queries, cx_ranks, cx_dirs):
    if len(rows) != 2 * len(queries) or len(cx_ranks) != len(rows):
        raise RuntimeError(
            f"row/rank length drift rows={len(rows)} "
            f"queries={len(queries)} cx={len(cx_ranks)}"
        )
    if not (cx_dirs[0] == "tail" and cx_dirs[1] == "head"):
        cx_ranks, cx_dirs = unbatch_complex_ranks(cx_ranks, cx_dirs, len(queries))
    for i, r in enumerate(rows):
        if r["direction"] != cx_dirs[i]:
            raise RuntimeError(
                f"direction drift at {i}: row={r['direction']} cx={cx_dirs[i]}"
            )
        if cx_ranks[i] is None:
            raise RuntimeError(f"missing ComplEx rank at {i}")
        r["ranks"]["complex"] = float(cx_ranks[i])
    return rows


def freeze_dir_select(valid_rows):
    buckets = defaultdict(lambda: {k: [] for k in KEYS})
    for r in valid_rows:
        key = (int(r["p"]), r["direction"])
        for k in KEYS:
            buckets[key][k].append(r["ranks"][k])
    choice = {}
    counts = defaultdict(int)
    n_small = 0
    for key, v in buckets.items():
        n = len(v["complex"])
        if n < MIN_N:
            choice[key] = "complex"
            n_small += 1
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in KEYS}
            choice[key] = max(scores, key=scores.get)
        counts[choice[key]] += 1
    payload = {
        "min_n": MIN_N,
        "n_keys": len(choice),
        "n_small_default_complex": n_small,
        "counts": dict(counts),
        "choice": {f"{p}:{d}": v for (p, d), v in sorted(choice.items())},
        "keys": list(KEYS),
        "default_small_n": "complex",
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice


def freeze_pred_select(valid_rows):
    buckets = defaultdict(lambda: {k: [] for k in KEYS})
    for r in valid_rows:
        for k in KEYS:
            buckets[int(r["p"])][k].append(r["ranks"][k])
    choice = {}
    counts = defaultdict(int)
    n_small = 0
    for p, v in buckets.items():
        n = len(v["complex"])
        if n < MIN_N:
            choice[p] = "complex"
            n_small += 1
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in KEYS}
            choice[p] = max(scores, key=scores.get)
        counts[choice[p]] += 1
    payload = {
        "min_n": MIN_N,
        "n_predicates": len(choice),
        "n_small_default_complex": n_small,
        "counts": dict(counts),
        "choice": {str(p): v for p, v in sorted(choice.items())},
        "keys": list(KEYS),
        "default_small_n": "complex",
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice


def apply_dir(rows, choice):
    return G59.metrics([
        r["ranks"][choice.get((int(r["p"]), r["direction"]), "complex")]
        for r in rows
    ])


def apply_pred(rows, choice):
    return G59.metrics([
        r["ranks"][choice.get(int(r["p"]), "complex")]
        for r in rows
    ])


def slice_apply_dir(rows, choice):
    out = {}
    for d in ("tail", "head"):
        out[d] = G59.metrics([
            r["ranks"][choice.get((int(r["p"]), r["direction"]), "complex")]
            for r in rows if r["direction"] == d
        ])
    return out


def key_test_delta(test_rows, choice):
    """Per (p,dir) TEST MRR(g51) − MRR(complex) for keys valid picked g51."""
    buckets = defaultdict(lambda: {"g51": [], "complex": []})
    picked = []
    for r in test_rows:
        key = (int(r["p"]), r["direction"])
        if choice.get(key) != "g51":
            continue
        buckets[key]["g51"].append(r["ranks"]["g51"])
        buckets[key]["complex"].append(r["ranks"]["complex"])
    deltas = []
    for key, v in buckets.items():
        n = len(v["g51"])
        if n == 0:
            continue
        mg = sum(1.0 / x for x in v["g51"]) / n
        mc = sum(1.0 / x for x in v["complex"]) / n
        deltas.append(mg - mc)
        picked.append({
            "p": key[0],
            "direction": key[1],
            "n_test": n,
            "g51": round(mg, 4),
            "complex": round(mc, 4),
            "delta": round(mg - mc, 4),
        })
    picked.sort(key=lambda r: r["delta"])
    if not deltas:
        med = None
        frac_lose = None
    else:
        s = sorted(deltas)
        mid = len(s) // 2
        med = s[mid] if len(s) % 2 else 0.5 * (s[mid - 1] + s[mid])
        frac_lose = sum(1 for d in deltas if d <= 0.0) / len(deltas)
    return {
        "n_keys_valid_picked_g51_with_test": len(deltas),
        "median_delta": None if med is None else round(med, 4),
        "frac_g51_le_complex": None if frac_lose is None else round(frac_lose, 4),
        "n_g51_loses_on_test": 0 if not deltas else int(sum(1 for d in deltas if d <= 0.0)),
        "worst": picked[:8],
        "best": list(reversed(picked[-8:])),
    }


def train_or_load_complex(train, nent, npred, rng, valid_sample, eval_sp, eval_po):
    if os.path.isfile(EMB_PATH):
        z = np.load(EMB_PATH)
        E_re = z["E_re"]
        E_im = z["E_im"]
        R_re = z["R_re"]
        R_im = z["R_im"]
        best_ep = int(z["best_epoch"])
        best_valid = float(z["best_valid_sample_mrr"])
        hist = json.loads(open(HIST_PATH, encoding="utf-8").read()) if os.path.isfile(HIST_PATH) else []
        print(
            f"loaded ComplEx embeddings {EMB_PATH} "
            f"best_epoch={best_ep} valid_sample_mrr={best_valid} "
            f"sha256={sha256_file(EMB_PATH)[:12]}",
            flush=True,
        )
        if best_ep < G72.MIN_EPOCH:
            raise RuntimeError(f"cached best_epoch={best_ep} < min_epoch={G72.MIN_EPOCH}")
        return (E_re, E_im, R_re, R_im), hist, best_ep, best_valid, True
    print(
        f"training ComplEx (G72 protocol seed={G72.SEED} dim={G72.DIM} "
        f"min_epoch={G72.MIN_EPOCH}) ...",
        flush=True,
    )
    t0 = time.time()
    emb, hist, best_ep, best_valid = G72.train_complex(
        train, nent, npred, rng,
        valid_q=valid_sample, eval_sp=eval_sp, eval_po=eval_po,
    )
    E_re, E_im, R_re, R_im = emb
    np.savez(
        EMB_PATH,
        E_re=E_re, E_im=E_im, R_re=R_re, R_im=R_im,
        best_epoch=np.int32(best_ep),
        best_valid_sample_mrr=np.float64(best_valid if best_valid is not None else -1.0),
    )
    with open(HIST_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    print(
        f"trained ComplEx in {time.time() - t0:.1f}s "
        f"best_epoch={best_ep} valid_sample_mrr={best_valid} "
        f"saved {EMB_PATH}",
        flush=True,
    )
    if best_ep is None or best_ep < G72.MIN_EPOCH:
        raise RuntimeError(f"selection violated min_epoch={G72.MIN_EPOCH}: {best_ep}")
    return emb, hist, best_ep, best_valid, False


def main():
    t0 = time.time()
    G72._assert_score_identity()
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

    rng = np.random.default_rng(G72.SEED)
    valid_idx = rng.choice(len(valid), size=min(G72.VALID_SAMPLE, len(valid)), replace=False)
    valid_sample = [valid[int(i)] for i in valid_idx]

    (E_re, E_im, R_re, R_im), hist, best_ep, best_valid, used_cache = train_or_load_complex(
        train, nent, npred, rng, valid_sample, eval_sp, eval_po,
    )

    print("scoring prior+G51 on FULL VALID (selector) ...", flush=True)
    t_g = time.time()
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    raw_rules = load_or_mine_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in raw_rules:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))
    idx = G59.slim_index(train)
    valid_rows = G59.score_split(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp_set, true_po_set, idx)
    print(f"VALID G51 {len(valid_rows)} in {time.time() - t_g:.1f}s", flush=True)

    print("ranking ComplEx on FULL VALID (selector) ...", flush=True)
    t_cv = time.time()
    v_cx, v_dirs, _ = G72.rank_complex(valid, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    attach_complex(valid_rows, valid, v_cx, v_dirs)
    print(f"VALID ComplEx in {time.time() - t_cv:.1f}s", flush=True)

    dir_mask, dir_choice = freeze_dir_select(valid_rows)
    pred_mask, pred_choice = freeze_pred_select(valid_rows)
    pred_gate, use_g51 = G59.freeze_gate(valid_rows)
    print(
        f"dir-select sha={dir_mask['sha256'][:12]} counts={dir_mask['counts']} "
        f"small={dir_mask['n_small_default_complex']}",
        flush=True,
    )
    print(
        f"pred-select sha={pred_mask['sha256'][:12]} counts={pred_mask['counts']}",
        flush=True,
    )
    print(
        f"G59 pred-gate sha={pred_gate['sha256'][:12]} "
        f"on={pred_gate['n_g51_on']} off={pred_gate['n_g51_off']}",
        flush=True,
    )

    print("scoring TEST (once, after masks hashed) ...", flush=True)
    t_te = time.time()
    test_rows = G59.score_split(
        test, nent, rules_by_head, out_adj, in_adj, true_sp_set, true_po_set, idx)
    t_cx, t_dirs, _ = G72.rank_complex(test, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    attach_complex(test_rows, test, t_cx, t_dirs)
    print(f"TEST scored in {time.time() - t_te:.1f}s", flush=True)

    used_complex = any(r["ranks"].get("complex") is not None for r in test_rows)
    used_g51_pick = any(dir_choice.get((int(r["p"]), r["direction"])) == "g51" for r in test_rows)
    used_prior_pick = any(dir_choice.get((int(r["p"]), r["direction"])) == "prior" for r in test_rows)

    arms = {
        "A_prior_support_neginf": G59.arm_from_rows(test_rows, "prior"),
        "B_g51_support_neginf": G59.arm_from_rows(test_rows, "g51"),
        "C_complex_all_entity": G59.arm_from_rows(test_rows, "complex"),
        "D_g59_pred_gate": G59.apply_gate(test_rows, use_g51),
        "E_pred_select": apply_pred(test_rows, pred_choice),
        "F_dir_select": apply_dir(test_rows, dir_choice),
    }
    slices = {
        "prior": G59.slice_direction(test_rows, "prior"),
        "g51": G59.slice_direction(test_rows, "g51"),
        "complex": G59.slice_direction(test_rows, "complex"),
        "dir_select": slice_apply_dir(test_rows, dir_choice),
    }
    f3_obs = key_test_delta(test_rows, dir_choice)

    cx = arms["C_complex_all_entity"]["mrr"]
    hy = arms["F_dir_select"]["mrr"]
    g51 = arms["B_g51_support_neginf"]["mrr"]
    prior = arms["A_prior_support_neginf"]["mrr"]
    gated = arms["D_g59_pred_gate"]["mrr"]
    delta = round(hy - cx, 4)
    f1_fired = (hy - cx) < BAR
    f2_fired = hy < cx
    f3_fired = (
        f3_obs["median_delta"] is None or f3_obs["median_delta"] <= 0.0
    )
    quoted_new_high = (hy - COMPLEX_REF) >= BAR

    c1_ok = len(test) == TEST_N
    c2_ok = leak == 0
    c3_ok = nent == NENT_OFFICIAL and npred == NPRED_OFFICIAL
    c4_ok = abs(cx - COMPLEX_REF) <= COMPLEX_TOL
    c5_ok = abs(g51 - G51_REF) <= 0.0005 and abs(prior - PRIOR_REF) <= 0.0005
    c6_ok = abs(gated - GATED_REF) <= 0.0005
    c7_ok = bool(dir_mask.get("sha256")) and used_complex
    lit = "unavailable"

    res = {
        "spike": "G75",
        "split": "official FB15k-237 train/valid/test",
        "source_git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
        "source_commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
        "field_order": "p,s,o",
        "headline_arm": "F_dir_select",
        "headline_is_test_grid": False,
        "quoted_new_high": quoted_new_high,
        "literature_compare": lit,
        "literature_note": "do not quote Bordes/RotatE/AMIE MRR; no excerpt under corpus/",
        "candidate_set": "all 14541 entities, filtered train+valid+test",
        "protocol": "filtered_all_entity",
        "scoreboard_note": (
            "pair-disjoint G54 0.2313 and official G59 0.2679 stay the "
            "observed+gate columns; G72 0.2755 stays the ComplEx all-entity "
            "column unless F beats it by +0.005"
        ),
        "select_keys": list(KEYS),
        "no_additive_stack": True,
        "no_global_override": True,
        "seed": G72.SEED,
        "dim": G72.DIM,
        "min_epoch": G72.MIN_EPOCH,
        "used_cached_embeddings": used_cache,
        "embedding_sha256": sha256_file(EMB_PATH) if os.path.isfile(EMB_PATH) else None,
        "valid_select_dir": dir_mask,
        "valid_select_pred": pred_mask,
        "g59_pred_gate": {
            "sha256": pred_gate["sha256"],
            "n_g51_on": pred_gate["n_g51_on"],
            "n_g51_off": pred_gate["n_g51_off"],
        },
        "replace_used_complex": used_complex,
        "replace_used_g51": used_g51_pick,
        "replace_used_prior": used_prior_pick,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "npred": npred,
        "nent": nent,
        "n_rules_2hop": len(raw_rules),
        "file_sha256": hashes,
        "same_pair_leak": {"n": leak, "n_test": len(test)},
        "field_order_obs": order_obs,
        "train_hist": hist,
        "valid_select": {
            "best_epoch": best_ep,
            "best_valid_sample_mrr": best_valid,
            "min_epoch": G72.MIN_EPOCH,
            "n_sample": G72.VALID_SAMPLE,
            "note": "early-stop sample is G72; selector uses full valid",
        },
        "arms": arms,
        "slices": slices,
        "hybrid_minus_complex": delta,
        "g51_picked_test_transfer": f3_obs,
        "controls": {
            "C1_test_n": {"n": len(test), "expected": TEST_N, "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_nent": {"nent": nent, "npred": npred, "ok": c3_ok},
            "C4_complex_identity": {
                "complex_mrr": cx,
                "expected": COMPLEX_REF,
                "tol": COMPLEX_TOL,
                "ok": c4_ok,
            },
            "C5_g51_prior_identity": {
                "g51": g51, "g51_ref": G51_REF,
                "prior": prior, "prior_ref": PRIOR_REF,
                "ok": c5_ok,
            },
            "C6_g59_gate": {"gated": gated, "ref": GATED_REF, "ok": c6_ok},
            "C7_mask_hashed_before_test": {
                "sha256": dir_mask["sha256"],
                "used_complex": used_complex,
                "ok": c7_ok,
            },
            "C8_literature_compare": {"value": lit, "ok": lit == "unavailable"},
        },
        "falsifiers": {
            "F1_not_a_new_latent_high": {
                "hybrid_mrr": hy,
                "complex_mrr": cx,
                "delta": delta,
                "bar": BAR,
                "fired": f1_fired,
                "fires_when": "hybrid - complex < 0.005",
                "description": "Fires if dir-select does not beat ComplEx by >= +0.005",
            },
            "F2_selection_hurts": {
                "hybrid_mrr": hy,
                "complex_mrr": cx,
                "fired": f2_fired,
                "fires_when": "hybrid < complex",
                "description": "Fires if picking G51/prior on some keys loses to ComplEx-only",
            },
            "F3_g51_picks_do_not_transfer": {
                "median_delta": f3_obs["median_delta"],
                "frac_g51_le_complex": f3_obs["frac_g51_le_complex"],
                "n_keys": f3_obs["n_keys_valid_picked_g51_with_test"],
                "fired": f3_fired,
                "fires_when": "median(TEST G51 − TEST ComplEx | valid picked G51) <= 0",
                "description": "Fires if G51-chosen keys do not stay G51-better on test",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out_json = os.path.join(HERE, "hybrid.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G75 ComplEx × G51 valid-select ===", flush=True)
    print(f"  prior     {prior:.4f}", flush=True)
    print(f"  G51       {g51:.4f}", flush=True)
    print(f"  ComplEx   {cx:.4f}  (G72 {COMPLEX_REF})", flush=True)
    print(f"  G59 gate  {gated:.4f}", flush=True)
    print(f"  pred-sel  {arms['E_pred_select']['mrr']:.4f}  {pred_mask['counts']}", flush=True)
    print(f"  dir-sel F {hy:.4f}  {dir_mask['counts']}  Δ vs ComplEx {delta:+.4f}", flush=True)
    print(f"  F1={f1_fired} F2={f2_fired} F3={f3_fired} quoted_new_high={quoted_new_high}", flush=True)
    print(f"  F3 median_delta={f3_obs['median_delta']} "
          f"frac_lose={f3_obs['frac_g51_le_complex']}", flush=True)
    print(f"  head F={slices['dir_select']['head']['mrr']:.4f} "
          f"cx={slices['complex']['head']['mrr']:.4f}", flush=True)
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="official test is 20466",
                can_fail_because="wrong test.txt",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="official test same-pair leak with train is 0",
                can_fail_because="wrong split",
                null_must_contain="leak>0"),
        Control("C3_nent", why="14541 entities / 237 relations",
                can_fail_because="pack_ids over train only",
                null_must_contain="nent!=14541"),
        Control("C4_complex_identity", why="G72 ComplEx 0.2755 ± 0.002",
                can_fail_because="different seed / min_epoch / dim",
                null_must_contain="complex far from 0.2755"),
        Control("C5_g51_prior_identity", why="G72/G59 prior 0.2334 G51 0.2585",
                can_fail_because="score_split drift",
                null_must_contain="prior/G51 not reproduced"),
        Control("C6_g59_gate", why="pred-gate 0.2679",
                can_fail_because="freeze_gate drift",
                null_must_contain="gated!=0.2679"),
        Control("C7_mask_hashed_before_test", why="dir-select hashed after valid, before test aggregates",
                can_fail_because="test-grid choice",
                null_must_contain="missing sha256"),
        Control("C8_literature_compare", why="no RotatE excerpt under corpus/",
                can_fail_because="invented literature MRR",
                null_must_contain="a literature MRR"),
    ]
    c_ok = [c1_ok, c2_ok, c3_ok, c4_ok, c5_ok, c6_ok, c7_ok, True]
    c_payload = [
        res["controls"]["C1_test_n"],
        res["controls"]["C2_leak"],
        res["controls"]["C3_nent"],
        res["controls"]["C4_complex_identity"],
        res["controls"]["C5_g51_prior_identity"],
        res["controls"]["C6_g59_gate"],
        res["controls"]["C7_mask_hashed_before_test"],
        res["controls"]["C8_literature_compare"],
    ]
    for ctl, ok, payload in zip(controls, c_ok, c_payload):
        ctl.observe(ok, payload)

    falsifiers = [
        Falsifier(
            "F1_not_a_new_latent_high",
            refutes="that mixing G51/prior into ComplEx is a +0.005 latent high",
            fires_when="hybrid - complex < 0.005",
            null_must_contain="a signed delta vs ComplEx, including a loss",
        ),
        Falsifier(
            "F2_selection_hurts",
            refutes="that the valid-selected mix is at least ComplEx",
            fires_when="hybrid < complex",
            null_must_contain="hybrid on either side of ComplEx",
        ),
        Falsifier(
            "F3_g51_picks_do_not_transfer",
            refutes="that G51-chosen (p,dir) keys stay G51-better on test",
            fires_when="median(TEST G51 − TEST ComplEx | valid picked G51) <= 0",
            null_must_contain="a signed per-key test delta, including G51 loss",
        ),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_not_a_new_latent_high"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_selection_hurts"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_g51_picks_do_not_transfer"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G72_complex_all_entity")],
        artifacts=[os.path.join(HERE, "hybrid.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("hybrid_json", json.dumps(res, sort_keys=True))],
        falsifier=(
            "dir-select hybrid does not beat ComplEx 0.2755 by +0.005, "
            "OR hybrid < ComplEx, OR G51-chosen keys lose on test"
        ),
        allow_dirty=True,
        note=(
            "G75: valid-select {ComplEx, G51, prior} per (p, dir) on official "
            "all-entity protocol. No stack. No literature MRR."
        ),
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
