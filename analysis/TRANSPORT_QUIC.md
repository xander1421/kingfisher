# QUIC for the device transport — evaluated against our own numbers

> **SUPERSEDED IN PART, 2026-08-17.** The deferral below rests on a
> `63.2 ms fixed + 37.9 MB/s` affine model measured over **USB**. Measured over
> real WiFi (`spikes/M1_7_transport/LAN_RESULT.md`), **the affine model does not
> hold** — bandwidth climbs from 1.0 to 28.3 MB/s with transfer size, so there
> is no single fixed component to be "27% and falling". The recommendation
> (defer) still stands. The *reason* below was first marked void and that was
> **too broad**: `units.affine_range` shows the USB fit holds over 173 KiB-32 MiB
> (57.3 ms + 37.5 MB/s), so it was valid where it was applied. What is actually
> wrong is that it was carried to WiFi, whose affine regime ends at ~1 MiB while
> deployable shards are 6.41 MB and above.
>
> The replacement reason was also tested and also false: plain-TCP keep-alive
> saves only **1–11%**, so it does not capture a large win either. What it
> reveals is that **connection setup on this path costs ~3 ms**, so QUIC's
> 0-RTT has ~3 ms to win against 27–130 ms transfers.
>
> **That is a LAN result and it is the friendliest path that exists.** At
> cellular RTT (~50 ms) the same handshake is 100–150 ms and 0-RTT would be
> decisive. The QUIC question is settled *for a LAN* and open everywhere else.

**Recommendation: not now, and the reason is measured, not architectural.**
QUIC's advantages land almost entirely on costs we have already shown are not
dominant. Revisit when one specific condition changes.

## Where QUIC genuinely fits a phone fleet
Three of its properties are the right shape for this problem, and one is a
capability we currently lack outright:

- **Connection migration.** A QUIC connection is keyed on a connection ID, not
  a 4-tuple, so it survives a WiFi↔cellular switch. A phone that changes network
  mid-job keeps the job. TCP drops it. This is the strongest argument and it is
  phone-specific.
- **0-RTT resumption.** Our worker long-polls repeatedly; every poll currently
  pays a full connection setup. QUIC amortises the handshake after the first.
- **Multiplexed streams without head-of-line blocking.** Matters when fetching
  many shards concurrently. Our fetch pattern is sequential today, so this is
  latent rather than realised.
- **Mandatory TLS 1.3.** We have **no encryption and no authentication at all**.
  QUIC would give encryption and *server* authentication for free.

That last one needs care: TLS authenticates the **server** to the device. It does
nothing about authenticating the **device**, which is the `operator = 1` problem
capping the domain vector. QUIC is not a step toward attestation.

## Why it is not the bottleneck — from M1.5b
Transfer cost decomposes as **63.2 ms fixed + 37.9 MB/s marginal** (USB; a real
network differs, but the *shape* holds). So:

| shard | fixed component | bytes component | dominated by |
|---|---|---|---|
| 2.6 KB (our corpus) | 63 ms | ~0 ms | **fixed cost** |
| 6.41 MB (B1's B=32) | 63 ms | ~169 ms | **bytes** |
| 34.83 MB (B1's B=1) | 63 ms | ~920 ms | **bytes** |

QUIC attacks the fixed component. At deployable shard sizes the fixed component
is **27% and falling**. QUIC does not make bytes move faster on the same link.

And in the regime where fixed cost *does* dominate, we already measured a
cheaper fix: **batching gave 38x** (3680 ms -> 97 ms for the same 173 KB across
67 shards). Connection reuse is most of what QUIC would buy there, and one
`adb push` of a directory already captures it.

## Honest cost
- **Coordinator**: fine. `quinn` is mature.
- **Device**: this is the problem. `HttpURLConnection` has no HTTP/3. The Android
  options are Cronet (**several MB** added to an APK whose entire pitch is
  running on consumer phones — `libhyperonc.so` is already 6.43 MiB) or an
  okhttp HTTP/3 engine. That is a real weight cost against a marginal latency
  gain.
- **Our current transport is loopback over `adb reverse`** with no network at
  all, so QUIC cannot even be exercised until there is a real network path.

## The condition that would change the answer
Adopt QUIC when **either**:
1. devices are observed changing network mid-job — connection migration is the
   one benefit with no cheaper substitute; or
2. the deployed shard size drops into the fixed-cost regime **and** batching is
   not available because fetches are demand-driven rather than pre-staged.

Neither holds today. (2) is also in tension with M2.1: pre-staging at charge
time is the residency policy we already want for locality reasons.

## What to do instead, in order
1. **A real network path at all.** Everything above is loopback. Until the phone
   dials a coordinator over WiFi, transport numbers are shapes, not values.
2. **TLS on whatever transport exists**, since we have none. This is a security
   gap today and does not require QUIC.
3. **Batch fetches** — measured 38x, already implemented for the adb path.

Recorded as a WORK_QUEUE item, not a rewrite. The CEO raised QUIC as "the
fastest transport possible", which is true in the regime it targets; our
measurements say we are not in that regime yet.
