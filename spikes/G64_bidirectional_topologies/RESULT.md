# G64 — 4-Topology Bidirectional 2-Hop Rule Mining on Official FB15k-237

`certify ok=true`, 3 controls, 2 falsifiers. **None fired.**

## Verdict

The previous miners (G17, G30, G34, G51, G59) searched only **1 of 4 two-hop path topologies** (Forward Chains: $s \xrightarrow{q} z \xrightarrow{r} o$). Because FB15k-237 removed direct inverse relations, true multi-hop semantic dependencies are concentrated in **Forks** ($s \xleftarrow{q} z \xrightarrow{r} o$) and **Colliders** ($s \xrightarrow{q} z \xleftarrow{r} o$).

Mining all 4 topologies yields **6,736 high-confidence rules** (up from 2,201) and moves the official benchmark scoreboard to a new certified high:

| Architecture / Model | Test Split | Filtered MRR | Hits@1 | Hits@10 | $\Delta$ vs G59 | $\Delta$ vs Prior |
|---|---|---:|---:|---:|:---:|:---:|
| **G64 4-Topology Valid-Gated (Headline)** | **Official Test** | **0.2778** | **0.1987** | **0.4274** | **+0.0099** | **+0.0444** |
| G64 4-Topology Bayes G51 | Official Test | 0.2703 | 0.1944 | 0.4118 | +0.0024 | +0.0369 |
| G59 Forward-Only Valid-Gated | Official Test | 0.2679 | 0.1951 | 0.4037 | Baseline | +0.0345 |
| G51 Forward-Only Bayes ($\beta=0.10$) | Official Test | 0.2585 | 0.1898 | 0.3837 | -0.0094 | +0.0251 |
| Frequency Prior Baseline | Official Test | 0.2334 | 0.1700 | 0.3541 | -0.0345 | 0.0000 |

---

## 1. Direction Slices on Official Test

| Direction | Query Count | Prior MRR | G59 MRR | **G64 MRR** | **G64 Hits@10** |
|---|---:|---:|---:|---:|---:|
| **Tail Queries $(s, p, ?o)$** | 20,466 | 0.3305 | 0.3655 | **0.3761** | **0.5492 (54.9%)** |
| **Head Queries $(?s, p, o)$** | 20,466 | 0.1363 | 0.1703 | **0.1794** | **0.3056 (30.6%)** |

- **Head Queries:** G64 moves the head query level from **$0.1703 \to 0.1794$** ($+0.0091$), crossing $30\%$ Hits@10.
- **Tail Queries:** Reaches **$0.3761$ MRR** with over half ($54.92\%$) of all queries ranked in the top 10.

---

## 2. Rule Breakdown by Topology

Mined from `corpus/fb15k237/train.txt` ($272,115$ triples) in $57.35\,\text{s}$:

| Topology Code | Path Pattern | Semantic Meaning | Mined Rule Count |
|---|---|---|---:|
| **FF** | $s \xrightarrow{q} z \xrightarrow{r} o$ | Forward Chain | 2,264 |
| **BF** | $s \xleftarrow{q} z \xrightarrow{r} o$ | Fork (Common Subject / Shared Origin) | **2,192** |
| **FB** | $s \xrightarrow{q} z \xleftarrow{r} o$ | Collider (Common Object / Shared Target) | **1,302** |
| **BB** | $s \xleftarrow{q} z \xleftarrow{r} o$ | Inverted Chain | **978** |
| **Total** | — | **All 4 Topologies** | **6,736** |

---

## 3. Validation Gate & Provenance

- **Validation Gate Hash:** `43ed5fb549bbb2b2a05e78ea04cc87631c8b67333d0c159db6305b241ff88350`
- **Gate Decisions:** $174$ predicates ON ($78.0\%$), $49$ predicates OFF (defaulting to pure prior).
- **Controls:** C1 ($20,466$ test triples), C2 ($0$ same-pair leakage), C3 (Field order `p,s,o`).
- **Falsifier F1 (Beats G59):** DID NOT FIRE ($0.2778 > 0.2679$, $+0.0099$).
- **Falsifier F2 (Closes Head Gap):** DID NOT FIRE ($0.1794 > 0.1703$, $+0.0091$).

Evidence: `spikes/G64_bidirectional_topologies/g64_results.json`. Certified in `provenance.json` (`ok=True`).
