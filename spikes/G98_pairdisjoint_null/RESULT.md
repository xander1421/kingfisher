# G98 — the selector survives the leak. The *ranking of the arms under it* does not.

`certify ok=true`, **6 controls, all fired**. F1–F3 stated in `CHANNEL.md` before
this directory existed; **none fired.**
Check: `python3 spikes/G98_pairdisjoint_null/pdnull.py` (223 s warm, 870 s cold)

Finishes **G94**, which claimed this measurement, reached one arm of five, and
stopped (§2: PARTIAL is not a verdict — split the row and finish the piece you
can). G94's headline is **withdrawn** in the same cycle; see §5.

## 1 · The question, and why it decides three earlier rows

G95 nulled G88's valid-select argmax and it survived; G96 measured that its
frozen per-key *table* does not; G97 measured the `MIN_N` constant behind it.
**All three ran on the OFFICIAL FB15k-237 split, of which G48 measured 30.0% of
test to carry a train edge on the same unordered entity pair — scoring 0.5318
against 0.1503 for the rest.** So none of the three said whether the selector
selects for structure or for the leak.

G98 runs **G88's own `freeze_dir_select`/`apply_dir`** and **G95's own null**
(1000 draws, arm multiset preserved) over the **pair-disjoint** split, with
ComplEx and RotatE retrained on it under their own published protocols, G94's
DistMult inherited, and the symbolic arm mined in process from pair-disjoint
train.

## 2 · The result

```
pair-disjoint MIX test MRR                      0.2914
single arms   g64 0.2580  distmult 0.2422  complex 0.2314  rotate 0.2181  prior 0.1999
NULL (1000 label permutations, multiset held)   median 0.2416  p95 0.2494  max 0.2584
  draws >= mix 0.2914                           0 / 1000
  draws >= best single arm (g64 0.2580)         1 / 1000
  mix - null median                             +0.0498
```

| | official (G95) | pair-disjoint (G98) |
|---|---|---|
| mix | 0.3143 | **0.2914** |
| best SINGLE arm | distmult 0.2852 | **g64 (symbolic) 0.2580** |
| null median / p95 / max | 0.2783 / 0.2848 / 0.2931 | 0.2416 / 0.2494 / 0.2584 |
| draws ≥ mix | 0/1000 | 0/1000 |
| draws ≥ best single arm | 43/1000 | **1/1000** |
| **mix − null median** | +0.0360 | **+0.0498** |

**F1 quiet, and in the direction that strengthens G95 rather than rescuing it.**
The selector's margin over its own null is **larger** without the leak
(+0.0498 against +0.0360), and 0 of 1000 permutations reach it. The null is
computed on the same rows as the real selector, so this comparison carries none
of §4's between-split confounds. **The argmax is not a leak artefact.**

**F2 and F3 quiet.** The mix beats the best single arm by +0.0334, and the arm it
has to beat is now the symbolic one.

## 3 · The finding: the leak is what made the EMBEDDINGS look good

| arm | official | pair-disjoint | Δ | |
|---|---|---|---|---|
| rotate | 0.2643 | 0.2181 | −0.0462 | −17.5% |
| complex | 0.2755 | 0.2314 | −0.0441 | −16.0% |
| distmult | 0.2852 | 0.2422 | −0.0430 | −15.1% |
| prior | 0.2334 | 0.1999 | −0.0335 | −14.4% |
| **g64 (symbolic)** | 0.2703 | **0.2580** | **−0.0123** | **−4.6%** |
| **MIX** | 0.3143 | **0.2914** | **−0.0229** | **−7.3%** |

**Every embedding arm loses 15–17.5%. The symbolic arm loses 4.6% — between 3.3
and 3.8 times less than any of them.** The ordering of the single arms inverts:
DistMult leads by +0.0149 on the official split and trails g64 by −0.0158
without the leak. **The mix loses less than any embedding arm** because the
selector reallocates away from them.

## 4 · Three things this table is NOT, and the first one killed my own first reading

**(a) The raw arm counts are not comparable between splits, and correcting them
removes most of the story I first wrote down.** Raw: g64 85 → **166** keys, which
reads as the selector doubling its use of symbolic. But `MIN_N=20` assigns the
`distmult` default to any key with too little validation data, and the
pair-disjoint validation set is **46,517 against the official 17,535** — so the
fallback collapses from **210 of 446 keys to 58 of 474**. Corrected to shares of
keys the selector actually *chose*:

| | distmult | g64 | complex | rotate | prior | chosen |
|---|---|---|---|---|---|---|
| official | 69 (29.2%) | 85 (36.0%) | 39 (16.5%) | 26 (11.0%) | 17 (7.2%) | 236 |
| pair-disjoint | 127 (30.5%) | 166 (**39.9%**) | 57 (13.7%) | 27 (6.5%) | 39 (9.4%) | 416 |

**The composition barely moves.** g64 36.0% → 39.9%, distmult 29.2% → 30.5%. The
apparent doubling is the key count and the fallback rate, not the leak. Recorded
because I had already drafted the opposite claim from the raw counts, and
because it is A26 with the knob held by the split rather than by an author.

**(b) The Δ column is a between-split difference, not a controlled ablation.**
The pair-disjoint split re-partitions train+valid+test, so its train set is
**217,081 against 272,115 — 20.2% smaller**. Every arm's drop therefore confounds
leak removal with less training data, and the two test sets differ in size
(46,518 vs 20,466) and identity. **What survives the confound is the
DIFFERENTIAL**: the symbolic arm is mined from that same smaller train set and
still drops 3.3–3.8× less. The absolute Δ values are not attributable to the leak
alone and must not be quoted as "the cost of the leak".

**(c) Not comparable to G54's 0.2313.** G94 recorded that its pair-disjoint
corpus is a different materialisation from G48's (310,116 triples / 248,611
groups / 1.247 per group, against G48's train-only 272,115 / 212,110 / 1.283).
Internally consistent; not interchangeable. **The scoreboard's `filtered_mrr`
still comes only from G54**, and G98 does not move it — `eval_graph_ai.py` reads
G54 and G51 and nothing here.

## 5 · G94's headline is withdrawn, and its intuition is confirmed on other evidence

G94 reported `G51 symbolic 0.2473 > DistMult 0.2422` and concluded *"remove the
leak and the ordering inverts"*. **That symbolic number was scored with rules
mined on the OFFICIAL train set** — its `rules_cache.json` is byte-identical
(`c083dd1e9fd2…`) to nine other spikes', `load_or_mine_rules` `shutil.copy2`'d
G72's in, and its own log says `loaded 2201 rules (G72)`, not `mined`. Withdrawn
in `out/RETRACTIONS.md` and in G94's own RESULT.md.

**The ordering does invert, and this is the honest measurement of it** — but it
is a *different symbolic arm*: G98's `g64` is `mine_all_4_topologies_fast`,
4,694 rules mined in process from pair-disjoint train, not G51's 2,201 2-hop
rules. **0.2580 is not a corrected 0.2473; it is a different arm.** G94's
conclusion is right for a reason G94 did not have.

## 6 · The defect class, and the control that now catches it

**CLASS: A CACHE KEYED ON A PATH AND NOT ON THE DATA IT WAS DERIVED FROM**
(family C). Swap the corpus underneath it and it answers the OLD question while
the run reports the answer as the new one, in a line that reads `loaded`. Three
instances, one fired:

1. **FIRED** — G94's `rules_cache.json` (above).
2. **Unfired, and sharper because it is in a trainer** — `rotate.py`'s
   `EMB_PATH` *is* the file `mix.py:71` loads, and `train_or_load` returns it
   when present. G94's `run_arm.py` chdirs into each arm's own directory before
   importing its trainer, so **`run_arm.py rotate` would have loaded the
   official-split RotatE and scored it as the pair-disjoint arm.** G94 ran only
   `distmult`, whose trainer is a copy in its own directory.
3. **In the guard against the class** — `pdsplit._materialise()`'s `leak == 0`
   and triples-per-group asserts sit *after* `if os.path.isfile(test.txt):
   return`, so on a materialised corpus neither runs. A check on the cold path
   only.

**Mechanised (§12.10), not just written down.** `C6 arms_postdate_the_corpus_they_claim`
asserts every arm's mtime exceeds the newest corpus file's. G94's rules cache
fails it by 11.5 hours (05:00 against 16:28). `C1` recomputes the split
invariants from the files rather than trusting (3): leak **0**, **1.2474**
triples/group against G48's published 1.283, test n 46,518. `C4` asserts every
arm's sha256 differs from its official-split counterpart, which is what (2) would
have produced.

**The mechanism already existed and was not invoked.** `certify(deps=[corpus],
artifacts=[cache])` is exactly this staleness path; G94's `certify` did not name
the corpus as a dep. §12.10 in its usual form.

## 7 · Against me

**I listed the two `.npz` under `artifacts` against `deps` including
`spikes/harness`, and certify refused.** It was right about the mtimes and wrong
about the dependency: five lanes commit to `spikes/harness` continuously, one
landed during the 870 s this run spent training, and an embedding does not depend
on the harness at all. Left as written, the refusal is a function of another
lane's commit clock — it would refuse a correct run and pass an incorrect one
whenever the ordering flipped (family A). **Fixed by tightening, not relaxing:**
the arms moved to `captures` (content hash, and family B refuses the empty-input
hash) and the dependency they actually have is asserted directly by C6. Said out
loud in the source because "relax a dep until the gate stops refusing" is the
shape of weakening a gate to pass it.

**I drafted the arm-count finding before computing `n_small_default`**, and it
did not survive it (§4a). The run was killed and restarted to record the number
that makes the counts interpretable.

## 8 · Not done here

**The per-key agreement between the official and pair-disjoint choice vectors is
UNCOMPUTED, and not for want of trying.** It was planned as an observation, never
as a falsifier (G96's rule against retro-fitting one). `G88_5way_hybrid/result.json`
publishes `choices` as **five integers — the counts — and a `choice_sha256`**.
**The per-key table the digest pins is not in the artifact**, so it cannot be
compared against anything without re-running G88's whole pipeline. That is worth
a row on its own: a digest that pins a table nobody can read is a commitment with
no opening.
