#!/usr/bin/env python3
"""G98 — finish G94: does the 5-way SELECTOR survive removing the entity-pair leak?

Run: python3 spikes/G98_pairdisjoint_null/pdnull.py

THE QUESTION, and why it is the one that decides three earlier rows.
G95 nulled G88's valid-select argmax and it survived; G96 measured that the
frozen PER-KEY table does not; G97 measured the MIN_N constant behind it. All
three ran on the OFFICIAL FB15k-237 split, and G48 measured that 30.0% of that
test set has a train edge on the same unordered entity pair, scoring 0.5318
against 0.1503 for the rest. So every one of those verdicts is stated over data
whose easy third is memorisable, and none of them says whether the selector is
selecting for structure or for the leak.

G94 claimed exactly this measurement, reached ONE arm of five, and its executing
session stopped. §2: PARTIAL is not a verdict -- split the item and finish the
piece you can. This is the piece.

WHAT IS REUSED AND WHY NOTHING IS REIMPLEMENTED.
  * the SPLIT is G94's `pdsplit`, which is G48's partitioner, injected as
    `official` via sys.modules so the trainers are byte-identical to the runs
    that produced G76/G79/G88 and only the DATA moves;
  * the SELECTOR is `G88_5way_hybrid/mix.py::freeze_dir_select` / `apply_dir`,
    called unmodified;
  * the NULL is G95's: permute the frozen choice vector across keys preserving
    its exact multiset, so arm quality and selection budget are held fixed and
    only the key-to-arm MATCH is destroyed. A20 is satisfied by construction --
    a permutation that lands the good arms on the right keys scores exactly what
    the real selector scores, so the null CAN contain the effect.

WHY THIS FILE DOES NOT USE G94's `run_arm.py`, AND THE DEFECT CLASS THAT SAYS SO.
`run_arm.py` chdirs into each arm's own spike directory before importing its
trainer. `G79_rotate_all_entity/rotate.py` sets
`EMB_PATH = os.path.join(HERE, "rotate_emb.npz")` and `train_or_load` RETURNS
THE CACHED FILE when it exists -- and it exists, because it is the file
`G88_5way_hybrid/mix.py:71` loads. `run_arm.py rotate` would therefore have
loaded the OFFICIAL-split RotatE, evaluated it against the pair-disjoint test
set, printed `loaded RotatE embeddings`, and reported it as the pair-disjoint
arm.

  CLASS: A CACHE KEYED ON A PATH AND NOT ON THE DATA IT WAS DERIVED FROM.
  Swap the corpus underneath it and the cache is unaware; it answers the OLD
  question and the run reports the answer as the new one. Family C.

IT HAD ALREADY FIRED, in G94, in the arm its headline rests on.
`spikes/G94_ensemble_pairdisjoint/rules_cache.json` is byte-identical
(`c083dd1e9fd2...`) to the rule set in G65/G66/G67/G72/G73/G75/G76/G77/G79 --
`load_or_mine_rules` found `G72_RULES` and `shutil.copy2`'d it in, and G94's own
log says `loaded 2201 rules (G72)`, not `mined`. Those rules are mined on the
OFFICIAL train set, which carries edges on entity pairs that are in the
pair-disjoint TEST set. So G94's `G51 0.2473`, the number its RESULT.md builds
"remove the leak and the ordering inverts" on, was scored with LEAKED rules and
is expected to be inflated. Corrected in `out/RETRACTIONS.md`; G98's symbolic arm
is `G64.mine_all_4_topologies_fast`, which mines from the `train` list in
process and has no on-disk cache at all.

The nine other copies are on the split they were mined for and are not wrong.
The defect is that NO copy records which corpus produced it, so the moment one
corpus moves nothing can tell -- which is why C1 recomputes the split invariants
here instead of trusting `pdsplit`'s own asserts. Those asserts sit AFTER an
`if os.path.isfile(...): return`, so on a materialised corpus they do not run:
the same class again, one level up, in the guard against it.

PRE-REGISTERED IN `CHANNEL.md` BEFORE THIS DIRECTORY EXISTED:
  F1  mix test MRR is NOT above the null p95  -> the argmax carries no
      key-specific information leak-free, and G95's verdict was leak-dependent.
  F2  mix test MRR <= the best SINGLE arm     -> the 5-way mix is not worth
      having leak-free.
  F3  mix test MRR <= the SYMBOLIC g64 arm    -> the whole embedding+selector
      stack is not worth its cost leak-free.
All three are decided INSIDE one run on one split materialisation, because G94
recorded that its pair-disjoint corpus is a DIFFERENT materialisation from G48's
and is not interchangeable with G54's 0.2313.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
G88 = os.path.join(SPIKES, "G88_5way_hybrid")
G94 = os.path.join(SPIKES, "G94_ensemble_pairdisjoint")


def _numpy_pythons():
    out = [os.path.join(SPIKES, "S5_hdc_prototype", ".venv", "bin", "python")]
    parent = os.path.dirname(ROOT)
    try:
        names = os.listdir(parent)
    except OSError:
        names = []
    for name in names:
        out.append(os.path.join(parent, name, "spikes",
                                "S5_hdc_prototype", ".venv", "bin", "python"))
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


# GUARDED, and at module level only because every import below needs numpy.
# G96's finding: `null.py` execv's unconditionally at module level, so
# `import null` under a numpy-less interpreter replaces the process with G95's
# entire run. This one returns without exec'ing when numpy is already present,
# so importing this file is safe; G97 pays the same care.
_reexec_with_numpy()

import numpy as np                                            # noqa: E402

sys.path.insert(0, os.path.join(SPIKES, "harness"))
for _d in ("G48_pairdisjoint_split", "G51_bayesian_lift_scoring",
           "G59_official_split", "G64_bidirectional_topologies",
           "G72_complex_all_entity", "G75_complex_gate",
           "G76_distmult_min10", "G79_rotate_all_entity"):
    sys.path.insert(0, os.path.join(SPIKES, _d))
sys.path.insert(0, G88)

# THE SWAP, and it happens BEFORE any trainer is imported, because a trainer
# binds `official` at import time. Loaded by explicit path rather than by
# putting G94 on sys.path: G94 also contains a `distmult.py`, and shadowing
# G76's would put the MODEL under test at the same time as the SPLIT.
_spec = importlib.util.spec_from_file_location("pdsplit", os.path.join(G94, "pdsplit.py"))
pdsplit = importlib.util.module_from_spec(_spec)
sys.modules["pdsplit"] = pdsplit
_spec.loader.exec_module(pdsplit)          # materialises corpus_pd on first use
sys.modules["official"] = pdsplit          # <-- every `import official` below

import bayesian_lift as G51                                   # noqa: E402
import complex as G72                                         # noqa: E402
import distmult as G76                                        # noqa: E402
import official as G59                                        # noqa: E402  == pdsplit
import rotate as G79                                          # noqa: E402
import run_g64 as G64                                         # noqa: E402
import split as G48                                           # noqa: E402
import mix as G88MIX                                          # noqa: E402  THE SUBJECT
from provenance import Control, Falsifier                     # noqa: E402
from kfcheck import certify                                   # noqa: E402

assert G59 is pdsplit, "the sys.modules swap did not take"

CORPUS = pdsplit.CORPUS
KEYS = G88MIX.KEYS
DEFAULT = "distmult"
SEED = 0xC0FFEE
DRAWS = 1000

# The pair-disjoint arms. DistMult is G94's, already trained on this corpus;
# ComplEx and RotatE are trained here and saved HERE, never into G75/G79, so the
# official-split embeddings that G88/G95/G96/G97 load are untouched. C4 asserts
# that all three differ from their official counterparts.
DM_PD = os.path.join(G94, "distmult_emb.npz")
CX_PD = os.path.join(HERE, "complex_emb_pd.npz")
ROT_PD = os.path.join(HERE, "rotate_emb_pd.npz")
DM_OFFICIAL = os.path.join(SPIKES, "G76_distmult_min10", "distmult_emb.npz")
CX_OFFICIAL = G88MIX.CX_EMB
ROT_OFFICIAL = G88MIX.ROT_EMB

# G94's published DistMult on this corpus, reproduced by C5.
G94_DISTMULT = 0.2422
# G48's published triples per unordered entity pair, the figure that catches a
# wrong grouping key even when a leak count agrees with the bug.
G48_RATIO = 1.283
PD_TEST_N = 46518


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_invariants():
    """Recompute the pair-disjoint invariants from the corpus ON DISK.

    NOT read from `SOURCE.txt` and NOT trusted to `pdsplit`'s own asserts: those
    sit after an `if os.path.isfile(test.txt): return`, so on an already
    materialised corpus they never execute. A check on the cold path only is the
    same defect class this spike is about.

    FIELD ORDER, stated once and never inferred. `load_split_txt` parses
    `h, r, t = line.split()` and returns (HEAD, RELATION, TAIL); `split.py` takes
    (PREDICATE, SUBJECT, OBJECT). Unpacking one as the other groups by
    (RELATION, TAIL) and lands at ~5.19 triples/group against G48's 1.283 -- and
    a leak count fed the same mis-ordered tuples AGREES WITH THE BUG and reports
    0. That is G94's own recorded defect, and G54's DONE line carries it too.
    """
    named = {}
    for name in ("train.txt", "valid.txt", "test.txt"):
        named[name] = [(h, r, t) for (h, r, t)
                       in G59.load_split_txt(os.path.join(CORPUS, name))]
    tr_pso = [(r, h, t) for (h, r, t) in named["train.txt"]]
    te_pso = [(r, h, t) for (h, r, t) in named["test.txt"]]
    leak = G48.leak_count(tr_pso, te_pso)
    groups = set()
    total = 0
    for rows in named.values():
        for (h, r, t) in rows:
            groups.add((h, t) if h <= t else (t, h))
            total += 1
    ratio = total / len(groups)
    return {
        "leak_train_test": int(leak),
        "n_groups": len(groups),
        "n_total": total,
        "triples_per_group": round(ratio, 4),
        "g48_published_ratio": G48_RATIO,
        "n_train": len(named["train.txt"]),
        "n_valid": len(named["valid.txt"]),
        "n_test": len(named["test.txt"]),
        "corpus_sha256": {n: sha256_file(os.path.join(CORPUS, n))
                          for n in ("train.txt", "valid.txt", "test.txt")},
    }


def train_or_load_pd(kind, train, valid, nent, npred, eval_sp, eval_po):
    """Each arm's OWN published protocol, on the pair-disjoint corpus.

    The rng is created from that arm's seed, advanced by its validation-sample
    draw, and then handed to the trainer -- the exact order `G75_complex_gate`
    and `G79_rotate_all_entity` use. Reseeding for the trainer would be a
    different protocol from the one that produced the published numbers.
    """
    mod = G72 if kind == "complex" else G79
    path = CX_PD if kind == "complex" else ROT_PD
    fields = ("E_re", "E_im", "R_re", "R_im") if kind == "complex" else ("E_re", "E_im", "theta")
    if os.path.isfile(path):
        z = np.load(path)
        best_ep = int(z["best_epoch"])
        print(f"loaded {kind} (pair-disjoint) {os.path.basename(path)} "
              f"best_epoch={best_ep} sha={sha256_file(path)[:12]}", flush=True)
        if best_ep < mod.MIN_EPOCH:
            raise RuntimeError(f"cached best_epoch={best_ep} < min_epoch={mod.MIN_EPOCH}")
        return tuple(z[f] for f in fields), best_ep, float(z["best_valid_sample_mrr"])

    rng = np.random.default_rng(mod.SEED)
    vi = rng.choice(len(valid), size=min(mod.VALID_SAMPLE, len(valid)), replace=False)
    valid_sample = [valid[int(i)] for i in vi]
    fn = G72.train_complex if kind == "complex" else G79.train_rotate
    print(f"training {kind} on PAIR-DISJOINT (seed={mod.SEED} dim={mod.DIM} "
          f"min_epoch={mod.MIN_EPOCH}) ...", flush=True)
    t0 = time.time()
    emb, hist, best_ep, best_valid = fn(train, nent, npred, rng,
                                        valid_q=valid_sample,
                                        eval_sp=eval_sp, eval_po=eval_po)
    np.savez(path, **dict(zip(fields, emb)),
             best_epoch=np.int32(best_ep),
             best_valid_sample_mrr=np.float64(-1.0 if best_valid is None else best_valid))
    with open(os.path.join(HERE, f"{kind}_hist_pd.json"), "w") as fh:
        json.dump(hist, fh)
    print(f"trained {kind} in {time.time()-t0:.1f}s best_epoch={best_ep} "
          f"valid_sample_mrr={best_valid} saved {os.path.basename(path)}", flush=True)
    if best_ep is None or best_ep < mod.MIN_EPOCH:
        raise RuntimeError(f"selection violated min_epoch={mod.MIN_EPOCH}: {best_ep}")
    return emb, best_ep, best_valid


def build_rows():
    """G95's pipeline, verbatim in order, over the PAIR-DISJOINT corpus."""
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"PAIR-DISJOINT split: train={len(train)} valid={len(valid)} "
          f"test={len(test)} npred={npred} nent={nent}", flush=True)

    all_tri = train + valid + test
    true_sp, true_po = G51.build_filter_index(all_tri)
    eval_sp, eval_po = G72.build_true_lists(all_tri)
    idx = G59.slim_index(train)

    out_adj = defaultdict(lambda: defaultdict(list))
    in_adj = defaultdict(lambda: defaultdict(list))
    for p, s, o in train:
        out_adj[p][s].append(o)
        in_adj[p][o].append(s)

    # MINED FROM `train`, IN PROCESS, NO ON-DISK CACHE. This is the line G94's
    # symbolic arm did not have: its rules came from a copied file whose corpus
    # was the official split.
    t0 = time.time()
    rules_by_head, _ = G64.mine_all_4_topologies_fast(train, out_adj, in_adj, npred)
    n_rules = sum(len(r) for r in rules_by_head.values())
    print(f"Mined {n_rules} G64 rules on PAIR-DISJOINT train in "
          f"{time.time()-t0:.1f}s.", flush=True)

    cx, best_cx, _ = train_or_load_pd("complex", train, valid, nent, npred, eval_sp, eval_po)
    rot, best_rot, _ = train_or_load_pd("rotate", train, valid, nent, npred, eval_sp, eval_po)
    zd = np.load(DM_PD)
    print(f"loaded distmult (pair-disjoint, G94) sha={sha256_file(DM_PD)[:12]}", flush=True)

    def score(split, label):
        t = time.time()
        rows = G64.score_split_4topo(split, nent, rules_by_head, out_adj,
                                     in_adj, true_sp, true_po, idx)
        for r in rows:
            r["ranks"]["g64"] = r["ranks"].pop("g51")
        c_t, c_d, _ = G72.rank_complex(split, cx[0], cx[1], cx[2], cx[3], eval_sp, eval_po)
        G88MIX.attach_named(rows, split, c_t, c_d, "complex")
        d_t, d_d, _ = G76.rank_distmult(split, zd["E"], zd["R"], eval_sp, eval_po)
        G88MIX.attach_named(rows, split, d_t, d_d, "distmult")
        r_t, r_d, _ = G79.rank_rotate(split, rot[0], rot[1], rot[2], eval_sp, eval_po)
        G88MIX.attach_named(rows, split, r_t, r_d, "rotate")
        print(f"scored {label}: {len(rows)} rows in {time.time()-t:.1f}s", flush=True)
        return rows

    print("Scoring VALID...", flush=True)
    valid_rows = score(valid, "valid")
    print("Scoring TEST...", flush=True)
    test_rows = score(test, "test")
    return valid_rows, test_rows, len(test), n_rules, (best_cx, best_rot)


def official_choice():
    """G88's frozen official-split choice vector, for an OBSERVATION only.

    Deliberately NOT a falsifier. G96 recorded that promoting a post-hoc
    subset figure into a threshold is how a measurement becomes an accusation;
    the agreement rate here is reported with its own chance baseline and no
    verdict is attached to it.
    """
    p = os.path.join(G88, "result.json")
    if not os.path.isfile(p):
        return None
    try:
        raw = json.loads(open(p, encoding="utf-8").read())
    except Exception:
        return None
    for node in (raw, raw.get("select", {}) if isinstance(raw, dict) else {}):
        if not isinstance(node, dict):
            continue
        for k, v in node.items():
            if "choice" in k.lower() and isinstance(v, dict) and v:
                return v
    return None


def main() -> int:
    t0 = time.time()
    print("=== G98: the 5-way selector on the PAIR-DISJOINT split ===", flush=True)

    inv = split_invariants()
    print(f"split invariants: leak={inv['leak_train_test']} "
          f"groups={inv['n_groups']} triples/group={inv['triples_per_group']} "
          f"test={inv['n_test']}", flush=True)

    valid_rows, test_rows, n_test, n_rules, (best_cx, best_rot) = build_rows()

    # G88's OWN selector, unmodified, fitted on PAIR-DISJOINT validation.
    mask, choice = G88MIX.freeze_dir_select(valid_rows, KEYS, default=DEFAULT)
    real = G88MIX.apply_dir(test_rows, choice, default=DEFAULT)["mrr"]
    counts = dict(mask["counts"])
    print(f"\npair-disjoint selector: counts={counts} sha={mask['sha256'][:12]}")
    # n_small_default IS NOT DECORATION. The pair-disjoint validation set is
    # 46,517 against the official split's 17,535, so MIN_N=20 gates far fewer
    # keys here -- and a shift in the arm COUNTS between the two splits is
    # therefore partly a function of how much validation data each key got, not
    # only of the leak. Reporting counts without this number would be A26 with
    # the knob held by the split rather than by the author.
    print(f"  keys={mask['n_keys']} fallback_below_MIN_N={mask['n_small_default']} "
          f"(MIN_N={mask['min_n']})")
    print(f"pair-disjoint MIX test MRR: {real:.4f}")

    singles = {k: G59.metrics([r["ranks"][k] for r in test_rows])["mrr"] for k in KEYS}
    best_single = max(singles, key=singles.get)
    print("single arms:", {k: round(v, 4) for k, v in singles.items()}, flush=True)

    # THE NULL, G95's, unchanged: permute the choice VECTOR across keys with the
    # multiset carried, so every draw makes exactly as many departures from the
    # default as the real selector did.
    keys = sorted(choice)
    vec = [choice[k] for k in keys]
    want = Counter(vec)
    rng = np.random.default_rng(SEED)
    draws, multiset_ok = [], True
    for i in range(DRAWS):
        perm = list(vec)
        rng.shuffle(perm)
        if Counter(perm) != want:
            multiset_ok = False
        draws.append(G88MIX.apply_dir(test_rows, dict(zip(keys, perm)),
                                      default=DEFAULT)["mrr"])
        if (i + 1) % 200 == 0:
            print(f"  null draw {i+1}/{DRAWS}", flush=True)
    draws = np.array(draws)
    med = float(np.median(draws))
    p95 = float(np.percentile(draws, 95))
    mx = float(draws.max())
    ge = int((draws >= real).sum())
    ge_single = int((draws >= singles[best_single]).sum())
    print(f"\nNULL over {DRAWS} label-permuted selectors (multiset preserved):")
    print(f"  median {med:.4f}  p95 {p95:.4f}  max {mx:.4f}  min {draws.min():.4f}")
    print(f"  draws >= mix {real:.4f}: {ge}/{DRAWS}")
    print(f"  draws >= best single arm {best_single} {singles[best_single]:.4f}: "
          f"{ge_single}/{DRAWS}")
    print(f"  mix - null median = {real - med:+.4f}", flush=True)

    # OBSERVATION, no threshold: how much of G88's official table survives.
    off = official_choice()
    agree = None
    if off:
        shared = [k for k in choice if str(k) in off or k in off]
        hits = 0
        for k in shared:
            v = off.get(k, off.get(str(k)))
            if v == choice[k]:
                hits += 1
        if shared:
            agree = {"shared_keys": len(shared), "agree": hits,
                     "rate": round(hits / len(shared), 4)}
            print(f"  OBSERVATION official-vs-pairdisjoint choice agreement: "
                  f"{hits}/{len(shared)} = {agree['rate']}", flush=True)

    c1 = Control(
        'pair_disjoint_split_reproduces',
        'every number here is about the leak-free split only if the split on '
        'disk still IS leak-free and still IS G48\'s grouping',
        null_must_contain='a leaking or mis-grouped corpus. leak_count and the '
                          'triples-per-group ratio are recomputed FROM THE FILES '
                          'here, not read from SOURCE.txt and not delegated to '
                          'pdsplit\'s asserts, which sit after an early return '
                          'and do not run on a materialised corpus',
        can_fail_because='a changed seed, a changed partitioner, or the (h,r,t) '
                         'vs (p,s,o) field-order swap that groups by '
                         '(RELATION, TAIL) and lands at ~5.19 triples/group '
                         'while leak_count, fed the same tuples, still says 0')
    c1_ok = (inv["leak_train_test"] == 0
             and 1.20 < inv["triples_per_group"] < 1.40
             and inv["n_test"] == PD_TEST_N)
    c1.observe(c1_ok, inv,
               f'leak {inv["leak_train_test"]}, {inv["triples_per_group"]} '
               f'triples/group vs G48 {G48_RATIO}, test n {inv["n_test"]}')

    c2 = Control(
        'null_preserves_selection_budget',
        'a draw that changes the arm counts is a different experiment, not a '
        'null of this selector',
        null_must_contain='a broken permutation. Counter(perm) is compared to '
                          'Counter(vec) on EVERY draw',
        can_fail_because='shuffling with replacement, or permuting the keys '
                         'instead of the values')
    c2.observe(multiset_ok, [len(draws), len(keys)],
               f'{DRAWS} draws, each carrying {counts}')

    c3 = Control(
        'null_is_non_degenerate',
        'a null whose draws all score the same cannot contain the effect and is '
        'not a null (A20)',
        null_must_contain='spread. If the selector were irrelevant every '
                          'permutation would score identically and the spread '
                          'would be 0 -- reachable, and exactly what a dead null '
                          'looks like',
        can_fail_because='every permutation scores identically, which would mean '
                         'apply_dir ignores the choice')
    c3.observe(float(draws.std()) > 0,
               [float(draws.min()), float(draws.max()), float(draws.std())],
               f'spread {draws.max()-draws.min():.4f}, sd {draws.std():.4f}')

    c4 = Control(
        'arms_are_pair_disjoint_not_official',
        'THE CONTROL FOR THIS SPIKE\'S OWN DEFECT CLASS: a trainer whose cache '
        'key is a path and not the data returns the OLD corpus\'s answer and the '
        'run reports it as the new one',
        null_must_contain='an arm that is byte-identical to its official-split '
                          'counterpart. That is precisely what `run_arm.py '
                          'rotate` would have produced, since rotate.py\'s '
                          'EMB_PATH is the file G88 loads and train_or_load '
                          'returns it when present',
        can_fail_because='pointing an EMB_PATH at the official file, or chdir-ing '
                         'into the arm\'s own spike directory before import')
    arm_sha = {'complex_pd': sha256_file(CX_PD), 'rotate_pd': sha256_file(ROT_PD),
               'distmult_pd': sha256_file(DM_PD),
               'complex_official': sha256_file(CX_OFFICIAL),
               'rotate_official': sha256_file(ROT_OFFICIAL),
               'distmult_official': sha256_file(DM_OFFICIAL)}
    c4_ok = all(arm_sha[f'{k}_pd'] != arm_sha[f'{k}_official']
                for k in ('complex', 'rotate', 'distmult'))
    c4.observe(c4_ok, arm_sha,
               'each pair-disjoint arm differs from its official-split counterpart')

    c6 = Control(
        'arms_postdate_the_corpus_they_claim',
        'THE MECHANISED FORM OF THIS SPIKE\'S DEFECT CLASS (§12.10: a guardrail '
        'that is written but not mechanised will be violated again by its own '
        'author). An artifact derived from a corpus must be NEWER than that '
        'corpus; G94\'s rules_cache.json is stamped 05:00 against a corpus_pd '
        'stamped 16:28 and nothing looked',
        null_must_contain='an arm older than the corpus. That is a reachable '
                          'state and is the exact state G94 shipped in',
        can_fail_because='a cached arm surviving a corpus re-materialisation, '
                         'which is precisely how a path-keyed cache answers the '
                         'old question')
    corpus_mtime = max(os.path.getmtime(os.path.join(CORPUS, n))
                       for n in ('train.txt', 'valid.txt', 'test.txt'))
    arm_mtime = {k: os.path.getmtime(p) for k, p in
                 (('complex_pd', CX_PD), ('rotate_pd', ROT_PD), ('distmult_pd', DM_PD))}
    c6.observe(all(m > corpus_mtime for m in arm_mtime.values()),
               {'corpus_newest_mtime': round(corpus_mtime, 1),
                'arm_mtime': {k: round(v, 1) for k, v in arm_mtime.items()},
                'g94_rules_cache_mtime': round(
                    os.path.getmtime(os.path.join(G94, 'rules_cache.json')), 1)
                if os.path.isfile(os.path.join(G94, 'rules_cache.json')) else None},
               'every arm is newer than the corpus it was trained on')

    c5 = Control(
        'g94_distmult_reproduces',
        'G98 inherits G94\'s DistMult rather than retraining it, so nothing here '
        'is continuous with G94 unless that arm still scores what G94 published',
        null_must_contain='a different mrr. The rank is recomputed from the npz '
                          'over rows built from the corpus, so a drifted '
                          'embedding or a re-materialised split both miss',
        can_fail_because='the npz being replaced, or corpus_pd being regenerated '
                         'under a different seed')
    c5.observe(round(singles['distmult'], 4) == G94_DISTMULT,
               {'reproduced': round(singles['distmult'], 6),
                'g94_published': G94_DISTMULT,
                'distmult_emb_sha256': arm_sha['distmult_pd']},
               f'reproduced {singles["distmult"]:.4f} vs G94 {G94_DISTMULT}')

    f1 = Falsifier(
        'F1_selector_carries_no_signal_leak_free',
        'refutes G95 as a statement about structure: the argmax carries no '
        'key-specific information once the entity-pair leak is gone, so the '
        '5-way gain G95 defended was leak-dependent',
        fires_when='mix test MRR is NOT above the null p95',
        null_must_contain='both answers. The null max is a realisable '
                          'permutation score, so the mix can land above or below it')
    f1.observe(not (real > p95), [real, p95, ge],
               f'mix {real:.4f} vs null p95 {p95:.4f}, {ge}/{DRAWS} >= mix')

    f2 = Falsifier(
        'F2_mix_does_not_beat_best_single_arm',
        'refutes the ensemble leak-free: if the best single arm matches the mix '
        'on a split that cannot leak, the 5-way machinery is not worth having',
        fires_when='mix test MRR <= the best single arm on the same rows',
        null_must_contain='both answers; both come from the same test rows')
    f2.observe(real <= singles[best_single],
               [real, singles[best_single], best_single],
               f'mix {real:.4f} vs best single {best_single} '
               f'{singles[best_single]:.4f}')

    f3 = Falsifier(
        'F3_mix_does_not_beat_symbolic',
        'refutes the whole embedding+selector stack leak-free: the symbolic arm '
        'needs no embeddings, no training and no selector',
        fires_when='mix test MRR <= the g64 symbolic arm alone on the same rows',
        null_must_contain='both answers, from the same test rows. G94 reported '
                          'symbolic AHEAD of DistMult on this split, so this '
                          'falsifier is live rather than decorative')
    f3.observe(real <= singles['g64'], [real, singles['g64']],
               f'mix {real:.4f} vs g64 {singles["g64"]:.4f}')

    out = os.path.join(HERE, 'pairdisjoint_null.json')
    json.dump({'spike': 'G98', 'split': 'pair-disjoint (G48 partitioner, G94 '
               'materialisation)', 'seed': SEED, 'draws': DRAWS,
               'split_invariants': inv,
               'n_g64_rules': n_rules,
               'best_epoch': {'complex': best_cx, 'rotate': best_rot},
               'arm_sha256': arm_sha,
               'arm_mtime_vs_corpus': {'corpus_newest': round(corpus_mtime,1),
                                      'arms': {k: round(v,1) for k,v in arm_mtime.items()}},
               'mix_test_mrr': round(real, 6),
               'selector_sha256': mask['sha256'], 'counts': counts,
               'selector_mask': {k: mask[k] for k in
                                 ('min_n', 'n_keys', 'n_small_default')},
               'n_keys': len(keys), 'n_test_triples': n_test,
               'single_arm_mrr': {k: round(v, 6) for k, v in singles.items()},
               'best_single_arm': best_single,
               'null_median': round(med, 6), 'null_p95': round(p95, 6),
               'null_max': round(mx, 6), 'null_min': round(float(draws.min()), 6),
               'null_sd': round(float(draws.std()), 6),
               'draws_ge_mix': ge, 'draws_ge_best_single_arm': ge_single,
               # THE DRAWS THEMSELVES, G95's rule: a null reported as five
               # statistics cannot be re-analysed against a question its author
               # did not ask, and the first such question arrived immediately.
               'null_draws': [round(float(x), 6) for x in draws],
               'mix_minus_null_median': round(real - med, 6),
               'official_choice_agreement': agree,
               'elapsed_sec': round(time.time() - t0, 2)},
              open(out, 'w'), indent=1, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[CORPUS, G88, os.path.join(SPIKES, 'harness')],
        # THE EMBEDDINGS MOVED FROM `artifacts` TO `captures`, v2, AND THAT IS A
        # TIGHTER PIN RATHER THAN A LOOSER ONE -- said explicitly because
        # "relax a dep until the gate stops refusing" is the shape of weakening
        # a gate to pass it, which §5 forbids outright.
        #
        # v1 listed the two .npz under `artifacts` against `deps` that include
        # `spikes/harness`, and certify refused: `STALE ARTIFACT
        # complex_emb_pd.npz predates harness source by 0.1h`. It was RIGHT
        # about the mtimes and WRONG about the dependency -- five lanes commit
        # to `spikes/harness` continuously, one landed during the 870 s this run
        # spent training, and an embedding does not depend on the harness at
        # all. It depends on the CORPUS and its trainer. Left as it was, the
        # refusal is a function of another lane's commit clock, so it would
        # refuse a correct run and pass an incorrect one whenever the ordering
        # happened to flip: family A, an instrument that cannot produce the
        # answer.
        #
        # What replaces it is strictly stronger on the property that matters.
        # `captures` pins each arm by CONTENT (sha256, and family B refuses the
        # empty-input hash), and the dependency the arms actually have -- being
        # newer than the corpus they were trained on -- is now asserted
        # directly by C6, which is the mtime comparison G94's rules_cache.json
        # fails by eleven and a half hours. mtime-against-an-unrelated-tree is
        # traded for content-hash plus mtime-against-the-real-input.
        # `pairdisjoint_null.json` stays an artifact: it is written at the end
        # of the run, so it postdates every dep by construction, and it carries
        # all three arm hashes.
        artifacts=[out],
        captures=[('complex_emb_pd_sha256', arm_sha['complex_pd']),
                  ('rotate_emb_pd_sha256', arm_sha['rotate_pd']),
                  ('distmult_emb_pd_sha256', arm_sha['distmult_pd'])],
        controls=[c1, c2, c3, c4, c5, c6], falsifiers=[f1, f2, f3],
        allow_dirty=True,
        note='G98 finishes G94. G95/G96/G97 all measured G88\'s valid-select '
             'argmax on the OFFICIAL FB15k-237 split, of which G48 measured 30.0% '
             'of test to have a train edge on the same unordered entity pair. '
             'G98 runs G88\'s own selector and G95\'s own null over the '
             'pair-disjoint split, with ComplEx and RotatE retrained on it under '
             'their own published protocols and G94\'s DistMult inherited. The '
             'symbolic arm is mined in process from the pair-disjoint train set, '
             'because G94\'s was a copied cache mined on the official one.',
        falsifier='If the mix were not above the p95 of 1000 multiset-preserving '
                  'label permutations of its own selector on a split that cannot '
                  'leak, then G95\'s verdict would be a statement about the leak '
                  'rather than about selection, and the ensemble thread would be '
                  'refuted where it matters.')
    print(f'\ncertify ok={ok}')
    for p in problems:
        print('  ' + p)
    print(f'elapsed {time.time()-t0:.1f}s')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
