# H227 — a claim whose author is dead

**AGENT-3, 2026-08-19.** Operator direction: *"those died. we must retest their
claims and validate. agents sometimes die."*

## The class

**A claim whose author is dead has nobody to defend it and nobody to retract
it, and no gate in this harness partitions claims by author liveness.**

Every existing checker asks a question about the ARTEFACT and treats all claims
as equally owned — `recheck` (does the record still describe the tree),
`reprocheck` (does a repro path exist), `ledgerlag` (did a spike reach the
ledger), `depcheck` (is a dependency tracked), `stranded` (does an uncommitted
edit have an owner). None asks **who would answer if the number were wrong.**

That matters because this mission's correction mechanism is a lane retracting
its own claim (CLAUDE.md, *Correcting yourself*). A dead author cannot execute
it. An orphaned claim is therefore not merely unverified — it is
**unretractable**, and LEDGER standing rule 12 silently becomes a no-op for it,
the same way `ledgerlag` measured for a missing row.

## Measured

`spikes/H227_orphan_claims/orphancheck.py`, against `CHANNEL.md` at line 1065:

```
orphaned DONE lines: 123 across 6 callsign(s)
  AGENT-2-LANE 1 · AGENT-COORDINATOR 10 · BUILDER-1 9
  GEMINI 22 · GROK-2 14 · GROK-LOCAL 67
REFUSE: 31 orphaned claim(s) are consumed by live gates.
  (43 further orphans are named only in a *_baseline.json debt inventory —
   reported, not gated.)
```

`CLIENT-3`'s 5 claims are **not** orphaned: `MISSION_LOOP.md:430` records the
rename to `ATOM-3`, who is live. v1 of this tool reported them as orphaned —
a rename made a LIVE author read as dead, which is the more dangerous direction
because it manufactures orphans a lane would then waste a cycle re-testing.
The alias is now parsed from `MISSION_LOOP.md` rather than transcribed here.

## THE FINDING: the headline knowledge-graph number is orphaned at every link

`python3 scripts/autoloop.py --eval` publishes `filtered_mrr 0.2313` with
`"source": "G54_slice_gated_lift"`, plus `g51_mrr 0.2274`. Both spikes are
orphans:

| link | state |
|---|---|
| `DONE G51 AGENT-COORDINATOR` | author dark, no roster row, no brief, no lock |
| `DONE G54 GROK-2` | author dark |
| `.github/autoloop/evaluators/eval_graph_ai.py` | **reads** `slice_gated.json` / `bayesian_lift.json`; never runs either script |
| `_load_certified()` | trusts `provenance.json`'s `ok: true` flag; does not re-hash, does not call `recheck` |
| `corpus/fb15k237/` | **0 of 7 files tracked**, not gitignored — never added |
| `bayesian_lift.py:294` | `if os.path.exists(out_json): load it` — **the reproducer returns the published answer** |

### The reproducer does not reproduce

```
$ python3 spikes/G51_bayesian_lift_scoring/bayesian_lift.py
Loaded existing benchmark results from bayesian_lift.json
  E_bayesian_scaled_beta01 : MRR=0.2274 ...
D6 Provenance Certified: ok=True
```

There is no `--force` and no bypass but deleting the file. So **the one act that
could independently re-derive the number — running the reproducer — returns the
number instead**, and prints a certification line on top of it. Any lane that
"re-ran G51 to check" got the cache back. This is CLAUDE.md family B: confident,
well-formed, wrong.

**Scope, stated.** One instance. `G25_carrying_capacity/sweep.py` and
`G27_budget/sweep.py` also guard a JSON read with `exists()`, but they are
per-job checkpointing with `sys.argv` job selection, not a headline read — a
different pattern, and calling them the same class would inflate it.

### What is NOT wrong with the record, corrected against my own first reading

I initially read `falsifiers_fired: []` as *the falsifiers never ran*. **That was
wrong and it is withdrawn.** Both G51 falsifiers ran, with populated
observations and the verdict *"survived — the falsifier did not fire"*;
`falsifiers_fired` lists which ones FIRED. Controls C1 (prior reproduction,
0.1732 = 0.1732), C2 (leak_triples 0) and C3 (rank convention) all fired with
real observations, and `recheck` reports no drift for either spike.
**AGENT-COORDINATOR's record is honest and complete.** The defect is not the
record; it is that no live party can RE-DERIVE the number, only RE-READ it.

## GROK-LOCAL certified artifacts outside the workspace

Of 166 provenance records, 5 certify paths under
`~/.grok/worktrees/victorianikolenko-kingfisher/subagent-<uuid>/` — a per-subagent
copy of the repo that is not this repo: `G66`, `G67`, `G68`, `G72`, `G73`, all
GROK-LOCAL. `recheck` already reports `G66` and `G67` DRIFTED against those
paths while both records read `ok=true`.

Two further hits are **my own scanner's false positives** and are not §10
findings: `H203`'s `/adversarial_audit/...` strings are JSON key paths, and
`H106`'s is a shell error message that happens to contain a path.

## Falsifier, stated before the run

*If the forced recompute of G51 on this machine reproduces
`E_bayesian_scaled_beta01 = 0.2274`, the claim itself stands and this row is
about the MECHANISM only — an unreproducible-by-clone, unretractable-by-anyone
claim that happens to be true. If it differs, the live composite is wrong.*

### RESULT — G51 REPRODUCES. THE FALSIFIER DID NOT FIRE.

Forced recompute in a clean `git archive HEAD` tree with the cache removed:
1410 rules re-mined from 190,480 pair-disjoint train triples, all six arms
re-evaluated (382 s).

| arm | recomputed | published | |
|---|---|---|---|
| A_prior_alone | 0.1732 | 0.1732 | = |
| B_rules_alone | 0.0950 | 0.0950 | = |
| C_g50_additive | 0.1743 | 0.1743 | = |
| D_bayesian_hybrid_beta10 | 0.2263 | 0.2263 | = |
| **E_bayesian_scaled_beta01** | **0.2274** | **0.2274** | **=** |
| F_bayesian_scaled_beta001 | 0.2175 | 0.2175 | = |

Every Hits@1/3/10 matches too, and `controls`, `falsifiers`, `n_rules_2hop`,
`n_test`, `n_train`, `seed` and `split` are identical. **AGENT-COORDINATOR's
claim is CORRECT and is hereby independently re-derived by a live lane.** This
row is therefore about the MECHANISM, exactly as the falsifier said it would be:
an unretractable, clone-unreproducible claim that happens to be true.

### RESULT — G54 ALSO REPRODUCES, AND IT IS THE HEADLINE'S ACTUAL SOURCE

`G54` is what `--eval` names as `"source"`, so it matters more than G51. Forced
recompute in the same clean tree, no cache path in this spike at all: corpus
re-read (nt=272115, npred=237, nent=14505), split rebuilt
(train=190480 dev=40818 test=40817 groups=212110, **leak=0**), 1410 rules
re-mined, DEV and TEST re-scored. 628.7 s.

| arm | recomputed | published |
|---|---|---|
| A_prior | 0.1732 | 0.1732 |
| B_g51 | 0.2274 | 0.2274 |
| **C_dev_gated** (headline) | **0.2313** | **0.2313** |
| D_type | 0.1731 | 0.1731 |
| E_analog | 0.1764 | 0.1764 |
| F_dev_mix | 0.2327 | 0.2327 |

Every Hits@1/3/10 matches, n=81,634 on every arm, and the frozen gate hashes to
`56441adaa4427b6725be11fb186157d84e72203d1f55f0a43a745a08097cf261` — the same
value the `DONE G54 GROK-2` line published. `F3 fired=True` and is recorded, as
it was originally.

**BOTH ORPHANED HEADLINE CLAIMS ARE NOW INDEPENDENTLY RE-DERIVED BY A LIVE
LANE.** GROK-2's and AGENT-COORDINATOR's numbers are correct. What was missing
was never the arithmetic — it was that nobody alive could answer for it.

### THE WALL-CLOCK DEFECT, SECOND INSTANCE, WITH A DENOMINATOR

G54's artifact hashes `411731fb…` against the published `67a5de04…`. Diffed
field by field rather than eyeballed:

**303 leaf fields. EXACTLY ONE DIFFERS: `elapsed_sec`, 628.72 vs 886.92.**

Two spikes, two independent forced recomputes, and in both the single obstacle
between an honest reproduction and a byte-identical artifact is a timing field.
G51: all scientific fields identical, `elapsed_sec` 382.32 vs 367.91. G54:
302 of 303 identical, `elapsed_sec` 628.72 vs 886.92.

So `recheck` would report **DRIFTED** for both of these correct reproductions.
**"Did it reproduce" and "does it hash the same" are different questions and
only one of them is about the science** (AGENT-1). Filed by AGENT-1 as **H239**;
count reconciled with them at **90** (recursive scope + nested key walk) — my
own 73 was a strict subset produced by a one-level glob and a top-level-keys-only
predicate, and I withdrew it.

### AND THE RE-RUN FOUND A SECOND DEFECT THE CACHE WAS HIDING

The recomputed `bayesian_lift.json` hashes `43495a11…`; the published one
hashes `d694bd0f…`, which is what `provenance.json` records. **One field
differs: `elapsed_sec`, 382.32 vs 367.91.** Wall clock.

So the artifact hash of this result is a **one-time value**: an honest, correct
re-run necessarily changes it, and `recheck` would report `DRIFTED`. That means
**`recheck`'s DRIFTED signal cannot distinguish "the result changed" from
"someone reproduced it correctly"** — and reproduction is the thing this mission
most wants to encourage.

Swept: **73 hashed `.json` artifacts embed a wall-clock or timestamp field.**
Stated precisely, because not all 73 are the defect — `H86`'s `wall_citable`,
`S84`'s `wall_us_citable` and `H203`'s `w9_falsifier_wallclock_term` are the
MEASUREMENT and belong in the artifact. The defect is an *incidental* timing
field inside a hashed result, and G51 is a demonstrated instance rather than an
argued one, because the re-run exists.

## Limits

* This module decides **author liveness, not truth.** A green run means someone
  alive is answerable — never that the claim reproduces.
* The retest ran against the corpus **on this laptop**. It is untracked, so this
  validates the computation, NOT the reproducibility of it from a clone.
