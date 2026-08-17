# G21 — 500 null draws in Rust. The p-value did not get smaller, and that is the result.

**G17 reported `p = 0.040` from 24 degree-preserving shuffles — exactly
`1/(24+1)`, the smallest p that 24 draws can express. This spike ran 500. The
p is now `0.0020`, which is exactly `1/(500+1)`. Still the floor. Zero of 500
shuffles reached the real value, and the largest fell 6.4 null-sd short.**

The intended result was "replace a floor-limited p with a real one". What
actually happened is better and required giving up the p-value as the headline:
**when an effect sits this far outside its null, the permutation p is
structurally floor-limited.** More draws only lower the floor. No number of
shuffles will ever produce a non-floor p, because none of them ever exceeds
real. The informative statistic is the standardised distance, and that needed
the null's shape checked before it could be read.

```
real statistic 0.4405469705   (Python 0.4405469705)
EQUIVALENCE GATE: PASS   (delta 1.110e-16)

null n=500   mean 0.3281   sd 0.0121   min 0.2933   max 0.3634
  >= real 0/500     permutation p = 0.0020   (floor 0.0020)
```

500 draws in **2 min 46 s** on 12 threads. The same loop in Python was ~25 s per
draw single-threaded, so this run would have been about **3 h 30 m** — which is
why G17 stopped at 24 in the first place.

## The equivalence gate, and the two bugs it did not catch

A faster null loop that computes a *different* statistic is worthless, so the
real-graph statistic must reproduce Python's before any null value is believed.

```
delta 1.110e-16
```

That is float summation order over 12 terms and nothing else. The port is
bit-equivalent up to associativity.

**But the gate passed only after two bugs were fixed by reading, not by
testing** — and both would have produced a confident wrong number:

1. **The gate was `|real - 0.441| < 0.0005`.** Python's value is
   `0.44054697045288443`, so the margin was 0.00005 on a threshold I had set by
   eye from a rounded printout. It happened to pass. A slightly different
   rounding and a *correct* port would have exited 2, looking like a porting
   error. The gate now reads `real_py.txt`, written by `dump_split.py`.
   This is the same defect agent-1 found in the quorum's ISA axis: a value
   **self-declared from a display** instead of **observed from the thing
   itself**.

2. **The sort was missing Python's tie-break.** `redo.py:126` sorts by
   `(-ho_conf, -ho_pairs)`; the Rust sorted by confidence alone. Ties at the
   top-12 boundary would pick a different 12th rule and move the statistic with
   no logic differing anywhere. `dump_split.py` now reports how many rules tie
   at the boundary (1 on the real graph, so it was not load-bearing there — but
   it is unchecked across 500 shuffled draws, which is exactly where it would
   have bitten silently).

Neither bug was found by running anything. Both were found by re-reading the
port before trusting it, which is the only reason this spike is not another G15.

## Is the distance readable? The null's shape says yes, up to a limit

A 9.3-sd distance means nothing if the null is skewed or heavy-tailed. Checked
in `tail_shape.py`:

```
skew -0.173   excess kurtosis -0.016

  >= 1.0 sd   observed  76   expected (Gaussian)  79.3
  >= 1.5 sd   observed  26   expected             33.4
  >= 2.0 sd   observed   8   expected             11.4
  >= 2.5 sd   observed   2   expected              3.1
  >= 3.0 sd   observed   0   expected              0.7

  observed max            2.91 sd
  E[max] of 500 Gaussians 2.91 sd
```

The extreme of the null lands exactly where the maximum of 500 Gaussians is
expected to. The tail is Gaussian-consistent everywhere draws exist, and if
anything slightly *thinner*.

**What that licenses, and what it does not.** A Gaussian tail puts 9.3 sd at
around `p ~ 1e-20`. **That number is not reported as a result.** It extrapolates
the tail about 6 sd past the furthest point any of these 500 shuffles reached,
and nothing here tests it out there. Quoting it would be the same move as G18's
withdrawn "exact bound 1021" — a clean number produced by an assumption rather
than a measurement.

**Supported:** 0 of 500 degree-preserving shuffles reached 0.4405; the largest
came up 0.0772 short; the shortfall is not an artefact of a skewed baseline.

## The correction this forces on how G17 is read

```
null mean 0.3281        real 0.4405        ratio 1.343
```

**The shuffle reproduces 74% of the real statistic from chance structure
alone.** The effect is the **0.1125 gap**, not the 0.4405. Any summary that
quotes "0.44 held-out confidence" as the finding is quoting mostly baseline. The
degree sequence and the predicate marginals do that much on their own.

Combined with G17's A20 capability test (`../G17_composition_redo/a20_capability.py`),
which measured one strong planted rule as worth **+0.051** of statistic: the
0.1125 gap is about **2.2 strong-rule equivalents**, spread across the top 12
rather than concentrated in one. The effect is broad and weak-per-rule, not one
rule the shuffle missed.

## What this does NOT show

- **Not that the null is complete.** A20 shows the null *can* contain a planted
  composition; it does not show the null contains everything non-compositional
  that the real graph has. Same one-directional strength agent-1 identified in
  provenance: it proves "could not have come from chance", never "did come from
  composition".
- **Not a p-value below the floor.** 0.0020 is `1/501`. Reporting it as though
  500 draws had *measured* a small probability would be wrong; they bounded it.
- **One dataset, one split.** FB15k-237, seed `0xC0FFEE`, 80/20. The split is
  fixed across all 500 draws by design — the shuffle is the randomisation, not
  the split.
- Single machine. No cross-device check on this spike; the statistic is pure
  arithmetic over integers and the Python/Rust agreement at 1.1e-16 is a
  stronger cross-implementation check than a second device running the same
  binary would be.

## Reproduce

```sh
cd spikes/G21_null_rust
python3 dump_split.py          # writes split.txt and real_py.txt
cargo build --release
./target/release/g21null 500   # writes nulls.txt, ~2m46s on 12 threads
python3 tail_shape.py
```

Draws are seeded `1000 + i`, so the run reproduces exactly. Verified: a second
500-draw run returned identical mean, sd and max.
