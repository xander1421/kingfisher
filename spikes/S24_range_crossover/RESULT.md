# S24 — the range-query crossover: the proof is never worse than doing it yourself, and at the limit it *is* doing it yourself

**AGENT-1, 2026-08-17.** `python3 range_crossover.py` · `range_crossover.json` ·
`certify ok=true`, 4 controls all fire, **falsifier did NOT fire**.

## The question S85 does not answer

S85 settled verification against re-execution for **membership**. S20 measured
the completeness verifier and found it rebuilds the answer subtrie, so its work
grows with the answer set while the authentication path shrinks. A cost that
grows with the answer set has a crossover against doing the work yourself; a flat
one does not.

**Both sides are sha256 bytes, on one instrument, and neither is a wall time.**
A client that refuses the proof must fetch the shard *and check it* — recompute
the root and compare — or it is trusting the server and has bought nothing. That
is `build()` under the same counting hashlib. `quiet.sh` refuses on this host and
has all day, so a seconds-denominated ratio would not be citable; **S85's
published 238×–56,734× are wall-time ratios and nothing here extends them.**

## Result

Shard: 4,096 triple keys, **49,152 B**. Rebuilding its root costs **205,184 B**
hashed — that is the whole cost of "do it yourself", and it is what every row
below is divided by.

| query prefix | answers | % of shard | verifier hashes | × rebuild | auth path | witness bytes |
|---|---|---|---|---|---|---|
| 1 B | 4,096.0 | **100.0%** | **205,184** | **1.000** | **0** | 49,152 |
| 6 B | 1,943.2 | 47.4% | 95,529.9 | 0.466 | 75 | 23,393.8 |
| 7 B | 204.8 | 5.0% | 10,961.0 | 0.053 | 1,320.5 | 3,777.9 |
| 8 B | 97.6 | 2.4% | 6,074.0 | 0.030 | 1,465.3 | 2,636.3 |
| 11 B | 3.2 | 0.08% | 2,547.9 | 0.012 | 2,304.2 | 2,343.0 |
| 12 B | 1.0 | 0.02% | 2,534.5 | 0.012 | 2,381.1 | 2,393.1 |

**The crossover is exact and degenerate: 1.000× at 100% of the shard, with an
authentication path of ZERO bytes and a witness of exactly 49,152 B — the shard
itself.** A completeness proof over the whole store is not "expensive to verify";
it *is* the store, and checking it is bit-for-bit the work of checking the store.
There is no regime where taking the proof is worse than refusing it.

Below that limit the advantage is large and non-linear: **81× cheaper at
point-sized answers, 33× at 2.4%, 19× at 5%, and still 2.1× when the answer is
nearly half the shard.**

`units.check_affine` **refuses** — adjacent slopes span 6.0 to 50.9, a 749%
spread against a 25% tolerance — so these are measured points and not a rate
(A18). The refusal is informative rather than a formality: the curve is steep at
large answers and **flat at small ones**, because below ~100 answers the
authentication path dominates and shrinking the answer further buys nothing
(2,547.9 B at 3.2 answers against 2,534.5 B at 1). **The floor is the path, not
the answer.**

## The falsifier, stated before the run

> If verifier work stays below the cost of rebuilding the whole shard across the
> entire reachable answer range, then a completeness proof is always cheaper than
> re-execution, S20's inversion is a curiosity rather than an operating
> constraint, and there is no crossover to publish.

**It did not fire** — the 1 B prefix reaches exactly 1.000×. The prediction
recorded beside it (*"there is one, and it sits where the answer set approaches
the shard"*) holds, and the exactness is the sharper statement.

**The first run of this sweep could not have answered it.** It topped out at a
4 B prefix — 47.6% of the shard, 0.468× — and the falsifier fired on that
evidence. Byte positions 0–2 carry one distinct value each, so a 1 B prefix
selects the whole store and 4/5/6 select the same 47%; the axis was widened to
the lengths that give **distinct** answer sizes rather than the run being
reported from a range that stopped short of the question (A20: the sweep must be
able to contain the effect).

## Controls (4, all fire)

| control | what would have made it not fire |
|---|---|
| `C_S20_operating_points_reproduce` | **gating**: S20's prefix lengths 6/7/8/11 must return the same mean answer counts here — Δ 0.000000 on all four. *The first version used 40 probes against S20's 60 and demanded exact equality, so it could not fire by construction (A15). Fixed by matching the probe count, not by loosening the comparison.* |
| `C_rebuild_reaches_the_same_root` | the baseline is only the real alternative if rebuilding lands on the prover's committed root; otherwise it is a cheaper computation that proves nothing and the duel is rigged |
| `C_every_proof_verified_true` | any proof failing to verify — the loop raises `SystemExit`, since counts from a verifier that returned False on line one are small, stable and fictional (A29) |
| `C_inversion_present` | verifier work not monotone **up** in answer size, or the auth path not monotone **down**. If they moved together this sweep would not be the regime S20 found and the crossover would be drawn on the wrong curve |

## Scope

- **One key set** (`S75_pathmap_check/keys_triples.bin`, 4,096 fixed-length
  12 B keys). The atom key sets have variable lengths and a different branching
  profile; S20 measured all three at one prefix fraction and they do not order
  the same way, so this crossover is not asserted for them.
- **Hash bytes, not seconds.** A verifier that streamed the answer set into an
  incremental fold would hash the same key bytes and allocate fewer node
  descriptors; nothing here says the constant is a lower bound (S20's open item).
- **The client-side baseline assumes the shard must be checked, not merely
  fetched.** A client willing to trust the server pays neither, and that client
  is not in this project's threat model.
