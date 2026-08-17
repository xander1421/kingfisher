# D3 — Economics as formulas, with the unmeasured inputs declared

**Status: spec. No constants are derived from unmeasured inputs. That is the point of the document.**

## The rule
> Every economic quantity ships as a **formula** with its inputs named and
> graded. An input that is unmeasured is **declared unmeasured** and no constant
> is computed from it. S69/S70 died from doing the opposite.

## Inputs, with grades

| symbol | meaning | value | grade |
|---|---|---|---|
| `q_dev` | jobs/s per device, 1 worker | **2.83** | **A** — S71, measured, gate green |
| `q_dev4` | jobs/s per device, 4 workers | **11.17** | **A** — S71, 3.95× scaling |
| `C_pov` | settlement ceiling, per-job posting | ~17 jobs/s | **B** — derived from Acurast runtime constants |
| `w` | witness bytes per verification | ~4.2 KB, flat in shard size | **B** — W1, aligned classes only |
| `b_res` | resident replica bytes/job | 12.8 MB / ~4,500 | **D** — S34 amortisation, inherits S32's INVALID. **Do not build on it** |
| `N` | fleet size | — | unset |
| `C` | shards cached per device | — | unset |
| `S` | shard count | — | unset |
| `R` | replication floor | — | unset |
| **`Δ`** | **shard demand distribution** | — | **UNMEASURED, and unmeasurable from inside this workspace** |

### On `Δ`
S52's query generator samples **uniformly over triples** (`realkg.c:170`), which
is an artefact of the harness, not a workload. Under it shard demand is flat
(max/median **1.04**). Under object-degree weighting it is 107.6. S70 fitted a
Zipf to the *predicate* histogram — the wrong axis — and the coverage
requirement it implied ranged **2R to 780R** across plausible models.

**No coverage target, replication floor, or Sybil cost may be stated as a number
until `Δ` is measured against a real query stream.** That instrument is a design
partner's logs (HUMAN_NEEDED #4).

## Formulas

**Feasibility (hard, no free parameters):**
```
N·C  ≥  R·S                      you cannot place R·S replicas in N·C slots
```
Equivalently `N·C/S ≥ R`. **This is the only surviving coverage constraint.**
Any multiplier above 1 is a function of `Δ`. S70's `4R` was circular — both its
"free" rows had coverage 100 and R 25, and 100 = 4×25 by construction.

**Fleet supply:**
```
Q_fleet(N, d, k) = N · q_dev4 · d / k
    d = duty cycle (charge-time; 0.05–0.25 honest)
    k = quorum size (3)
```

**Settlement, batched:**
```
jobs/s_settled = C_pov            when results are Merkle-batched
                                  (quorum compare is off-chain; only the root posts)
jobs/s_settled = C_pov / k        when posting per job
```
At `k=3`: 5.7 jobs/s per-job, versus ~17 batched. **A single device
(`q_dev4` = 11.17) saturates the per-job path**, which is the argument for
batching stated as arithmetic rather than assertion.

**Verification bandwidth:**
```
bytes/job = (k−1) · w             witnessed, aligned classes
bytes/job = (k−1) · shard_bytes   non-aligned classes  (W1: witness ≥ shard)
```
The second row is why W3 exists.

**Orphan-shard placement — priced as availability, never as security:**
```
forced_placements(R) = Σ_s max(0, R − pool(s))       pool(s) is a function of Δ
```
S70 reported this as a *mean* cost while the threat model concerns the
*minimum*. It is an availability figure: a shard with zero phone replicas is a
100% miss against the desktop shard host (S8), **not a lost object** — M1.5
calls the phone side an LRU cache. Load on the shard host, not data loss.

## Falsifiers
| # | falsifier | test |
|---|---|---|
| F1 | Any constant in this document is derived from `Δ` | grep: no coverage target, no `R`, no Sybil cost is numeric |
| F2 | `q_dev4` does not hold under thermal soak | rerun S71 over ≥1 h; 12 s windows are not a duty measurement |
| F3 | Batched settlement does not achieve `C_pov` | measure a real batched extrinsic's PoV; currently arithmetic |
| F4 | `b_res` is used anywhere load-bearing | it is grade D; W1 removed the need for it |
| F5 | Feasibility bound is violated by a working configuration | any deployment with `N·C < R·S` that nonetheless meets the floor |

## What this document deliberately does not say
No recommended coverage. No `R`. No stake floor. No price per job. Every one of
those is a function of `Δ`, and inventing them is precisely the failure that
produced S70's `4R`.
