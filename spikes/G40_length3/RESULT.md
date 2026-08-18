# G40 — length-3 rule bodies do NOT raise filtered MRR. F1 fired.

**Verdict: F1 FIRED.** Adding 612 mined length-3 rules to a 3,387-rule base
*lowers* filtered MRR by 0.001061. Both falsifiers were posted to `CHANNEL.md`
before the run.

```
arm             rules      MRR        H@1      H@10
base_len1_2     3,387   0.106019    0.0591   0.1785
plus_len3       3,999   0.104958    0.0561   0.1771
                        ---------
delta                   -0.001061
```

Mining: 400,000 random 3-hop walks, seed `0xC0FFEE`, 22,093 distinct 3-bodies
observed, 612 rules kept at `min_sup=8 / min_conf=0.05`. `MAX_RULES=12000` never
bound — **0 dropped**, so the negative is not a truncation artefact.

## What this costs, and what it corrects

**It narrows G39.** G39 concluded the machinery is *search-limited, not
selection-limited*, and I took that to mean depth. It does not. G39's evidence
was that `evo.mutate` cannot express a **length-1** body while length-1 alone
scores 0.1572. That is a **rule-family** limit, not a **depth** limit. Extending
the search *downward* in length paid enormously; extending it *upward* pays
nothing. The correct reading of "search-limited" is **the missing families were
length-1 and constants**, and both are now in.

**It reconciles with G23 instead of contradicting it.** G23 measured depth-3
against its own null at a *smaller* gap than depth-2 (+0.0949 vs +0.1157) with a
null twice as noisy, and concluded depth pays less than width. That was the
top-12 held-out statistic, which G30 retired. I flagged before this run that
G38's finding — the evolved population 2.36× worse in absolute MRR while 2.11×
*better* at matched rule count — meant "weaker per rule" and "raises MRR" could
both be true, and only a run would separate them. **They are not both true.**
Depth-3 is weaker per rule *and* does not buy coverage worth having. Two
statistics, two spikes, one conclusion.

## F2 satisfied by construction

This file contains **no evaluator**. It imports `varlen.evaluate_varlen`, which
G37 pinned to `yardstick.py` at 6 decimal places. A spike that both mines and
scores its own rules can move the number twice and report it once.

## Why the base is 0.106 and not G34's 0.2648

The base arm is **2-hop + length-1 subsumption only**. Constant-grounded rules
carry a `const` field that varlen's body walk has no slot for, and inverse
length-1 rules are `p(x,y) <- q(y,x)` — a *backward* walk varlen does not
express. Including either by pretending it is a forward body would score a rule
that means something else.

So the controlled comparison is **base vs base+len3 inside one process**, and
G34's published 0.264807 is context, not the baseline. Comparing my base against
a number built from a larger rule family is the differently-sized-population
error this repo retracted G15 for.

The base's 3,198 two-hop rules match G17's published count exactly, which is the
cheap check that this process built the same thing.

## What this does NOT show

- **Not that length-3 is worthless in general.** It shows *path-sampled* length-3
  rules at `min_sup=8 / min_conf=0.05` do not help *this* base. A different
  mining strategy (exhaustive extension of high-support 2-hop bodies, or
  AnyBURL's own sampler with its confidence estimator) could differ.
- **Not measured against the full G34 system.** Whether length-3 helps a base
  that already has constants and inverses is untested — and constants are where
  G34's largest single gain came from (+41.6% relative).
- **One seed, one split.** No band on the −0.001061. It is small enough that the
  honest claim is "does not raise", not "lowers".
- 400k walks is a sample. A larger sample finds rarer bodies; whether they are
  *good* rules is exactly what `min_conf` already filters for.

## Reproduce

```sh
cd spikes/G40_length3 && python3 len3.py     # ~4 min
```
