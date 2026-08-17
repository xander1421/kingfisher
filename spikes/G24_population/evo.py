#!/usr/bin/env python3
"""G24 — an actual evolving rule population. G22 was not one, and that is why
it did nothing.

G22 wrote mined conclusions back into the graph and got a controlled negative.
The explanation given there ("a materialised deduction carries no information")
was fitted to the number. The structural explanation is better and is the reason
this spike exists:

    G22 satisfied ZERO of Lewontin's three conditions for evolution.
      variation            none - derived edges were a deterministic function
                           of train. One outcome. No population.
      heredity             trivial - the graph persisted, but nothing
                           reproduced with modification.
      differential fitness none - every top-k rule was written, none removed,
                           nothing competed for anything finite.

    It was deduction plus re-reading. Calling it evolution was a category
    error, and a system with none of the three conditions is not expected to
    adapt.

This builds the three conditions explicitly, plus the parts the operator named
(problem space, adversarial co-evolution, waves), each as a mechanism that can
be switched OFF so its contribution is measurable rather than assumed.

  GENOTYPE   a rule: (body predicate tuple, head predicate)
  PHENOTYPE  the endpoint pairs its body matches and the head edges it asserts
  VARIATION  mutation operators: swap, extend, contract, rehead, recombine,
             duplicate. Rules are GENERATED, not enumerated - enumeration has
             no population and no lineage. Proposals are structure-biased in
             BOTH directions (what follows p, what precedes q), because uniform
             draws over 237 predicates gave a flat landscape with no slope.
  ABDUCTION  the operator that turned this spike from nothing into something.
             All the above mutate first and discover relevance afterwards.
             Abduction runs the other way: take a problem the population cannot
             solve, find a path between its endpoints, propose the rule that
             path implies. It makes the problem space an INPUT to variation
             rather than only a scoreboard. Without it the positive control was
             never found and test coverage moved +180; with it, +2892.
  HEREDITY   offspring carry a parent's body/head with one edit; population
             persists across rounds and lineage is recorded
  FITNESS    dev triples predicted correctly, novelty-weighted so a crowd of
             rules solving the same easy triple each earn less
             (frequency-dependent selection - without it the population
             collapses to one predicate)
  DEATH      ECAN as a finite economy, which is where it always belonged.
             A fixed wage pool is shared each round; rules pay rent by size;
             importance <= 0 removes the rule. Finite carrying capacity is
             what MAKES fitness differential - with unlimited room, fitness
             differences do nothing.
  PROBLEM    fitness is defined against open queries, not against the graph
   SPACE     in general. Unanswered (a,r,?) drive everything.
  WAVES      activation spreads from unsolved problems through the graph and
             multiplies wages in high-activation regions, so variation is paid
             for where the problems are. Recomputed each round, so the wave
             MOVES as problems get solved.
  ADVERSARY  reshuffled every round, and chosen best-of-m to MAXIMISE the
             current population's score - the hardest null it can find. A
             static null gets memorised; this one co-evolves (Red Queen).

--------------------------------------------------------------------------
THE HONESTY CHECK, WHICH IS THE WHOLE POINT
--------------------------------------------------------------------------
An evolutionary loop selecting on dev WILL improve on dev. That is what
selection does and it is not evidence of anything. TEST is never used for
selection, never used for wages, never seen by any operator. If dev climbs and
test does not, the population found the scoring function rather than the truth,
and this reports that in the same table rather than in a footnote.

--------------------------------------------------------------------------
ARMS
--------------------------------------------------------------------------
  full            everything on
  no_variation    no mutation; the seeded population only (this is G22's shape)
  no_abduct       mutation on, problem-directed proposal off
  no_death        no rent, nothing removed (no carrying capacity)
  static_adv      adversary fixed at round 0 instead of co-evolving
  no_waves        wage multiplier forced to 1

A15 POSITIVE CONTROL. A synthetic composition is planted whose rule is NOT in
the seed population and is reachable only by mutation. If `full` does not
discover it, the variation operators are blind and every arm comparison here is
void.
"""

import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "G17_composition_redo"))
import redo as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

MIN_PAIRS = 30
MAX_PAIRS = 40_000       # a rule whose body matches more than this is
                         # EXCLUDED, not truncated. v1 truncated and scored
                         # anyway, which is invalid twice over: the confidence
                         # came from an arbitrary iteration-order subset rather
                         # than a random sample, and clamping n let a genuinely
                         # broad rule dodge the per-assertion rent. 150 of ~2000
                         # evaluations in v1's full arm, 525 in no_death.
                         # This is a stated exclusion criterion, not a silent cap.
SEED = 0xC0FFEE
RUN_SEED = 1234          # was inline in run(). Hoisted so repeats are possible:
                         # G24 ran one seed per arm and its own RESULT.md lists
                         # that as a limitation, which makes any coverage
                         # DIFFERENCE between arms unbounded below by noise.

POP_SEED = 60            # enumerated rules the population starts from
OFFSPRING = 40           # offspring generated per round
ROUNDS = 15
MAX_POP = 200

WAGE_POOL = 120.0         # total importance paid out per round (finite!)
RENT = 0.5               # per body predicate, per round
RENT_PRED = 0.05         # per 1000 predictions asserted -- a rule that claims
                         # more pays more. Without this, fitness rewards hits
                         # and never charges for breadth, so the population
                         # evolves rules that assert everything: the first run
                         # gained coverage while precision fell 0.021 -> 0.011.
START_IMP = 4.0
ADV_TRIES = 2            # adversary shuffles tried per round; hardest is kept
WAVE_STEPS = 2
WAVE_DECAY = 0.5
TOP_N = 12

OPS = ("swap", "extend", "contract", "rehead", "recombine", "duplicate")


class Idx:
    """by_pred: p -> [(s,o)];  sp: (s,p) -> [o];  pair: (s,o) -> {p};
    out_adj: s -> [(p,o)]"""

    def __init__(self, triples):
        self.by_pred = defaultdict(list)
        self.sp = defaultdict(list)
        self.pair = defaultdict(set)
        self.out_adj = defaultdict(list)
        for p, s, o in triples:
            if s == o:
                continue
            self.by_pred[p].append((s, o))
            self.sp[(s, p)].append(o)
            self.pair[(s, o)].add(p)
            self.out_adj[s].append((p, o))


def body_pairs(idx, body, cap=None):
    # cap resolved in the BODY, not bound as a default argument. AGENT-2 caught
    # this as a live trap for a sweeping harness: `cap=MAX_PAIRS` binds at
    # function-definition time, so `evo.MAX_PAIRS = 999` leaves the default at
    # 40000 and a swept config would silently do nothing while reporting NO
    # EFFECT -- a false negative wearing the shape of a finding. MAX_PAIRS is the
    # most likely next knob, since its rejection rule is what doubled precision
    # in v2.
    """Endpoint pairs the body matches. Guards mirror redo.py: no step returns
    to the node it came from and no endpoint pair is a self-loop."""
    cap = MAX_PAIRS if cap is None else cap
    reach = {(a, b) for a, b in idx.by_pred.get(body[0], ()) if a != b}
    capped = False
    for q in body[1:]:
        nxt = set()
        for a, b in reach:
            for c in idx.sp.get((b, q), ()):
                if c != a and c != b:
                    nxt.add((a, c))
            if len(nxt) > cap:
                capped = True
                break
        reach = nxt
        if capped:
            break
    return reach, capped


def score(idx, body, r, exclude, target, cap=None, stats=None):
    cap = MAX_PAIRS if cap is None else cap   # see body_pairs
    bp, capped = body_pairs(idx, body, cap)
    if capped:
        # Reject rather than truncate. A truncated walk yields a confidence
        # measured on whatever the iteration order happened to reach.
        if stats is not None:
            stats["rejected_capped"] = stats.get("rejected_capped", 0) + 1
        return None
    if len(bp) < MIN_PAIRS:
        return None
    cand = [ac for ac in bp if r not in exclude.get(ac, ())]
    if len(cand) < MIN_PAIRS:
        return None
    hit = [ac for ac in cand if r in target.get(ac, ())]
    # `cand` is returned so a second target (test) can be scored without
    # re-walking the body — the walk is the expensive part and the pairs a rule
    # matches do not depend on what it is scored against.
    return {"n": len(cand), "hits": len(hit), "conf": len(hit) / len(cand),
            "solved": hit, "cand": cand, "capped": capped}


def population_metrics(pop, ev, target):
    """What the POPULATION collectively gets right, which is the thing that
    matters and is not the same as how good its best members are.

    Selection can raise coverage while lowering top-12 confidence: a crowd of
    narrow accurate rules is replaced by fewer broad ones, or vice versa. G17's
    top-12 statistic measures individuals. Reporting only that would have made
    a population improving in coverage look like a regression.
    """
    preds, correct = set(), set()
    confs = []
    for r in pop:
        s = ev.get(r["id"])
        if not s:
            continue
        confs.append(sum(1 for ac in s["cand"] if r["head"] in
                         target.get(ac, ())) / len(s["cand"]))
        for ac in s["cand"]:
            preds.add((r["head"], ac))
            if r["head"] in target.get(ac, ()):
                correct.add((r["head"], ac))
    confs.sort(reverse=True)
    k = min(TOP_N, len(confs))
    return {"solved": len(correct), "predicted": len(preds),
            "precision": len(correct) / len(preds) if preds else 0.0,
            "top12": sum(confs[:k]) / k if k else 0.0}


# ---------------------------------------------------------------- variation
def build_bias(idx):
    """Which predicates actually FOLLOW which, and which heads actually sit at
    the endpoints of a body.

    Uniform mutation over 237 predicates cannot evolve anything here, and the
    first run of this spike showed it: the fitness landscape is FLAT. A rule
    either clears MIN_PAIRS support or scores nothing at all, so there is no
    partial credit and no slope. Reaching a 3-token rule by uniform search means
    three simultaneous correct choices with zero fitness on every intermediate.

    So variation is structure-aware: a proposed next predicate is sampled from
    the ones that genuinely continue a path. This is mutational bias, and it is
    not a cheat -- it is the genotype-phenotype map doing its job. The bias uses
    only the TRAIN graph's connectivity; it never sees dev or test.

    The bias is BIDIRECTIONAL. An earlier version only had `follows`, so a swap
    at body position 0 fell back to a uniform draw over 237 predicates -- and a
    rule whose first token is the rare one is then reachable only by jackpot.
    `precedes` makes position 0 as informed as the rest: given what comes next,
    which predicates actually lead into it.
    """
    follows, precedes = defaultdict(Counter), defaultdict(Counter)
    for p, edges in idx.by_pred.items():
        for _, bnode in edges:
            for q, _ in idx.out_adj.get(bnode, ()):
                follows[p][q] += 1
                precedes[q][p] += 1

    def pack(d):
        out = {}
        for k, ctr in d.items():
            ks = list(ctr)
            out[k] = (ks, [ctr[x] for x in ks])
        return out

    return pack(follows), pack(precedes)


def pick(tbl, p, rng, preds, explore=0.15):
    """Sample a continuation of p. `explore` keeps a uniform channel open so the
    bias narrows the search without closing it -- a fully biased proposal
    distribution cannot reach anything the graph does not already suggest."""
    if p is not None and p in tbl and rng.random() > explore:
        ks, ws = tbl[p]
        return rng.choices(ks, weights=ws, k=1)[0]
    return rng.choice(preds)


def heads_at(idx, cand, rng, sample=300):
    """Predicates actually asserted at a body's endpoint pairs. A rehead drawn
    from here proposes a conclusion the graph makes somewhere, rather than one
    of 237 that mostly appears nowhere near these entities."""
    ps = cand if len(cand) <= sample else rng.sample(cand, sample)
    c = Counter()
    for ac in ps:
        for r in idx.pair.get(ac, ()):
            c[r] += 1
    return c


def pick_parent(pop, rng, repro):
    """Fitness-proportional reproduction when `repro`, uniform otherwise.

    Weight is accumulated importance, floored just above zero so a rule that
    has not yet earned can still occasionally reproduce -- that floor is the
    neutral-drift channel, and without it a population converges on whatever
    paid first and stops exploring.
    """
    if not repro:
        return rng.choice(pop)
    w = [max(r["imp"], 0.05) for r in pop]
    return rng.choices(pop, weights=w, k=1)[0]


def abduct(idx, unsolved, rng, tries=40):
    """PROBLEM-DIRECTED VARIATION. Take a problem the population cannot solve,
    find a path in the graph between its endpoints, and propose the rule that
    path implies.

    Every other operator is blind: it mutates a rule and only afterwards
    discovers whether the result explains anything. This is the reverse, and it
    is what makes the problem space an INPUT to variation rather than only a
    scoreboard. It is bottom-up clause construction -- the same move as
    mode-directed inverse entailment in ILP -- and it is the mechanism that
    makes a rule with a zero-fitness mutational path reachable at all.

    Uses TRAIN structure and the DEV problem list. Never test.
    """
    for _ in range(tries):
        r, a, c = unsolved[rng.randrange(len(unsolved))]
        for p, b in idx.out_adj.get(a, ()):
            if b == a:
                continue
            for q, cc in idx.out_adj.get(b, ()):
                if cc == c and c != a and c != b and r not in (p, q):
                    return (p, q), r
    return None


def mutate(rule, preds, rng, pool, tbl, idx, ev):
    """One edit, one offspring. Returns None if the edit is a no-op."""
    fwd, bwd = tbl
    op = rng.choice(OPS)
    body, r = list(rule["body"]), rule["head"]
    if op == "swap":
        i = rng.randrange(len(body))
        # position 0 uses `precedes` (what leads INTO the next token); later
        # positions use `follows`. Both are structure-aware; neither is uniform.
        body[i] = (pick(fwd, body[i - 1], rng, preds) if i
                   else pick(bwd, body[1] if len(body) > 1 else None, rng,
                             preds))
    elif op == "extend":
        if len(body) >= 3:
            return None
        body.append(pick(fwd, body[-1], rng, preds))
    elif op == "contract":
        if len(body) <= 2:
            return None
        body.pop()
    elif op == "rehead":
        s = ev.get(rule["id"])
        c = heads_at(idx, s["cand"], rng) if s else None
        if c:
            ks = list(c)
            r = rng.choices(ks, weights=[c[k] for k in ks], k=1)[0]
        else:
            r = rng.choice(preds)
    elif op == "recombine":
        other = rng.choice(pool)
        ob = list(other["body"])
        k = rng.randrange(1, len(body))
        body = body[:k] + ob[min(k, len(ob) - 1):]
        body = body[:3]
    elif op == "duplicate":
        pass  # exact copy; drifts on a later round. Gene duplication.
    if len(body) < 2 or r in body:
        return None
    nb = tuple(body)
    if nb == rule["body"] and r == rule["head"] and op != "duplicate":
        return None
    return {"body": nb, "head": r, "imp": START_IMP, "parent": rule["id"],
            "op": op}


# -------------------------------------------------------------------- waves
def wave(idx, unsolved, steps=WAVE_STEPS, decay=WAVE_DECAY):
    """Activation spreads from the endpoints of unsolved problems. Recomputed
    every round, so the wave moves as the problem set changes."""
    act = defaultdict(float)
    for _, a, c in unsolved:
        act[a] += 1.0
        act[c] += 1.0
    for _ in range(steps):
        nxt = defaultdict(float)
        for node, v in act.items():
            outs = idx.out_adj.get(node)
            if not outs or v < 1e-3:
                continue
            share = v * decay / len(outs)
            for _, o in outs:
                nxt[o] += share
        for k, v in nxt.items():
            act[k] += v
    mx = max(act.values()) if act else 1.0
    return {k: v / mx for k, v in act.items()}


def wave_mult(act, pairs, rng, sample=200):
    if not act or not pairs:
        return 1.0
    ps = list(pairs)
    if len(ps) > sample:
        ps = rng.sample(ps, sample)
    s = sum(act.get(a, 0.0) + act.get(c, 0.0) for a, c in ps)
    return 1.0 + s / (2 * len(ps))


# ------------------------------------------------------------------ seeding
def seed_population(train, p_tr, p_dev, rng, banned):
    """The starting population: enumerated depth-2 rules, ranked on the problem
    space. Evolution needs something to vary; this is the ancestral stock, and
    the A15 plant is deliberately NOT in it."""
    body, head = R.mine_pairs(train)
    cands = []
    for (p, q, r), _ in head.items():
        bp = body[(p, q)]
        if len(bp) < MIN_PAIRS or r == p or r == q:
            continue
        cand = [ac for ac in bp if r not in p_tr.get(ac, ())]
        if len(cand) < MIN_PAIRS:
            continue
        h = sum(1 for ac in cand if r in p_dev.get(ac, ()))
        cands.append(((p, q), r, h / len(cand)))
    cands.sort(key=lambda x: -x[2])
    # The A15 rule is REMOVED from the ancestral stock. A positive control that
    # starts inside the seed tests nothing about variation -- the first smoke
    # run reported "A15 yes" at round 0, before a single mutation had happened.
    cands = [c for c in cands if not (c[0] == banned[:2] and c[1] == banned[2])]
    return [{"body": b, "head": r, "imp": START_IMP, "parent": None,
             "op": "seed"} for b, r, _ in cands[:POP_SEED]]


# -------------------------------------------------------------------- plant
def plant(npred, nent, n=600, ents=None, rng=None):
    """A15. A composition (P1,P2)=>T that is real and strong, whose rule is NOT
    in the seed population -- P1/P2 edges are added such that the pair (P1,P2)
    has ample support, but T conclusions are mostly held out so the enumerator
    ranks it below the seed cut while a mutation can still reach it."""
    p1, p2, t = npred + 1, npred + 2, npred + 3
    tr, dev = [], []
    # Planted on REAL entities, which matters and was wrong first time round.
    # With fresh entities the plant is a disconnected island: no real predicate
    # ever leads into p1, so the mutation bias table never proposes it and the
    # only route in is a uniform 1-in-240 jump landing on body position 0. That
    # is not a hard control, it is an unreachable one, and it would have made
    # "A15 NO" a fact about my plant rather than about the operators.
    #
    # On real entities, p1-edges leave nodes that carry real predicates, so
    # `follows` proposes p1 after them; and once p1 is in the body, p2 follows
    # it by construction and `heads_at` proposes t. The plant is then reachable
    # by a gradient rather than by a jackpot -- which is what discovery of real
    # structure would look like.
    for i in range(n):
        a, b, c = rng.sample(ents, 3)
        tr.append((p1, a, b))
        tr.append((p2, b, c))
        (tr if i % 12 == 0 else dev).append((t, a, c))
    return (p1, p2, t), tr, dev


# --------------------------------------------------------------------- loop
def run(arm, train, dev_pairs, test_pairs, npred, planted, log=True):
    rng = random.Random(RUN_SEED)
    idx = Idx(train)
    p_tr = idx.pair
    preds = sorted(idx.by_pred)
    pop = seed_population(train, p_tr, dev_pairs, rng, planted)
    for i, r in enumerate(pop):
        r["id"] = i
    nid = len(pop)

    # `arm` is a "+"-joined SET of ablations, so combinations are expressible.
    # G24 ran one ablation at a time and could not fill the death x abduction
    # 2x2; the missing cell is what G25 needed. Single names behave as before.
    abl = set(arm.split("+"))
    variation = "no_variation" not in abl
    death = "no_death" not in abl
    coevo = "static_adv" not in abl
    waves = "no_waves" not in abl
    abduction = "no_abduct" not in abl
    # REPRODUCTIVE selection, separate from SURVIVAL selection.
    #
    # Agent-1's correction to G24 was right and the cause is structural: `imp`
    # had exactly ONE consumer, the death filter. Parents were drawn
    # rng.choice(pop) UNIFORMLY, so with death off, wages still accumulated
    # into `imp` and nothing ever read them. `no_death` was therefore not "the
    # full system minus carrying capacity" -- it was propose-and-keep-
    # everything, an algorithm with no selection at all, and "death is what
    # makes fitness differential" was measured against the wrong baseline.
    #
    # The deeper error is a missing mechanism, not a bad parameter. Biology
    # selects twice: who survives, and who reproduces. I had only the first.
    # With parent choice weighted by importance, `no_death` keeps reproductive
    # selection while losing survival selection, and the ablation finally
    # means what its name says. It is also the ECAN-faithful design: STI is
    # supposed to drive attention allocation, not only eviction.
    repro = "uniform_parents" not in abl

    adv_idx = Idx(R.shuffled(train, 555))
    tbl = build_bias(idx)   # (follows, precedes)
    ev = {}                       # previous round's evaluations; drives rehead
    unsolved = []                 # previous round's open problems; drives abduction
    hist, stats = [], {"rejected_capped": 0}
    dev_all = {(r, a, c) for (a, c), rs in dev_pairs.items() for r in rs}

    for rnd in range(ROUNDS):
        # ---- variation: generate offspring from the living population
        if variation and pop:
            kids = []
            n_abd = OFFSPRING // 4 if (abduction and unsolved) else 0
            for j in range(OFFSPRING):
                if j < n_abd:
                    a_ = abduct(idx, unsolved, rng)
                    k = ({"body": a_[0], "head": a_[1], "imp": START_IMP,
                          "parent": None, "op": "abduct"} if a_ else None)
                else:
                    k = mutate(pick_parent(pop, rng, repro), preds, rng,
                               pop, tbl, idx, ev)
                if k:
                    k["id"] = nid
                    nid += 1
                    kids.append(k)
            pop = pop + kids

        # ---- evaluate on the real graph against the problem space (dev)
        ev = {}
        for r in pop:
            s = score(idx, r["body"], r["head"], p_tr, dev_pairs, stats=stats)
            ev[r["id"]] = s

        # ---- adversary: co-evolving, chosen to be the hardest recent null
        if coevo:
            best, best_mean = adv_idx, -1.0
            for t in range(ADV_TRIES):
                cand_idx = Idx(R.shuffled(train, 90000 + rnd * 17 + t))
                cs = [score(cand_idx, r["body"], r["head"], cand_idx.pair,
                            dev_pairs) for r in pop]
                cs = [c["conf"] for c in cs if c]
                m = sum(cs) / len(cs) if cs else 0.0
                if m > best_mean:
                    best, best_mean = cand_idx, m
            adv_idx = best
        adv = {r["id"]: score(adv_idx, r["body"], r["head"], adv_idx.pair,
                              dev_pairs) for r in pop}

        # ---- problem space and the wave over it
        solved_now = set()
        for r in pop:
            s = ev.get(r["id"])
            if s:
                solved_now |= {(r["head"], a, c) for a, c in s["solved"]}
        unsolved = list(dev_all - solved_now)
        act = wave(idx, rng.sample(unsolved, min(4000, len(unsolved)))) \
            if (waves and unsolved) else {}

        # ---- fitness: novelty-weighted excess over the adversary
        crowd = defaultdict(int)
        for r in pop:
            s = ev.get(r["id"])
            if s:
                for ac in s["solved"]:
                    crowd[(r["head"], ac)] += 1
        value = {}
        for r in pop:
            s, a_ = ev.get(r["id"]), adv.get(r["id"])
            if not s:
                value[r["id"]] = 0.0
                continue
            excess = s["conf"] - (a_["conf"] if a_ else 0.0)
            if excess <= 0:
                value[r["id"]] = 0.0
                continue
            novel = sum(1.0 / crowd[(r["head"], ac)] for ac in s["solved"])
            m = wave_mult(act, s["solved"], rng) if waves else 1.0
            value[r["id"]] = excess * novel * m

        # ---- the finite economy: a fixed pool, shared. This is the death.
        tot = sum(value.values())
        for r in pop:
            wage = (WAGE_POOL * value[r["id"]] / tot) if tot > 0 else 0.0
            s = ev.get(r["id"])
            cost = RENT * len(r["body"]) + RENT_PRED * ((s["n"] / 1000.0)
                                                        if s else 0.0)
            r["imp"] += wage - (cost if death else 0.0)
        if death:
            pop = [r for r in pop if r["imp"] > 0]
            pop.sort(key=lambda r: -r["imp"])
            pop = pop[:MAX_POP]

        # ---- report. dev drives selection; test is never touched by it.
        # Both targets reuse the SAME body walks in `ev`, so test costs nothing
        # extra and cannot influence anything: it is read after selection has
        # already happened this round.
        md = population_metrics(pop, ev, dev_pairs)
        mt = population_metrics(pop, ev, test_pairs)
        found = any(r["body"] == planted[:2] and r["head"] == planted[2]
                    for r in pop)
        hist.append({"round": rnd, "pop": len(pop), "dev": md, "test": mt,
                     "unsolved": len(unsolved), "a15": found,
                     "mean_body": (sum(len(r["body"]) for r in pop) / len(pop))
                     if pop else 0})
        if log:
            print(f"   r{rnd:<3}pop {len(pop):4d}  dev solved {md['solved']:6d}"
                  f"  test solved {mt['solved']:6d}  test prec "
                  f"{mt['precision']:.4f}  test top12 {mt['top12']:.4f}"
                  f"  body {hist[-1]['mean_body']:.2f}"
                  f"  A15 {'yes' if found else '-'}")
        if not pop:
            break
    return hist, stats["rejected_capped"], pop


def dataset():
    """Split, plant, index. Extracted from main() unchanged so another spike can
    run these exact conditions rather than re-deriving them and drifting."""
    nt, npred, nent, tri = R.load()
    idx_ = list(range(nt))
    random.Random(SEED).shuffle(idx_)
    a, b = int(nt * 0.70), int(nt * 0.85)
    train = [tri[i] for i in idx_[:a]]
    dev = [tri[i] for i in idx_[a:b]]
    test = [tri[i] for i in idx_[b:]]

    ents = sorted({x for _, s_, o in train for x in (s_, o)})
    planted, ptr, pdev = plant(npred, nent, ents=ents,
                               rng=random.Random(4242))
    train += ptr
    dev += pdev
    print(f"split  train {len(train)}  dev {len(dev)}  test {len(test)}")
    print(f"A15 planted {planted[0]},{planted[1]}=>{planted[2]}  "
          f"{len(ptr)} train edges, {len(pdev)} dev conclusions\n")
    return train, Idx(dev).pair, Idx(test).pair, npred, planted


def main():
    train, p_dev, p_test, npred, planted = dataset()

    out = {}
    # The 2x2 on SELECTION TYPE that G24 could not express. Its old `no_death`
    # is this table's `no_death+uniform_parents` -- neither kind of selection.
    for arm in ("full", "no_variation", "no_abduct", "no_death",
                "uniform_parents", "no_death+uniform_parents",
                "static_adv", "no_waves"):
        print(f"ARM {arm}")
        h, capped, _pop = run(arm, train, p_dev, p_test, npred, planted)
        out[arm] = {"hist": h, "capped_evals": capped}
        print()

    print(f"{'arm':<14}{'testSolved0':>12}{'testSolvedN':>12}{'delta':>8}"
          f"{'prec0':>8}{'precN':>8}{'popN':>6}{'A15':>5}")
    for arm, v in out.items():
        h = v["hist"]
        if not h:
            continue
        print(f"{arm:<14}{h[0]['test']['solved']:>12}"
              f"{h[-1]['test']['solved']:>12}"
              f"{h[-1]['test']['solved'] - h[0]['test']['solved']:>+8}"
              f"{h[0]['test']['precision']:>8.4f}"
              f"{h[-1]['test']['precision']:>8.4f}{h[-1]['pop']:>6}"
              f"{('yes' if h[-1]['a15'] else 'NO'):>5}")

    fh = out["full"]["hist"]
    if not fh or not fh[-1]["a15"]:
        v = ("VOID — A15 not discovered by the full arm; the variation "
             "operators cannot reach a rule that is present by construction, "
             "so no arm comparison here is evidence")
    else:
        dt = {k: (v["hist"][-1]["test"]["solved"] - v["hist"][0]["test"]["solved"])
              for k, v in out.items() if v["hist"]}
        # v1 ranked arms on raw coverage delta and concluded that no_death
        # "beat" full -- a comparison between a 548-rule population and a
        # 94-rule one, which is G15's retracted headline in new clothes. An arm
        # now wins only by getting more correct at no more predictions.
        f = out["full"]["hist"][-1]["test"]
        dominators = [k for k, v in out.items()
                      if k != "full" and v["hist"]
                      and v["hist"][-1]["test"]["solved"] > f["solved"]
                      and v["hist"][-1]["test"]["predicted"] <= f["predicted"]]
        best = max(dt, key=dt.get)
        if dominators:
            v = (f"AN ABLATION DOMINATES — {dominators} get more correct at no "
                 f"more predictions than the full system")
        elif dt["full"] <= 0:
            v = (f"SELECTION DOES NOT GENERALISE — full arm solved "
                 f"{dt['full']:+d} more test triples. Dev is the only thing "
                 f"that improved.")
        else:
            v = (f"FULL SYSTEM NOT DOMINATED — {dt['full']:+d} test triples at "
                 f"precision {f['precision']:.4f}; no ablation gets more "
                 f"correct without asserting more. Raw coverage deltas: "
                 f"{ {k: dt[k] for k in dt} }")
    print(f"\nVERDICT: {v}")

    json.dump({"arms": out, "verdict": v, "planted": list(planted),
               "params": {"pop_seed": POP_SEED, "offspring": OFFSPRING,
                          "rounds": ROUNDS, "wage_pool": WAGE_POOL,
                          "rent": RENT, "adv_tries": ADV_TRIES,
                          "max_pairs": MAX_PAIRS, "ops": list(OPS)},
               "conditions": {"data": "real:FB15k-237+planted",
                              "split": "70/15/15", "split_seed": SEED,
                              "platforms": [["macos", "aarch64"]],
                              "concurrency": "single-process",
                              "swept": {"arm": list(out)}},
               "cites": ["G17_composition_redo", "G22_evolve", "G5_ecan_metta"]},
              open(os.path.join(HERE, "evo.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
