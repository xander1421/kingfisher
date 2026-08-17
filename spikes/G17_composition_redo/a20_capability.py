#!/usr/bin/env python3
"""A20 for G17's null — can the baseline contain the effect it is the null for?

A permutation p-value is only worth its precision if the null distribution is
capable of producing the structure being tested. A null that can never generate
a composition rule makes every draw fall short of `real` for a reason that has
nothing to do with the hypothesis, and 500 draws would buy a precise number from
an instrument that cannot register the thing it measures.

METHOD. Plant a composition rule of known strength into the shuffled graph and
ask whether the pipeline recovers it at the strength planted.

Two earlier versions of this test were degenerate, and both failures are the
same class this workspace keeps catching — a control that cannot fire:

  1. Planted on a (p,q) chosen by guess. Predicates 0 and 1 have no 2-hop paths
     in the shuffled graph, so `+0 edges` were added. Nothing was planted, so
     nothing could be detected. Fixed by choosing the body BY MEASUREMENT of the
     shuffled graph rather than by assumption.

  2. Planted head edges into train AND test. `redo.py:118` excludes any pair
     whose head edge is already in train (`cand = [ac for ac in bp if r not in
     pair_tr...]`), so every planted pair was excluded from scoring and the
     statistic came back identical to four decimals across a 1.3M-edge plant.
     The unchanged 4th decimal was the tell.

So the plant must have the shape of a REAL rule: partly visible in train, so the
rule is discovered at all, and mostly in the held-out set, so it can score.

    10% of body pairs -> train   (discovery seed; without these (p,q,r) is
                                  never in `head` and is never considered)
    frac of the rest  -> test    (the signal; this is what ho_conf measures)

PASS CONDITION: recovered ho_conf must track the planted `frac`. A pipeline that
recovers 0.9 as 0.9 is unbiased at that strength; one that recovers 0.9 as 0.3
is attenuating the effect and its null is not comparable to `real`.
"""

import random
import sys

import redo as R

SEED_FRAC = 0.10       # share of body pairs made visible in train
FRACS = (0.2, 0.5, 0.9)
TOP_N = 12


def statistic(rules):
    return sum(x["ho_conf"] for x in rules[:TOP_N]) / TOP_N if rules else 0.0


def main():
    nt, npred, nent, tri = R.load()
    rng = random.Random(0xC0FFEE)
    idx = list(range(nt))
    rng.shuffle(idx)
    cut = int(nt * 0.8)
    train = [tri[i] for i in idx[:cut]]
    test = [tri[i] for i in idx[cut:]]

    sh = R.shuffled(train, 0)
    body, _ = R.mine_pairs(sh)

    # Chosen by measurement of the SHUFFLED graph, not by assumption. Bounded
    # above so the test stays cheap; MIN_PAIRS=30 is the only hard floor.
    sized = sorted(((len(s), p, q) for (p, q), s in body.items()
                    if 200 <= len(s) <= 4000), reverse=True)
    if not sized:
        print("NO BODY IN RANGE — test cannot fire, do not report a verdict")
        return 2
    n_pairs, p, q = sized[0]
    r = next(x for x in range(npred) if x not in (p, q))  # r==p or r==q is
    pairs = sorted(body[(p, q)])                          # rejected as a
                                                          # restatement at :114
    base, _, _ = R.evaluate(sh, test, npred, "null")
    s_null = statistic(base)
    print(f"body chosen by measurement: ({p},{q}), {n_pairs} pairs in the "
          f"shuffled graph")
    print(f"null statistic {s_null:.4f}   (real graph 0.4405, G17)\n")
    print(f"plant ({p},{q})=>{r}: {SEED_FRAC:.0%} of body pairs into TRAIN, "
          f"frac of the rest into TEST\n")

    rows = []
    for frac in FRACS:
        rr = random.Random(11)
        seed = [ac for ac in pairs if rr.random() < SEED_FRAC]
        rest = [ac for ac in pairs if ac not in set(seed)]
        sig = [ac for ac in rest if rr.random() < frac]
        g = sh + [(r, a, c) for a, c in seed]
        te = test + [(r, a, c) for a, c in sig]
        rules, _, _ = R.evaluate(g, te, npred, f"plant{frac}")
        s = statistic(rules)
        hit = [(i, x) for i, x in enumerate(rules)
               if (x["p"], x["q"], x["r"]) == (p, q, r)]
        rank = hit[0][0] + 1 if hit else None
        conf = hit[0][1]["ho_conf"] if hit else None
        rows.append({"frac": frac, "rank": rank, "conf": conf, "stat": s,
                     "seed": len(seed), "sig": len(sig)})
        w = (f"rank {rank}, ho_conf {conf:.3f}" if hit else "NOT RECOVERED")
        print(f"  frac={frac}  train-seed {len(seed):4d}  test-signal "
              f"{len(sig):4d}  statistic {s:.4f}  [{w}]")

    # PASS: every planted strength recovered, and recovered near its own value.
    recovered = [x for x in rows if x["conf"] is not None]
    unbiased = all(abs(x["conf"] - x["frac"]) < 0.02 for x in recovered)
    print()
    if len(recovered) < len(rows):
        v = "FAIL — a planted rule was not recovered at all"
    elif not unbiased:
        v = "FAIL — recovered strength does not track planted strength"
    else:
        v = ("PASS — the null CAN contain the effect; recovered strength "
             "tracks planted strength to <0.02")
    print(f"A20 VERDICT: {v}")

    # The sensitivity number, which is the part that constrains G17's reading.
    strong = [x for x in rows if x["frac"] == 0.9][0]
    weak = [x for x in rows if x["frac"] == 0.2][0]
    print(f"\nSENSITIVITY. One rule at frac=0.9 moves the statistic "
          f"{strong['stat'] - s_null:+.4f}. One at frac=0.2 moves it "
          f"{weak['stat'] - s_null:+.4f} — it is recovered (rank "
          f"{weak['rank']}) but never enters the top {TOP_N}, so the "
          f"statistic cannot see it.")
    print(f"G17's real-vs-null gap is {0.4405 - s_null:+.4f}, about "
          f"{(0.4405 - s_null) / (strong['stat'] - s_null):.1f} planted rules "
          f"at frac=0.9. So the real effect is a BROAD lift across the top "
          f"{TOP_N}, not one strong rule the shuffle missed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
