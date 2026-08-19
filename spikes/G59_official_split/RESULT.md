# G59 — official FB15k-237 valid/test from git, then G51 + valid-gated

**GROK-2, 2026-08-19.** Operator: fetch from git AND TEST. `certify ok=true`, 5 controls, 3 falsifiers stated in `CHANNEL.md` before the directory. **F1 did not fire. F2 fired. F3 did not fire.**

Source: `git clone` `DeepGraphLearning/KnowledgeGraphEmbedding@2e440e0` `data/FB15k-237`. Files in `corpus/fb15k237/` with sha256 in `SOURCE.txt`. `triples.bin` was not replaced. **No Bordes/RotatE/AMIE number is quoted** (`literature_compare: unavailable`, G35).

## Verdict

`triples.bin` **is** official train (F1 quiet: predicate-count bags match; 272,115 / 237 / 14,505). Official **test has 0 G46 same-pair leak** (F2 fired — I had called that unlikely). On that cut, frequency prior is **0.2334**, G51 **0.2585**, and a G54-style gate fitted on official **valid** (hashed before test) is **0.2679** (+0.0094). The gate **transfers**.

| Arm | Split | Filtered MRR | Hits@1 | Hits@10 |
|---|---|---:|---:|---:|
| prior | official test | 0.2334 | 0.1700 | 0.3541 |
| G51 β=0.10 | official test | 0.2585 | 0.1898 | 0.3837 |
| **valid-gated (headline)** | official test | **0.2679** | **0.1951** | **0.4037** |
| prior | pair-disjoint (G49) | 0.1732 | 0.1141 | 0.2855 |
| G51 | pair-disjoint (G51) | 0.2274 | 0.1524 | 0.3662 |
| DEV-gated | pair-disjoint (G54) | 0.2313 | 0.1535 | 0.3783 |

Pair-disjoint was the harder local benchmark. Official test is easier for the prior (+0.0602) and the lift over prior shrinks (0.0251 vs 0.0542). Do not mix the two columns.

## Fetch

| file | n | sha256 |
|---|---:|---|
| train.txt | 272115 | `6e4c2782169a…` |
| valid.txt | 17535 | `cf6309010852…` |
| test.txt | 20466 | `5711cf41623c…` |

237 relations. 14,505 entities in train (matches `triples.bin`). 14,541 in train+valid+test (36 test/valid-only). Filter index = train+valid+test (C5). 2,201 2-hop rules (full train; pair-disjoint train had 1,410).

## Falsifiers

| F | stated | observed |
|---|---|---|
| F1 | official train pred-counts ≠ `triples.bin` | **quiet.** bags match |
| F2 | official test same-pair leak with train is 0 | **fired.** 0/20466 |
| F3 | valid-gated ≤ official G51 | **quiet.** 0.2679 − 0.2585 = **+0.0094** |

F2 firing is the useful negative of my prior: G46's 30% leak is a property of **re-splitting train**, not of FB15k-237. The official cut already implements the G46 detector.

Gate: 157 on / 66 off, sha256 `9559856568a9…`, fitted on valid only.

## Slices (official)

| | prior | G51 | gated |
|---|---:|---:|---:|
| tail | 0.3305 | 0.3525 | 0.3655 |
| head | 0.1363 | 0.1645 | 0.1703 |

Head is still the hard *level*. Same shape as pair-disjoint.

## What is not claimed

- Not that 0.2679 beats AnyBURL / RotatE / AMIE. Those figures are still unsourced here (G35).
- Not that pair-disjoint 0.2313 is withdrawn. It is the leak-controlled re-split of train.
- Not a new `eval_graph_ai` headline. Pair-disjoint G54 stays `filtered_mrr`. Official numbers are a second column.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G59_official_split/official.py`. Check: `python3 kitchen/test_g59.py`.
