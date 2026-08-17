# G15 — discovery works, on a corpus that has redundancy

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
