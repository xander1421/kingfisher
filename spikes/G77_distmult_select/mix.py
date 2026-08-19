#!/usr/bin/env python3
"""G77 — add G76 DistMult to the G75 valid-select set.

G75 F 0.3034 is {ComplEx, G51, prior}. G76 DistMult 0.2852 beat ComplEx
0.2755 as a single model. This row asks whether putting DistMult in the
per-(p, dir) set beats 0.3034.

Loads G75/G76 saved embeddings. Does not retrain. No additive stack.

F1: mix − 0.3034 < +0.005.
F2: mix < 0.3034.
F3: on keys valid picked DistMult (n≥20), median TEST DistMult−ComplEx ≤ 0.

  spikes/S5_hdc_prototype/.venv/bin/python spikes/G77_distmult_select/select.py
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
sys.path.insert(0, os.path.join(SPIKES, "G75_complex_gate"))
sys.path.insert(0, os.path.join(SPIKES, "G76_distmult_min10"))

import bayesian_lift as G51  # noqa: E402
import complex as G72  # noqa: E402
import distmult as G76  # noqa: E402
import hybrid as G75  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS = G59.CORPUS
RULES_CACHE = os.path.join(HERE, "rules_cache.json")
G75_RULES = os.path.join(SPIKES, "G75_complex_gate", "rules_cache.json")
CX_EMB = os.path.join(SPIKES, "G75_complex_gate", "complex_emb.npz")
DM_EMB = os.path.join(SPIKES, "G76_distmult_min10", "distmult_emb.npz")
KEYS = ("distmult", "complex", "g51", "prior")
G75_KEYS = ("complex", "g51", "prior")
MIN_N = 20
G75_REF = 0.3034
CX_REF = 0.2755
DM_REF = 0.2852
G51_REF = 0.2585
PRIOR_REF = 0.2334
GATED_REF = 0.2679
BAR = 0.005
NENT_OFFICIAL = 14541
NPRED_OFFICIAL = 237
TEST_N = 20466
G75_SHA = "17509ac9df1e"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_or_mine_rules(out_adj, pair_tr, byp, rev):
    for path, label in ((RULES_CACHE, "local"), (G75_RULES, "G75")):
        if os.path.isfile(path):
            raw = json.loads(open(path, encoding="utf-8").read())
            if path != RULES_CACHE:
                os.makedirs(HERE, exist_ok=True)
                shutil.copy2(path, RULES_CACHE)
            print(f"loaded {len(raw)} rules ({label})", flush=True)
            return raw
    raise RuntimeError("rules_cache missing; G75/G72 should have mined it")


def attach_named(rows, queries, ranks, dirs, name):
    if len(rows) != 2 * len(queries) or len(ranks) != len(rows):
        raise RuntimeError(f"{name} length drift {len(rows)} vs {len(ranks)}")
    if not (dirs[0] == "tail" and dirs[1] == "head"):
        ranks, dirs = G75.unbatch_complex_ranks(ranks, dirs, len(queries))
    for i, r in enumerate(rows):
        if r["direction"] != dirs[i]:
            raise RuntimeError(f"{name} dir drift at {i}: {r['direction']} vs {dirs[i]}")
        r["ranks"][name] = float(ranks[i])
    return rows


def freeze_dir_select(valid_rows, keys, default):
    buckets = defaultdict(lambda: {k: [] for k in keys})
    for r in valid_rows:
        key = (int(r["p"]), r["direction"])
        for k in keys:
            buckets[key][k].append(r["ranks"][k])
    choice = {}
    counts = defaultdict(int)
    n_small = 0
    for key, v in buckets.items():
        n = len(v[default])
        if n < MIN_N:
            choice[key] = default
            n_small += 1
        else:
            scores = {k: sum(1.0 / x for x in v[k]) / n for k in keys}
            choice[key] = max(scores, key=scores.get)
        counts[choice[key]] += 1
    payload = {
        "min_n": MIN_N,
        "n_keys": len(choice),
        "n_small_default": n_small,
        "default_small_n": default,
        "counts": dict(counts),
        "choice": {f"{p}:{d}": v for (p, d), v in sorted(choice.items())},
        "keys": list(keys),
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in ("min_n", "choice")}, sort_keys=True).encode()
    ).hexdigest()
    return payload, choice


def apply_dir(rows, choice, default):
    return G59.metrics([
        r["ranks"][choice.get((int(r["p"]), r["direction"]), default)]
        for r in rows
    ])


def slice_apply(rows, choice, default):
    out = {}
    for d in ("tail", "head"):
        out[d] = G59.metrics([
            r["ranks"][choice.get((int(r["p"]), r["direction"]), default)]
            for r in rows if r["direction"] == d
        ])
    return out


def picked_delta(test_rows, choice, picked, a, b):
    buckets = defaultdict(lambda: {a: [], b: []})
    for r in test_rows:
        key = (int(r["p"]), r["direction"])
        if choice.get(key) != picked:
            continue
        buckets[key][a].append(r["ranks"][a])
        buckets[key][b].append(r["ranks"][b])
    deltas = []
    for key, v in buckets.items():
        n = len(v[a])
        if n == 0:
            continue
        ma = sum(1.0 / x for x in v[a]) / n
        mb = sum(1.0 / x for x in v[b]) / n
        deltas.append(ma - mb)
    if not deltas:
        return {"n_keys": 0, "median_delta": None, "frac_le_0": None, "n_lose": 0}
    s = sorted(deltas)
    mid = len(s) // 2
    med = s[mid] if len(s) % 2 else 0.5 * (s[mid - 1] + s[mid])
    n_lose = int(sum(1 for d in deltas if d <= 0.0))
    return {
        "n_keys": len(deltas),
        "median_delta": round(med, 4),
        "frac_le_0": round(n_lose / len(deltas), 4),
        "n_lose": n_lose,
    }


def main():
    t0 = time.time()
    if not os.path.isfile(CX_EMB) or not os.path.isfile(DM_EMB):
        raise RuntimeError(f"need saved embeddings {CX_EMB} and {DM_EMB}")
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
    leak = G51.count_same_pair_leak(train, test)
    all_tri = train + valid + test
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)

    zc = np.load(CX_EMB)
    E_re, E_im, R_re, R_im = zc["E_re"], zc["E_im"], zc["R_re"], zc["R_im"]
    zd = np.load(DM_EMB)
    E, R = zd["E"], zd["R"]
    print(
        f"loaded ComplEx {sha256_file(CX_EMB)[:12]} ep={int(zc['best_epoch'])} "
        f"DistMult {sha256_file(DM_EMB)[:12]} ep={int(zd['best_epoch'])}",
        flush=True,
    )

    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    raw_rules = load_or_mine_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in raw_rules:
        rules_by_head[r["head"]].append((tuple(r["body"]), r["conf"]))
    idx = G59.slim_index(train)

    print("scoring VALID ...", flush=True)
    valid_rows = G59.score_split(
        valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    v_cx, v_cd, _ = G72.rank_complex(valid, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_cx, v_cd, "complex")
    v_dm, v_dd, _ = G76.rank_distmult(valid, E, R, eval_sp, eval_po)
    attach_named(valid_rows, valid, v_dm, v_dd, "distmult")

    four_mask, four_choice = freeze_dir_select(valid_rows, KEYS, default="distmult")
    three_mask, three_choice = freeze_dir_select(valid_rows, G75_KEYS, default="complex")
    pred_gate, use_g51 = G59.freeze_gate(valid_rows)
    print(
        f"4-way sha={four_mask['sha256'][:12]} {four_mask['counts']} "
        f"small={four_mask['n_small_default']}",
        flush=True,
    )
    print(
        f"3-way sha={three_mask['sha256'][:12]} {three_mask['counts']}",
        flush=True,
    )

    print("scoring TEST (once, after masks hashed) ...", flush=True)
    test_rows = G59.score_split(
        test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    t_cx, t_cd, _ = G72.rank_complex(test, E_re, E_im, R_re, R_im, eval_sp, eval_po)
    attach_named(test_rows, test, t_cx, t_cd, "complex")
    t_dm, t_dd, _ = G76.rank_distmult(test, E, R, eval_sp, eval_po)
    attach_named(test_rows, test, t_dm, t_dd, "distmult")

    arms = {
        "A_prior": G59.arm_from_rows(test_rows, "prior"),
        "B_g51": G59.arm_from_rows(test_rows, "g51"),
        "C_complex": G59.arm_from_rows(test_rows, "complex"),
        "D_distmult": G59.arm_from_rows(test_rows, "distmult"),
        "E_g59_gate": G59.apply_gate(test_rows, use_g51),
        "F_g75_three_way": apply_dir(test_rows, three_choice, "complex"),
        "G_four_way": apply_dir(test_rows, four_choice, "distmult"),
    }
    slices = {
        "distmult": G59.slice_direction(test_rows, "distmult"),
        "complex": G59.slice_direction(test_rows, "complex"),
        "four_way": slice_apply(test_rows, four_choice, "distmult"),
    }
    f3_obs = picked_delta(test_rows, four_choice, "distmult", "distmult", "complex")

    hy = arms["G_four_way"]["mrr"]
    g75 = arms["F_g75_three_way"]["mrr"]
    cx = arms["C_complex"]["mrr"]
    dm = arms["D_distmult"]["mrr"]
    g51 = arms["B_g51"]["mrr"]
    prior = arms["A_prior"]["mrr"]
    gated = arms["E_g59_gate"]["mrr"]
    delta = round(hy - g75, 4)
    f1_fired = (hy - G75_REF) < BAR
    f2_fired = hy < G75_REF
    f3_fired = f3_obs["median_delta"] is None or f3_obs["median_delta"] <= 0.0
    quoted_new_high = (hy - G75_REF) >= BAR

    used = {k: any(four_choice.get((int(r["p"]), r["direction"])) == k for r in test_rows)
            for k in KEYS}

    c1_ok = len(test) == TEST_N
    c2_ok = leak == 0
    c3_ok = nent == NENT_OFFICIAL and npred == NPRED_OFFICIAL
    c4_ok = abs(g75 - G75_REF) <= 0.0005
    c5_ok = abs(dm - DM_REF) <= 0.0005
    c6_ok = abs(cx - CX_REF) <= 0.002
    c7_ok = abs(g51 - G51_REF) <= 0.0005 and abs(prior - PRIOR_REF) <= 0.0005
    c8_ok = abs(gated - GATED_REF) <= 0.0005
    lit = "unavailable"

    res = {
        "spike": "G77",
        "split": "official FB15k-237 train/valid/test",
        "field_order": "p,s,o",
        "headline_arm": "G_four_way",
        "headline_is_test_grid": False,
        "quoted_new_high": quoted_new_high,
        "literature_compare": lit,
        "protocol": "filtered_all_entity",
        "scoreboard_note": (
            "G59 0.2679 stays observed+gate. G75 0.3034 stays the 3-way "
            "all-entity mix unless G beats it by +0.005."
        ),
        "select_keys": list(KEYS),
        "no_additive_stack": True,
        "complex_emb_sha256": sha256_file(CX_EMB),
        "distmult_emb_sha256": sha256_file(DM_EMB),
        "valid_select_four": four_mask,
        "valid_select_three": {
            "sha256": three_mask["sha256"],
            "counts": three_mask["counts"],
        },
        "replace_used": used,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "npred": npred,
        "nent": nent,
        "file_sha256": hashes,
        "same_pair_leak": {"n": leak, "n_test": len(test)},
        "arms": arms,
        "slices": slices,
        "four_minus_g75": delta,
        "distmult_picked_vs_complex": f3_obs,
        "controls": {
            "C1_test_n": {"n": len(test), "ok": c1_ok},
            "C2_leak": {"leak": leak, "ok": c2_ok},
            "C3_nent": {"nent": nent, "npred": npred, "ok": c3_ok},
            "C4_g75_identity": {"three_way": g75, "ref": G75_REF, "ok": c4_ok},
            "C5_distmult_identity": {"mrr": dm, "ref": DM_REF, "ok": c5_ok},
            "C6_complex_identity": {"mrr": cx, "ref": CX_REF, "ok": c6_ok},
            "C7_g51_prior": {"g51": g51, "prior": prior, "ok": c7_ok},
            "C8_g59_gate": {"gated": gated, "ref": GATED_REF, "ok": c8_ok},
            "C9_literature": {"value": lit, "ok": True},
        },
        "falsifiers": {
            "F1_not_a_new_high": {
                "hybrid_mrr": hy, "g75_ref": G75_REF, "delta": delta,
                "bar": BAR, "fired": f1_fired,
                "fires_when": "four-way - 0.3034 < 0.005",
            },
            "F2_selection_hurts": {
                "hybrid_mrr": hy, "g75_ref": G75_REF, "fired": f2_fired,
                "fires_when": "four-way < 0.3034",
            },
            "F3_distmult_picks_do_not_transfer": {
                **f3_obs, "fired": f3_fired,
                "fires_when": "median(TEST DistMult − ComplEx | valid DistMult) <= 0",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)
    out_json = os.path.join(HERE, "select.json")
    os.makedirs(HERE, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G77 DistMult in the G75 set ===", flush=True)
    print(f"  prior     {prior:.4f}", flush=True)
    print(f"  G51       {g51:.4f}", flush=True)
    print(f"  ComplEx   {cx:.4f}", flush=True)
    print(f"  DistMult  {dm:.4f}", flush=True)
    print(f"  G59 gate  {gated:.4f}", flush=True)
    print(f"  G75 3-way {g75:.4f}  {three_mask['counts']}", flush=True)
    print(f"  4-way G   {hy:.4f}  {four_mask['counts']}  Δ vs G75 {delta:+.4f}", flush=True)
    print(f"  F1={f1_fired} F2={f2_fired} F3={f3_fired} quoted_new_high={quoted_new_high}", flush=True)
    print(f"  F3 {f3_obs}", flush=True)
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_test_n", why="20466", can_fail_because="wrong test",
                null_must_contain="n!=20466"),
        Control("C2_leak", why="leak 0", can_fail_because="wrong split",
                null_must_contain="leak>0"),
        Control("C3_nent", why="14541/237", can_fail_because="pack_ids train only",
                null_must_contain="nent!=14541"),
        Control("C4_g75_identity", why="3-way reproduces 0.3034",
                can_fail_because="unbatch/score drift",
                null_must_contain="3-way!=0.3034"),
        Control("C5_distmult_identity", why="G76 0.2852",
                can_fail_because="wrong embeddings",
                null_must_contain="distmult!=0.2852"),
        Control("C6_complex_identity", why="G72 0.2755",
                can_fail_because="wrong embeddings",
                null_must_contain="complex!=0.2755"),
        Control("C7_g51_prior", why="0.2585/0.2334",
                can_fail_because="score_split drift",
                null_must_contain="prior/G51 drift"),
        Control("C8_g59_gate", why="0.2679",
                can_fail_because="freeze_gate drift",
                null_must_contain="gated!=0.2679"),
        Control("C9_literature", why="no excerpt",
                can_fail_because="invented literature MRR",
                null_must_contain="a literature MRR"),
    ]
    ckeys = [
        "C1_test_n", "C2_leak", "C3_nent", "C4_g75_identity",
        "C5_distmult_identity", "C6_complex_identity", "C7_g51_prior",
        "C8_g59_gate", "C9_literature",
    ]
    oks = [c1_ok, c2_ok, c3_ok, c4_ok, c5_ok, c6_ok, c7_ok, c8_ok, True]
    for ctl, k, okv in zip(controls, ckeys, oks):
        ctl.observe(okv, res["controls"][k])

    falsifiers = [
        Falsifier("F1_not_a_new_high",
                  refutes="that adding DistMult is a +0.005 high over G75",
                  fires_when="four-way - 0.3034 < 0.005",
                  null_must_contain="a signed delta vs 0.3034"),
        Falsifier("F2_selection_hurts",
                  refutes="that the 4-way is at least G75",
                  fires_when="four-way < 0.3034",
                  null_must_contain="4-way on either side of 0.3034"),
        Falsifier("F3_distmult_picks_do_not_transfer",
                  refutes="that DistMult-chosen keys stay DistMult-better than ComplEx",
                  fires_when="median(TEST DistMult − ComplEx | valid DistMult) <= 0",
                  null_must_contain="a signed per-key test delta"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_not_a_new_high"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_selection_hurts"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_distmult_picks_do_not_transfer"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[CORPUS,
              os.path.join(SPIKES, "G75_complex_gate"),
              os.path.join(SPIKES, "G76_distmult_min10")],
        artifacts=[os.path.join(HERE, "mix.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("select_json", json.dumps(res, sort_keys=True))],
        falsifier="4-way does not beat G75 0.3034 by +0.005, OR loses, OR DistMult picks fail to transfer",
        allow_dirty=True,
        note="G77: {DistMult, ComplEx, G51, prior} valid-select. No literature MRR.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
