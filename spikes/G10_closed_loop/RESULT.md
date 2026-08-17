# G10 — the loop closes, survives, and tracks a greedy oracle

**Verdict: SURVIVES.** Ten cycles of query → stimulus → ECAN epoch → forget the
least important → query the smaller graph. No collapse, no oscillation, and
attention-driven forgetting lands **within 0–6% of a greedy oracle that is shown
the answers**, using only local stimulus.

This is the first unambiguously positive result in the G-series beyond "it runs".

```
cycle  live  control  attention   oracle  headroom
    0    60    100%      100%      100%       0%
    1    54     79%       99%       99%       0%
    3    45     52%       93%       93%       1%
    5    37     24%       80%       83%       4%
    7    31     18%       69%       73%       3%
    9    26     16%       64%       63%      -1%
```

At 43% of the original graph the loop still answers **64%** of the baseline
findings. The identical prune schedule with attention removed answers **16%**.

## The three outcomes it could have had

A feedback system has more than one failure mode, and the experiment was
designed to distinguish them:

- **COLLAPSE** — pruning removes what the next query needed, stimulus shrinks,
  more gets pruned, the graph eats itself. Did not happen: preservation is
  monotone and never approaches zero.
- **OSCILLATE** — importance sloshes between regions and answers flicker.
  Did not happen: the sequence is monotone non-increasing at every cycle.
- **CONVERGE** — observed. Decay is smooth and decelerating; the last three
  cycles move 69 → 66 → 64%.

## Attention is at the achievable ceiling, not merely above the floor

A floor alone cannot distinguish "attention works" from "this task is easy".
The oracle arm scores each node by how much mean preservation it contributes,
weighting each query by `1/|baseline_q|` so `q_green`'s 148 findings do not
drown `q_invalid`'s 6, and keeps the top *n* — with full knowledge of the
answers.

Attention **matches it**, and at cycle 9 exceeds it by a point.

That the oracle can be beaten is the honest caveat: it is **greedy per node**,
scoring nodes independently while a finding needs *both* endpoints. So it is an
approximate upper bound, not an optimum. The defensible claim is:
**attention-driven forgetting is at least as good as a greedy oracle with
answer knowledge, while using only local stimulus.**

## Preservation is not uniform — it tracks what fits

```
cycle 9, 26 nodes live      touched at baseline
  q_invalid   100%                  7 nodes
  q_yellow    100%                 11
  q_red        53%                 33
  q_2hop_red   43%                 45
  q_green      23%                 55
```

Small query classes are preserved perfectly for all ten cycles. Large ones decay
toward their information limit — **a query needing 55 nodes cannot be answered
from 26**, so `q_green`'s 23% is near the floor imposed by arithmetic, not by
the policy.

The loop protects what fits. That is a property worth stating in the design: a
device holding a working set serves narrow query classes indefinitely and broad
ones only while the shard is large.

## Configuration, all placeholders and labelled as such per B5

```
CYCLES 10   PRUNE_FRAC 0.10/cycle   EPOCHS 1 per cycle
SCALE 1000  RENT 50  SEED 1000      5 query classes, one context each
```

Per G9, each query class gets its own context and a node survives on its **best**
standing across contexts — several budgets, membership second-order.

## What this does NOT show

- **60 nodes, one graph, one prune rate, one epoch per cycle.** Nothing swept.
  A steeper prune rate or fewer contexts could collapse it and neither was tried.
- **Not run on the phone.** G1 and G5 established two-device byte-identity for
  single passes; the loop is desktop-only and the transport half is M1.5's.
- **The oracle is greedy**, so "matches the ceiling" means "matches a greedy
  ceiling". A true optimum is a set-cover problem and was not computed.
- Preservation is measured against the **baseline answers**, so this measures
  retention, not discovery. The loop never learns anything new — G2–G4 already
  established it cannot at this n.

## Reproduce

```sh
cd spikes/G10_closed_loop && python3 loop.py     # ~33 s, 10 cycles x 2 arms
```
