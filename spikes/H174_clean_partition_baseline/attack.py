#!/usr/bin/env python3
"""H174 — the comparison H165 refused to make: G89 vs RotatE on the CLEAN partition.

H165 measured RotatE at 0.0214 MRR on the 4,096 WN18RR test queries whose
reversed triple is NOT in train, and G91 publishes a "10.0x MRR lift over pure
symbolic rules (G89: 0.0355)". Those two numbers are at DIFFERENT OPERATING
POINTS -- 0.0355 is over all 6,268 queries -- so H165 deliberately did not quote
them against each other (A18, a ratio without its operating point).

This runs G89's OWN `mine_4_topologies_wn` and `evaluate_symbolic_wn` by import,
twice, on the SAME partition object H165 used:

  ARM-FULL   all 3,134 test triples   -> must reproduce G89's published 0.0355
  ARM-CLEAN  the 2,048 clean triples  -> G89 where generalisation is required

Passing a shorter test list to G89's own evaluator is not a reimplementation of
it: the filter dicts `true_sp`/`true_po` are still built from train+valid+test,
so the filtered setting is unchanged, and every rule, score and rank convention
is theirs.

ONE CONTAMINANT, FOUND BY READING AND DISCLOSED IN CHANNEL BEFORE THE RUN.
The two systems tie-break differently:

    G89   rank = 1 + greater + equal//2      (MID-RANK, plus a frequency-prior
                                              backoff when the target scores 0)
    G91   rank = 1 + sum(scores > tgt)       (OPTIMISTIC)

Normally that voids a comparison. It does not here, and the reason is measured
rather than assumed: H165's F3 found RotatE's optimistic and pessimistic MRR
IDENTICAL at 0.3546 (30 tied competitors in 6,268 queries), so RotatE's
convention has no room to flatter it. G89's mid-rank can only cost G89.

FALSIFIERS, PREREGISTERED IN CHANNEL.md, EACH REFUTING ME:
  F1  G89-on-clean < RotatE-on-clean (0.0214) -> RotatE still wins where
      generalisation is required; G91's lift claim survives in weakened form and
      the LEDGER row moves to C rather than INVALID. I withdraw.
  F2  ARM-FULL misses G89's published 0.0355 to 4 dp -> the run is VOID and the
      second number is not reported at all.
  F3  the clean partition is not exactly 2,048 triples / 4,096 queries -> it is
      not H165's partition and nothing here is comparable.
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

sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G89_wn18rr_symbolic_mining"))

import kfcheck
from provenance import Control, Falsifier
from run import (  # G89's own code, imported not copied
    load_split_txt, pack_ids, mine_4_topologies_wn, evaluate_symbolic_wn,
)

CORPUS_WN = Path(ROOT) / "corpus" / "wn18rr"
H165_JSON = Path(SPIKES) / "H165_rotate_symmetry_leak" / "result.json"
G89_JSON = Path(SPIKES) / "G89_wn18rr_symbolic_mining" / "result.json"


def main() -> int:
    t0 = time.time()
    print("=== H174: G89 vs RotatE on the CLEAN partition ===", flush=True)

    # The comparands are READ FROM THE COMMITTED ARTIFACTS, never retyped. A
    # transcribed constant is a claim with no provenance (C).
    h165 = json.loads(H165_JSON.read_text())
    rotate_clean = h165["leak_partition"]["mrr_clean"]
    rotate_full = h165["reproduction"]["my_mrr_optimistic"]
    n_clean_q_h165 = h165["leak_partition"]["clean_queries"]
    g89_published = json.loads(G89_JSON.read_text())["metrics"]["mrr"]
    print(f"  comparands read from disk: RotatE full {rotate_full}, RotatE clean "
          f"{rotate_clean} ({n_clean_q_h165} q); G89 published {g89_published}", flush=True)

    train_txt = load_split_txt(CORPUS_WN / "train.txt")
    valid_txt = load_split_txt(CORPUS_WN / "valid.txt")
    test_txt = load_split_txt(CORPUS_WN / "test.txt")

    # H165's partition, recomputed from the same definition on raw strings.
    train_set = set(train_txt)
    clean_mask = [(o, p, s) not in train_set for (s, p, o) in test_txt]
    clean_txt = [t for t, keep in zip(test_txt, clean_mask) if keep]

    train, valid, test, npred, nent, r_map, e_map = pack_ids(train_txt, valid_txt, test_txt)
    # NOT a second pack_ids on the shorter list: entity ids are assigned in order
    # of first appearance, so re-packing renumbers every entity and the result
    # would index a DIFFERENT adjacency than out_adj/true_sp were built from.
    # pack_ids preserves order, so the mask applies directly to the packed list.
    clean_test = [t for t, keep in zip(test, clean_mask) if keep]

    out_adj = defaultdict(lambda: defaultdict(list))
    in_adj = defaultdict(lambda: defaultdict(list))
    for p, s, o in train:
        out_adj[p][s].append(o)
        in_adj[p][o].append(s)

    true_sp, true_po = defaultdict(set), defaultdict(set)
    for p, s, o in train + valid + test:          # FULL split, so filtering is unchanged
        true_sp[(s, p)].add(o)
        true_po[(p, o)].add(s)

    rules = mine_4_topologies_wn(train, out_adj, in_adj, npred)
    print(f"  mined {len(rules)} rules", flush=True)

    print("\n-- ARM-FULL (must reproduce G89's published number) --", flush=True)
    full = evaluate_symbolic_wn(test, nent, rules, out_adj, in_adj, true_sp, true_po, train)
    print("\n-- ARM-CLEAN (reverse not in train) --", flush=True)
    clean = evaluate_symbolic_wn(clean_test, nent, rules, out_adj, in_adj, true_sp, true_po, train)

    c1_ok = full["mrr"] == g89_published
    c2_ok = (len(clean_txt) == 2048) and (clean["n_queries"] == 4096) \
        and (clean["n_queries"] == n_clean_q_h165)
    c3_ok = full["n_queries"] == 6268

    controls = [
        Control("C1_reproduces_G89",
                why="ARM-FULL must land on G89's own published MRR or nothing here is about G89",
                can_fail_because="a different MRR, i.e. G89 is not deterministic and neither of "
                                 "its numbers can be attacked or defended",
                null_must_contain="ARM-FULL != published"),
        Control("C2_same_partition_as_H165",
                why="the clean split must be H165's exact partition: 2,048 triples / 4,096 queries",
                can_fail_because="a different leak definition or an off-by-one, which would make "
                                 "the two systems' clean numbers incomparable",
                null_must_contain="partition size mismatch"),
        Control("C3_full_split_evaluated",
                why="ARM-FULL covers all 6,268 queries",
                can_fail_because="a truncated test list",
                null_must_contain="query count != 6268"),
    ]
    controls[0].observe(c1_ok, {"arm_full": full["mrr"], "g89_published": g89_published})
    controls[1].observe(c2_ok, {"clean_triples": len(clean_txt), "clean_queries": clean["n_queries"],
                                "h165_clean_queries": n_clean_q_h165})
    controls[2].observe(c3_ok, {"full_queries": full["n_queries"]})

    f1 = clean["mrr"] < rotate_clean
    f2 = not c1_ok
    f3 = not c2_ok

    falsifiers = [
        Falsifier("F1_rotate_still_wins_on_clean",
                  refutes="that G91's 10.0x lift inverts once the leaked triples are removed",
                  fires_when=f"G89-on-clean < RotatE-on-clean ({rotate_clean})",
                  null_must_contain="G89 clean below RotatE clean"),
        Falsifier("F2_run_is_void",
                  refutes="that this run measured G89 at all",
                  fires_when="ARM-FULL does not reproduce G89's published MRR to 4 dp",
                  null_must_contain="ARM-FULL != published"),
        Falsifier("F3_partition_mismatch",
                  refutes="that this is H165's partition",
                  fires_when="clean split is not 2,048 triples / 4,096 queries",
                  null_must_contain="partition size mismatch"),
    ]
    falsifiers[0].observe(f1, {"g89_clean": clean["mrr"], "rotate_clean": rotate_clean})
    falsifiers[1].observe(f2, {"arm_full": full["mrr"], "g89_published": g89_published})
    falsifiers[2].observe(f3, {"clean_triples": len(clean_txt), "clean_queries": clean["n_queries"]})

    ratio = (clean["mrr"] / rotate_clean) if rotate_clean else None
    res = {
        "spike": "H174",
        "settles": "the operating-point question H165 left open (A18)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "partition": {"definition": "clean iff (o,p,s) NOT in train.txt",
                      "clean_triples": len(clean_txt), "clean_queries": clean["n_queries"]},
        "arm_full": full,
        "arm_clean": clean,
        "comparands_read_from_disk": {
            "g89_published_mrr": g89_published,
            "rotate_full_mrr": rotate_full,
            "rotate_clean_mrr": rotate_clean,
        },
        "verdict_on_clean": {
            "g89_symbolic": clean["mrr"], "rotate_g91": rotate_clean,
            "g89_over_rotate": round(ratio, 4) if ratio else None,
        },
        "tie_convention_note": "G89 mid-ranks (1+greater+equal//2, frequency-prior backoff at "
                               "score 0); G91 is optimistic. H165 measured RotatE's optimistic and "
                               "pessimistic MRR as identical (0.3546, 30 ties in 6,268 q), so the "
                               "asymmetry cannot flatter RotatE. G89's mid-rank can only cost G89.",
        "controls": {"C1_reproduces_G89": {"ok": c1_ok},
                     "C2_same_partition_as_H165": {"ok": c2_ok},
                     "C3_full_split_evaluated": {"ok": c3_ok}},
        "falsifiers": {"F1_rotate_still_wins_on_clean": {"fired": f1},
                       "F2_run_is_void": {"fired": f2},
                       "F3_partition_mismatch": {"fired": f3}},
    }

    out_json = Path(HERE) / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    print(f"\n  G89  full {full['mrr']:.4f}  clean {clean['mrr']:.4f}", flush=True)
    print(f"  G91  full {rotate_full:.4f}  clean {rotate_clean:.4f}", flush=True)

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(CORPUS_WN), str(Path(SPIKES) / "G89_wn18rr_symbolic_mining"),
              str(Path(SPIKES) / "H165_rotate_symmetry_leak")],
        artifacts=[str(out_json)],
        controls=controls, falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="if G89 scores below RotatE on the clean partition, G91's lift claim survives "
                  "in weakened form and this attack is withdrawn",
        allow_dirty=True,
        note="H174: G89 vs RotatE at ONE operating point — the non-leaked partition.")
    print(f"\nD6 Provenance Certified: ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
