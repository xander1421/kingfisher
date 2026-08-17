# G17 — a weak composition signal survives everything that killed G15

> **UPDATE 2026-08-17 — two things closed, one reading corrected. The verdict
> stands; the headline number was being read wrong.**
>
> **1. A20 capability test: PASS** (`a20_capability.py`, output in
> `A20_OUTPUT.txt`). A permutation p is only worth its precision if the null can
> *produce* the structure being tested. Planting a composition rule of known
> strength into the shuffled graph recovers it at the strength planted:
>
> ```
> frac=0.2  recovered rank 38  ho_conf 0.199   statistic +0.0000
> frac=0.5  recovered rank  1  ho_conf 0.499   statistic +0.0181
> frac=0.9  recovered rank  1  ho_conf 0.895   statistic +0.0511
> ```
>
> The test was degenerate **twice** before it passed, both times reporting a
> clean "NOT DETECTED" on an empty intervention — once planting on a `(p,q)`
> with no 2-hop paths (`+0 edges`), once planting into train *and* test so
> `redo.py:118` excluded every planted pair (statistic unchanged to four
> decimals under a 1.3M-edge plant). Both are recorded in the script's
> docstring. A control that runs on no input still prints a verdict.
>
> **2. The p-value is replaced by a distance, not by a smaller p**
> (`../G21_null_rust/`). 500 draws in Rust, gate-checked bit-equivalent to this
> implementation at 1.1e-16:
>
> ```
> null n=500  mean 0.3281  sd 0.0121  max 0.3634     >= real 0/500
> p = 0.0020, which is exactly 1/501 — STILL THE FLOOR
> ```
>
> `p = 0.040` below was `1/(24+1)`; `0.0020` is `1/(500+1)`. More draws only
> lower the floor. **The permutation p is structurally floor-limited for an
> effect this far out** and is not the informative statistic. The null's tail is
> Gaussian-consistent as far as it can be checked (max of 500 draws lands at
> 2.91 sd, exactly `E[max]` for 500 Gaussians), so the distance is readable:
> real is **6.4 sd above the largest of 500 shuffles**.
>
> **3. The reading correction, which matters more than either.** The null mean
> is **0.328**. The shuffle reproduces **74% of the real statistic from chance
> structure alone**. The effect is the **0.113 gap**, not the 0.441. Any summary
> quoting "0.44 held-out confidence" as the finding is quoting mostly baseline —
> the degree sequence and predicate marginals do that much unaided. And since
> A20 measured one strong rule as worth +0.051, that gap is ~2.2 strong-rule
> equivalents **spread across the top 12**, not one rule the shuffle missed.

**Verdict: SURVIVES, at about a third of nothing like the strength G15 claimed.**
Real mean top-12 held-out confidence **0.441** against a degree-preserving null
of **0.329** (n=24, sd 0.012, max 0.350). Zero nulls reach it.

G15 claimed 4–7×. What actually survives the exclusions is **1.34×**.

```
real                        0.441
null n=24   mean 0.329   sd 0.012   min 0.301   max 0.350
  >= real   0/24        permutation p = 0.040
  effect    (0.441-0.329)/0.012 = 9.3 null-sd
```

## Every defect the review named is closed, and each closure is in the code

| G15 defect | closure here | evidence |
|---|---|---|
| `ho_n` counted paths | denominator is distinct `(a,c)` pairs | `MIN_PAIRS=30` |
| body was a near-inverse pair | reject if `rev(q) ∩ p` exceeds 30% of `p` | **357 rules rejected** |
| self-loops made tautologies | drop `s==o` edges; guard `a==b`, `b==c`, `c==a` | preds 56/81/146 are >90% self-loop |
| head restated a body predicate | reject `r == p` or `r == q` | **1331 rules rejected** |
| 4M cap, non-random truncation | **no cap** | full walk |
| the null lived in prose | **the null is in `redo.py` and its output is in `redo.json`** | — |

### Positive control, which the review found sitting unused in the data

```
predicates >90% self-loops: [56, 81, 146]
tautologies surviving into the output: 0    PASS
```

`a--81-->a--q-->c ⊢ a--q-->c` is a tautology at conf 1.000 and topped G15's
uncapped ranking. If it appeared here the run would be void regardless of the
main result. It does not.

## Two honest weaknesses in my own statistic

**p is floor-limited and I chose n to clear alpha.** With 24 draws the smallest
expressible p is `1/25 = 0.040`. I ran 10 first, got `0/10 → p = 0.091`, and
extended to 24 because that is the smallest n where `p < 0.05` is *reachable*.
That is legitimate only if stated, so: **stated.** The true p is bounded above by
0.040 and unbounded below; the sample size was chosen against the threshold.

**Effect size is the better statistic here** because it does not move with n:
real sits **9.3 null-sd** above the null mean and above the maximum of 24 draws.
But null sd is only 0.012 because a mean of twelve order statistics over ~2,700
rules is very stable, so 9.3 sd overstates how surprising this is to a reader
who has not seen the null's tightness.

## The rules that are not blobs

G15's headline was 6 subjects and 6 objects. Three survivors here have real
entity counts:

```
  5,178 => 4    pairs 2558   ho_n 1001   conf 0.408   737 entities
  4,178 => 5    pairs 2595   ho_n  991   conf 0.385   737 entities
 66,133 => 48   pairs 1302   ho_n  558   conf 0.314  1275 entities
```

Caveat on the first two: predicates 4 and 5 are near-duplicates
(Jaccard 0.680), so `5,178=>4` and `4,178=>5` are close to the same rule stated
twice — the same duplication that inflated G15's top-2, surviving in a milder
form because the inverse filter targets `rev(q) ∩ p`, not `p ∩ q`. A
near-duplicate *head* is not caught by any exclusion here.

## What this does and does not restore

**Restores:** relational composition carries *some* held-out signal on FB15k-237
beyond degree structure, at 1.34× over a degree-preserving null, with tautology
and inverse bodies excluded and the control in the code.

**Does not restore:** G15's retraction stands in full. Its 4–7× was the excluded
degeneracy. And "discovery needs redundancy" remains withdrawn as a *measured*
claim — 1.34× on one corpus with a floor-limited p is not the evidence that
sentence needs.

**Still not shown:** that the substrate discovered anything. Mining is Python
search over an index; G16 established hyperon can *apply* such a rule and agree,
on the one rule small enough to run before the 1024 panic.

## Reproduce

```sh
cd spikes/G17_composition_redo && python3 redo.py     # ~77 s, includes 3 nulls
```

The 24-draw null is an extension of the same function, not a separate script;
`redo.json` carries the 3-draw version and this file carries the 24.
