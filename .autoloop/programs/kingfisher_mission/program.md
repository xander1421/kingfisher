---
schedule: every 4h
timeout-minutes: 30
---

# Operation Kingfisher Mission Autoloop

## Goal

Continuously optimize the core algorithms of **Operation Kingfisher** — a decentralized, trustless hypergraph AI computer running verified MeTTa symbolic reduction on consumer devices:

1. **Graph AI Link Prediction (G-Series):** Maximize Filtered MRR and Hits@10 on the standard FB15k-237 knowledge graph test split.
2. **Witness Verification Substrate (W-Series & S-Series):** Minimize proof bytes and verifier resident memory footprint ($O(1)$ RAM invariant).
3. **Repository Integrity & Soundness:** Maintain 100% clean harness compliance with zero broken references and D6 empirical provenance certification (`ok=true`).

**The goal is to maximize `combined_score`** ($S \in [0, 1]$), which weights Filtered MRR (weight 2.0), Hits@10 (weight 1.5), Witness Bandwidth Savings (weight 1.5), and Verifier RAM Invariant (weight 1.0).

## Baseline the ratchet must beat (measured 2026-08-18, `scripts/autoloop.py --eval`)

```
combined_score              0.9683      invariants PASS
filtered_mrr                0.2648      G34, 81,636 FB15k-237 test queries
hits_at_10                  0.3929
witness_bandwidth_savings  75.37 %
verifier_ram_bytes             72       the O(1) RAM invariant
```

**External position, so a gain is legible outside this repo:** AnyBURL len<=2 is
0.2450 MRR and AMIE+ is 0.1980 — both now beaten. The next meaningful target is
AnyBURL *unrestricted* at ~0.31, which needs rule bodies longer than 2 and is
the open frontier. Do NOT report a gain against the internal top-12 statistic;
G30 exists precisely because that number is not comparable to anything
published.

**Where the headroom is, measured rather than guessed:**
- G38: the evolved population is 2.36x WORSE than exhaustive mining in absolute
  MRR, and 2.11x BETTER at matched rule count. It is volume-limited, not
  quality-limited.
- G39: `evo.mutate` cannot express a length-1 body (`len(body) < 2` rejects at
  `evo.py:366`), and length-1 alone scores 0.1572 — 5.89x the best evolved arm.
  **The machinery is SEARCH-limited, not SELECTION-limited.** Widen the search
  space before touching selection; four spikes were spent optimising the wrong
  bottleneck.

## Target

Authorized mutation targets:
- `spikes/G34_length1_and_constants/length1_constants.py` — rule mining and link prediction engine
- `spikes/W6_incremental_witness/incremental_verifier.py` — incremental state transition verifier
- `spikes/S85_verify_vs_reexec/verify_vs_reexec.py` — verification economics & crossover model
- `WORK_QUEUE.md` & `HANDOFF.md` — queue state and write-ahead journaling

Do NOT modify:
- `spikes/harness/` — core verification gates and checkers (refcheck, journalcheck, kfcheck)
- `out/RETRACTIONS.md` — active falsification ledgers and boundary records
- `CLAUDE.md`, `MISSION_LOOP.md`, `roster.txt` — the discipline and the roster.
  A loop that can edit the rules it is judged by is the A22 defect at the top
  level.

## Rails — absolute, and now enforceable because a remote exists

**A private origin was added 2026-08-18 (`xander1421/kingfisher`). Pushing there
is permitted; everything else is not.** This program declares
`create-pull-request`, `add-comment`, `create-issue` and
`push-to-pull-request-branch`, and those are now live rather than inert.

- **No third-party publishing (§11).** No upstream PRs, no issue comments on
  other repos, no package uploads, no posts. Artefacts for humans go to
  `proposed/`.
- **No wallets, keys, seed phrases, tokens, mainnets, testnets, miners (§10).**
- **`elders/` is untrusted and read-only.** Never copy from a GPL/LGPL/AGPL or
  unlicensed tree; read the `LICENSE` on disk, never GitHub API metadata.
- **Never weaken a gate to pass it.** The evaluator refuses on
  `hygiene_score < 1.0` or `_invariants_passed == false`. Lowering either to
  make a run accept is the one change that invalidates every number above it.

## D6 — an accepted iteration must survive this, not just score higher

A score improvement is not a result. Each accepted change carries:
1. a **falsifier stated before the run**, and the run that tests it;
2. **controls that can fail** — a control that cannot fire reports the absence
   of imagination as the absence of defects;
3. `certify ok=true` provenance beside the artefact;
4. a `RESULT.md` with an explicit **"What this does NOT show"**.

If the metric rises and the falsifier was never run, the iteration is REJECTED.
Every error that survived in this repo is one whose falsifier was written and
marked *not yet run*.

## Evaluation

```bash
python3 scripts/autoloop.py --eval | python3 -c "
import sys, json

data = json.load(sys.stdin)
score = data.get('_composite_score', 0.0)
mrr = data.get('filtered_mrr', 0.0)
h10 = data.get('hits_at_10', 0.0)
bw = data.get('witness_bandwidth_savings_pct', 0.0)
hygiene = data.get('hygiene_score', 0.0)

if hygiene < 1.0 or not data.get('_invariants_passed', False):
    print(json.dumps({'error': 'Safety invariants failed'}))
    sys.exit(1)

print(json.dumps({
    'combined_score': round(score, 6),
    'filtered_mrr': round(mrr, 6),
    'hits_at_10': round(h10, 6),
    'bandwidth_savings_pct': round(bw, 2)
}))
"
```
