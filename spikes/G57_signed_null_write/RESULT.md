# G57 — G51's write is always positive. The canary is a miss, not a sign.

**GROK-2, 2026-08-19.** `certify ok=true`, 6 controls, 3 falsifiers stated in `CHANNEL.md` before the directory. **F1 did not fire. F2 did not fire. F3 fired.** Pair-disjoint split. Instrument = G51 imported. Hurting names frozen from G54 json (top 20 of 36; p=13 is first).

## Verdict

The transformer residual that looked transferable — a signed write, or a NULL option — **loses to G51**. `log(1+β·lift)` was load-bearing damping, not a hack. lift<1 writes are not the bug: when p=13's true target is fired, lift is **always >1** (2526/2526). What hurts is 2-hop spray: rules fire on 99% of p=13 queries, miss the answer on 52% of the queries they make worse, and when they hit it the false candidates still get **2× the write** (5.40 vs 2.72).

The gate that works remains G54's predicate-level "write nothing." A per-candidate signed residual is not that gate.

| Arm | Write | Filtered MRR | Hits@1 | Hits@10 | vs G51 |
|---|---|---:|---:|---:|---:|
| A | prior only | 0.1732 | 0.1141 | 0.2855 | −0.0542 |
| B | G51 `log(1+β·lift)` always | **0.2274** | 0.1524 | 0.3662 | 0 |
| **C (headline)** | G51 write only if lift>1 | 0.2275 | 0.1524 | 0.3662 | **+0.0001** |
| D | signed `log(lift)` | 0.2118 | 0.1365 | 0.3442 | **−0.0156** |
| E | softmax-null `α·log(lift)` | 0.2064 | 0.1373 | 0.3362 | **−0.0210** |

Headline C was declared before the run. **+0.0001 is rounding, not a method.** I will not quote 0.2275 as a new high. G54 gated **0.2313** is still the leak-free number.

## 1. p=13 canary (principle 5)

3856 queries, matches G54 (C5).

| | n | frac |
|---|---:|---:|
| any 2-hop fires | 3830 | 0.9933 |
| true target in firings | 2526 | 0.6551 |
| G51 rank worse than prior | 2472 | 0.6411 |
| among those, true **missed** | 1282 | **0.5186** |
| among those, true fired | 1190 | 0.4814 |
| true fired with lift<1 | **0** | 0 |
| true fired with lift>1 | 2526 | 1.0 |

F1 was "miss is NOT the mechanism" (true present on ≥50% of hurt queries). **0.4814, so F1 did not fire.** Miss is the larger half, barely. The other half is worse: true is present and still loses because **mean G51 write on false fired candidates is 5.40 against 2.72 on the true target.** lift = conf/P, so the extra write is on *rare* false entities the 2-hop happens to reach, not hubs.

1,569,947 false writes vs 2,526 true writes on this one predicate. That is spray.

## 2. Why the transformer transfer failed

G51 always writes `log(1+0.1·lift) > 0`. I treated that as "attention without NULL." Three knob-free fixes:

- **lift>1** — refuse the write when lift<1. Inert, because those writes almost never happen on the answer. F2 did not fire at +0.0001; I am not claiming it.
- **signed `log(lift)`** — real Bayes, can go negative. **−0.0156.** F3 fired. Removing G51's `log(1+βx)` over-boosts the same rare false entities (lift of 3000 becomes +8 instead of +5.7).
- **softmax-null** `lift/(lift+1) · log(lift)` — damped signed. **−0.0210.** Worse.

The residual that transferred from the last turn is **G54's ability to attend to nothing at the predicate**, not a per-candidate signed update. G56 already showed that mask is not selection noise (0/1000 random same-size masks reach 0.2313).

On the frozen hurting slice (9,910 queries, top-20 names): prior 0.2442, G51 0.2104, signed 0.1697, null 0.1389. Every "more transformer-like" write digs the hole.

## 3. Head is still the hard slice and this did not touch it

| direction | prior | G51 | lift>1 | signed |
|---|---:|---:|---:|---:|
| tail | 0.2478 | 0.3017 | 0.3017 | 0.2844 |
| head | 0.0986 | 0.1532 | 0.1532 | 0.1392 |

Δ(G51−prior) is still ~0.054 both ways. Head's *level* is the remaining question. None of these writes close it.

## 4. Controls

C1 0.1732, C2 0.2274, C3 leak=0, C4 `max(p)=236`, C5 n(p=13)=3856, C6 per-query matches imported eval.

## 5. What is not claimed

- Not that 0.2275 is better than 0.2274.
- Not that signed Bayes is "more correct" on this split. It lost.
- Not a new scoreboard number. `eval_graph_ai.py` stays on G54 0.2313.
- Official test split still absent.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G57_signed_null_write/signed_null.py` (~5 min). Check: `python3 kitchen/test_g57.py`.
