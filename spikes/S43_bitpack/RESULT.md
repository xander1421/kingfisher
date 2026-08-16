# S43 — bit-packing is exact and 12.7× at q=1, and it loses at q≥16. S18's roofline was wrong.

**Verdict: GREEN on exactness, GREEN on the low-q speedup, RED on my own "pack everything" recommendation, and RED on S18's central claim.**

Claimed in `chat.log` 17:20Z (AGENT-3), extended 17:35Z with the ternary identity (AGENT-4). Neither of us had run it.

Code `pack.py`, logs `pack.log` / `stream.log`. n=100,000, D=1024, M4 Pro (10P+4E, 24 GB), `loadavg 1.30 → 1.41`, competing: another python. **Numbers are soft by this workspace's own rule and are reported anyway with the flag on.**

## 1. The exactness gate — both identities hold

```
EXACTNESS GATE  bipolar OK, ternary OK  (2000 vectors, ternary zero-rate 0.0000)
float32 path == packed path on the full 100,000 store: True
```

For bipolar `a,b ∈ {−1,+1}^D`, `dot(a,b) = D − 2·hamming(a,b)`. For the bundled ternary store, AGENT-4's two-bitplane identity reproduces the int32 reference exactly. Asserted before any timing; a failed gate would have suppressed the run.

**This is the load-bearing result.** It is what makes a popcount NPU kernel legal in a byte-comparison network, and it is now checked against a true int32 reference rather than argued.

One correction owed to AGENT-4 and to my own entry: at D=1024 with three odd terms the measured ternary **zero-rate is 0.0000** — `sign()` of three ±1 terms cannot be zero. Ties only appear at even bundling arity. The mask bitplane is still needed for the general case, but the "bundled store is ternary so you only get 4×" caveat does not bite for odd-arity bundles.

## 2. Storage: 8.0× confirmed

```
store  int8 102.4 MB   packed 12.8 MB   8.0x smaller
```

## 3. Speed — and the regime split nobody predicted

```
    q   float32 (S18)      packed   speedup   GOP/s f32   GOP/s pk  ms/query pk
    1         26.5 ms      2.1 ms    12.70x         7.7       98.1       2.087
    4         32.2 ms      8.3 ms     3.86x        25.5       98.2       2.085
   16         29.1 ms     33.3 ms     0.87x       112.5       98.3       2.083
   64         33.1 ms    134.0 ms     0.25x       395.9       97.8       2.093
  256         49.9 ms    536.8 ms     0.09x      1051.4       97.7       2.097
```

**At q=1 packing is 12.7× — better than the 8× I claimed**, because it removes the traffic *and* the float32 materialisation. At q≥16 it loses, and at q=256 it is 11× slower.

The packed column is **flat at ~98 GOP/s and 2.09 ms/query at every q**. It does not amortise across a batch, because a popcount kernel does `O(q·n·D)` bit work with no matrix structure to exploit, while `Q @ Tᵀ` hands the batch to a blocked GEMM that reaches 1,051 GOP/s.

**So the two representations are complementary, not substitutes:**

| regime | winner | why |
|---|---|---|
| q=1 — one device, one query (M1) | **packed popcount, 12.7×** | no batch to exploit; traffic and conversion dominate |
| q≥16 — shard host, shaping (M2/M4) | **matmul**, up to 11× the other way | a real matrix engine amortises |

My chat.log entry said "pack the store, 8×, ranked #1". That is right for the case the plan actually specifies and **wrong as a blanket recommendation.** A shard host serving batches wants the matmul path — which is also the path HMX accelerates.

**Declared confound:** the float32 arm runs multi-threaded Accelerate; the packed arm is single-threaded numpy with a materialised `bitwise_count` temp. This is S13's error shape (mismatched baselines) and I am flagging it rather than reporting past it. A threaded NEON `vcntq_u8` kernel would close an unknown part of the q≥16 gap. Until it exists the crossover point is not established — only that one exists between q=4 and q=16.

## 4. S18's central claim is false on this machine

S18: *"at q=1 the kernel is bandwidth bound, the CPU is already at the memory roof, and an NPU shares the same memory bus."*

Measured roofs (`stream.log`):

```
copy  int8 102.4MB      1.476 ms   138.8 GB/s   (read+write)
copy  packed 12.8MB     0.150 ms   171.2 GB/s
scan  packed read-only  0.276 ms    46.4 GB/s   (single-threaded)
kernel packed q=1       2.070 ms     6.2 GB/s   effective
```

The machine streams the whole 102.4 MB int8 store in **~0.74 ms**. S18 measured 26.5–28.0 ms for the same pass. That is **~36× above the memory roof, not at it.**

And the packed kernel is not at the roof either — 6.2 GB/s against a 46.4 GB/s single-threaded read-only scan, so **another ~7× of headroom sits inside numpy's temp allocation.** A SIMD popcount at scan rate would take ~0.28 ms, which would be ~95× versus S18's number.

S18's architectural conclusions (Amdahl against the exact-match stage; NPU wants batch; shard-host ≠ worker) survive intact and are still the best reasoning in the workspace. Its *mechanism* does not: at q=1 nothing was bandwidth-bound, so "an NPU shares the same memory bus" does not decide the question. What decides it is that the CPU can capture the headroom itself with ~40 lines of NEON — no NPU required, for a different reason than S18 gave.

## 5. What this gives the fleet arithmetic

Per-device, measured on the host, single-threaded, packed, q=1:

```
2.087 ms/query  ->  479 queries/s/core
```

Projected to the phone with S30's **sustained** ratio (3.7×, not the burst 2.7×): **~130 queries/s/device**, single core, before any NEON or NPU work. Marked as a projection; no phone ran this.

```
1,000 devices    ~130k queries/s      8 B triples resident @128 B/triple, 1 GB/device
10,000 devices   ~1.3M queries/s     80 B triples
```

Those are the numbers a proposal should use, and they are floor numbers: single-threaded, no SIMD, no NPU, unbundled packing.

## 6. What this does NOT show

- One machine, one D, one n, uniform synthetic data. Nothing here ran on the phone.
- The q≥16 crossover is confounded by threading (§3) and is not a fair fight yet.
- `np.bitwise_count` materialises a temp; the numbers are an upper bound on a real kernel's time, not an estimate of it.
- Bundled (B=64) stores were exactness-checked but not timed. The VTCM residency case is still untested.
- Contention flag was on for the whole run.

## Reproducing

```sh
./spikes/S5_hdc_prototype/.venv/bin/python spikes/S43_bitpack/pack.py 100000 1024
```
