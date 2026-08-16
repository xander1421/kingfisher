# S18 — does a phone NPU have anything to accelerate?

**Verdict: RED for the NPU story as currently framed.** The pre-filter kernel is
memory-bound at low batch sizes. A device serving **one query at a time runs at
7.3 GOP/s — 1.4% of the 1,032 GOP/s the same kernel reaches at batch 256.**
There is no compute to accelerate at that granularity, and an NPU shares the
same memory bus.

Log: `S18_batch_intensity.log`. D=1024, 100k triples, laptop CPU via Accelerate.

## The argument, then the measurement

S9 established that this kernel's arithmetic intensity is `2·q` ops/byte: ops are
`2·q·n·D`, bytes streamed are `n·D` (the shard), so intensity depends **only on
the query batch size q**, not on D and not on shard size. NPUs win on
compute-bound work. So the whole NPU premise reduces to one question: how many
queries does a device run against a resident shard at once?

| queries | intensity | warm ms | GOP/s | ms/query |
|---|---|---|---|---|
| 1 | 2 o/B | 28.0 | **7.3** | 28.03 |
| 4 | 8 o/B | 30.0 | 27.3 | 7.51 |
| 16 | 32 o/B | 30.6 | 107.2 | 1.91 |
| 64 | 128 o/B | 33.9 | 386.4 | 0.53 |
| 100 | 200 o/B | 38.4 | 532.8 | 0.38 |
| 256 | 512 o/B | 50.8 | **1032.1** | 0.20 |

**141× throughput swing from batch size alone.** Note the wall-clock column:
28.0 ms for one query, 38.4 ms for a hundred. You pay to stream the shard once;
every query after the first is nearly free. Marginal cost per query collapses
from 28.03 ms to 0.20 ms.

## What this does to the architecture

`out/PORT_PLAN.md` M1's exit criterion is "a phone plugged in overnight fetches a
shard by CID, evaluates a MeTTa program under a fuel limit, uploads an envelope."
**One job, one device.** At that granularity `q = 1`, the kernel is bandwidth
bound, and the NPU contributes nothing — the CPU is already at the memory roof.

The NPU earns its place only if the device is a **shard host answering many
queries against resident data**, not a **worker executing one job**. Those are
different products with different economics: the first is a read-heavy service
that wants uptime and residency, the second is an opportunistic batch worker that
wants charge-time scheduling. `spikes/S6_scheduler/` designed the second.

## Compounding problem, from S17

S17 measured the CPU exact-match stage checking **10–22% of the store** at useful
compression (B=16–64), versus 0.01% at B=1 (which costs 102 MB). So the
two-stage design has the NPU accelerating the *cheap* stage while the expensive
stage is symbolic work an NPU cannot touch. Amdahl works against the design
exactly where compression makes deployment possible.

## What would refute this
1. **Measure the exact-match stage on device.** If `interpret_step` over a
   10–22% shortlist is cheap relative to a 28 ms matmul, the Amdahl objection
   dies. Nobody has measured it.
2. **Measure QNN/Hexagon at q=1.** If the NPU has a private high-bandwidth path
   or on-chip shard residency, the memory roof moves and this result does not
   transfer. `/vendor/lib64/libsnap_qnn.so` is on the attached device.
3. **Show that devices naturally batch.** If a shard host accumulates 100+
   queries per shard-stream, q=100 is the real operating point and the NPU is
   back in play at 532 GOP/s.
