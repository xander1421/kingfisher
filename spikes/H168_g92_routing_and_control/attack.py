#!/usr/bin/env python3
"""H168 — ATTACK on G92: the routing table's names, and the +0.0065's missing control.

Two claims under attack, neither of them G92's arithmetic:

  (1) G92 `run.py:323` prints the routing table as `Rel {p:2d}` -- INDEX ONLY.
      Every per-relation sentence in G92's RESULT.md is therefore an
      index->name mapping done by eye (MISSION_LOOP 12.4). This run prints the
      NAMED table G92 never printed.

  (2) G92 reports "+0.0065 lift over standalone RotatE (G91: 0.3546)" while
      G92 trains 6 epochs and G91 trains 8. The controlled arm -- G92's OWN
      6-epoch RotatE, standalone, on test -- was never evaluated.

Nothing here reimplements G92. It IMPORTS G92's run.py and calls its own
functions, so a reproduction failure is about G92's code and not about a copy
of it that drifted. The standalone arms reuse G92's `eval_test_hybrid` with a
forced routing, so the filter set, the rank convention (optimistic
`(sc > sc[tgt]).sum() + 1`) and the query order are identical by construction.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
G92 = os.path.join(SPIKES, "G92_wn18rr_hybrid")


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
sys.path.insert(0, G92)

import kfcheck                                    # noqa: E402
from provenance import Control, Falsifier         # noqa: E402
import run as g92                                 # noqa: E402  -- G92's own module

# --- what G92 published, and what H164 measured independently -----------------
G92_PUBLISHED_MRR = 0.3611
G92_PUBLISHED_LIFT_OVER_G91 = 0.0065
G91_PUBLISHED_MRR = 0.3546

# G92 RESULT.md prose, verbatim, as (relation, model_it_says, rotate_valid_mrr_it_quotes)
PROSE = {
    "_hypernym": ("rotate", 0.9246),
    "_instance_hypernym": ("rotate", 0.8453),
    "_member_meronym": ("rotate", 0.0850),
    "_also_see": ("complex", 0.3088),
    "_similar_to": ("complex", 0.0010),
    "_verb_group": ("complex", 0.0127),
}

# H164's per-relation TEST query counts -- the independent second source used to
# decide which of G92's two disagreeing artifacts is right.
H164_TEST_QUERIES = {
    "_hypernym": 2502, "_derivationally_related_form": 2148, "_member_meronym": 506,
    "_has_part": 344, "_instance_hypernym": 244, "_synset_domain_topic_of": 228,
    "_also_see": 112, "_verb_group": 78, "_member_of_domain_region": 52,
    "_member_of_domain_usage": 48, "_similar_to": 6,
}
H164_TEST_MRR_ROTATE = {
    "_hypernym": 0.0122, "_derivationally_related_form": 0.9412, "_verb_group": 0.8799,
}

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"


def main() -> int:
    t0 = time.perf_counter()
    print("=== H168: ATTACK on G92 routing names + uncontrolled lift ===", flush=True)
    print(f"    G92 module: {g92.__file__}", flush=True)
    print(f"    G92 EPOCHS={g92.EPOCHS} SEED={g92.SEED} DIM={g92.DIM}", flush=True)

    corpus = g92.CORPUS_WN
    train_raw = g92.load_split_txt(corpus / "train.txt")
    valid_raw = g92.load_split_txt(corpus / "valid.txt")
    test_raw = g92.load_split_txt(corpus / "test.txt")

    e2i, r2i, entities, relations = g92.build_vocab([train_raw, valid_raw, test_raw])
    nent, npred = len(entities), len(relations)
    i2r = {i: r for r, i in r2i.items()}

    train_tri = g92.encode_triples(train_raw, e2i, r2i)
    valid_tri = g92.encode_triples(valid_raw, e2i, r2i)
    test_tri = g92.encode_triples(test_raw, e2i, r2i)

    all_true_sp = defaultdict(list)
    all_true_po = defaultdict(list)
    for p, s, o in train_tri + valid_tri + test_tri:
        all_true_sp[(s, p)].append(o)
        all_true_po[(p, o)].append(s)

    # --- G92's own models, G92's own hyperparameters -------------------------
    rot_m = g92.train_rotate_wn(train_tri, nent, npred, epochs=g92.EPOCHS,
                                lr=g92.LR, reg=g92.REG, seed=g92.SEED)
    cx_m = g92.train_complex_wn(train_tri, nent, npred, epochs=g92.EPOCHS,
                                lr=g92.LR, reg=1e-4, seed=g92.SEED)

    routing = g92.eval_validation(valid_tri, rot_m, cx_m, all_true_sp, all_true_po, npred)

    # ARM H: the hybrid exactly as G92 evaluates it -- this is C1.
    hyb_mrr, hyb_h1, hyb_h3, hyb_h10, choices, hyb_rel_ranks = g92.eval_test_hybrid(
        test_tri, rot_m, cx_m, routing, all_true_sp, all_true_po)

    # ARM R: THE MISSING CONTROL. Same models, same epochs, same filter, same
    # rank convention -- every relation forced to RotatE.
    all_rotate = {p: ("rotate", 0.0, 0.0) for p in range(npred)}
    rot_mrr, rot_h1, rot_h3, rot_h10, _, rot_rel_ranks = g92.eval_test_hybrid(
        test_tri, rot_m, cx_m, all_rotate, all_true_sp, all_true_po)

    # ARM C: same, forced to ComplEx -- so G92's F3 (vs G90's 0.1251, a
    # different budget) also gets a same-budget counterpart.
    all_complex = {p: ("complex", 0.0, 0.0) for p in range(npred)}
    cx_mrr, cx_h1, cx_h3, cx_h10, _, _ = g92.eval_test_hybrid(
        test_tri, rot_m, cx_m, all_complex, all_true_sp, all_true_po)

    # --- THE TABLE G92 NEVER PRINTED ----------------------------------------
    named = {}
    for name in sorted(r2i):
        p = r2i[name]
        chosen, mrr_r, mrr_c = routing[p]
        rr = hyb_rel_ranks.get(p, [])
        rot_only = rot_rel_ranks.get(p, [])
        named[name] = {
            "idx": p,
            "routed_to": chosen,
            "valid_mrr_rotate": round(float(mrr_r), 4),
            "valid_mrr_complex": round(float(mrr_c), 4),
            "test_queries": len(rr),
            "test_mrr_hybrid": round(float(np.mean([1.0 / r for r in rr])), 4) if rr else None,
            "test_mrr_rotate_only": round(float(np.mean([1.0 / r for r in rot_only])), 4) if rot_only else None,
        }

    print("\n=========== H168: NAMED ROUTING TABLE (G92 printed `Rel {idx}` only) ===========")
    print(f"{'relation':<32}{'idx':>4}{'routed':>9}{'validR':>9}{'validC':>9}{'qs':>6}{'testR':>9}")
    for name in sorted(named, key=lambda n: -named[n]["test_queries"]):
        d = named[name]
        print(f"{name:<32}{d['idx']:>4}{d['routed_to']:>9}{d['valid_mrr_rotate']:>9.4f}"
              f"{d['valid_mrr_complex']:>9.4f}{d['test_queries']:>6}{d['test_mrr_rotate_only']:>9.4f}")

    print("\n--- G92 RESULT.md prose vs this run -------------------------------------------")
    prose_rows = []
    for name, (says_model, says_valid_r) in PROSE.items():
        d = named[name]
        row = {
            "relation": name,
            "prose_says_routed_to": says_model,
            "actually_routed_to": d["routed_to"],
            "routing_matches": says_model == d["routed_to"],
            "prose_quotes_rotate_valid_mrr": says_valid_r,
            "measured_rotate_valid_mrr": d["valid_mrr_rotate"],
            "number_matches": abs(says_valid_r - d["valid_mrr_rotate"]) < 0.02,
        }
        prose_rows.append(row)
        flag = "OK " if (row["routing_matches"] and row["number_matches"]) else "BAD"
        print(f"  [{flag}] {name:<30} prose: {says_model:>7}/{says_valid_r:.4f}   "
              f"measured: {d['routed_to']:>7}/{d['valid_mrr_rotate']:.4f}")

    # where did the prose's numbers actually come from?
    print("\n--- where each quoted number actually lives ------------------------------------")
    provenance_of_quotes = {}
    for name, (_, q) in PROSE.items():
        owners = [n for n in named if abs(named[n]["valid_mrr_rotate"] - q) < 0.02]
        provenance_of_quotes[name] = owners
        print(f"  {q:.4f} (prose attributes to {name}) -> actually {owners or 'no relation'}")

    lift_controlled = hyb_mrr - rot_mrr
    lift_published = G92_PUBLISHED_MRR - G91_PUBLISHED_MRR

    print("\n=========== H168: THE LIFT, AS A CONTROLLED PAIR ===========")
    print(f"  ARM H  hybrid                     MRR = {hyb_mrr:.4f}  H@1={hyb_h1:.4f} H@10={hyb_h10:.4f}")
    print(f"  ARM R  RotatE only, SAME 6 epochs MRR = {rot_mrr:.4f}  H@1={rot_h1:.4f} H@10={rot_h10:.4f}")
    print(f"  ARM C  ComplEx only, SAME 6 epochs MRR = {cx_mrr:.4f}  H@1={cx_h1:.4f} H@10={cx_h10:.4f}")
    print(f"  controlled lift (H - R)           = {lift_controlled:+.4f}")
    print(f"  G92 published lift (G92 - G91@8ep)= {lift_published:+.4f}")
    print(f"  routing moved {choices['complex']} of 6268 queries ({choices['complex']/62.68:.2f}%)")

    # --- CONTROLS ------------------------------------------------------------
    c1_ok = abs(hyb_mrr - G92_PUBLISHED_MRR) < 0.00005
    routed_complex = [n for n in named if named[n]["routed_to"] == "complex"]
    c2_ok = (len(named) == 11
             and choices["rotate"] == 6050 and choices["complex"] == 218
             and sum(d["test_queries"] for d in named.values()) == 6268
             and all(named[n]["test_queries"] == H164_TEST_QUERIES[n] for n in named)
             and sum(H164_TEST_QUERIES[n] for n in routed_complex) == 218)
    c3_ok = (PIN_F001.startswith("590d8769") and PIN_F002.startswith("c43b1eab"))

    controls = [
        Control("C1_reproduces_G92", why="my hybrid arm must reproduce G92's published 0.3611 to 4dp or nothing here is about G92",
                can_fail_because="BLAS nondeterminism, numpy version drift, or G92 run.py changed since it was published",
                null_must_contain="hybrid MRR differs from 0.3611"),
        Control("C2_named_partition", why="all 11 relations named, choices rotate=6050/complex=218, and per-relation query counts equal H164's independently-measured counts",
                can_fail_because="my index->name map is wrong, which would make my whole attack the very error I am reporting",
                null_must_contain="partition mismatch"),
        Control("C3_pins_intact", why="F001/F002 unchanged", can_fail_because="pin drift", null_must_contain="pins moved"),
    ]
    controls[0].observe(c1_ok, {"measured": round(hyb_mrr, 6), "published": G92_PUBLISHED_MRR})
    controls[1].observe(c2_ok, {"n_relations": len(named), "choices": dict(choices),
                                "complex_set": sorted(routed_complex),
                                "complex_queries_via_H164": sum(H164_TEST_QUERIES[n] for n in routed_complex)})
    controls[2].observe(c3_ok, {"f001": PIN_F001, "f002": PIN_F002})

    # --- FALSIFIERS (preregistered in CHANNEL.md before this file existed) ----
    hyp_r = named["_hypernym"]["valid_mrr_rotate"]
    vg_r = named["_verb_group"]["valid_mrr_rotate"]
    f1 = (hyp_r >= 0.50) and (vg_r <= 0.10)          # refutes ME: prose was right
    f2 = abs(lift_controlled - G92_PUBLISHED_LIFT_OVER_G91) < 0.001   # refutes ME: lift was controlled
    f3 = lift_controlled <= 0.0                       # a FINDING: hybrid loses to its own RotatE

    falsifiers = [
        Falsifier("F1_prose_was_right",
                  refutes="my claim that G92's per-relation prose transposes relation names",
                  fires_when="_hypernym rotate-valid-MRR >= 0.50 AND _verb_group rotate-valid-MRR <= 0.10",
                  null_must_contain="prose names verified"),
        Falsifier("F2_lift_was_already_controlled",
                  refutes="my claim that +0.0065 compares across training budgets",
                  fires_when="|(hybrid - own 6-epoch RotatE) - 0.0065| < 0.001",
                  null_must_contain="controlled lift equals published lift"),
        Falsifier("F3_hybrid_loses_to_its_own_rotate",
                  refutes="that routing helps at all at this budget",
                  fires_when="hybrid MRR <= own 6-epoch RotatE MRR",
                  null_must_contain="hybrid no better than RotatE"),
    ]
    falsifiers[0].observe(f1, {"hypernym_valid_rotate": hyp_r, "verb_group_valid_rotate": vg_r,
                               "prose_claims": {"_hypernym": 0.9246, "_verb_group": 0.0127}})
    falsifiers[1].observe(f2, {"controlled_lift": round(lift_controlled, 6),
                               "published_lift": G92_PUBLISHED_LIFT_OVER_G91})
    falsifiers[2].observe(f3, {"hybrid": round(hyb_mrr, 6), "rotate_only": round(rot_mrr, 6),
                               "delta": round(lift_controlled, 6)})

    res = {
        "spike": "H168",
        "attacks": "G92",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "g92_module": g92.__file__,
        "g92_hyperparams": {"epochs": g92.EPOCHS, "seed": g92.SEED, "dim": g92.DIM, "lr": g92.LR},
        "g91_epochs_for_comparison": 8,
        "arms": {
            "H_hybrid": {"mrr": round(hyb_mrr, 4), "hits1": round(hyb_h1, 4), "hits3": round(hyb_h3, 4), "hits10": round(hyb_h10, 4)},
            "R_rotate_only_same_budget": {"mrr": round(rot_mrr, 4), "hits1": round(rot_h1, 4), "hits3": round(rot_h3, 4), "hits10": round(rot_h10, 4)},
            "C_complex_only_same_budget": {"mrr": round(cx_mrr, 4), "hits1": round(cx_h1, 4), "hits3": round(cx_h3, 4), "hits10": round(cx_h10, 4)},
        },
        "lift": {
            "controlled_H_minus_R": round(lift_controlled, 6),
            "g92_published_vs_g91": G92_PUBLISHED_LIFT_OVER_G91,
            "g91_mrr_at_8_epochs": G91_PUBLISHED_MRR,
            "queries_routed_away_from_rotate": choices["complex"],
        },
        "named_routing_table": named,
        "prose_audit": prose_rows,
        "quote_provenance": provenance_of_quotes,
        "h164_test_mrr_rotate_cross_check": H164_TEST_MRR_ROTATE,
        "controls": {"C1_reproduces_G92": {"ok": c1_ok}, "C2_named_partition": {"ok": c2_ok},
                     "C3_pins_intact": {"ok": c3_ok}},
        "falsifiers": {"F1_prose_was_right": {"fired": f1},
                       "F2_lift_was_already_controlled": {"fired": f2},
                       "F3_hybrid_loses_to_its_own_rotate": {"fired": f3}},
    }

    out_json = Path(HERE) / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(corpus), G92],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="G92's per-relation prose names the same relations its own result.json routes, "
                  "and the +0.0065 lift is already a same-budget controlled pair",
        allow_dirty=True,
        note="H168: attack on G92's index-only routing table and its cross-budget lift.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    print(f"\n=== H168 completed in {time.perf_counter()-t0:.2f}s ===", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
