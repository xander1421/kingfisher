# G27 — selection does use the extra room, and the two fair comparisons disagree

**Verdict: at matched population a selected population dominates an unselected
one — 3/3 seeds — and the dominance is carried by the PREDICTION axis, not the
coverage axis. At matched proposal budget neither dominates, 0/3. Both matchings
are legitimate and they cannot both hold, because `no_death`'s population *is* its
proposal budget.**

G25 left one hole: it wanted selected-557 vs unselected-557 and could not build a
selected population past ~239, because 40× the wage pool bought only 2.17× the
population. The reason was the supply of rules whose confidence beats the
co-evolving adversary — and supply is not a constant, it is `ROUNDS × OFFSPRING`,
fixed at 600 for the whole G-series. So this spike turns the budget, not the price.

```
config           rounds  offs  budget   pop     preds  correct     prec  cov/rule
sel_r15_o40          15    40     600   229    286436     5934   0.0207      25.9
sel_r30_o40          30    40    1200   258    242660     6205   0.0256      24.1
sel_r45_o40          45    40    1800   296    251201     5923   0.0236      20.0
sel_r15_o160         15   160    2400   568    809066     6875   0.0085      12.1
sel_r45_o160         45   160    7200   684    710014     7427   0.0105      10.9
nd_r15_o40           15    40     600   557    969298     6361   0.0066      11.4
nd_r30_o40           30    40    1200  1061   1658198     7514   0.0045       7.1
nd_r15_o160          15   160    2400  2031   2718691     8454   0.0031       4.2
```

**Offspring buys population where money could not.** 12× the budget moves the
selected population 229 → 684 (2.99×), and it is `OFFSPRING` that does the work:
4× offspring at fixed rounds gives 568, while 3× rounds at fixed offspring gives
only 296. G25's stated reason for saturation was right.

## The two matchings, and why only one can hold

`no_death` removes nothing, so its standing population equals every
non-degenerate proposal it has ever made. **Its population is its budget.** A
selected population therefore cannot match it at equal budget — discarding is
what selection *is* — and to match its size you must hand selection a larger
budget. There is no setting where both are equal.

```
BUDGET-MATCHED (same rounds x offspring, populations differ)
  budget  600: sel 5934/ 286436 pop 229   nd 6361/ 969298 pop  557   trade
  budget 1200: sel 6205/ 242660 pop 258   nd 7514/1658198 pop 1061   trade
  budget 2400: sel 6875/ 809066 pop 568   nd 8454/2718691 pop 2031   trade

POPULATION-MATCHED (selected grown to a no_death population)
  pop 568 vs 557: sel 6875/809066  vs nd 6361/969298   SELECTED DOMINATES  (4x proposals)
  pop 684 vs 557: sel 7427/710014  vs nd 6361/969298   SELECTED DOMINATES  (12x proposals)
```

0/3 dominance at matched budget; 2/2 at matched population. **Which arm wins is a
choice of what to hold fixed, not a property of the algorithms.** G24 reported the
budget-matched view; G25 was asking the population-matched question. Both were
honest and they conflict for a structural reason. The confound in the
population-matched column is stated, not removed: the selected arm attempted 4–12×
the proposals to reach the same standing size.

## Which axis the dominance actually rests on

At one seed the coverage gap was 514 triples — inside the **1338-triple** seed band
G25 measured on `full_base`, the same band used to retire two of G24's arm claims.
Applying that standard here rather than only to someone else's spike, the closest
matched pair (568 vs 557) was repeated under three seeds:

```
seed 777    sel 6970/ 614384/579   nd 6843/1144867/562   DOMINATES
seed 1234   sel 6875/ 809066/568   nd 6361/ 969298/557   DOMINATES
seed 31337  sel 6899/ 708234/550   nd 6196/1069786/579   DOMINATES
```

- **COVERAGE axis — weak.** Paired differences +127 / +514 / +703; ranges separate
  by **32 triples**, which is 2% of the seed band. Not defensible as a headline.
- **PREDICTION axis — robust.** Selection reaches the same coverage while
  asserting **0.54× / 0.83× / 0.66×** as much. Same direction every seed, and it
  is what turns these into dominances rather than trades.
- **Paired sign test**, respecting the design: 3/3 same direction, floor
  **p = 1/8 = 0.125**. An unpaired permutation gives p = 1/20 = 0.050, but it buys
  the smaller floor by discarding the pairing the design built in, so 0.125 is the
  honest number.

That correction — headline the prediction ratio, not the coverage disjointness —
came from AGENT-2's review, applying to me the standard I had just applied to them.

## C7 FAILED, and the failure was worth more than the pass

The first run of this spike was contaminated: `pick_parent` (importance-weighted
reproduction) was committed **mid-sweep** at 10:58:51, so 6 of my 12 runs used
reproductive selection and 6 did not, all recorded under the same arm names. C7
compared the original set against a full regeneration and caught it — **6 of 12
configs moved.**

Classification is by the commit timestamp, an external criterion, **not** by which
runs happen to differ — and it agrees with the observed reproduce/diverge split
**12 of 12**, which is what makes it a check rather than a story fitted to the data.

- **C7a — PASS.** All 6 pre-mechanism runs reproduce exactly under the renamed
  `uniform_parents` arms. *Fails if* any moved; 6 others in the same set did.
- **C7b — the contamination is a controlled experiment.** Those 6 pairs differ only
  in reproductive selection, at identical seed and budget, which is the paired
  measurement neither lane had:

```
config                 repro ON            repro OFF           dcorrect  preds  prec
nd_r15_o160        8578/2642060 (.0032)  8454/2718691 (.0031)     +124   0.97x  1.04x
nd_r15_o40_s31337  6188/ 738232 (.0084)  6196/1069786 (.0058)       -8   0.69x  1.45x
nd_r15_o40_s777    6629/1028718 (.0064)  6843/1144867 (.0060)     -214   0.90x  1.08x
nd_r30_o40         8090/1654343 (.0049)  7514/1658198 (.0045)     +576   1.00x  1.08x
sel_r15_o160_s31337 7219/545050 (.0132)  6899/ 708234 (.0097)     +320   0.77x  1.36x
sel_r15_o160_s777  6649/ 528537 (.0126)  6970/ 614384 (.0113)     -321   0.86x  1.11x
```

**Coverage: 3/6 up, no consistent direction** — which matches AGENT-2's own
conclusion that the mechanism is worth ~nothing. **But predictions fall in 6/6 and
precision rises in 6/6 (1.04–1.45×).** So `pick_parent` does pay, on the same
axis this spike found robust — and it was declared inert from the coverage axis at
one seed, which is the exact trap its author had warned me about. One caveat
against over-reading it: `nd_r30_o40`'s ratio is 0.998, i.e. neutral, so this is
5 clear cases plus 1 null, not 6 clear cases, and the sign-test floor of 1/64
should not be quoted as if all six were real.

## Controls

- **C1′ REPRO — PASS.** `sel_r15_o40` and `nd_r15_o40` reproduce G25's `wage1200`
  and `nodeath` to the unit (229/286436/5934 and 557/969298/6361).
- **C5 SUPPLY — PASS.** 12× budget → 2.99× selected population. *Fails if* the
  population had stayed near 239, which would have made G25's stated reason for
  saturation wrong.
- **C6 A15 — PASS.** Every arm found the planted rule. *Fails if* a budget large
  enough to swamp it lost it.
- **C7a / C7b** as above.

## ATTACK on this spike's own headline: the 4×-proposals confound, removed

The population-matched column above carries a confound I shipped rather than
removed: the selected arm attempted 4–12× the proposals. A skeptic's whole reading
of this spike is *of course it won, it did four times the work.* That confound is
removable, and `attack_subsample.py` removes it.

`nd_r15_o160` is `no_death` at budget 2400: **2031 rules, all kept**.
`sel_r15_o160` is selection at the same budget 2400: **568 rules, chosen**. Both
saw the same 2400 proposals. So draw 568 of `no_death`'s 2031 at random, 20 draws,
seeds recorded. Now **budget matches AND population matches**, and the only
remaining difference is *which* 568 — selection versus a coin.

```
selected 568                     6875 correct /  809066 preds   prec 0.0085
random 568 x20 draws             3844-5731     /  797303-1158237
selected has more correct than   20/20 draws   (+1144 over the BEST draw)
selected strictly dominates      18/20 draws
```

**The confound is answered on the coverage axis: 20/20, and by a margin of 1144
triples over the best of 20 draws** from the very population that contains every
rule selection kept plus 1463 more. Selection's advantage is about *which* rules
are retained, not about how many proposals were attempted.

**But C8 did not fire under its own pre-registered criterion (strict dominance on
all 20), so `provenance.json` for this attack is `ok=false` and the attack is
recorded as VOID rather than as a pass.** Two draws (seeds 9018, 9019) assert
1.5% *fewer* predictions than selection while getting 1145 and 2925 *fewer*
correct — they undercut one axis by a hair while losing the other badly, so they
are not counterexamples on the merits. That reasoning is stated here and is
deliberately **not** promoted into a second, looser control chosen after seeing
the numbers: a criterion picked post hoc to pass is the failure this spike spent
three cycles documenting in other people's work.

So: the budget confound is answered, the strict version of the test is 18/20, and
the honest label on the artifact is red.

## What this does NOT show, and one honest red light

- **`provenance.json` reports `ok=false`, deliberately.** Six run artifacts predate
  G25's `analyse.py`, which sits in a directory declared as a dep. `analyse.py` is
  provably not an input — `sweep.py` imports `sweep` from G25, never `analyse` —
  but the staleness check works at directory granularity and cannot tell a dep's
  runner from a dep's analysis code. Dropping the dependency would turn the light
  green by removing a real dependency, so the light stays red with its cause named.
  Posted to CHANNEL as a harness class, second instance.
- **The population-matched column has an unavoidable confound**: 4–12× the
  proposals. It is the price of matching population at all, and it is the reason
  both matchings are reported instead of one.
- **One seed per budget cell**; only the 568-vs-557 pair has three. The dial's
  shape between budgets is not claimed.
- **p = 0.125 is a floor at n=3**, reached by 3/3 agreement, not evidence of a
  large effect.
- **`sel_r45_o160` has no repeats** — 7200 proposals at pop 684 is the most
  expensive cell here and it is not the headline.
- Single dataset, single split, single machine — inherited from G24.

## Reproduce

```sh
cd spikes/G27_budget
python3 sweep.py        # 12 runs, checkpointed per config in runs/
python3 analyse.py      # both matchings, seed test, C7a/C7b, verdict
```
`runs_mixed_state/` is the contaminated original set, kept as evidence because C7b
measures against it. Arms carry the explicit `uniform_parents` token so the runs
name the algorithm they measure rather than inheriting a name whose meaning moved.
