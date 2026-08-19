#!/usr/bin/env python3
"""Shared FB15k-237 split + protocol tags for the graph eval setup.

triples.bin is official TRAIN (272,115). Official valid/test live in
corpus/fb15k237/ (G59, git 2e440e0). A literature MRR (TransE 0.29, RotatE)
is still a number from a paper, not from this tree; quoting it is A18.

  python3 -c 'from kg_split import official_test_status; print(official_test_status())'
"""
from __future__ import annotations

import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

OFFICIAL_TEST_CANDIDATES = (
    os.path.join(ROOT, "corpus", "FB15k-237", "test.txt"),
    os.path.join(ROOT, "corpus", "fb15k237", "test.txt"),
    os.path.join(ROOT, "spikes", "S52_realkg", "test.txt"),
    os.path.join(ROOT, "spikes", "S52_realkg", "FB15k_237", "test.txt"),
)


def official_test_status():
    """Observe. Presence of a file is not a licence check and not a literature MRR."""
    found = [p for p in OFFICIAL_TEST_CANDIDATES if os.path.isfile(p) and os.path.getsize(p) > 0]
    scored = os.path.isfile(os.path.join(ROOT, "spikes", "G59_official_split", "official.json"))
    if scored and found:
        reason = (
            "G59 scored official test; excerpt now in "
            "corpus/refs/sun-2019-rotate-fb15k237.txt (Sun 2019 Table 5 / "
            "README @2e440e0) but trainer/dim do not match, so "
            "literature_compare stays unavailable as a headline (G35/A18)"
        )
    elif found:
        reason = "official valid/test on disk; no scored official-test run yet"
    else:
        reason = "triples.bin is FB15k-237 TRAIN only; official test not in tree"
    return {
        "official_test_available": bool(found),
        "paths_found": found,
        "official_test_scored": bool(scored and found),
        "literature_compare": "unavailable",
        "reason": reason,
    }


def field_order_ok(tri, npred, nent):
    if not tri:
        return False, {"reason": "empty"}
    max_p = max(p for p, s, o in tri)
    max_s = max(s for p, s, o in tri)
    max_o = max(o for p, s, o in tri)
    ok = max_p < npred and max_s < nent and max_o < nent
    return ok, {
        "declared_order": "p,s,o",
        "npred": npred,
        "nent": nent,
        "max_p": max_p,
        "max_s": max_s,
        "max_o": max_o,
    }


def pair_disjoint_split(tri, rng_shuffle, frac_train=0.70, frac_dev=0.15):
    """Same partition G51 uses. rng_shuffle(list) mutates in place."""
    groups = defaultdict(list)
    for p, s, o in tri:
        groups[(s, o) if s <= o else (o, s)].append((p, s, o))
    keys = list(groups)
    rng_shuffle(keys)
    n_target_train = int(len(tri) * frac_train)
    n_target_dev = int(len(tri) * frac_dev)
    train, dev, test = [], [], []
    for k in keys:
        g = groups[k]
        if len(train) < n_target_train:
            train.extend(g)
        elif len(dev) < n_target_dev:
            dev.extend(g)
        else:
            test.extend(g)
    return train, dev, test, len(groups)
