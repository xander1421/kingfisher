#!/usr/bin/env python3
"""G99 — G88's `choice_sha256` now has an opening. This is the check that it does.

Run: python3 spikes/G99_choice_opening/verify.py     (< 1 s, reads artifacts only)

G88 published a 64-hex `choice_sha256` over `{min_n, choice}` (`mix.py:124`) and
emitted only the five per-arm COUNTS. The per-key table the digest pins was in no
artifact, so the frozen selector could not be compared against a re-fit, another
split, or a later run without re-executing G88's whole pipeline -- which is what
G98 hit when it wanted the official-vs-pair-disjoint agreement and had to record
the observation as uncomputable.

CLASS: A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS. Worse than publishing
neither, because a reader takes the digest as evidence the table is fixed and has
no way to discover that it is unavailable. Family C.

`mix.py` v2 emits `payload["choice"]` -- the SAME object the digest is taken
from, not a second construction of it, because a rebuilt table could disagree
with the digest and that is the defect one level up.

THIS FILE IS THE STANDING CHECK, not the fix. It re-derives the digest from the
published table and refuses if they disagree, so `result.json` can never again
carry a digest that does not open. It reads artifacts only and takes under a
second, so it is cheap enough to run on every pull.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
G88 = os.path.join(os.path.dirname(HERE), "G88_5way_hybrid", "result.json")

# Pinned from G88's OWN published artifact BEFORE this change (mix.py v1), so a
# re-run that moved the selector would be caught rather than absorbed.
PUBLISHED_SHA = "f2e8f705f91de769"
PUBLISHED_MRR = 0.3143


def main() -> int:
    r = json.loads(open(G88, encoding="utf-8").read())
    bad = []

    if "choice" not in r:
        print("FAIL: result.json has no `choice` -- the digest has no opening again")
        return 1
    ch, sha = r["choice"], r["choice_sha256"]

    # THE CHECK. Recompute the digest from the PUBLISHED table, byte-identically
    # to mix.py:124. If mix.py ever emits a table that is not the one it hashed,
    # this is the line that says so.
    recomputed = hashlib.sha256(
        json.dumps({"min_n": r["choice_min_n"], "choice": ch}, sort_keys=True).encode()
    ).hexdigest()
    if recomputed != sha:
        bad.append(f"the published table does not hash to the published digest: "
                   f"{recomputed[:16]} vs {sha[:16]}")
    if not sha.startswith(PUBLISHED_SHA):
        bad.append(f"digest moved from the v1 artifact: {sha[:16]} vs {PUBLISHED_SHA}")
    if len(ch) != r["choice_n_keys"]:
        bad.append(f"table has {len(ch)} entries, n_keys says {r['choice_n_keys']}")
    if r["metrics"]["mrr"] != PUBLISHED_MRR:
        bad.append(f"mrr moved: {r['metrics']['mrr']} vs {PUBLISHED_MRR}")

    # The counts must be DERIVABLE from the table, which is the property that
    # makes the table and the five integers one object rather than two records
    # that can disagree (H39's shape).
    derived = {}
    for v in ch.values():
        derived[v] = derived.get(v, 0) + 1
    if derived != r["choices"]:
        bad.append(f"counts are not derivable from the table: {derived} vs {r['choices']}")

    fallback = sum(1 for k, v in ch.items() if v == "distmult")
    for b in bad:
        print("FAIL: " + b)
    if bad:
        return 1
    print(f"ok: {len(ch)} keys, digest {sha[:16]} reproduces from the published "
          f"table, counts derive from it, mrr {r['metrics']['mrr']}")
    print(f"    min_n={r['choice_min_n']} n_small_default={r['choice_n_small_default']} "
          f"(distmult entries incl. fallback: {fallback})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
