# G5 — the missing organ, built: deterministic fixed-point ECAN in MeTTa

**Verdict: GREEN, and it carries a finding that matters more than the organ —
the bug it had first was perfectly deterministic.**

A11 specified a deterministic ECAN, S67 modelled it in Python, nobody built it.
This builds it **in MeTTa**, so it inherits hyperon's byte-reproducibility
instead of needing a separate proof of it.

```
                  arch      os        status  fuel_used   raw_hash
desktop (M4 Pro)  aarch64   macos     OK      2,887,738   88bea8a2593b75eb...
phone (SM8750)    aarch64   android   OK      2,887,738   88bea8a2593b75eb...
```

Identical `raw_hash`, identical `sorted_hash`, identical fuel. Device gate OPEN
(`cpu_busy 0.7%`, thermal 33.9 C). Both aarch64 — **cross-OS/cross-libc, not
cross-ISA**, per S57's correction of S15.

## A11's three clauses, each realised in the program

| clause | how |
|---|---|
| **accumulate wide** | MeTTa integers are i64 and every product is formed *before* any division, so no rounding enters a sum |
| **round canonically** | exactly **one** floor division per derived quantity, `(/ (* v rate) SCALE)`. Verified `(/ 7 2) = 3` |
| **update synchronously** | `collapse` fully evaluates generation *t+1* from *t* before a single atom of *t+1* is added — BSP double-buffering by construction |

Contrast with what DAS ships (`StimulusSpreader.cc`): same
`rent = rate·imp`, `wages = stim·to_spread/total`, `imp += wages − rent` — but
float, dispatched inline from three gRPC entry points onto one shared
`HebbianNetwork` with per-node mutexes only, and with an `a + b*c`
FMA-contraction site at `:74-75`. This one is integer, serial and hashed.

## The result

60 nodes from G1's citation graph, stimulus = in-degree, 3 epochs,
`SCALE=1000 RENT_RATE=50 SEED=1000`:

```
(B1 935) (M1 1167) (N1 935) (Q1 972) (S11 1127) (S14 895)
(S18 1204) (S32 1204) (S34 1204) (S30 1088) ...
total 59,907
```

Heavily-cited spikes gained importance, barely-cited ones lost it. Attention
concentrated where the workspace actually leaned.

## The finding: **a deterministic wrong answer is still wrong**

The first version omitted an epoch index on `(total-stim …)`. Three epochs
therefore left three identical atoms in the space, the BSP join multiplied
against all of them, and every node's importance was counted **six times**.

It was **completely deterministic while broken**:

```
fuel_limit 20,000,000  ->  fuel_used 11,010,665
fuel_limit 80,000,000  ->  fuel_used 11,010,665      identical
```

Same fuel, same hash, every run. Two honest devices running that program would
have agreed perfectly, byte for byte, on a wrong answer.

**What caught it was not the hash. It was conservation.** Rent is redistributed
as wages, so the total must stay within floor-division loss of `SEED × N`:

```
broken:  377,352   against a seed total of 60,000   (6.3x — the multiplied join)
fixed:    59,907   against 60,000                   (93 lost to floor division)
```

That control is now emitted into the program itself and returns `True`.

### Why this matters beyond G5

This workspace's verification thesis is **byte comparison between replicas**.
G5 is a worked demonstration of that thesis's boundary:

> **Replication catches disagreement. It cannot catch a shared bug.** Two honest
> devices executing the same defective program agree perfectly and are perfectly
> wrong.

So byte-identical agreement verifies *that the same computation ran*, never
*that it was the right computation*. Quorum, seal and hash comparison are all
agreement mechanisms. **Correctness needs invariants** — conservation laws,
plausibility gates, range checks — and those must ship inside the job, not in
the verifier, because the verifier only ever sees hashes.

That is a design requirement nothing in `PORT_PLAN` or the LEDGER currently
states, and it fell out of a bug rather than an argument.

## Cost

```
fuel_used 2,887,738 for 60 nodes x 3 epochs   (~16k fuel per node-epoch)
run_ms ~19s desktop — not cited; the host gate was REFUSED throughout and
       every claim here is a count, a hash or a fuel figure
```

The broken version cost 11.0M, so the duplicated join was 4x the work. Fuel is a
useful cost signal independent of the clock.

## What this is NOT

- **Not DAS's ECAN.** No Hebbian link creation, no spreading across the graph
  topology, no forgetting threshold. This is rent + wages + one stimulus source.
  The spreading step (`b_cursor`-style traversal over neighbours) is unbuilt.
- **Not tuned.** `RENT_RATE=50`, `SCALE=1000`, `EPOCHS=3` are placeholders with
  no justification beyond producing legible numbers. Per B5 they are labelled
  as such, not presented as chosen.
- **Not the closed loop.** The phone ran the same program; it did not query,
  emit stimuli, and pull a reshaped shard. Transport is still nothing.

## Reproduce

```sh
cd spikes/G5_ecan_metta
python3 gen_ecan.py
../S30_speed_duel/bin/fuelrun.v2.host ecan.metta 20000000
```
