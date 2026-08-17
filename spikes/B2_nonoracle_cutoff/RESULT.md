# B2 — B1's "% store checked" is a per-query ORACLE MINIMUM, and its stated meaning needs ~12× the reported budget

**Verdict: B1's numbers all stand and are reproduced exactly. One SENTENCE in B1
is scoped, and it is the sentence that says what the number means.** The
headline VTCM conclusion — B=16 fits an 800k-triple shard in 8 MB — is untouched:
it is about store size and involves no cutoff at all.

`certify ok=true`, 4 controls, falsifier stated before the run and **it fired**.
Artefacts: `nonoracle.py` (stdlib, seed 20260817, pinned to B1's), `RUN.txt`,
`nonoracle.json`, `certify.py`, `provenance.json`.

## What B1 measures

`spikes/B1_bundling_real/bundling.py:91-103`:

```python
pos    = order.index(row) // B      # the bundle CONTAINING THE ANSWER
target = score(bundles[pos])        # the ANSWER's score
beat   = sum(1 for _ in range(600) if score(bundles[randrange(nb)]) >= target)
```

That is the **per-query oracle minimum**: the smallest shortlist that happens to
contain this query's answer, computed by looking the answer up. A deployed
prefilter has no `pos`. `out/RETRACTIONS.md` rule 5 — *"a cutoff, threshold or
parameter fitted to the ground truth must be labelled as an oracle and its cost
reported"* — was written after `decay.c` computed `truth` from the answers. The
same shape is here, unlabelled, under a **GREEN** claim.

## Control C1 first, because it is what licenses everything below

The scorer is copied from B1, so it must reproduce B1 or it describes a
different instrument. **14 of 14 comparisons exact** (median and p90, all 7 B).

**It failed on the first run, and that is the more useful half.** I reconstructed
`base()` and the bundling step from a truncated read and *invented* both: a
2-term binding instead of a 3-way majority, and a bitwise OR instead of a per-bit
majority vote. B=64 median came out **76%** against B1's 0.17%. Nothing in the
output looked malformed. Had C1 not been written first, this page would have
reported a 450× discrepancy as a finding about B1.

## Measured — same corpus, same seed, same instrument

Per-query oracle minimum, as a fraction of the store:

| B | store MB | median | p90 | p99 | **max** |
|---|---|---|---|---|---|
| 1 | 34.83 | 0.00% | 0.00% | 0.17% | 0.33% |
| 4 | 8.71 | 0.00% | 0.00% | 0.17% | 0.83% |
| 8 | 4.35 | 0.00% | 0.17% | 0.33% | 0.67% |
| **16** | **2.18** | **0.00%** | **0.17%** | **1.00%** | **1.50%** |
| 32 | 1.09 | 0.00% | 0.50% | 1.50% | 3.17% |
| 64 | 0.54 | 0.17% | 1.17% | 3.00% | 3.83% |
| 128 | 0.27 | 0.50% | 3.17% | 4.50% | 5.00% |

Recall at a budget **fixed in advance**, no per-query oracle:

| B | 0.1% | 0.2% | 0.5% | 1.0% | 2.0% | 5.0% |
|---|---|---|---|---|---|---|
| 16 | 75.0% | **90.8%** | 94.2% | 99.2% | **100%** | 100% |
| 64 | 43.3% | 55.0% | 70.8% | 85.0% | 95.8% | **100%** |
| 128 | 28.3% | 42.5% | 56.7% | 65.8% | 78.3% | **100%** |

## The three findings

**1 · The stated meaning is the max, and the reported statistic is the median.**
B1's own comment says the quantity is *"what FRACTION OF THE STORE must the exact
stage check **to be sure of catching the answer**"*. "Sure" is 100% recall, which
is the **max** over queries, not the median. At B=16 that is **1.50% against a
reported 0.00%**; at B=128, **5.00% against 0.50%, exactly 10×**. Family E: the
number is real, the model is wrong.

**2 · With a budget fixed in advance, B=16 needs 2.0% for full recall — ~12× the
published 0.17% p90.** The falsifier said: if a non-oracle cutoff reached full
recall inside the spread of B1's published figures, the oracle was decorative.
It did not. **The falsifier fired.**

**3 · Every published figure is at the instrument's quantum.** `SAMP = 600`, so
every fraction is `k/600` for integer `k` (control C2). B1's median of **0.00%
for B=1…32 means "below one sampled bundle", not zero**, and its p90 of 0.17% is
**exactly one sampled bundle** — the smallest non-zero value the instrument can
express. A headline of "0.2% of the store checked" is the resolution floor being
quoted as a measurement.

## What this does NOT say

- **No B1 number is withdrawn.** C1 reproduces every one of them.
- **B1's GREEN verdict is not overturned.** The VTCM claim is about *store size*
  and never used the cutoff. 2.0% of a 2.18 MB store is still a small shortlist,
  so the *direction* of B1's argument survives at its own operating point.
- **This is a scope, not a kill**, and the distinction is the one
  `out/RETRACTIONS.md` insists on: the evidence is right, one sentence about what
  it means is wrong.
- **It does not sweep the class.** The unassigned LEDGER item is *"every bundling
  and shaping result in the tree, including the real-KG 4.1–5.6×, uses a cutoff
  fitted to the ground truth"*. This spike settles **one** of them, at the one
  place a live GREEN claim rests on it. S11 / S17 / S47 / S48 / N1 are unexamined
  and the item stays open.

## Reproduce

```sh
cd spikes/B2_nonoracle_cutoff
python3 nonoracle.py     # ~5 min, stdlib only; C1 must print PASS
python3 certify.py       # must print ok
```

`nonoracle.py` exits non-zero if C1 fails, so a drifted copy cannot publish.
