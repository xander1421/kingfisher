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

Result: recorded below when the run lands.

## Limits

* This module decides **author liveness, not truth.** A green run means someone
  alive is answerable — never that the claim reproduces.
* The retest ran against the corpus **on this laptop**. It is untracked, so this
  validates the computation, NOT the reproducibility of it from a clone.
