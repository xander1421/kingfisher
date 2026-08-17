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

---

# The keep-alive falsifier, run

Stated at the end of the section above and left unrun: *"plain-TCP connection
reuse would capture most of the same win, and that is one flag and is not run."*
Run now. 20 blobs per size, one curl per request versus one curl reusing the
connection across all 20, timed on-device with `%{time_total}`:

| KiB | fresh (ms) | reused (ms) | saved | per request |
|---|---|---|---|---|
| 4 | 544.3 | 483.2 | 11.2% | **3.1 ms** |
| 64 | 967.0 | 953.1 | 1.4% | **0.7 ms** |
| 1024 | 2658.0 | 2579.6 | 2.9% | **3.9 ms** |

**My hypothesis was wrong and the conclusion is stronger for it.** Reuse saves
only 1–11%, so keep-alive does *not* capture a large win — but that is because
**there is barely a win to capture**: connection setup on this path costs about
**3 ms**.

QUIC's 0-RTT can at best remove connection setup. If setup is 3 ms, 0-RTT saves
3 ms — against a 27 ms request at 4 KiB or a 130 ms one at 1 MiB. Negligible.

## So the deferral now rests on its third reason, and the first two are dead
1. ~~"fixed cost is 27% and falling"~~ — **void**: the affine model it came from
   does not hold on a real network.
2. ~~"keep-alive would capture most of the win"~~ — **false**: reuse saves 1–11%.
3. **"connection setup costs ~3 ms on this path, so 0-RTT has ~3 ms to win"** —
   measured, and it is the reason that survives.

## And it is path-dependent, which is the part that decides the future
This is a LAN: sub-millisecond RTT. A TLS+TCP handshake is 2–3 round trips, so
~3 ms here. On **cellular at 50 ms RTT that same handshake is 100–150 ms**, and
0-RTT resumption would be decisive rather than negligible.

**We have measured one path and it is the friendliest one that exists.** The
QUIC question is not settled by this; it is settled *for a LAN*. The measurement
that would actually settle it is the phone on cellular against a coordinator it
must reach over the internet — which is also the first configuration where
binding beyond the local network becomes a real exposure rather than a
documented one, and where TLS stops being optional.

Recorded rather than resolved.

---

# TLS on the LAN path — done, with three controls

We had no encryption and no server identity at all. Now:

```
coordinator 192.168.1.25:18080   LAN bind, TLS 1.2+, token required
pinned SPKI sha256: 1P74+TNkmPdy3RsPwg2P1iDNY7j9nemszQHS/0eo2C8=

control A, no token:        HTTP 401   (TLS succeeded, auth refused)
control B, wrong pin:       refused    (TLS refused before auth)
control C, cleartext:       refused

over WiFi+TLS: 20/20 envelopes in 10.8 s, 83,375 shard bytes
```

Against 10.6 s for the same run without TLS — **~2% cost on this path**, which
removes any performance argument for leaving it off.

## Design: pinning, not a PKI
The cert is self-signed, generated per run, valid one day, and neither the key
nor the cert leaves the workspace or outlives the process. Nothing is installed
into a device trust store. The device pins the **public key by hash**
(`--pinnedpubkey sha256//…`), which is the right shape when there is exactly one
server and it is ours.

### The thing that made it fail first
`--pinnedpubkey` is an **additional** check, not a replacement for chain
validation. Curl still walked the system CA store, rejected the self-signed
cert, and never reached the pin — all three controls returned `000`, including
the one that should have produced a 401. It needs `-k` **and** the pin together:
skip the CA path, require an exact public key.

`-k` alone would be strictly insecure. `-k` + pinning is **stronger** than CA
validation for a single known server, because it accepts exactly one key rather
than anything a public CA will sign. Worth stating precisely, because the flag
that makes it work is the one that usually means "I gave up on security".

## What this does and does not buy
- **Confidentiality on the wire.** The bearer token no longer crosses the LAN in
  clear text. That was a live defect in the previous run.
- **Server identity.** The phone can prove it is talking to *our* coordinator.
- **NOT device authentication.** Pinning says nothing about *which* phone is
  connecting. `operator = 1` is untouched, and the domain vector still binds
  there. TLS was never going to fix that and should not be read as progress on it.
