# S34 — N1 + N4: packed popcount closes the gap, and it is bit-exact on two machines

**Verdict: GREEN, and it moves three separate arguments.** The packed bitplane popcount kernel is **13.9× faster than scalar int8 on the phone**, produces **byte-identical int32** to both other kernels on both machines, and shrinks the store **8×**. The 17× shortfall S33 identified is closed on the CPU alone. But the roof moves too, and the honest justification for custody turns out to be network fetch, not memory bandwidth.

## N4 first — exactness, because speed is meaningless without it

Three kernels: `K0` scalar int8 reference, `K1` NEON `vdotq_s32` (SDOT), `K2` packed bitplane popcount (`veorq/vandq/vcntq_u8`).

```
                        phone (SM8750)      host (M4 Pro)
K0 scalar     fnv   f4e64fb7d70b9b0c    f4e64fb7d70b9b0c
K1 SDOT       fnv   f4e64fb7d70b9b0c    f4e64fb7d70b9b0c
K2 popcount   fnv   f4e64fb7d70b9b0c    f4e64fb7d70b9b0c

N4, q=100 full score array (40,000,000 bytes):
K2            fnv   b3bfb70e74b94aa7    b3bfb70e74b94aa7
```

**Six kernel/machine combinations, one digest.** A 40 MB int32 score array identical across Snapdragon/bionic and Apple Silicon/libSystem.

The identity `K2` implements, for the real three-valued query `Q ∈ {−2,0,+2}` against a bipolar store:
```
score = 2·nnz(Q) − 4·popcount(mask & (sign_q XOR sign_t))
```
One XOR, one AND, one popcount per 64 elements replaces 64 multiply-accumulates. **No scale, no zero point, no accumulator width, nothing to negotiate** — which is exactly why this form is legal in a byte-comparison network and a quantised matmul is not. S31 measured what the alternative costs: the natural output scale saturated the matches and returned recall 0/8, silently.

## N1 — speed

| q | phone K0 | phone K1 | phone **K2** | host K0 | host K1 | host **K2** |
|---|---|---|---|---|---|---|
| 1 | 50.9 | 75.4 | **710.0** | 170.1 | 146.0 | **1113.0** |
| 100 | 50.6 | 74.0 | **704.8** | 159.7 | 145.2 | **1061.7** |
| 256 | 50.4 | 73.4 | **699.6** | 159.9 | 145.2 | **1047.0** |

GOP/s, counting equivalent int8 ops so the columns are comparable.

- **Packing beats SDOT by 9.5× on the phone** (704.8 vs 74.0). Bit-packing is worth far more than instruction selection.
- **The phone is only 1.5× slower than an M4 Pro on this kernel** (705 vs 1062) — against 3.7× on MeTTa reduction. Packed popcount is the phone's best relative showing anywhere in this workspace.
- SDOT is *slower than scalar on the host* (145 vs 160): clang already auto-vectorises the scalar loop well there, and my hand-written intrinsics get in the way. On the phone SDOT is a genuine 1.46× win. Same source, opposite verdicts — a reminder that kernel claims are per-target.

## The 17× gap, honestly re-derived

S33: the phone needs **5.0 TOP/s** to be bandwidth-bound at q=100 against the *int8* shard, and had ~300 GOP/s at 8-way — 17× short.

With K2: 704.8 GOP/s single-thread, and S32 measured 5.87× scaling on 8 cores → **≈4.1 TOP/s at 8-way, i.e. 1.2× short.** On the CPU alone, without touching the NPU.

**But packing moves the roof.** The packed store is 12.8 MB, not 102.4 MB, so streaming it costs 8× less and the bandwidth-bound threshold rises 8×:

| | int8 store | packed store |
|---|---|---|
| shard bytes | 102.4 MB | 12.8 MB |
| stream once @ ~25 GB/s | 4.1 ms | **0.51 ms** |
| ops to fill that window at q=100 | 5.0 TOP/s | **40 TOP/s** |
| 8-way CPU achieves | 0.3 TOP/s (17× short) | 4.1 TOP/s (**10× short**) |

So packing does not make the phone bandwidth-bound; it makes it **13.9× faster while staying compute-bound**. Both statements matter, and only reporting the first would be the same flattery S9 caught.

## What this does to custody — the justification changes

Marginal cost per query, phone: **0.29 ms** single-thread, **~0.05 ms** at 8-way. Streaming the packed shard from DRAM: ~0.51 ms. So a DRAM re-stream costs about **1.7 queries' worth of compute** — nothing like the 70× the tier model claimed, and S18's memory-bandwidth argument for custody does not survive at any store size.

The real argument is one nobody has stated: **network fetch, not memory bandwidth.**

> Fetching a 12.8 MB packed shard to a phone over a home connection at ~10 MB/s costs ≈1.3 s — about **4,500 queries** at 8-way. *That* is why custody is the right scheduling unit.

Same conclusion the tier model reached, for a reason that is 2,600× larger and survives measurement. It also reframes the design: what must be amortised is the **transfer**, so the scheduler should keep shards resident for hours, and `prefer_cached_cids` matters because re-fetching is expensive, not because re-reading is.

## What it does to the NPU argument
Weaker than S33 suggested, and more specific. The CPU now gets within 1.2× of the *int8-era* roof, so "the NPU is required to make custody viable" is no longer true. The remaining NPU case is:

1. **Offload, not speedup** — every millisecond the pre-filter does not spend on the CPU is a millisecond available for MeTTa exact-match on the shortlist, which is the stage that cannot be packed or offloaded.
2. **The genuinely compute-bound job classes** — shaping and batched clustering (every triple against every centroid), where there is no shortlist to fall back to.
3. **Energy per query**, still unmeasured, and the one number that could justify the NPU on its own.

## Caveats
- Single-threaded; the 8-way figures are S32's 5.87× applied to K2, not measured directly for K2.
- 25 GB/s for the phone's achievable DRAM bandwidth is an assumption, not a measurement.
- Random ±1 data. Real shards are not random, and the packed path's speed is data-independent while the int8 path's is not — this favours K2 and should be re-checked on a clustered store.
- No NPU was involved. This is all CPU.
