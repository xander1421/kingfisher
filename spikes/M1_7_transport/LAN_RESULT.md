# M1.7b/c — the phone dials over real WiFi, and the transfer model does not survive

**20/20 envelopes over WiFi with token auth, and the `fixed + marginal` split
that deferred QUIC turns out not to hold on a real network.**

## The path is real now
```
coordinator 192.168.1.25:18080   (LAN bind, token required)
phone       192.168.1.20         (WiFi, same /24)

control, unauthenticated request from the phone:  HTTP 401
over WiFi: 20/20 envelopes in 10.6 s, 20 OK, 83,375 shard bytes
```

Everything before this was `adb reverse`, i.e. USB. No RTT, no radio, no loss.

### Exposure, stated rather than implied
This puts a job-dispatch endpoint on the local network. What is done about it:

- `server.serve()` **refuses** a non-loopback bind unless `KF_TOKEN` is set.
  Control verified — it raises.
- Bind is to the specific LAN address, never `0.0.0.0`.
- Bearer token on every endpoint, compared with `hmac.compare_digest`.
- The server lives only for the run.

What that does **not** buy, and the distinction matters: the token authenticates
**the fleet**, not **a device**. It cannot tell two workers apart and does
nothing about collusion, so it is not the attestation root `operator = 1` needs.
**There is still no TLS**, so the token crosses the LAN in clear text.

### A cache bug that would have faked the result
The first LAN run reported `shard_bytes: 0` — `agent.sh` hardcoded
`/data/local/tmp/m17` and silently reused the warm cache from the adb runs. The
run "succeeded" over WiFi while transferring nothing. Made overridable; the real
run moved 83 KB.

## The transfer model does not survive contact with a network
M1.5b over USB: **63.2 ms fixed + 37.9 MB/s marginal**. Over WiFi, timed
**on-device** with curl's own `%{time_total}` so adb is not in the measurement:

| KiB | ms | apparent MB/s |
|---|---|---|
| 4 | 14.4 | 0.3 |
| 16 | 25.8 | 0.6 |
| 64 | 31.6 | 2.0 |
| 256 | 53.2 | 4.7 |
| 1024 | 130.9 | 7.6 |
| 4096 | 295.4 | 13.5 |
| 16384 | 719.3 | 22.2 |

Fitting the two largest points gives `154.1 ms fixed + 28.3 MB/s`. **That is
wrong**, and its own data says so: a 154 ms fixed cost cannot coexist with a
4 KiB request completing in 14.4 ms.

Fitting each adjacent pair separately:

| pair | implied MB/s | implied fixed ms |
|---|---|---|
| 4→16 | 1.0 | 10.6 |
| 64→256 | 8.7 | 24.4 |
| 1024→4096 | 18.2 | 76.1 |
| 4096→16384 | 28.3 | 154.1 |

A stable affine model shows one bandwidth and one intercept. Bandwidth climbs
monotonically and the implied intercept swings from 11 ms to 154 ms.
**Bandwidth is a function of transfer size** — TCP slow start and window growth
— so `fixed + marginal` is the wrong model here, and any two-point fit reports
an artifact of where you sampled.

This is A18 applied to my own analysis one level up: A18 says check which
regime the measurement sits in. Here the regime never stabilises within the
range measured, so there is no single rate to report at all.

## What this does to the QUIC decision
`analysis/TRANSPORT_QUIC.md` deferred QUIC because the fixed component was "27%
and falling" at deployable shard sizes — computed from the USB affine fit.
**That reasoning is void**, because the affine fit is void.

What the WiFi data supports instead:
- small transfers are dominated by per-request cost (4 KiB at 0.3 MB/s
  effective), so **batching and pre-staging remain the right lever** and were
  measured at 38x;
- large transfers reach 22 MB/s and are bandwidth-bound, where QUIC does not
  help;
- the middle is slow-start, which **0-RTT and connection reuse genuinely do
  attack** — and this is the regime B1's 6.41 MB shards sit in.

So QUIC's case is **stronger than the USB analysis suggested**, and still not
made: connection reuse over plain TCP would capture most of the same win. The
honest next test is keep-alive versus fresh connections on this same curve,
which costs one flag and is not run.

## Limits
- One AP, one phone, one room, no contention, no loss. A LAN is not a fleet.
- `curl` process spawn is inside every timing; the 4 KiB point is an upper
  bound on per-request cost, not a measurement of it.
- Single seed, median of 5, no confidence intervals.
