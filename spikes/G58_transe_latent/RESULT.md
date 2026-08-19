# G58 — TransE on the leak-free split, same candidate set as G51

Setup, not a literature bake-off. Toutanova & Chen (MSR 2015, not FAIR)
compared observed features to latent embeddings after stripping inverses.
This tree had the observed side (prior / G51 / G54 gate) and no latent arm,
and no official test.

Falsifiers stated in CHANNEL before the run.

| F | stated | observed |
|---|---|---|
| F1 | TransE_support ≥ G54 gated 0.2313 + 0.005 | **did not fire.** 0.1534 vs 0.2313 (−0.0779) |
| F2 | TransE_support < prior 0.1732 | **fired.** 0.1534 < 0.1732 |

`certify ok=true`. C1 prior 0.1732. C3 leak=0. C4 `(p,s,o)`. C5 official test **absent**.

## Arms (81,634 queries, pair-disjoint, rank on train support of p)

| arm | MRR | Hits@10 |
|---|---:|---:|
| frequency prior (same support) | **0.1732** | 0.2855 |
| TransE dim=32, 8 epochs, L2 hinge | 0.1534 | (see json) |
| G54 DEV-gated (reference, not re-run) | 0.2313 | 0.3783 |

Hinge fires dropped 129,865 → 55,405 over 8 epochs, so the latent arm
*trained*. It still loses to the predicate-conditional count. That is
G49 again: on this protocol the frequency prior is a strong model, not
a dummy.

## What this added to the setup

- `spikes/harness/kg_split.py` — field-order, pair-disjoint helper,
  official-test detector (observe, do not fetch).
- `eval_graph_ai.py` — emits `official_test_available=false` and
  `literature_compare=unavailable`; refuses a `literature` / quoted
  headline; attaches TransE MRR as a sidecar, **not** the scoreboard.
- Autoloop graph timeout 180s → 1200s (G54 is a 15-minute script).

Do **not** quote Bordes/RotatE literature MRR against 0.1534 or 0.2313.
Those numbers are official-test, all-entity filtered rank. This run is a
re-split of TRAIN, prior-support candidates.

After this run finished, GROK-2 (operator-asked) placed official
`corpus/fb15k237/{train,valid,test}.txt` (test 20,466; hashes match
`SOURCE.txt`). Detector now reports the files present.
`literature_compare` stays **unavailable** until something is *scored*
on that split. G58's C5 recorded absence at start-of-run and is left
as observed.

Evidence: `transe.json`. Check: `python3 kitchen/test_g58.py`.
