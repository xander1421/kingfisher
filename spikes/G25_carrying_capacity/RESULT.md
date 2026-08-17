# G25 — `no_death +5059` was a knob I picked and an operator I under-credited

**Verdict: G24's `no_death` arm does not show that death costs coverage.** Two
independent findings, either of which is sufficient:

1. **ATTRIBUTION.** At matched population and with no selection on either side
   (531 vs 557 rules), removing abduction costs **4847 of the 5059** correct
   triples (6361 → 1514). `no_death`'s coverage is problem-directed proposal
   retained without limit, not population volume.
2. **CALIBRATION.** Keeping death and raising `WAGE_POOL` alone — a constant I
   chose, not a measurement — closes **51–85%** of the gap across three run
   seeds, at 2.6× fewer predictions and 2.5× the precision.

And the reason the comparison was worth running at all is a defect in the
ablation, visible in G24's code and absent from its RESULT.md:

> **The `no_death` arm has no selection in it.** With `death` off nothing is
> removed, `MAX_POP` never applies, and parents are drawn `rng.choice(pop)` —
> uniformly. Wages are computed and accumulate into `imp`, and `imp` is read by
> exactly one statement: the one death uses. So `no_death` is not "the full
> system minus carrying capacity". It is propose-and-keep-everything, and its
> +5059 was earned with **zero differential fitness**.

An ablation that removes more than it names cannot answer what the named part
does. That is what made "removing the finite economy gets MORE coverage" look
like a finding about ECAN.

## The 2×2 G24 had three cells of

`test correct / predictions / population`, one run seed (1234):

```
                 abduct on              abduct off
  death on     4144/ 116752/110      1359/  40414/134   (G24)
  death off    6361/ 969298/557      1514/ 442116/531   <- new cell
```

Read down the right column: **without abduction, removing death buys 155 correct
triples for 400k extra predictions.** Read across the bottom: at essentially the
same population (531 vs 557) and with selection absent from both, abduction is
worth 4847. G24's `analyse.py` reasons from "coverage rises with population size
almost mechanically" — that premise is now measured, and it is false at this
scale. Coverage per rule: full 37.7, `no_death` 11.4, `no_death+no_abduct` **2.9**.

## The capacity dial, and why the matched comparison is unreachable

```
config            wage   pop     preds  correct    prec  cov/rule   delta  A15
full_base          120   110    116752     4144  0.0355      37.7   +2842  yes
full_cap2000       120   110    116752     4144  0.0355      37.7   +2842  yes
wage300            300   153    249938     4981  0.0199      32.6   +3679  yes
wage600            600   171    178571     4455  0.0249      26.1   +3153  yes
wage1200          1200   229    286436     5934  0.0207      25.9   +4632  yes
wage2400          2400   228    269743     5724  0.0212      25.1   +4422  yes
wage4800          4800   239    369616     5980  0.0162      25.0   +4678  yes
wage600_noabduct   600   184     68140     1533  0.0225       8.3    +231   NO
nodeath            120   557    969298     6361  0.0066      11.4   +5059  yes
nodeath_noabduct   120   531    442116     1514  0.0034       2.9    +212   NO
```

Population is set by `WAGE_POOL / RENT`, not by `MAX_POP` (C2). But the dial
**saturates**: 40× the pool buys 2.17× the population, and it stops at ~239.

```
   120 -> 110      600 -> 171     2400 -> 228
   300 -> 153     1200 -> 229     4800 -> 239
```

So the comparison this spike was designed around — *selected 557 vs unselected
557* — **was never run and cannot be, by this dial.** A rule draws a wage only if
its confidence exceeds the co-evolving adversary's; the ceiling is the supply of
such rules, which more money cannot manufacture. That is a finding about the
selection regime, and it is also the largest hole in this spike: the CALIBRATION
claim rests on a trade (fewer predictions, more precision, slightly less
coverage), not on a dominance.

## The headline is a ratio of differences, so it gets an error bar

G24 ran one seed per arm and lists that as a limitation. Here the three configs
the headline rests on were repeated under seeds 777 / 1234 / 31337:

```
config             seed 777              seed 1234             seed 31337
full_base    4719/ 227142/134      4144/ 116752/110      3381/  97145/117
wage1200     5795/ 255938/224      5934/ 286436/229      5773/ 319992/195
nodeath      6843/1144867/562      6361/ 969298/557      6196/1069786/579
gap closed by WAGE_POOL alone:  51%   /   81%   /   85%
```

`full_base` spans **3381–4719** across seeds — a 1338-triple range, so a single
coverage difference of a few hundred means nothing here, and the non-monotone
dial points (`wage600` 4455 < `wage300` 4981; `wage2400` 5724 < `wage1200` 5934)
are inside that band. The capacity effect itself is not: `wage1200 − full_base` =
**+1753**, ranges **disjoint**, exact permutation over the 20 ways to split six
runs into two groups of three gives **p = 1/20 = 0.050 one-sided**, which is the
floor at n=3 and is stated as the floor rather than as a result.

## Does ECAN belong in the loop?

**As a precision mechanism, yes. As a coverage cost, the claim was mine to
retract.** Every setting with death holds 2.5–5.4× `no_death`'s precision, and at
matched population without selection the coverage story belongs to abduction.
G24's own conclusion — "abduction is the load-bearing operator" — survives and
gets stronger: it is worth 4847 triples with selection switched off entirely.
What does not survive is the framing that removing the finite economy *gains*
coverage; ~2/3 of that gain is a constant I set, and the rest is abduction
hoarding.

## Controls, and the input that would make each fail

- **C1 REPRO** — PASS. `full_base` is line-identical to G24's published full arm
  (110 / 4144 / 0.0355). *Fails if* the arm-set refactor or the monkeypatched
  globals changed `evo.py`'s behaviour.
- **C2 CAP** — PASS. `MAX_POP` 200→2000 changes nothing (110→110, 4144→4144).
  *Fails if* population rose, which would mean the sweep turned the wrong knob.
- **C3 A15** — PASS for every ranked arm. *Fails if* an abduction-on arm misses
  the plant — e.g. a capacity setting large enough to swamp it. **Scope changed
  from G24's, deliberately:** the gate covers abduction-on arms only, because
  G24 established the plant is unreachable by blind mutation, so demanding it
  from `no_abduct` arms makes the gate permanently red rather than strict. The
  two exempt arms are reported and unranked.
- **C4 VOLUME NULL** — fired, and refuted the hypothesis it was built to test.
  The null had to be *capable* of producing ~6361 correct at pop ~531, which is
  exactly what "coverage rises with population size" predicts. It produced 1514.

Observations are persisted in `provenance.json` (`ok=true`), not just in this
prose.

## Changelog

**2026-08-17, same day, after the run — the G-series AGENT-2 took the finding one
level further and it dates this spike.** I found that `imp` was read by exactly
one statement and concluded "this arm has no selection". The better decomposition
is that there are **two** selections and only one was missing: **survival**
selection (the death filter) and **reproductive** selection (which rules get to
be parents). `rng.choice(pop)` was uniform, so reproductive selection never
existed in *any* arm — including `full`. `evo.py` now has `pick_parent()`,
weighting parent choice by accumulated importance with a 0.05 drift floor, and an
arm list including `uniform_parents` and `no_death+uniform_parents`.

Consequences for everything above, none of which changes a number:

- **Every run here predates `pick_parent`.** In the new arm vocabulary this
  spike's `full` is **`full+uniform_parents`**, and its `no_death` is
  `no_death+uniform_parents`. The verdict is unchanged in substance — the
  attribution of coverage to abduction and to `WAGE_POOL` does not depend on how
  parents are chosen — but "selected" here means *survival-selected only*.
- **`provenance.json` now pins an `evo.py` that no longer matches the code that
  produced these runs.** That is A24 working, not a defect. Deliberately **not**
  re-recorded: re-digesting the patched `evo.py` against the old runs would be
  the actual violation. The digest plus this paragraph is the honest state.
- The saturation ceiling at pop ~239 is a fact about the *uniform-parents*
  selection regime. Weighted parents change the supply of adversary-beating
  rules, so the ceiling has to be re-measured before it is cited again.

## The provenance record said `ok=true` and was wrong

AGENT-2's adversarial review of this spike found it, and the file contained its
own disproof: **10 of 16 run artifacts predated the `sweep.py` recorded as having
produced them**, and 10 had no `run_seed` key while 6 did — because `sweep.py`
was edited mid-sweep (that is when `REPEATS` landed) and the per-config
checkpointing that makes the sweep resumable is exactly what preserved the older
files. Two code versions in one `runs/` directory, and nothing inside the files
said which produced them.

The check missed it because I passed `no_deps_reason` claiming that recording
`evo.py`'s digest under `artifacts` pinned the code state. **Artifacts are
hashed; deps are staleness-checked.** With `deps=()` the A24 comparison never
ran, so the mtimes sat in the file unexamined. This is agent-1's own E7 defect,
third instance on disk, in the spike backing a correction to G24.

Repaired by regeneration rather than by re-recording, because a true `ok=false`
still leaves an artifact set nobody can reproduce:

- `runs/` regenerated in one code state; the original set kept as
  `runs_mixed_state/` — evidence, not garbage.
- every arm renamed to the explicit **`uniform_parents`** token, since `evo.py`
  has gained `pick_parent` and "full" no longer names the algorithm these runs
  measured. The regenerated runs are the pre-fix algorithm *named honestly*, not
  the post-fix one silently substituted under an old name.
- **deps declared**: `G24_population` (evo.py) and `G17_composition_redo`
  (redo.py, the data loader, which no spike had ever declared).
- **the record is now written last.** It had been digesting `sweep.json` *before*
  writing it, so it pinned the previous invocation's artifact. The repaired
  staleness check caught that too.

**C7 REGENERATION EQUIVALENCE — PASS, 16 configs compared, 0 moved.** Every
config's `(pop, preds, correct)` is identical between the mixed-state set and the
regenerated set, which is what proves both the mid-sweep `sweep.py` edit and the
`uniform_parents` mapping were behaviour-neutral. *Fails if* any config moved —
and the arm renaming is exactly the kind of change that would move one.

**Hole this leaves, and it is a harness-level one:** the spike's own directory
cannot be declared as a dep, because its newest file is its own run log, so every
artifact reads as stale against it. That means *edit `sweep.py`, do not re-run*
— the original defect — is still undetected in the general case. C7 covers this
instance. The general fix is for `record()` to exclude a spike's own recorded
artifacts from that dep's source floor (`newest_source_mtime` already takes an
`exclude`). Posted to CHANNEL for the harness owner rather than patched here.

## What this does NOT show

- **No matched-population comparison at 557.** Saturation blocked it. Selected-N
  vs unselected-N is therefore untested above N≈239, and the CALIBRATION verdict
  is a trade on the plane, not a dominance.
- **One seed per capacity point.** Only `full_base`, `wage1200`, `nodeath` have
  three. The dial's shape between 300 and 4800 is not claimed; only the
  endpoints separate.
- **p = 0.050 is the floor at n=3**, reached by complete separation. It is not
  evidence of a large effect, only that the effect exceeds seed noise.
- **`ROUNDS` held at 15 throughout.** More rounds would also grow the population
  and might reach 557 with selection intact; that is the obvious follow-up and it
  was not run.
- Single dataset, single split, single machine — inherited from G24.
- The `analyse.py` docstring still asserts the population-size premise it was
  written under. Kept as written, corrected in G24's RESULT.md changelog rather
  than edited away.

## Reproduce

```sh
cd spikes/G25_carrying_capacity
python3 sweep.py        # 16 runs, ~25 min, checkpointed per config in runs/
python3 analyse.py      # table, controls, 2x2, dial, permutation test, verdict
```
`sweep.py <name> ...` runs named configs only; finished ones are skipped.
The two-line change to G24's `evo.py` (`RUN_SEED` hoisted out of `run()`,
ablations parsed as a `+`-joined set) is what made repeats and the missing 2×2
cell expressible; C1 exists to prove it changed nothing else.
