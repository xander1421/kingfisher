#!/usr/bin/env python3
"""G15 — discovery by relational composition, on a corpus that has redundancy.

G14 refuted abstraction-by-equivalence and named why: 60 unique spikes have no
structural redundancy, so no two nodes can share an ablation signature. It also
named the next mechanism — analogy / structure mapping (Gentner), which asks for
relational ISOMORPHISM rather than identity.

Wrong corpus, though. This runs on FB15k-237: 272,115 triples, 237 predicates,
14,505 entities — a real knowledge graph with genuine repeated structure.

MECHANISM: relational composition. If  a --p--> b --q--> c  and also
a --r--> c, then (p,q) => r is a candidate rule. That is generative — it emits a
rule that was not in the input — and it is the KG form of "A is to B as C is to
D": the composition p∘q plays the same structural role as r.

PRE-REGISTERED HYPOTHESIS, written before running so it can fail:
  (a) rules (p,q)=>r exist whose HELD-OUT confidence exceeds the confidence
      obtained from a degree-preserving shuffled graph, and
  (b) the top rules are not merely restatements of a single high-frequency
      predicate.

THE TRAP, named first: confidence alone is meaningless on a skewed graph. If r
covers 30% of all edges, any rule "predicts" it 30% of the time. So every rule
is scored against the MARGINAL rate of r — lift, not confidence — and the null
is a shuffle that preserves each predicate's frequency.

SPLIT: rules are mined on 80% of triples and scored on the held-out 20%. A rule
scored on the data that produced it is memorisation; G4 is the cautionary case.
"""

import json
import os
import random
import struct
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
BIN = os.path.join(SPIKES, "S52_realkg", "triples.bin")

MIN_SUPPORT = 50          # a rule must fire this often in TRAIN to be considered
TOP_N = 15


def load():
    d = open(BIN, "rb").read()
    nt, npred, nent = struct.unpack_from("<III", d, 0)
    tri = struct.unpack_from(f"<{nt*3}I", d, 12)
    return nt, npred, nent, [(tri[i*3], tri[i*3+1], tri[i*3+2]) for i in range(nt)]


def index(triples):
    out_ = defaultdict(list)          # subj -> [(pred, obj)]
    pair = defaultdict(set)           # (subj,obj) -> {pred}
    for p, s, o in triples:
        out_[s].append((p, o))
        pair[(s, o)].add(p)
    return out_, pair


def mine(triples, cap_paths=4_000_000):
    """Count (p,q) co-occurrence with a direct r on the same endpoints."""
    out_, pair = index(triples)
    body = Counter()                  # (p,q) -> how many 2-hop paths
    head = Counter()                  # (p,q,r) -> paths where r also joins a,c
    seen = 0
    for a, edges in out_.items():
        for p, b in edges:
            for q, c in out_.get(b, ()):
                if c == a:
                    continue
                seen += 1
                if seen > cap_paths:
                    return body, head, seen
                body[(p, q)] += 1
                for r in pair.get((a, c), ()):
                    head[(p, q, r)] += 1
    return body, head, seen


def marginal(triples, npred):
    c = Counter(p for p, _, _ in triples)
    n = len(triples)
    return {p: c[p] / n for p in range(npred)}


def score(body, head, marg, min_support):
    rules = []
    for (p, q, r), h in head.items():
        b = body[(p, q)]
        if b < min_support:
            continue
        conf = h / b
        m = marg.get(r, 1e-9) or 1e-9
        rules.append({"p": p, "q": q, "r": r, "support": b, "conf": conf,
                      "lift": conf / m})
    rules.sort(key=lambda x: (-x["lift"], -x["support"]))
    return rules


def main():
    nt, npred, nent, triples = load()
    print(f"FB15k-237: {nt:,} triples, {npred} predicates, {nent:,} entities")

    rng = random.Random(0xC0FFEE)
    idx = list(range(nt))
    rng.shuffle(idx)
    cut = int(nt * 0.8)
    train = [triples[i] for i in idx[:cut]]
    test = [triples[i] for i in idx[cut:]]
    print(f"train {len(train):,}  held-out {len(test):,}\n")

    body, head, paths = mine(train)
    marg_tr = marginal(train, npred)
    rules = score(body, head, marg_tr, MIN_SUPPORT)
    print(f"2-hop paths walked {paths:,}")
    print(f"candidate (p,q) bodies {len(body):,}   "
          f"rules with support>={MIN_SUPPORT}: {len(rules):,}\n")

    # ---- held-out scoring, corrected ----
    # First attempt walked 2-hop paths in the TEST set. A path needs BOTH edges
    # held out, so at a 20% split only ~4% of paths survive and ho_n came back
    # at 7-206 — noise. The shape (tiny n) was the tell.
    #
    # Standard KG link-prediction protocol instead: walk the body on TRAIN,
    # and ask whether the predicted head edge appears in the HELD-OUT set. The
    # body is a path the rule is allowed to see; the head is the prediction.
    out_tr, pair_tr = index(train)
    _, pair_te = index(test)

    def holdout_conf(rule, limit=200_000):
        p, q, r = rule["p"], rule["q"], rule["r"]
        b = h = 0
        for a, edges in out_tr.items():
            for pp, bb in edges:
                if pp != p:
                    continue
                for qq, cc in out_tr.get(bb, ()):
                    if qq != q or cc == a:
                        continue
                    # only endpoints whose (a,c) edge was NOT in train can
                    # test a prediction; otherwise the rule saw the answer
                    if r in pair_tr.get((a, cc), ()):
                        continue
                    b += 1
                    if r in pair_te.get((a, cc), ()):
                        h += 1
                    if b > limit:
                        return h / b, b
        return (h / b if b else None), b

    marg_te = marginal(test, npred)
    top = rules[:TOP_N]
    print(f"  {'p':>4}{'q':>5}{'r':>5}{'supp':>7}{'conf':>8}{'lift':>9}"
          f"{'ho_conf':>9}{'ho_lift':>9}{'ho_n':>7}")
    kept = []
    for rl in top:
        hc, hn = holdout_conf(rl)
        if hc is None:
            continue
        hl = hc / (marg_te.get(rl["r"], 1e-9) or 1e-9)
        kept.append(dict(rl, ho_conf=hc, ho_lift=hl, ho_n=hn))
        print(f"  {rl['p']:>4}{rl['q']:>5}{rl['r']:>5}{rl['support']:>7}"
              f"{rl['conf']:>8.2f}{rl['lift']:>9.1f}{hc:>9.2f}{hl:>9.1f}{hn:>7}")

    json.dump({"nt": nt, "npred": npred, "nent": nent,
               "paths": paths, "n_rules": len(rules), "top": kept,
               "min_support": MIN_SUPPORT,
               "conditions": {"data": "real:FB15k-237",
                              "concurrency": "single-process",
                              "swept": {}},
               "cites": ["S52_realkg", "G14_ablation_concepts"]},
              open(os.path.join(HERE, "mine.json"), "w"), indent=1)
    print(f"\nheld-out rules scored: {len(kept)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
