# G48 — on a split that cannot leak, this lane's filtered MRR is 0.1358

**AGENT-2, 2026-08-18, builder cycle C22.** `certify ok=true`, 3 controls,
3 falsifiers stated in `CHANNEL.md` before the run. **None fired.**

## Verdict

| split | train | test | **same-pair leak** | **MRR** | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|---|---|---|---|
| original 70/15/15 shuffle | 190,480 | 40,818 | **12,249** | **0.2648** | 0.1748 | 0.3169 | 0.3929 |
| **pair-disjoint** | 190,480 | 40,817 | **0** | **0.1358** | 0.0978 | 0.1506 | 0.2061 |

**Leak-free, by construction, at zero — not below a threshold.** Partition by
**unordered entity pair** rather than by triple: every triple on a given `{s,o}`
pair goes to one side, so no test triple can have a train edge on its own pair
in either direction. **212,110 pairs over 272,115 triples, 1.283 triples per
pair.** There is no constant to fit and nothing calibrated against the answer —
A26, and the property both the 70/15/15 shuffle and
`PROGRAM.md:40`'s `>= 0.2500 (Current: 0.2648)` lack in opposite directions.

## The falsifier I most expected to fire did not, and it is the reason this is a measurement

**F3 — the training-volume confound — did not fire, and it did not fire
exactly.** Greedy fill over shuffled pair groups landed on **190,480 train
triples, identical to the original to the triple**, ratio **1.0000**, with the
test sets differing by **one** triple. I wrote in the preregistration that pairs
are unequal in size so this could not hit the targets exactly and that it was
"the one I am most likely to be wrong about". **It hit exactly, so the drop is
attributable to the split's structure and not to how much data trained it.**

- **F1** *if the pair-disjoint split leaves ANY test triple with a same-pair
  train edge, the instrument is fiction — "small" is not accepted.* **Did not
  fire: 0.**
- **F2** *if the leak-free split lands within 0.002 of 0.2648, G46's mechanism is
  retracted and only its arithmetic kept.* **Did not fire: 0.1358, a gap of
  0.1290.**
- **C1** the same detector still reports **12,249 (30.01%)** on the original
  split, so F1's zero is a clean split and not a blind detector (A15) ·
  **C2** test sets differ by 1 triple · **C3** the original arm returns
  **0.2648 / 0.3929 exactly**, so this is the instrument G34, G46 and G47 used
  and only the split moved.

## Against my own previous cycle: the proxy was optimistic

**G46 called 0.1503 "the honest number". It is not — 0.1358 is, and 0.1503
overstated it by 0.0145, about 11%.** Both are in the same direction and G46's
verdict stands, but the correction matters and it has a mechanism: `no_same_pair`
filtered the **test** side only, leaving every leaky pair edge in **train**,
where it still helps other predictions through composition. **A post-hoc filter
removes the queries that leak; it does not remove the leakage from the model.**
G46 labelled 0.1503 a proxy and stated that ceiling; this is what the ceiling was
worth, measured rather than left as a caveat.

## What this costs, said plainly

`filtered_mrr` carries weight 2.0 with `min_acceptable` **0.25**. On a split that
cannot leak, this lane measures **0.1358** — not 0.2648, and not 0.1503.
Every G-series number from here should be quoted on this split.

**And the gate is uninformative, so this is neither a pass nor a fail.**
`.github/autoloop/PROGRAM.md:40` writes `filtered_mrr >= 0.2500` on the same line
as `(Current: 0.2648)` — the bar was derived from the number it gates, which is
the same oracle-fitting this repo already killed a prefilter cutoff for.
**ATOM-3 found it; the framing is theirs and it is right: a threshold whose
purpose is "has the method improved" cannot be derived from any measurement of
the current method, in either direction.** A bar from a baseline the method does
not share (frequency ranking, or a published comparand if one ever arrives) can
fail; one from our own number cannot. **Not re-baselined here — re-baselining a
gate this lane is measured by is A22 whichever way it moves, and the eligible
parties are a lane not scored on it, or the operator.**

## What this is not

**Not FB15k-237's official test split**, which is still not in this repository —
the ask is open in `HUMAN_NEEDED.md`. This is a **pair-disjoint re-split of the
official TRAIN split**: a better *local* benchmark, not a literature comparand.
**No published figure is quoted in either direction** (G35: 7 of 7 external
attributions in this tree resolve to nothing under `corpus/`).

It also does not remove every leakage structure — it removes **one**, the
same-entity-pair edge, which is the one G46 measured and the one length-1 rules
consume. Whether other structures survive is unmeasured and is not claimed
either way.

## Files

`split.py` (both splits, the detector, controls, `certify`) · `split.json` ·
`provenance.json`.

```sh
python3 spikes/G48_pairdisjoint_split/split.py   # ~110 s, ok=true, C3 pins 0.2648
```
