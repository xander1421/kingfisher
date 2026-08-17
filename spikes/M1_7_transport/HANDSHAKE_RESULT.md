# Connection setup costs 15.3 ms, not 3 ms — and we pay it on every request

**Two earlier conclusions are withdrawn. QUIC's case is materially stronger than
I said, and there is a cheaper fix available first.**

## What was wrong
The keep-alive falsifier reported *"reuse saves only 1–11%, so connection setup
costs ~3 ms"* and that became the surviving reason for deferring QUIC.

**Reuse was never happening.** The coordinator sends `Connection: close` — which
I had added to work around the okhttp bug — so both arms of the comparison
opened a fresh connection per request:

```
ONE curl, 5 URLs, production server:
  time_connect = 23ms  9ms  8ms  10ms  8ms     <- non-zero every time
```

**The fix for one problem invalidated the measurement of another**, and the
comparison had no control that could have caught it: fresh-vs-fresh looks
exactly like reuse-that-does-not-help.

## Measured properly

Handshake phases, read from curl on device rather than inferred:

| phase | plain | TLS |
|---|---|---|
| `time_connect` (TCP done) | 6.4 ms | 5.9 ms |
| `time_appconnect` (TLS done) | — | 14.9 ms |
| `time_total` | 12.8 ms | 20.3 ms |

```
TCP handshake     6.4 ms   = 1 round trip
TLS handshake    +9.0 ms   = 1.4 x the TCP RTT
total setup      15.3 ms
```

And against a server that actually permits keep-alive:

```
20 requests, one curl:      1/20 connects, median 0.00 ms
20 requests, 20 curls:     20/20 connects, median 6.60 ms
per-request setup avoided:  6.6 ms   (the whole TCP handshake)
```

So setup is **15.3 ms**, five times the 3 ms I reported, and reuse recovers all
of it.

## Also: ICMP was the wrong instrument
`ping` from the phone gave **23.3 ms average** against a **7.1 ms minimum** —
WiFi power-save parks the radio and an ICMP probe measures the idle path. The
TCP handshake says the real RTT is ~6.4 ms. A latency number from ping on a
sleeping phone is not the latency a data flow sees.

## What this does to QUIC
At the measured 2.4-round-trip setup:

| RTT | setup | 0-RTT saves |
|---|---|---|
| 6.4 ms (this LAN) | 15.3 ms | 15.3 ms |
| 30 ms | ~72 ms | ~72 ms |
| 50 ms (cellular) | ~120 ms | ~120 ms |
| 80 ms | ~192 ms | ~192 ms |

The deferral **still holds for a LAN**, but for a corrected reason: plain-TCP
keep-alive recovers the same 15.3 ms and costs nothing. QUIC's distinct value is
what keep-alive cannot do — survive a **reconnect**, which a polling phone does
constantly, and survive a **network change**.

## The action this actually points at
**We currently pay 15.3 ms on every single request**, because our own server
forbids reuse. That is not a QUIC problem, it is a workaround we chose:

```
server.py:  self.send_header('Connection', 'close')
            self.close_connection = True
```

Added to stop okhttp throwing `unexpected end of stream`. So the sequence is:
an app bug forced a workaround, the workaround disabled keep-alive, and the
disabled keep-alive then produced a measurement that argued against fixing any
of it.

Fixing okhttp properly and re-enabling keep-alive is worth **15.3 ms per
request** and is strictly cheaper than adopting QUIC. Queued, not done.
