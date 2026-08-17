# G15 — RETRACTED. The result was an inverse-pair artifact measured on 15 pairs.

> **VERDICT: RED. Retracted 2026-08-17 after adversarial review.** Every number
> below the retraction was reproduced exactly by the reviewer — the arithmetic
> was never wrong. The unit was. Independently re-verified before accepting.
>
> ```
> rule 130,4=>178   489 paths  ->  15 distinct (a,c) pairs, 1 hit, 6 subjects
>   published ho_conf   0.501      (path-weighted)
>   pair-level conf     0.067
> pred4 reversed inside pred130   0.808   <- NEAR-INVERSE, not composition
> pred4 vs pred5 Jaccard          0.680   <- top two rules are ONE rule
> pred114  100 edges / 12 entities        <- clique, not transitivity
> ```

## What killed it, in order

**1. `ho_n` counts PATHS, not endpoint pairs** (`mine.py:145,148`). Parallel
paths between the same `(a,c)` were treated as independent trials. The headline's
489 "trials" are 15 pairs, of which one — `(399,117)` — carries 245 of the 489
denominator entries and all 245 hits. `ho_conf = 0.50` is **one Bernoulli trial
path-weighted 33× into a coin flip.**

This is A9 in its widest form: `conf`, `lift` and `ho_conf` were fitted to a
path-counting population and asserted about entity pairs. The premise *each path
is an independent test* never held, and I never checked it.

**2. The body is a near-inverse pair, so it is co-membership not composition.**
`4 <-> 130` at fwd 0.808 / rev 0.522 — one of only three near-inverse pairs in
FB15k-237. `a--130-->b--4-->c` means *a and c are two subjects sharing an object
b*. `mine.py:73` excludes `c == a` and nothing excludes this.

**3. Self-compositions are cliques.** `114` is a near-complete symmetric
12-entity clique (100 edges, symmetry 0.880). Every 2-hop path inside a clique
closes by construction. `114,114=>114` measures clique density. Same for `180`
(18 entities).

**4. Ranking by lift selects for degeneracy.** All seven distinct head
predicates in the top-15 have 100–149 edges against a corpus median of 373 —
and small predicates are exactly the ones living in dense low-entity blobs.
The lift figure is also uninterpretable: `marg[r]` is P(random triple has r)
while `conf` is P(r joins this pair | a path joins it) — different sample
spaces, off by 169–338×.

**5. THE PRE-REGISTERED NULL IS NOT IN THE CODE.** `mine.py:17-27` pre-registers
a degree-preserving shuffle control. `grep shuffle mine.py` finds it only in
prose and in `rng.shuffle(idx)`, the train/test split.

I *ran* the shuffle — CP5/CP6 of the session, reporting real 0.394 against null
0.055–0.104 — **as an inline heredoc that was never saved.** So the artifact
cannot reproduce it and the reviewer was right to call hypothesis (a) untested.
That is a straight B5 violation: *every input present in the artefact, or the
result is unfalsifiable by anyone who was not in the room.* I have levelled that
exact criticism at other spikes in this workspace.

**And the null would not have saved it anyway.** A degree-preserving shuffle
destroys cliques and near-inverse pairs — precisely the structures generating
the signal. "Real beats null" therefore reduces to *"the real graph contains
cliques and near-inverse predicates and the shuffle does not."* True, and not
discovery.

**6. The 4M path cap discards 73% of paths and 83% of subjects, non-randomly.**
`out_` is keyed by first appearance, so high-degree subjects enter first: visited
subjects average out-degree 32.84 against 12.57 for the 11,325 never reached.
`support` is computed on the truncated walk while `ho_n` walks all 13,620
subjects — **two different populations**, with `MIN_SUPPORT=50` applied to the
truncated one.

**7. 1,625 self-loops make tautologies, and the cap is the only thing hiding
them.** `mine.py:73` guards `c == a` but not `a == b` or `b == c`. Predicates 56,
81 and 146 are **100% self-loops**, so `a--81-->a--q-->c` therefore `a--q-->c`
is a tautology at `conf = 1.000`. Uncapped, ranks 1–6 and 15 are entirely
tautological and 10/15 have `r == p` or `r == q`. The published table escapes
only because the cap truncated before those subjects.

**8. Three `conf = 1.000` rules were silently dropped** at `mine.py:161`
(`if hc is None: continue`), each spanning **one entity pair** reached 151 ways.
They outranked the published headline and vanished with no diagnostic — the
clearest instance of finding 1 available in the artifact's own output, discarded
rather than reported.

## What survives

Almost nothing at the stated strength. Two rules survive a pair-level recount —
`197,64=>197` at 19/48 and `114,114=>114` at 23/53 — and both are confined to
blobs of ≤62 entities, with `114` being the clique.

**G15's conclusion is withdrawn.** "Discovery needs redundancy" is still a
plausible reading of the G14/G15 contrast, but it is no longer supported by
this spike, because what G15 actually detected was *degeneracy*, and a
degenerate blob is a kind of redundancy that predicts nothing.

## The methodological lesson, which is the only durable output

Every guardrail this workspace owns fired here and I shipped anyway:

- **A9** — path-fitted statistic asserted about pairs
- **A13 / degeneracy** — the control that would have caught it was prose
- **A17.4** — three unpopulated `conf = 1.000` rules dropped silently
- **B1** — reported n 172–522, true n 15–53, 6 subjects for the headline
- **A15** — a known tautology (`81,q=>q`, conf 1.000) sits in the data as a
  ready-made positive control and was never used

Pre-registering a hypothesis is not enough if the *control* is pre-registered in
prose. **A pre-registration that names a control must fail loudly when that
control is absent from the run.**

---

<details>
<summary>Original text as published, retained for provenance</summary>


**Verdict: HYPOTHESIS (a) CONFIRMED — and by a different statistic than the one
I reached for first.** Relational-composition rules mined from FB15k-237 predict
**held-out** edges at mean confidence **0.394**, against **0.055–0.104** for
degree-preserving shuffles of the same graph.

This is the first G-series spike to produce something that was not in the input.

```
FB15k-237   272,115 triples · 237 predicates · 14,505 entities
train 217,692   held-out 54,423   2-hop paths walked 4,000,001
bodies 5,191    rules with support>=50: 3,058

   p    q    r   supp   conf    lift  ho_conf  ho_lift  ho_n
 130    4  178   3228   0.85  1852.5     0.50   1090.7   489
 130    5  178   3326   0.85  1840.5     0.50   1096.8   522
 197   64  197    460   0.73  1927.6     0.42   1213.3   314
 114  114  114    150   0.60  1696.3     0.42    990.5   172
 218  139  234     50   0.78  1426.9     0.33    589.6    40
```

## The comparison I got wrong first

The pre-registered null was a degree-preserving shuffle. Run it and compare
**top lift**:

```
REAL     3,058 rules   top lift 1954.0   median lift 4.4
NULL 0   1,274 rules   top lift 1750.2   median lift 1.0
NULL 4   1,289 rules   top lift 1140.8   median lift 0.9
```

**Top lift is not above null.** 1954 against a null maximum of 1750 is nothing —
the max of 1,274 null rules is high by extreme-value effect alone, the same
mistake as comparing G9's discovered partition against the best of 25.

Two statistics do separate:

- **median lift**: 4.4 real against 0.8–1.0 null — the *population* differs even
  though the extreme does not.
- **held-out confidence**: 0.394 against 0.055/0.104/0.055 — 4–7×, and this is
  the one that matters because it scores prediction rather than fit.

Comparing maxima was the third lenient comparison in this series to fire on
noise (G2's 5 shuffles, G9's two-point gap). The pattern is consistent enough to
state as a rule: **never compare extremes across populations of different size.**

## The held-out protocol was also wrong first

First attempt walked 2-hop paths **inside the test set**. A path needs *both*
edges held out, so at an 80/20 split only ~4% survive — `ho_n` came back at
7–206 and the confidences were noise.

Corrected to the standard KG link-prediction shape: **walk the body on train,
check the head against held-out edges**, and skip endpoint pairs whose `r`-edge
was already in train (otherwise the rule is scored on an answer it saw).
`ho_n` rose to 172–522.

The tell was `ho_n` being tiny, not the confidences being low. Shape first,
again.

## Why this worked where G14 failed

Same mechanism family, opposite result, and the difference is the corpus.

G14 asked whether two nodes are **functionally equivalent** and found zero
classes across 60 spikes, because a sparse irregular citation graph has no
structural redundancy — every node is unique. G15 asks whether relational
**composition** is predictive, on a graph with 272k triples over 237 predicates
where structure repeats by construction.

> **Discovery needs redundancy. The mechanism was never the problem; the
> substrate was.**

That retroactively explains the whole G2/G3/G4 failure too — 124 claims with
unique features cannot support rule induction, and no amount of reframing was
going to fix a corpus with no repeated structure.

## Hypothesis (b), partially standing

(b) said the top rules should not be restatements of a single high-frequency
predicate. Two of the top rules are **self-compositions** — `114,114 => 114` and
`180,180 => 180` — which is the signature of a *transitive* predicate, an
interpretable structural discovery rather than a frequency artifact.

**Not yet verified.** An adversarial review is running against this spike
specifically to check whether the top rules are inverse-predicate artifacts,
hub-dominated, or truncated by the 4M path cap. FB15k-237 is known to contain
near-inverse relation pairs and extreme degree skew, and this spike has done
nothing to exclude either.

## What this does NOT show

- **Not that the substrate discovered it.** Mining is Python search over an
  index. MeTTa was not involved. The honest claim is that *the mechanism* works
  on this data, not that *the graph* found it. Expressing the discovered rules
  in MeTTa and verifying they reproduce is a separate step.
- **Not validated against inverse pairs or hubs** — see above, review pending.
- Path walk capped at 4,000,001 and returns early, so later subjects in
  iteration order are never visited. Whether that biases which bodies are
  counted is unchecked.
- One split, one seed, one support threshold.

## Reproduce

```sh
cd spikes/G15_analogy_realkg && python3 mine.py     # ~1.4 s
```

</details>
