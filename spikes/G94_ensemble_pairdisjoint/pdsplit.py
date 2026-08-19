#!/usr/bin/env python3
"""G94 — serve the PAIR-DISJOINT split through G59's interface, unchanged.

The embedding trainers (G76 distmult, G79 rotate, G72/G75 complex) all do
`import official as G59` and use exactly four names: CORPUS, load_split_txt,
pack_ids, slim_index. They are hardwired to the OFFICIAL split.

Rather than fork three trainers -- which would put the models under test at the
same time as the split, and let a difference be attributed to either -- this
module swaps only the DATA SOURCE and is injected as `official` via sys.modules.
The models are byte-identical to the ones that produced G76/G79/G88.

The partition is G48's, reused rather than reimplemented: group by UNORDERED
entity pair, assign whole groups. A reimplementation would risk a DIFFERENT
split, and then "the ensemble scores lower" could mean "on a harder split"
rather than "without the leak".
"""
import os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))
sys.path.insert(0, os.path.join(SPIKES, "G48_pairdisjoint_split"))
import official as _G59            # noqa: E402  borrow its parsers verbatim
import split as _G48               # noqa: E402  borrow its partitioner verbatim

SEED = 0xC0FFEE
CORPUS = os.path.join(HERE, "corpus_pd")     # written on first use
_cache = {}


def _materialise():
    """Write train/valid/test.txt for the pair-disjoint split, once."""
    if os.path.isfile(os.path.join(CORPUS, "test.txt")):
        return
    os.makedirs(CORPUS, exist_ok=True)
    oc = _G59.CORPUS
    rows = []
    for f in ("train.txt", "valid.txt", "test.txt"):
        rows += _G59.load_split_txt(os.path.join(oc, f))
    # FIELD ORDER. load_split_txt returns (HEAD, RELATION, TAIL) -- it parses
    # `h, r, t = line.split()`. G48's partitioner takes (p, s, o). Unpacking one
    # as the other groups by (RELATION, TAIL) instead of (HEAD, TAIL), which is
    # ~4x coarser: 59,734 groups at 5.19 triples/group against G48's published
    # 212,110 at 1.283.
    #
    # AND THE LEAK ASSERT PASSED ON IT. leak_count consumed the same mis-ordered
    # tuples, so it agreed with the bug and reported 0. A control that shares a
    # defect with the thing it checks confirms it. G54's own DONE line already
    # carries "field-order p,s,o" as a known hazard in this corpus; that is the
    # second time it has bitten.
    tri = [(r, h, t) for (h, r, t) in rows]
    tr, dv, te, ngroups = _G48.pair_disjoint_split(tri, SEED)
    for name, rows in (("train.txt", tr), ("valid.txt", dv), ("test.txt", te)):
        with open(os.path.join(CORPUS, name), "w", encoding="utf-8") as fh:
            for p, s, o in rows:
                fh.write(f"{s}\t{p}\t{o}\n")
    leak = _G48.leak_count(tr, te)
    with open(os.path.join(CORPUS, "SOURCE.txt"), "w") as fh:
        fh.write(f"pair-disjoint split of official FB15k-237, seed {SEED}\n"
                 f"groups {ngroups}  train {len(tr)}  valid {len(dv)}  "
                 f"test {len(te)}  leak {leak}\n"
                 f"partitioner: spikes/G48_pairdisjoint_split/split.py "
                 f"(reused, not reimplemented)\n")
    ratio = (len(tr) + len(dv) + len(te)) / ngroups
    print(f"[pdsplit] materialised: {ngroups} groups, train {len(tr)} "
          f"valid {len(dv)} test {len(te)}, LEAK {leak}, "
          f"{ratio:.3f} triples/group", flush=True)
    assert leak == 0, f"pair-disjoint split leaked {leak} — refusing to serve it"
    # SECOND, INDEPENDENT CHECK, because the leak assert above was fooled once.
    # G48 published 1.283 triples per unordered entity pair. A grouping keyed on
    # the wrong field lands at 5.19. This catches the field order even when
    # leak_count agrees with the bug.
    assert 1.20 < ratio < 1.40, (
        f"triples/group {ratio:.3f} is not near G48's published 1.283 — "
        f"the grouping key is wrong even though leak_count returned {leak}")


def load_split_txt(path):
    return _G59.load_split_txt(path)


def pack_ids(train_txt, valid_txt, test_txt):
    return _G59.pack_ids(train_txt, valid_txt, test_txt)


def slim_index(train):
    return _G59.slim_index(train)


_materialise()
