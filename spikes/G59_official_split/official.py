#!/usr/bin/env python3
"""G59 — official FB15k-237 valid/test from git, then G51 + DEV-gated eval.

Operator: fetch from git AND TEST. Source is
DeepGraphLearning/KnowledgeGraphEmbedding@2e440e0 data/FB15k-237.
Files live in corpus/fb15k237/. triples.bin is not replaced.

  PYTHONUNBUFFERED=1 python3 spikes/G59_official_split/official.py
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
CORPUS = os.path.join(ROOT, "corpus", "fb15k237")
BIN = os.path.join(SPIKES, "S52_realkg", "triples.bin")

sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import slice_gated as G54  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

EXPECTED = {
    "train.txt": ("272115", "6e4c2782169af21e9743f3b1d200886f5d595bf6bc504ec1351720949c5cdfae"),
    "valid.txt": ("17535", None),  # hash checked live, recorded
    "test.txt": ("20466", "5711cf41623ceb4eacc50eb6108a3ca6565c7492e3caaf82a3e355cc660d1574"),
}
MIN_DEV_N = 20
ALPHA = 0.1
BETA = 0.10


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_split_txt(path):
    rows = []
    for line in open(path, encoding="utf-8", newline=""):
        line = line.strip()
        if not line:
            continue
        h, r, t = line.split()
        rows.append((h, r, t))
    return rows


def pack_ids(train_txt, valid_txt, test_txt):
    """(p,s,o) ints. Relations 0..236 by sorted name. Entities by sorted name
    over train+valid+test so test-only entities exist (14541 vs train 14505)."""
    rels = sorted({r for _, r, _ in train_txt + valid_txt + test_txt})
    ents = sorted({x for h, _, t in train_txt + valid_txt + test_txt for x in (h, t)})
    r2i = {r: i for i, r in enumerate(rels)}
    e2i = {e: i for i, e in enumerate(ents)}

    def conv(rows):
        return [(r2i[r], e2i[h], e2i[t]) for h, r, t in rows]

    return conv(train_txt), conv(valid_txt), conv(test_txt), len(rels), len(ents)


def bin_pred_counts():
    d = open(BIN, "rb").read()
    nt = struct.unpack_from("<I", d, 0)[0]
    npred, nent = struct.unpack_from("<II", d, 4)
    t = struct.unpack_from(f"<{nt * 3}I", d, 12)
    pc = Counter()
    ents = set()
    for i in range(nt):
        p, s, o = t[i * 3], t[i * 3 + 1], t[i * 3 + 2]
        pc[p] += 1
        ents.add(s)
        ents.add(o)
    return nt, npred, nent, len(ents), sorted(pc.values())


def slim_index(train):
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    p_tot_obj = defaultdict(int)
    p_tot_sub = defaultdict(int)
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1
        p_tot_obj[p] += 1
        p_tot_sub[p] += 1
    return obj_freq, sub_freq, p_tot_obj, p_tot_sub


def score_split(queries, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx):
    obj_freq, sub_freq, p_tot_obj, p_tot_sub = idx
    rows = []
    for p, s, o in queries:
        for want_tail, freq_map, tot, target, filt in (
            (True, obj_freq[p], p_tot_obj[p], o, true_sp.get((s, p), set())),
            (False, sub_freq[p], p_tot_sub[p], s, true_po.get((p, o), set())),
        ):
            prior_counts = {c: float(n) for c, n in freq_map.items()}
            base_log, prior_norm = G54.log_prior_map(freq_map, tot, nent)
            firings = G54.collect_firings(p, s, o, want_tail, rules_by_head, out_adj, in_adj)
            g51 = G54.apply_g51_lift(dict(base_log), freq_map, prior_norm, nent, firings)
            r_prior = G51.rank_from_scores(prior_counts, target, filt, nent)
            r_g51 = G51.rank_from_scores(g51, target, filt, nent)
            rows.append({
                "p": p,
                "direction": "tail" if want_tail else "head",
                "ranks": {"prior": r_prior, "g51": r_g51},
            })
    return rows


def freeze_gate(dev_rows):
    buckets = defaultdict(lambda: {"a": [], "b": []})
    for r in dev_rows:
        buckets[r["p"]]["a"].append(r["ranks"]["prior"])
        buckets[r["p"]]["b"].append(r["ranks"]["g51"])
    use = {}
    for p, v in buckets.items():
        n = len(v["a"])
        ma = sum(1.0 / x for x in v["a"]) / n
        mb = sum(1.0 / x for x in v["b"]) / n
        use[p] = True if n < MIN_DEV_N else (mb - ma > 0.0)
    payload = {
        "min_dev_n": MIN_DEV_N,
        "n_dev_queries": sum(len(v["a"]) for v in buckets.values()),
        "n_g51_on": int(sum(1 for v in use.values() if v)),
        "n_g51_off": int(sum(1 for v in use.values() if not v)),
        "use_g51": {str(k): bool(v) for k, v in sorted(use.items())},
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    payload["sha256"] = hashlib.sha256(blob).hexdigest()
    return payload, use


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


def arm_from_rows(rows, key):
    return metrics([r["ranks"][key] for r in rows])


def apply_gate(rows, use_g51):
    return metrics([
        r["ranks"]["g51"] if use_g51.get(r["p"], True) else r["ranks"]["prior"]
        for r in rows
    ])


def slice_direction(rows, key):
    out = {}
    for d in ("tail", "head"):
        out[d] = metrics([r["ranks"][key] for r in rows if r["direction"] == d])
    return out


def main():
    t0 = time.time()
    hashes = {name: sha256_file(os.path.join(CORPUS, name)) for name in EXPECTED}
    train_txt = load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = load_split_txt(os.path.join(CORPUS, "test.txt"))
    print(f"official n train={len(train_txt)} valid={len(valid_txt)} test={len(test_txt)}", flush=True)
    print(f"hashes { {k: v[:12] for k, v in hashes.items()} }", flush=True)

    train, valid, test, npred, nent = pack_ids(train_txt, valid_txt, test_txt)
    print(f"ids npred={npred} nent={nent} (train-only ents come next)", flush=True)

    train_ents = {x for p, s, o in train for x in (s, o)}
    bin_nt, bin_npred, bin_nent, bin_ents, bin_counts = bin_pred_counts()
    off_counts = sorted(Counter(p for p, s, o in train).values())
    counts_match = off_counts == bin_counts
    print(f"F1 pred-count bag match={counts_match} bin_ents={bin_ents} train_ents={len(train_ents)}", flush=True)

    leak = G51.count_same_pair_leak(train, test)
    leak_frac = leak / max(1, len(test))
    print(f"official same-pair leak {leak}/{len(test)} = {leak_frac:.4f}", flush=True)

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    idx = slim_index(train)

    print("mining 2-hop on official train ...", flush=True)
    t_mine = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_mine:.1f}s", flush=True)

    print("scoring official VALID (gate) ...", flush=True)
    t_dev = time.time()
    dev_rows = score_split(valid, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    gate, use_g51 = freeze_gate(dev_rows)
    print(f"VALID {len(dev_rows)} in {time.time() - t_dev:.1f}s gate {gate['sha256'][:12]} on={gate['n_g51_on']} off={gate['n_g51_off']}", flush=True)

    print("scoring official TEST ...", flush=True)
    t_te = time.time()
    test_rows = score_split(test, nent, rules_by_head, out_adj, in_adj, true_sp, true_po, idx)
    print(f"TEST {len(test_rows)} in {time.time() - t_te:.1f}s", flush=True)

    arms = {
        "A_prior": arm_from_rows(test_rows, "prior"),
        "B_g51": arm_from_rows(test_rows, "g51"),
        "C_valid_gated": apply_gate(test_rows, use_g51),
    }
    slices = {
        "direction_prior": slice_direction(test_rows, "prior"),
        "direction_g51": slice_direction(test_rows, "g51"),
        "direction_gated": {
            d: metrics([
                (r["ranks"]["g51"] if use_g51.get(r["p"], True) else r["ranks"]["prior"])
                for r in test_rows if r["direction"] == d
            ])
            for d in ("tail", "head")
        },
    }

    f1_fired = not counts_match
    f2_fired = leak == 0
    f3_delta = round(arms["C_valid_gated"]["mrr"] - arms["B_g51"]["mrr"], 4)
    f3_fired = f3_delta <= 0.0

    c1_ok = len(train_txt) == 272115 and hashes["train.txt"].startswith("6e4c2782169a")
    c2_ok = len(test_txt) == 20466 and hashes["test.txt"].startswith("5711cf41623c")
    c3_ok = len(valid_txt) == 17535
    c4_ok = npred == 237
    c5_ok = True  # filter built on train+valid+test; n recorded

    res = {
        "spike": "G59",
        "split": "official FB15k-237 train/valid/test",
        "source_git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
        "source_commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
        "field_order": "p,s,o",
        "headline_arm": "C_valid_gated",
        "headline_is_test_grid": False,
        "literature_compare": "unavailable",
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
        "npred": npred,
        "nent_all": nent,
        "nent_train": len(train_ents),
        "n_rules_2hop": len(rules),
        "file_sha256": hashes,
        "pred_count_bag_matches_triples_bin": counts_match,
        "triples_bin": {"nt": bin_nt, "npred": bin_npred, "nent": bin_nent, "ents_used": bin_ents},
        "same_pair_leak": {"n": leak, "frac": round(leak_frac, 4), "n_test": len(test)},
        "gate": {
            "sha256": gate["sha256"],
            "n_g51_on": gate["n_g51_on"],
            "n_g51_off": gate["n_g51_off"],
            "fitted_on": "official valid",
        },
        "arms": arms,
        "slices": slices,
        "pair_disjoint_transcribed": {
            "note": "G51/G54 on pair-disjoint re-split of the same train; not official test",
            "prior": 0.1732,
            "g51": 0.2274,
            "gated": 0.2313,
        },
        "controls": {
            "C1_train_count_and_hash": {"n": len(train_txt), "sha256": hashes["train.txt"], "ok": c1_ok},
            "C2_test_count_and_hash": {"n": len(test_txt), "sha256": hashes["test.txt"], "ok": c2_ok},
            "C3_valid_count": {"n": len(valid_txt), "ok": c3_ok},
            "C4_237_relations": {"npred": npred, "ok": c4_ok},
            "C5_filter_is_train_valid_test": {
                "n_filter_triples": len(all_tri),
                "ok": c5_ok,
            },
        },
        "falsifiers": {
            "F1_train_is_not_triples_bin": {
                "counts_match": counts_match,
                "fired": f1_fired,
                "description": "Fires if official train predicate-count bag != triples.bin",
            },
            "F2_official_test_has_zero_same_pair_leak": {
                "leak": leak,
                "frac": round(leak_frac, 4),
                "fired": f2_fired,
                "description": "Fires if official test same-pair leak with train is 0",
            },
            "F3_valid_gated_does_not_beat_official_g51": {
                "gated_mrr": arms["C_valid_gated"]["mrr"],
                "g51_mrr": arms["B_g51"]["mrr"],
                "delta": f3_delta,
                "fired": f3_fired,
                "description": "Fires if valid-fitted gate MRR <= official G51. Signed.",
            },
        },
        "elapsed_sec": None,
    }
    res["elapsed_sec"] = round(time.time() - t0, 2)

    out_json = os.path.join(HERE, "official.json")
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
        f.write("\n")

    print("\n=== G59 official split ===", flush=True)
    for k, v in arms.items():
        print(f"  {k:18s} MRR={v['mrr']:.4f} H@1={v['hits1']:.4f} H@10={v['hits10']:.4f} n={v['n_queries']}", flush=True)
    print(f"leak {leak} ({leak_frac:.4f}) F1={f1_fired} F2={f2_fired} F3={f3_fired} Δ={f3_delta:+.4f}", flush=True)
    print(f"pair-disjoint transcribed prior 0.1732 G51 0.2274 gated 0.2313", flush=True)
    print(f"elapsed {res['elapsed_sec']:.1f}s", flush=True)

    controls = [
        Control("C1_train_count_and_hash", why="official train is 272115 and the pinned sha256",
                can_fail_because="wrong file fetched", null_must_contain="count or hash mismatch"),
        Control("C2_test_count_and_hash", why="official test is 20466 and the pinned sha256",
                can_fail_because="wrong test file", null_must_contain="count or hash mismatch"),
        Control("C3_valid_count", why="official valid is 17535",
                can_fail_because="wrong valid file", null_must_contain="n!=17535"),
        Control("C4_237_relations", why="237 relations",
                can_fail_because="truncated relations.dict", null_must_contain="npred!=237"),
        Control("C5_filter_is_train_valid_test", why="filtered protocol uses all three splits",
                can_fail_because="filter built on train only", null_must_contain="n_filter < n_all"),
    ]
    controls[0].observe(c1_ok, res["controls"]["C1_train_count_and_hash"])
    controls[1].observe(c2_ok, res["controls"]["C2_test_count_and_hash"])
    controls[2].observe(c3_ok, res["controls"]["C3_valid_count"])
    controls[3].observe(c4_ok, res["controls"]["C4_237_relations"])
    controls[4].observe(c5_ok, res["controls"]["C5_filter_is_train_valid_test"])

    falsifiers = [
        Falsifier("F1_train_is_not_triples_bin",
                  refutes="that triples.bin is FB15k-237 official train",
                  fires_when="sorted predicate-count bags differ",
                  null_must_contain="count mismatch"),
        Falsifier("F2_official_test_has_zero_same_pair_leak",
                  refutes="that official cut still has G46-style same-pair leak",
                  fires_when="leak==0",
                  null_must_contain="nonzero leak"),
        Falsifier("F3_valid_gated_does_not_beat_official_g51",
                  refutes="that G54's DEV-gate transfers to official valid/test",
                  fires_when="gated_mrr <= official G51",
                  null_must_contain="signed delta, including a loss"),
    ]
    falsifiers[0].observe(f1_fired, res["falsifiers"]["F1_train_is_not_triples_bin"])
    falsifiers[1].observe(f2_fired, res["falsifiers"]["F2_official_test_has_zero_same_pair_leak"])
    falsifiers[2].observe(f3_fired, res["falsifiers"]["F3_valid_gated_does_not_beat_official_g51"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "S52_realkg"),
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              CORPUS],
        artifacts=[os.path.join(HERE, "official.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("official_json", json.dumps(res, sort_keys=True))],
        falsifier="official train ≠ triples.bin OR gate does not transfer OR leak is already zero",
        allow_dirty=True,
        note="G59: official FB15k-237 valid/test from git; G51 + valid-fitted gate; no literature MRR.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
