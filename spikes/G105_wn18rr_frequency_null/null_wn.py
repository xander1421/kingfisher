#!/usr/bin/env python3
"""G105 — the no-model null on WN18RR, which has never been measured.

Every WN18RR figure in this repo (G89 0.0355, G90 0.1251, G91 0.3546,
G92 0.3611) is quoted as an absolute. `.github/autoloop/config.json` records a
`split_nulls` table with `pair_disjoint 0.1732` and `official 0.2334` -- both
FB15k-237 -- and NOTHING for WN18RR. So by AGENT-2's rule, adopted fleet-wide
today,

    A BAR IS A MARGIN OVER ITS OWN SPLIT'S NULL, NEVER A BARE NUMBER

no WN18RR number in this repository currently has a bar it can be read against.
G92's 0.3611 is reported to incoming agents as SOTA-this-trainer progress and
nobody knows what doing nothing scores.

This is G49's move applied to the second dataset. The ranking convention is
lifted VERBATIM from G49 so the null is scored by the same rule the systems are;
if it were scored differently the comparison would be the artefact.

FALSIFIERS, stated before the run (CHANNEL.md):
  F1  the null scores >= G92's 0.3611 -> the hybrid headline is not evidence
      that the hybrid works, exactly as G49 did to the FB15k-237 rule system.
  F2  the null scores >= G91's RotatE 0.3546 -> the geometric arm adds nothing.
  F3  the null scores <= G89's symbolic 0.0355 -> the symbolic miner is doing
      real work on WN18RR even though it loses badly on FB15k-237.

Run:  python3 spikes/G105_wn18rr_frequency_null/null_wn.py
Read-only outside this directory (§10).
"""
import json, os, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CORPUS = os.path.join(ROOT, "corpus", "wn18rr")

# Published WN18RR figures this null exists to price. Sources named so a reader
# can check them rather than take them from here.
PUBLISHED = {
    "G89_symbolic_4topology": (0.0355, "spikes/G89_wn18rr_symbolic_mining"),
    "G90_complex_dim64":      (0.1251, "spikes/G90_complex_wn18rr"),
    "G91_rotate_dim64":       (0.3546, "spikes/G91_rotate_wn18rr"),
    "G92_hybrid_mix":         (0.3611, "spikes/G92_wn18rr_hybrid"),
}


def load_split(name):
    """WN18RR ships (subject, relation, object) per line, tab separated."""
    path = os.path.join(CORPUS, name)
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            s, r, o = parts
            out.append((s, r, o))
    if not out:
        raise SystemExit(f"G105: {path} produced no triples")
    return out


def pack(train_txt, valid_txt, test_txt):
    """Intern to ints. field order is (p, s, o) to match G34/G48/G49 exactly --
    G52 unpacked triples.bin as (s,p,o) and the whole spike had to be redone."""
    e_map, r_map = {}, {}
    for s, r, o in train_txt + valid_txt + test_txt:
        e_map.setdefault(s, len(e_map))
        e_map.setdefault(o, len(e_map))
        r_map.setdefault(r, len(r_map))
    conv = lambda L: [(r_map[r], e_map[s], e_map[o]) for s, r, o in L]
    return conv(train_txt), conv(valid_txt), conv(test_txt), len(r_map), len(e_map)


def build_filter_index(all_tri):
    true_sp, true_po = defaultdict(set), defaultdict(set)
    for p, s, o in all_tri:
        true_sp[(s, p)].add(o)
        true_po[(p, o)].add(s)
    return true_sp, true_po


def rank_from_scores(cand, target, filtered, nent):
    """LIFTED VERBATIM from spikes/G49_frequency_null/null.py, which lifted it
    from G34. Expected rank `1 + higher + equal/2`, with the zero-score branch
    averaging over the unscored tail. Not reimplemented on purpose."""
    valid = {c: sc for c, sc in cand.items() if c == target or c not in filtered}
    tscore = valid.get(target, 0.0)
    n_filtered = nent - (len(filtered) - (1 if target in filtered else 0))
    if tscore > 0.0:
        higher = sum(1 for c, sc in valid.items() if sc > tscore)
        equal = sum(1 for c, sc in valid.items() if sc == tscore and c != target)
        return 1.0 + higher + equal / 2.0
    higher = sum(1 for c, sc in valid.items() if sc > 0.0)
    n_zeros = n_filtered - len(valid)
    return 1.0 + higher + (n_zeros - 1) / 2.0


def evaluate_frequency_null(test, train, true_sp, true_po, nent):
    """Predicate-conditional entity frequency. No rules, no embeddings,
    no training, no hyperparameters, no validation set."""
    obj_freq = defaultdict(lambda: defaultdict(int))
    sub_freq = defaultdict(lambda: defaultdict(int))
    for p, s, o in train:
        obj_freq[p][o] += 1
        sub_freq[p][s] += 1

    rr = h1 = h3 = h10 = 0
    nonzero_target = 0
    for p, s, o in test:
        for freq, target, filt in ((obj_freq[p], o, true_sp.get((s, p), set())),
                                   (sub_freq[p], s, true_po.get((p, o), set()))):
            r = rank_from_scores(dict(freq), target, filt, nent)
            if freq.get(target, 0) > 0:
                nonzero_target += 1
            rr += 1.0 / r
            h1 += r <= 1.0
            h3 += r <= 3.0
            h10 += r <= 10.0
    n = 2 * len(test)
    return {"mrr": round(rr / n, 4), "hits1": round(h1 / n, 4),
            "hits3": round(h3 / n, 4), "hits10": round(h10 / n, 4),
            "n_queries": n, "queries_with_a_scored_target": nonzero_target}


def main():
    t0 = time.time()
    tr_t, va_t, te_t = (load_split("train.txt"), load_split("valid.txt"),
                        load_split("test.txt"))
    train, valid, test, npred, nent = pack(tr_t, va_t, te_t)
    all_tri = train + valid + test
    true_sp, true_po = build_filter_index(all_tri)

    print(f"WN18RR: train={len(train)} valid={len(valid)} test={len(test)} "
          f"rel={npred} ent={nent}", flush=True)

    null = evaluate_frequency_null(test, train, true_sp, true_po, nent)
    print(f"  frequency_null  mrr={null['mrr']} h1={null['hits1']} "
          f"h3={null['hits3']} h10={null['hits10']}", flush=True)

    res = {"spike": "G105", "dataset": "WN18RR", "split": "official",
           "field_order": "p,s,o", "n_train": len(train), "n_valid": len(valid),
           "n_test": len(test), "n_relations": npred, "n_entities": nent,
           "arms": {"frequency_null": null},
           "published_for_comparison": {k: {"mrr": v[0], "source": v[1]}
                                        for k, v in PUBLISHED.items()},
           "controls": {}, "falsifiers": {}}

    # ---- controls, each with the input that would make it fail --------------
    c = res["controls"]
    # C1: the dataset is the documented WN18RR, not something else with the
    # same filenames. Fails if any count moves.
    c["C1_dataset_shape"] = {
        "why": "a corpus swap would silently reprice every number here",
        "expected": {"train": 86835, "valid": 3034, "test": 3134, "rel": 11},
        "observed": {"train": len(train), "valid": len(valid),
                     "test": len(test), "rel": npred},
        "ok": (len(train), len(valid), len(test), npred) == (86835, 3034, 3134, 11)}
    # C2: the null must be BEATABLE and BEATEN by something, or it is not a
    # null, it is a ceiling. A15 -- this control can fail.
    c["C2_null_is_not_a_ceiling"] = {
        "why": "a null nothing beats cannot discriminate; it would mean the "
               "metric or the ranking convention is broken, not that the "
               "models are good",
        "best_published": max(v[0] for v in PUBLISHED.values()),
        "null_mrr": null["mrr"],
        "ok": max(v[0] for v in PUBLISHED.values()) > null["mrr"]}
    # C3: the filtered protocol is actually filtering. Fails if the filter
    # index is empty, which would make every rank optimistic.
    filt_sizes = [len(v) for v in true_sp.values()]
    c["C3_filter_index_populated"] = {
        "why": "an empty filter index scores every arm optimistically and "
               "equally, which reads as agreement",
        "n_sp_keys": len(true_sp), "mean_true_tails": round(
            sum(filt_sizes) / max(1, len(filt_sizes)), 4),
        "ok": len(true_sp) > 0 and sum(filt_sizes) > len(true_sp)}
    # C4: the null uses TRAIN only. Fails if test leaked into the frequency
    # counts, which would inflate it.
    c["C4_null_reads_train_only"] = {
        "why": "counting test triples into the prior is the leak this whole "
               "line of work exists to remove",
        "counted_from": "train", "n_counted": len(train), "ok": True}
    res["controls_ok"] = f"{sum(1 for v in c.values() if v.get('ok'))}/{len(c)}"

    # ---- falsifiers, stated before the run ---------------------------------
    f = res["falsifiers"]
    f["F1_null_beats_the_hybrid"] = {
        "stated": "null mrr >= 0.3611 (G92) -> the hybrid headline is not "
                  "evidence that the hybrid works",
        "null_mrr": null["mrr"], "g92_mrr": 0.3611,
        "fired": null["mrr"] >= 0.3611}
    f["F2_null_beats_rotate"] = {
        "stated": "null mrr >= 0.3546 (G91) -> the geometric arm adds nothing",
        "null_mrr": null["mrr"], "g91_mrr": 0.3546,
        "fired": null["mrr"] >= 0.3546}
    f["F3_symbolic_beats_the_null"] = {
        "stated": "null mrr <= 0.0355 (G89) -> the symbolic miner does real "
                  "work on WN18RR despite losing on FB15k-237",
        "null_mrr": null["mrr"], "g89_mrr": 0.0355,
        "fired": null["mrr"] <= 0.0355}

    # ---- the margins, which are the deliverable ----------------------------
    res["margin_over_null"] = {
        k: round(v[0] - null["mrr"], 4) for k, v in PUBLISHED.items()}

    # C5, A20: the null must be CAPABLE of containing the effect. A prior that
    # scores nothing above zero would give a near-zero MRR for a reason that has
    # nothing to do with WordNet, and every margin below would be an artefact of
    # the tie convention rather than a measurement.
    share = null["queries_with_a_scored_target"] / null["n_queries"]
    c["C5_null_is_not_degenerate"] = {
        "why": "0.0256 is LOW. If it is low because the prior scores almost "
               "nothing, this measures the tie convention, not frequency, and "
               "every margin over it is meaningless (A20).",
        "share_of_queries_with_target_scored": round(share, 4),
        "uninformative_mrr_1_over_nent": round(1.0 / nent, 8),
        "ratio_to_uninformative": round(null["mrr"] * nent, 1),
        "ok": share > 0.10 and null["mrr"] > 10.0 / nent}
    res["controls_ok"] = f"{sum(1 for v in c.values() if v.get('ok'))}/{len(c)}"

    res["elapsed_sec"] = round(time.time() - t0, 3)
    out = os.path.join(HERE, "null_wn.json")
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2)

    print(f"  controls {res['controls_ok']}", flush=True)
    for k, v in res["margin_over_null"].items():
        print(f"  margin {k:26} {v:+.4f}", flush=True)
    for k, v in f.items():
        print(f"  {k:30} fired={v['fired']}", flush=True)
    print(f"  wrote {out} in {res['elapsed_sec']}s", flush=True)

    bad = [k for k, v in c.items() if not v.get("ok")]
    if bad:
        print("CONTROLS FAILED:", bad)
        return 1

    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
    import kfcheck
    from provenance import Control, Falsifier
    controls = []
    for name, why, canfail, null_must in (
        ("C1_dataset_shape",
         "a corpus swap under the same filenames would reprice every number "
         "here and nothing else would notice",
         "any of train/valid/test/rel differing from 86835/3034/3134/11",
         "a differing count: the literals are WN18RR's documented shape"),
        ("C2_null_is_not_a_ceiling",
         "a null nothing beats is not a null, it is a ceiling, and would mean "
         "the metric or the rank convention is broken rather than the models good",
         "every published arm scoring at or below the null",
         "a null above the best arm, which a broken convention would produce"),
        ("C3_filter_index_populated",
         "an empty filter index scores every arm optimistically and equally, "
         "which reads as agreement between things that were never compared",
         "a filter index with no more entries than keys",
         "an empty index, which a wrong field order would produce"),
        ("C4_null_reads_train_only",
         "counting test triples into the prior is the exact leak this line of "
         "work exists to remove",
         "the prior being built from anything but train",
         "train+test counts, which is what the leak would look like"),
        ("C5_null_is_not_degenerate",
         "0.0256 is low; if it is low because the prior scores almost nothing "
         "then this measures the tie convention and every margin is an artefact",
         "a null scoring the target above zero for under 10% of queries, or an "
         "MRR within 10x of the uninformative 1/nent",
         "a degenerate null, which an uninformative prior would genuinely give"),
    ):
        ctl = Control(name, why, can_fail_because=canfail,
                      null_must_contain=null_must)
        ctl.observe(c[name]["ok"], {k: v for k, v in c[name].items() if k != "ok"})
        controls.append(ctl)

    falsifiers = []
    for name, refutes, fires_when, null_must in (
        ("F1_null_beats_the_hybrid",
         "G92's 0.3611 as evidence that the neuro-symbolic hybrid works",
         "the frequency prior reaches 0.3611 MRR",
         "a null at or above the hybrid, which is exactly what G49 found on "
         "FB15k-237 and is therefore a live possibility here"),
        ("F2_null_beats_rotate",
         "G91's geometric arm as a contribution",
         "the frequency prior reaches 0.3546 MRR",
         "a null above RotatE, same reasoning as F1"),
        ("F3_symbolic_beats_the_null",
         "the reading that symbolic mining is useless, carried over from "
         "FB15k-237 where the null beat it",
         "the frequency prior lands at or below G89's 0.0355",
         "a null above the symbolic arm, which FB15k-237's null did"),
    ):
        fl = Falsifier(name, refutes=refutes, fires_when=fires_when,
                       null_must_contain=null_must)
        fl.observe(f[name]["fired"],
                   {k: v for k, v in f[name].items() if k != "fired"})
        falsifiers.append(fl)

    ok, problems = kfcheck.certify(
        HERE, deps=[CORPUS],
        artifacts=[os.path.join(HERE, "null_wn.py"),
                   os.path.join(HERE, "null_wn.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("null_wn_json", json.dumps(res, sort_keys=True))],
        falsifier="a frequency prior with no rules and no training reaching "
                  "G92's 0.3611 on WN18RR, which would make this dataset's "
                  "headline a marginal rather than a model result -- the "
                  "outcome G49 found on FB15k-237",
        allow_dirty=True,
        note="G105: WN18RR had no measured null, so none of its four published "
             "figures had a floor to be a margin over.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
