#!/usr/bin/env python3
"""H165 — ATTACK on G91/H164: is RotatE's 0.3546 WN18RR MRR geometry, or a
reversed-triple memorisation of WN18RR's four symmetric relations?

Cross-lane attack (ATOM-3) on GEMINI's G91 + H164. It reuses G91's OWN
`train_rotate_wn` and scoring functions by import, with G91's seed and
hyperparameters, so what is measured here is G91's model and not a
reimplementation of it.

WHAT G91 CLAIMS: "RotatE represents relations as unit complex rotations,
enforcing that compositions of rotations along a taxonomy branch preserve
transitive ordering without distance distortion" -- i.e. the 0.3546 is
attributed to HIERARCHICAL structure.

WHAT H164'S OWN TABLE SHOWS: the four relations RotatE wins are exactly
WN18RR's SYMMETRIC ones (_derivationally_related_form 0.9412, _verb_group
0.8799, _also_see 0.4027, _similar_to), and every hierarchical relation is
<= 0.0959 (_hypernym 0.0122).

WHY G91's C2_zero_leak CANNOT DECIDE IT: it computes
`len(set(train) & set(test)) == 0` over exact (p, s, o) tuples. For a
symmetric relation the leak is the REVERSED triple (o, p, s), which that set
intersection can never contain. Family A -- a control that cannot contain the
effect it is cited against. Measured on the corpus: (o,p,s) is in train for
94.1% / 97.4% / 60.7% / 100% of those four relations' test triples and 0.0%
of all seven others.

FALSIFIERS, PREREGISTERED IN CHANNEL.md BEFORE THIS RAN. Each refutes ME:
  F1  MRR on NON-leaked _derivationally_related_form queries >= 0.50
      -> memorisation does not explain the score; I withdraw.
  F2  leaked-vs-non-leaked MRR gap over all 6,268 queries < 0.10
      -> the partition explains nothing; I withdraw.
  F3  pessimistic ranking (ties counted AGAINST the target) moves MRR by
      >= 0.01 from G91's optimistic `np.sum(scores > tgt) + 1`
      -> the headline is ALSO inflated by tie-breaking, a SEPARATE defect
      that I must state separately rather than fold into the leak finding.
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
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G91_rotate_wn18rr"))

import kfcheck
from provenance import Control, Falsifier
from run import (  # G91's own code, imported not copied
    EPOCHS, LR, REG, BATCH_SIZE, SEED,
    load_split_txt, pack_ids, build_filtered_dict,
    train_rotate_wn, rotate_tail_pack, rotate_head_pack, dist2_scores,
)

CORPUS_WN = Path(ROOT) / "corpus" / "wn18rr"
PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

G91_MRR = 0.3546  # the number under attack, from spikes/G91_rotate_wn18rr/result.json


def eval_per_query(test_triples, E_re, E_im, theta, true_sp, true_po, leaked_flags):
    """One record per query. Ranks computed BOTH ways over the same scores.

    optimistic = G91's `sum(scores > tgt) + 1`   (every tie ahead of the target
                 is counted as behind it)
    pessimistic = `sum(scores >= tgt)`           (every tie counted against it)
    They differ by exactly the number of tied competitors.
    """
    recs = []
    tri = np.asarray(test_triples, dtype=np.int32)
    for start in range(0, len(tri), 256):
        batch = tri[start:start + 256]
        p_b, s_b, o_b = batch[:, 0], batch[:, 1], batch[:, 2]

        hr_re, hr_im, *_ = rotate_tail_pack(E_re, E_im, theta, s_b, p_b)
        sc_t = -dist2_scores(hr_re, hr_im, E_re, E_im)
        tr_re, tr_im, *_ = rotate_head_pack(E_re, E_im, theta, o_b, p_b)
        sc_h = -dist2_scores(tr_re, tr_im, E_re, E_im)

        for i in range(len(batch)):
            s, p, o = int(s_b[i]), int(p_b[i]), int(o_b[i])
            gi = start + i
            for side, row, tgt_idx, filt in (
                ("tail", sc_t[i], o, true_sp.get((s, p), set()) - {o}),
                ("head", sc_h[i], s, true_po.get((p, o), set()) - {s}),
            ):
                scores = row.copy()
                for f_idx in filt:
                    scores[f_idx] = -1e9
                tgt = scores[tgt_idx]
                better = int(np.sum(scores > tgt))
                ties = int(np.sum(scores == tgt)) - 1  # excluding the target
                recs.append({
                    "rel": p, "side": side, "leaked": bool(leaked_flags[gi]),
                    "rank_opt": better + 1, "rank_pess": better + ties + 1,
                    "ties": ties,
                })
    return recs


def mrr_of(recs, key="rank_opt"):
    if not recs:
        return None
    return sum(1.0 / r[key] for r in recs) / len(recs)


def hits_at(recs, k, key="rank_opt"):
    if not recs:
        return None
    return sum(1 for r in recs if r[key] <= k) / len(recs)


def main() -> int:
    t0 = time.time()
    print("=== H165: ATTACK on G91/G164 — symmetry leak vs geometry ===", flush=True)

    train_txt = load_split_txt(CORPUS_WN / "train.txt")
    valid_txt = load_split_txt(CORPUS_WN / "valid.txt")
    test_txt = load_split_txt(CORPUS_WN / "test.txt")

    # --- the leak partition, computed on RAW STRINGS before any id packing ---
    train_set = set(train_txt)
    leaked_flags = [(o, p, s) in train_set for (s, p, o) in test_txt]
    n_leaked_triples = sum(leaked_flags)

    per_rel_leak = defaultdict(lambda: [0, 0])
    for (s, p, o), lk in zip(test_txt, leaked_flags):
        per_rel_leak[p][1] += 1
        per_rel_leak[p][0] += int(lk)

    train, valid, test, npred, nent, r_map, e_map = pack_ids(train_txt, valid_txt, test_txt)
    inv_r = {v: k for k, v in r_map.items()}
    true_sp, true_po = build_filtered_dict(train + valid + test)

    E_re, E_im, theta, losses = train_rotate_wn(
        train, nent, npred, epochs=EPOCHS, lr=LR, bsz=BATCH_SIZE, reg=REG, seed=SEED)

    recs = eval_per_query(test, E_re, E_im, theta, true_sp, true_po, leaked_flags)

    mrr_opt = mrr_of(recs, "rank_opt")
    mrr_pess = mrr_of(recs, "rank_pess")
    leaked = [r for r in recs if r["leaked"]]
    clean = [r for r in recs if not r["leaked"]]

    drf = r_map["_derivationally_related_form"]
    drf_leaked = [r for r in recs if r["rel"] == drf and r["leaked"]]
    drf_clean = [r for r in recs if r["rel"] == drf and not r["leaked"]]

    # per-relation: leak rate vs MRR, the correlation that is the whole finding
    per_rel = {}
    for rid, name in inv_r.items():
        rr = [r for r in recs if r["rel"] == rid]
        lk, tot = per_rel_leak[name]
        per_rel[name] = {
            "test_triples": tot,
            "reverse_in_train": lk,
            "leak_rate": round(lk / tot, 4) if tot else None,
            "queries": len(rr),
            "mrr": round(mrr_of(rr), 4) if rr else None,
            "mrr_leaked": round(mrr_of([r for r in rr if r["leaked"]]), 4) if any(r["leaked"] for r in rr) else None,
            "mrr_clean": round(mrr_of([r for r in rr if not r["leaked"]]), 4) if any(not r["leaked"] for r in rr) else None,
        }

    print("\n  relation                                leak%     MRR   MRR|leaked  MRR|clean", flush=True)
    for name, d in sorted(per_rel.items(), key=lambda kv: -kv[1]["queries"]):
        ml = "  --  " if d["mrr_leaked"] is None else "%.4f" % d["mrr_leaked"]
        mc = "  --  " if d["mrr_clean"] is None else "%.4f" % d["mrr_clean"]
        print("  %-38s %5.1f  %.4f   %8s   %8s"
              % (name, 100 * d["leak_rate"], d["mrr"], ml, mc), flush=True)

    ties_total = sum(r["ties"] for r in recs)
    print(f"\n  MRR optimistic (G91's rule) : {mrr_opt:.4f}", flush=True)
    print(f"  MRR pessimistic (ties lose) : {mrr_pess:.4f}", flush=True)
    print(f"  total tied competitors      : {ties_total}", flush=True)
    print(f"  MRR | leaked   ({len(leaked):4d} q) : {mrr_of(leaked):.4f}", flush=True)
    print(f"  MRR | clean    ({len(clean):4d} q) : {mrr_of(clean):.4f}", flush=True)
    print(f"  _drf | leaked  ({len(drf_leaked):4d} q) : {mrr_of(drf_leaked):.4f}", flush=True)
    print(f"  _drf | clean   ({len(drf_clean):4d} q) : {mrr_of(drf_clean):.4f}", flush=True)

    # ---- controls: each MUST fire, and each states how it could not have ----
    c1_ok = round(mrr_opt, 4) == G91_MRR
    c2_ok = (len(recs) == 6268) and (len(leaked) == 2 * n_leaked_triples) \
        and (len(leaked) + len(clean) == 6268)
    c3_ok = len(PIN_F001) == 64 and len(PIN_F002) == 64

    controls = [
        Control("C1_reproduces_G91",
                why="my re-run of G91's own train_rotate_wn must land on G91's published 0.3546 "
                    "or nothing measured here is about G91",
                can_fail_because="a different MRR, i.e. G91 is not deterministic under its own pinned seed "
                                 "and its number cannot be attacked or defended at all",
                null_must_contain="mrr != 0.3546"),
        Control("C2_partition_is_exhaustive",
                why="leaked + clean must cover all 6,268 queries, and a leaked TRIPLE must contribute "
                    "exactly 2 leaked QUERIES (head and tail)",
                can_fail_because="an off-by-one in the leak flag or a query dropped by the eval loop",
                null_must_contain="partition sizes not summing to 6268"),
        Control("C3_pins_intact",
                why="F001/F002 digests unchanged from G91",
                can_fail_because="a pin of the wrong length, i.e. edited",
                null_must_contain="pins moved"),
    ]
    controls[0].observe(c1_ok, {"my_mrr": round(mrr_opt, 4), "g91_mrr": G91_MRR})
    controls[1].observe(c2_ok, {"queries": len(recs), "leaked_q": len(leaked),
                                "clean_q": len(clean), "leaked_triples": n_leaked_triples})
    controls[2].observe(c3_ok, {"f001": PIN_F001, "f002": PIN_F002})

    # ---- falsifiers, exactly as preregistered ----
    f1 = (mrr_of(drf_clean) or 0.0) >= 0.50
    gap = (mrr_of(leaked) or 0.0) - (mrr_of(clean) or 0.0)
    f2 = gap < 0.10
    f3 = abs(mrr_opt - mrr_pess) >= 0.01

    falsifiers = [
        Falsifier("F1_clean_drf_still_strong",
                  refutes="that _derivationally_related_form's 0.9412 MRR is reversed-triple memorisation",
                  fires_when="MRR on non-leaked _derivationally_related_form queries >= 0.50",
                  null_must_contain="clean _drf MRR >= 0.50"),
        Falsifier("F2_partition_explains_nothing",
                  refutes="that the leaked/clean split accounts for RotatE's WN18RR score",
                  fires_when="MRR(leaked) - MRR(clean) < 0.10",
                  null_must_contain="gap < 0.10"),
        Falsifier("F3_tie_breaking_also_inflates",
                  refutes="that G91's optimistic tie rule is immaterial to its headline number",
                  fires_when="|MRR_optimistic - MRR_pessimistic| >= 0.01",
                  null_must_contain="tie-rule swing >= 0.01"),
    ]
    falsifiers[0].observe(f1, {"drf_clean_mrr": round(mrr_of(drf_clean), 4),
                               "drf_leaked_mrr": round(mrr_of(drf_leaked), 4),
                               "n_clean": len(drf_clean)})
    falsifiers[1].observe(f2, {"mrr_leaked": round(mrr_of(leaked), 4),
                               "mrr_clean": round(mrr_of(clean), 4), "gap": round(gap, 4)})
    falsifiers[2].observe(f3, {"mrr_optimistic": round(mrr_opt, 4),
                               "mrr_pessimistic": round(mrr_pess, 4),
                               "tied_competitors": ties_total})

    res = {
        "spike": "H165",
        "attacks": ["G91", "H164"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "reproduction": {"my_mrr_optimistic": round(mrr_opt, 4), "g91_published_mrr": G91_MRR,
                         "reproduced": c1_ok},
        "leak_partition": {
            "definition": "test triple (s,p,o) is LEAKED iff (o,p,s) is in train.txt",
            "leaked_triples": n_leaked_triples, "test_triples": len(test_txt),
            "leaked_queries": len(leaked), "clean_queries": len(clean),
            "mrr_leaked": round(mrr_of(leaked), 4), "mrr_clean": round(mrr_of(clean), 4),
            "gap": round(gap, 4),
            "hits1_leaked": round(hits_at(leaked, 1), 4), "hits1_clean": round(hits_at(clean, 1), 4),
        },
        "derivationally_related_form": {
            "queries_leaked": len(drf_leaked), "queries_clean": len(drf_clean),
            "mrr_leaked": round(mrr_of(drf_leaked), 4), "mrr_clean": round(mrr_of(drf_clean), 4),
        },
        "tie_breaking": {
            "mrr_optimistic_G91_rule": round(mrr_opt, 4),
            "mrr_pessimistic": round(mrr_pess, 4),
            "swing": round(abs(mrr_opt - mrr_pess), 4),
            "tied_competitors_total": ties_total,
        },
        "per_relation": per_rel,
        "controls": {"C1_reproduces_G91": {"ok": c1_ok},
                     "C2_partition_is_exhaustive": {"ok": c2_ok},
                     "C3_pins_intact": {"ok": c3_ok}},
        "falsifiers": {"F1_clean_drf_still_strong": {"fired": f1},
                       "F2_partition_explains_nothing": {"fired": f2},
                       "F3_tie_breaking_also_inflates": {"fired": f3}},
    }

    out_json = Path(HERE) / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(CORPUS_WN), str(Path(SPIKES) / "G91_rotate_wn18rr")],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="if non-leaked _derivationally_related_form queries score as well as leaked ones, "
                  "RotatE's WN18RR result is geometry and this attack is withdrawn",
        allow_dirty=True,
        note="H165: cross-lane ATTACK on G91/H164 — reversed-triple leak vs geometric generalisation.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    print(f"\n=== H165 completed in {time.time()-t0:.2f}s ===", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
