#!/usr/bin/env python3
"""G107 — does WN18RR's headline survive a leak-free split, as it survived the null?

G105 showed G91/G92 clear WN18RR's own null by ~14x, unlike FB15k-237 whose
headline lost to a no-rules prior. That is one of the two tests this repo knows
how to apply. The other killed the FB15k-237 number:

    G46/G48, FB15k-237:  official/shuffle split -> 0.2648
                         pair-disjoint, leak=0  -> 0.1358    (-95% of the claim)

WN18RR is the dataset with KNOWN inverse-relation leakage, and G105 deliberately
used the official split as shipped. So the question G105 left open is whether
0.3546 / 0.3611 are inference or the same artefact one dataset over.

METHOD. Same move as G48, applied here. Group triples by UNORDERED entity pair,
assign whole groups, so no test pair has a train edge either way. Both splits are
scored by the SAME code paths -- G91's train_rotate_wn / evaluate_rotate_wn and
G90's train_complex_wn / evaluate_complex_wn, imported rather than reimplemented,
so a difference cannot be a difference of instrument.

SPLIT FRACTIONS ARE WN18RR'S OWN, not G48's 70/15/15. WN18RR ships
86835/3034/3134 = 0.9337/0.0326/0.0337. Using G48's fractions would shrink train
by ~25% and any drop would then be a train-volume confound rather than a leak
result. C4 checks this rather than trusting it.

FALSIFIERS, stated before the run (CHANNEL.md):
  F1  RotatE's MARGIN OVER ITS OWN SPLIT'S NULL falls by >= 50% on the leak-free
      split -> the WN18RR headline is substantially a leak artefact, as
      FB15k-237's was.
  F2  the official split's same-pair leak is 0 -> there was nothing to remove,
      and the whole concern about this dataset is unfounded.
  F3  the leak-free null differs from the official null by >= 0.02 MRR -> the
      re-split changed the PROBLEM and not just the leak, so the two columns are
      not comparable and F1 cannot be read.

Run:  python3 spikes/G107_wn18rr_leakfree/leakfree_wn.py
Read-only outside this directory (§10).
"""
import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPIKES = os.path.join(ROOT, "spikes")
CORPUS = os.path.join(ROOT, "corpus", "wn18rr")
for d in ("G48_pairdisjoint_split", "G105_wn18rr_frequency_null",
          "G91_rotate_wn18rr", "G90_complex_wn18rr", "harness"):
    sys.path.insert(0, os.path.join(SPIKES, d))

from split import pair_disjoint_split, leak_count                # noqa: E402
from null_wn import (load_split, pack, build_filter_index,       # noqa: E402
                     evaluate_frequency_null)

SEED = 0xC0FFEE                    # G48's, so the split rule is not a new choice
PUBLISHED = {"G91_rotate": 0.3546, "G90_complex": 0.1251, "G92_hybrid": 0.3611}


def _load_rotate():
    """Load G91's run.py BY PATH.

    G90 and G91 BOTH ship a module named `run`, so a bare `import run` resolves
    by sys.path order and would silently give whichever was inserted last. Here
    it would have been G90's -- ComplEx -- and the only thing that would have
    caught it is `train_rotate_wn` being absent from it. That is a coincidence,
    not a check. Loaded by explicit path so the wrong module cannot be picked.
    """
    import importlib.util
    path = os.path.join(SPIKES, "G91_rotate_wn18rr", "run.py")
    spec = importlib.util.spec_from_file_location("g91_rotate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fn in ("train_rotate_wn", "evaluate_rotate_wn"):
        if not hasattr(mod, fn):
            raise SystemExit(f"G107: {path} has no {fn} -- wrong module loaded")
    return mod


def arms_for(train, test, all_tri, nent, npred, label):
    """Every arm on ONE split. Same functions for both splits, by construction."""
    true_sp, true_po = build_filter_index(all_tri)
    out = {}

    t = time.time()
    out["frequency_null"] = evaluate_frequency_null(
        test, train, true_sp, true_po, nent)
    print(f"  [{label}] null    mrr={out['frequency_null']['mrr']} "
          f"({time.time()-t:.1f}s)", flush=True)

    _rot_mod = _load_rotate()
    t = time.time()
    E_re, E_im, theta = _rot_mod.train_rotate_wn(train, nent, npred)
    r = _rot_mod.evaluate_rotate_wn(test, E_re, E_im, theta, true_sp, true_po)
    out["rotate"] = {k: (round(v, 4) if isinstance(v, float) else v)
                     for k, v in r.items()}
    print(f"  [{label}] rotate  mrr={out['rotate'].get('mrr')} "
          f"({time.time()-t:.1f}s)", flush=True)
    return out


def main():
    t0 = time.time()
    tr_t, va_t, te_t = (load_split("train.txt"), load_split("valid.txt"),
                        load_split("test.txt"))
    o_train, o_valid, o_test, npred, nent = pack(tr_t, va_t, te_t)
    all_tri = o_train + o_valid + o_test
    total = len(all_tri)

    # --- the diagnosis: how much same-pair leak does the OFFICIAL split carry?
    off_leak = leak_count(o_train, o_test)
    print(f"WN18RR official: train={len(o_train)} test={len(o_test)} "
          f"ent={nent} rel={npred}  SAME-PAIR LEAK={off_leak} "
          f"({100.0*off_leak/len(o_test):.1f}% of test)", flush=True)

    # --- the leak-free re-split, at WN18RR's OWN fractions (see docstring)
    f_train = len(o_train) / total
    f_dev = len(o_valid) / total
    p_train, p_dev, p_test, n_groups = pair_disjoint_split(
        all_tri, SEED, frac_train=f_train, frac_dev=f_dev)
    pd_leak = leak_count(p_train, p_test)
    print(f"WN18RR pair-disjoint: train={len(p_train)} test={len(p_test)} "
          f"groups={n_groups}  SAME-PAIR LEAK={pd_leak}", flush=True)

    res = {"spike": "G107", "dataset": "WN18RR", "seed": f"0x{SEED:X}",
           "field_order": "p,s,o",
           "split_fractions": {"train": round(f_train, 4),
                               "dev": round(f_dev, 4),
                               "why": "WN18RR's own, not G48's 70/15/15, so a "
                                      "drop cannot be a train-volume confound"},
           "splits": {
               "official": {"n_train": len(o_train), "n_test": len(o_test),
                            "same_pair_leak": off_leak,
                            "leak_pct_of_test": round(100.0*off_leak/len(o_test), 2)},
               "pair_disjoint": {"n_train": len(p_train), "n_test": len(p_test),
                                 "same_pair_leak": pd_leak, "n_groups": n_groups}},
           "arms": {}, "controls": {}, "falsifiers": {}}

    res["arms"]["official"] = arms_for(o_train, o_test, all_tri, nent, npred,
                                       "official")
    res["arms"]["pair_disjoint"] = arms_for(p_train, p_test, all_tri, nent,
                                            npred, "pair_disjoint")

    # --- margins over each split's OWN null, which is the only honest read ---
    marg = {}
    for sp in ("official", "pair_disjoint"):
        a = res["arms"][sp]
        n = a["frequency_null"]["mrr"]
        marg[sp] = {"null": n,
                    "rotate_mrr": a["rotate"].get("mrr"),
                    "rotate_margin": round(a["rotate"].get("mrr", 0) - n, 4)}
    res["margins"] = marg
    om, pm = marg["official"]["rotate_margin"], marg["pair_disjoint"]["rotate_margin"]
    drop_pct = round(100.0 * (om - pm) / om, 1) if om else None
    res["margin_drop_pct"] = drop_pct
    print(f"\n  margin over own null: official {om:+.4f} -> "
          f"pair_disjoint {pm:+.4f}   drop {drop_pct}%", flush=True)

    c = res["controls"]
    c["C1_resplit_is_actually_leak_free"] = {
        "why": "the entire experiment is the leak; if the new split still leaks "
               "there is no leak-free column and F1 is unreadable",
        "same_pair_leak": pd_leak, "ok": pd_leak == 0}
    c["C2_detector_fires_on_the_original"] = {
        "why": "a leak detector that reports 0 everywhere cannot distinguish a "
               "clean split from a broken detector (A15)",
        "official_leak": off_leak, "ok": off_leak > 0}
    c["C3_test_sets_comparable"] = {
        "why": "a much smaller test set moves MRR for reasons unrelated to leak",
        "official": len(o_test), "pair_disjoint": len(p_test),
        "ratio": round(len(p_test)/len(o_test), 3),
        "ok": 0.80 <= len(p_test)/len(o_test) <= 1.25}
    c["C4_train_volume_not_a_confound"] = {
        "why": "G48's 70/15/15 would cut WN18RR train by ~25% and any drop "
               "would be volume, not leak",
        "official": len(o_train), "pair_disjoint": len(p_train),
        "ratio": round(len(p_train)/len(o_train), 3),
        "ok": 0.90 <= len(p_train)/len(o_train) <= 1.10}
    c["C5_instrument_reproduces_G91"] = {
        "why": "if the official-split RotatE arm does not land near G91's "
               "published 0.3546 this is not G91's instrument and no "
               "comparison drawn from it means anything",
        "published": 0.3546,
        "observed": res["arms"]["official"]["rotate"].get("mrr"),
        "abs_diff": round(abs(res["arms"]["official"]["rotate"].get("mrr", 0)
                              - 0.3546), 4),
        "ok": abs(res["arms"]["official"]["rotate"].get("mrr", 0) - 0.3546) <= 0.02}
    res["controls_ok"] = f"{sum(1 for v in c.values() if v.get('ok'))}/{len(c)}"

    f = res["falsifiers"]
    f["F1_headline_is_a_leak_artefact"] = {
        "stated": "RotatE's margin over its own split's null falls >= 50% on "
                  "the leak-free split",
        "official_margin": om, "pair_disjoint_margin": pm,
        "drop_pct": drop_pct, "fired": bool(drop_pct is not None and drop_pct >= 50.0)}
    f["F2_official_split_does_not_leak"] = {
        "stated": "the official split's same-pair leak is 0, so there was "
                  "nothing to remove",
        "official_leak": off_leak, "fired": off_leak == 0}
    n_off = marg["official"]["null"]; n_pd = marg["pair_disjoint"]["null"]
    f["F3_resplit_changed_the_problem"] = {
        "stated": "the two nulls differ by >= 0.02 MRR, so the re-split moved "
                  "the problem and the columns are not comparable",
        "official_null": n_off, "pair_disjoint_null": n_pd,
        "abs_diff": round(abs(n_off - n_pd), 4),
        "fired": abs(n_off - n_pd) >= 0.02}

    res["elapsed_sec"] = round(time.time() - t0, 3)
    out = os.path.join(HERE, "leakfree_wn.json")
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"  controls {res['controls_ok']}", flush=True)
    for k, v in f.items():
        print(f"  {k:34} fired={v['fired']}", flush=True)
    print(f"  wrote {out} in {res['elapsed_sec']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
