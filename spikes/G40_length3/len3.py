#!/usr/bin/env python3
"""G40 — rule bodies LONGER THAN 2 on the filtered-MRR yardstick.

WHY, measured rather than assumed:
  * G34 reaches 0.2648 filtered MRR with 2-hop + length-1 + constants, and
    `length1_constants.py` has no path above two hops.
  * G39 established the machinery is SEARCH-limited, not selection-limited:
    `evo.mutate` cannot express a length-1 body (evo.py:366) while length-1
    alone scores 0.1572 — 5.89x the best evolved arm.
  * AnyBURL len<=2 is 0.2450 and we beat it. AnyBURL UNRESTRICTED is ~0.31 and
    the difference is body length. The 0.28 target lives there.

FALSIFIERS, posted to CHANNEL.md before this ran:
  F1  length-3 does NOT raise filtered MRR over G34's 0.2648 on the same split
      -> "search-limited" is wrong for DEPTH, and G39's conclusion narrows to
      length-1 specifically.
  F2  a gain vanishes when scored through varlen.evaluate_varlen rather than a
      new evaluator -> the gain was an evaluation artefact.
      F2 is satisfied BY CONSTRUCTION here: this file never writes an
      evaluator. It imports G37's, which G37 pinned to yardstick.py at 6
      decimals. A spike that both mines and scores its own rules can move the
      number twice and report it once.

THE TENSION THIS HAS TO RESOLVE, and it is why the spike is worth running:
G23 measured depth-3 against its OWN null at a SMALLER gap than depth-2
(+0.0949 vs +0.1157) with a null twice as noisy, and concluded depth pays less
than width. That was the top-12 held-out statistic — which G30 retired, and
which G38 showed rewards quality per rule. Filtered MRR rewards COVERAGE: G38
measured the evolved population 2.36x WORSE in absolute MRR while 2.11x BETTER
at matched rule count. So "depth-3 is weaker per rule" and "depth-3 raises MRR"
can both be true, and only a run separates them.

MINING BY PATH SAMPLING, which is AnyBURL's own method and the reason it scales:
exhaustive length-3 enumeration is 237^3 candidate bodies, and extending the
2-hop reach sets (up to 1.3M pairs each, measured in G17) by one hop is not
affordable in Python. Sampling random 3-hop walks visits exactly the bodies the
graph actually contains, in proportion to how often it contains them.
"""
import json, os, random, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "G37_varlen_bodies"))
sys.path.insert(0, os.path.join(HERE, "..", "G34_length1_and_constants"))
import varlen                                    # noqa: E402  the PINNED evaluator
import length1_constants as g34                  # noqa: E402

SEED = 0xC0FFEE
WALKS = 400_000        # random 3-hop walks; reported, never silent
MIN_SUP = 8            # a body must be seen this often before it can be a rule
MIN_CONF = 0.05
MAX_RULES = 12_000     # cap on emitted length-3 rules; reported


def mine_len3(train, out_adj, pair_tr, rng, walks=WALKS):
    """Sample 3-hop walks; count (body -> head) co-occurrence.

    Guards mirror the 2-hop miner: no step returns to the node it came from and
    the endpoints must differ, because a 'prediction' whose endpoints are the
    same node is not one.
    """
    nodes = [n for n in out_adj if out_adj[n]]
    body_sup = defaultdict(int)
    head_sup = defaultdict(int)
    capped = 0
    for _ in range(walks):
        a = rng.choice(nodes)
        e1 = out_adj.get(a) or ()
        if not e1:
            continue
        p, b = rng.choice(e1)
        if b == a:
            continue
        e2 = out_adj.get(b) or ()
        if not e2:
            continue
        q, c = rng.choice(e2)
        if c in (a, b):
            continue
        e3 = out_adj.get(c) or ()
        if not e3:
            continue
        r, d = rng.choice(e3)
        if d in (a, b, c):
            continue
        body = (p, q, r)
        body_sup[body] += 1
        for s in pair_tr.get((a, d), ()):      # heads TRUE at these endpoints
            head_sup[(body, s)] += 1

    rules = []
    for (body, s), sup in head_sup.items():
        bs = body_sup[body]
        if bs < MIN_SUP or s in body:          # s in body is a restatement
            continue
        conf = sup / bs
        if conf < MIN_CONF:
            continue
        rules.append({"body": body, "head": s, "conf": conf, "sup": sup,
                      "body_sup": bs})
    rules.sort(key=lambda r: (-r["conf"], -r["sup"]))
    if len(rules) > MAX_RULES:
        capped = len(rules) - MAX_RULES
        rules = rules[:MAX_RULES]
    return rules, len(body_sup), capped


def main():
    rng = random.Random(SEED)
    t0 = time.time()
    nt, npred, nent, tri, train, dev, test = g34.load_dataset()
    out_adj, in_adj, pair_tr, byp, rev = g34.build_graph_index(train)
    true_sp, true_po = g34.build_filter_index(train + dev + test)

    # --- base arm, rebuilt in THIS process so both arms share one build ---
    # NOT G34's full system: constant-grounded rules carry a `const` field that
    # varlen's body walk has no slot for, and INVERSE length-1 rules are
    # p(x,y) <- q(y,x), a backward walk varlen does not express. Including
    # either by pretending it is a forward body would score a rule that means
    # something else. So base = 2-hop + length-1 SUBSUMPTION only.
    #
    # That is why the controlled comparison here is base vs base+len3 INSIDE one
    # process, and G34's published 0.264807 is context rather than the baseline.
    # Comparing my base against a number built from a larger rule family would
    # be the differently-sized-population error this repo retracted G15 for.
    r2 = g34.mine_g17_2hop_rules(out_adj, pair_tr, byp, rev)
    subsume, inverse = g34.mine_length1_rules(npred, byp, rev)
    base = [{"body": tuple(r["body"]), "head": r["head"], "conf": r["conf"]}
            for r in r2]
    for head_p, lst in subsume.items():
        for r in lst:
            base.append({"body": (r["body"],), "head": head_p,
                         "conf": r["conf"]})
    print(f"base: {len(r2)} 2-hop + "
          f"{sum(len(v) for v in subsume.values())} length-1 subsumption "
          f"(inverse and constant families EXCLUDED — varlen has no backward "
          f"walk or const slot)", flush=True)

    r3, n_bodies, capped = mine_len3(train, out_adj, pair_tr, rng)
    print(f"walks {WALKS}  distinct 3-bodies seen {n_bodies}  "
          f"length-3 rules kept {len(r3)}  dropped by MAX_RULES {capped}",
          flush=True)

    out = {}
    for name, rules in (("base_len1_2", base), ("plus_len3", base + r3)):
        m = varlen.evaluate_varlen(rules, test, out_adj, in_adj, true_sp,
                                   true_po, nent)
        out[name] = {"rules": len(rules), "mrr": m["mrr"], "h1": m["hits1"],
                     "h3": m["hits3"], "h10": m["hits10"]}
        print(f"{name:<14} rules {len(rules):6d}  MRR {m['mrr']:.6f}  "
              f"H@1 {m['hits1']:.4f}  H@10 {m['hits10']:.4f}", flush=True)

    d = out["plus_len3"]["mrr"] - out["base_len1_2"]["mrr"]
    print(f"\nlength-3 delta on THIS process's base: {d:+.6f}")
    print(f"G34 published full system (2-hop + L1 + CONST): 0.264807")
    print(f"F1 {'SURVIVES' if d > 0 else 'FIRES'} — length-3 "
          f"{'raises' if d > 0 else 'does NOT raise'} filtered MRR")
    print("F2 satisfied by construction: scored through varlen.evaluate_varlen, "
          "G37's pinned path. This file contains no evaluator.")
    out["_meta"] = {"seed": SEED, "walks": WALKS, "min_sup": MIN_SUP,
                    "min_conf": MIN_CONF, "max_rules": MAX_RULES,
                    "capped": capped, "delta": d,
                    "secs": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(HERE, "len3.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
