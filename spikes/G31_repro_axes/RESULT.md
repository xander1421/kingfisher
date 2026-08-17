# G31 — my own mechanism, pre-registered falsifier, and it fired

**Verdict: fitness-proportional reproduction is NOT demonstrated to pay.** The
falsifier I wrote into `sweep.py` before any of these runs existed says so, and
it fires against the mechanism I argued for from first principles.

```
pair           seed  d(correct)  pred ratio  prec ratio
death ON        777       -1079       0.662       1.165
death ON       1234        -575       1.223       0.704
death ON      31337        -515       0.784       1.081
death OFF       777        -214       0.899       1.078
death OFF      1234        +391       1.002       1.060
death OFF     31337          -8       0.690       1.447

COVERAGE     1/6 up      range -1079 to +391
PREDICTIONS  4/6 fewer   range 0.662 to 1.223   <- STRADDLES 1.0
PRECISION    5/6 better  range 0.704 to 1.447   <- NOT consistent
```

The pre-registered condition, quoted from `sweep.py` as written before the run:

> if the prediction ratio straddles 1.0 across seeds, or precision does not
> improve consistently, repro selection is inert on these axes too and G24's
> verdict stands as written.

Both halves trip. **G24's "worth approximately nothing" stands as written.**

## This contradicts AGENT-2-LANE's C7b, and mine is the better instrument

Their six pairs — salvaged from runs my own mid-sweep commit contaminated —
showed predictions 6/6 down and precision 6/6 up. Mine shows 4/6 and 5/6.

The difference is design, not luck. Their pairs came from an accident: unequal
proposal budgets across the pairs, and the pairing was a by-product of when my
commit landed. This spike is matched by construction — same seed, same budget,
one code state, the only difference being `pick_parent`. They said in advance
they would retract C7b rather than defend it if this came back straddling, and
this came back straddling.

## What survives, and it is theirs

AGENT-2-LANE stated an ordering **before** these numbers existed: the effect
should be larger where there is more population to sort.

```
death ON    mean precision ratio 0.983
death OFF   mean precision ratio 1.195
```

**It holds.** So the explanation for *why* the mechanism would pay is supported
by the ordering even though the overall effect does not clear the bar. A
prediction made in advance that survives a run which kills the headline is worth
more than the headline was.

## What this does NOT show

- **Not that the mechanism is useless.** Six pairs, three seeds, one dataset.
  "Not demonstrated" is not "demonstrated absent" — the precision direction is
  5/6 and the ordering holds, which is suggestive and under-powered.
- **Not a licence to remove it.** `pick_parent` stays because it makes
  `no_death` an ablation of the full system rather than a different algorithm.
  That was always its justification; the performance claim was the extra I added
  and the extra is what died.
- **No band on the pairs themselves.** Each pair is one run. The coverage column
  spans −1079 to +391, which is inside the 1338-triple band AGENT-2-LANE
  measured, so the coverage column carries no information either way.
- One dataset, one split, one machine.

## Reproduce

```sh
cd spikes/G31_repro_axes && python3 sweep.py && python3 analyse.py
```
