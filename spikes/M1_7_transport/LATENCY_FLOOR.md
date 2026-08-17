# The lowest achievable per-request latency, measured

**Floor is 7.0 ms — one round trip. We ship 17.8 ms. And the obvious fix,
applied naively, makes it 51.9 ms.**

| configuration | median | vs floor |
|---|---|---|
| persistent connection, Nagle ON (default) | **51.9 ms** | 7.4x worse |
| fresh connection per request — **what we ship** | 17.8 ms | 2.5x worse |
| **persistent connection + `TCP_NODELAY`** | **7.0 ms** | floor |
| measured TCP RTT (1 handshake round trip) | 6.4 ms | — |

7.0 ms against a 6.4 ms round trip means the persistent path is at the physical
limit: one RTT, no handshake, no stall.

## The trap: enabling keep-alive alone makes it worse
Python's `BaseHTTPRequestHandler` leaves Nagle's algorithm on. On a persistent
connection with small responses this collides with delayed ACK and produces the
classic ~40 ms stall — visible as the 48–57 ms cluster. **Turning on keep-alive
without `TCP_NODELAY` is three times slower than the fresh connections it
replaces.**

`disable_nagle_algorithm = True` on the handler. One line, 7.4x.

## What this does to the QUIC question, finally
The research is clear on the landscape ([TLS 1.3 over TFO vs QUIC](https://eprint.iacr.org/2019/433.pdf),
[Akamai on early data](https://www.akamai.com/blog/edge/lightning-fast-requests-with-early-data),
[QUIC connection migration](https://www.gocodeo.com/post/quic-vs-tcp-why-quic-is-critical-for-low-latency-web-applications)):
QUIC's 0-RTT and TLS 1.3 early data both remove **handshake** round trips.

**A persistent connection has no handshake to remove.** At 7.0 ms we are already
at 1 RTT, which is what 0-RTT converges to — you cannot deliver a request in
less than the time it takes to cross the network.

So for our workload — a worker that long-polls continuously — the ordering is:

1. **persistent connection + `TCP_NODELAY`** — 7.0 ms, at the floor, costs one line
2. keep-alive within a session — same, while the session lasts
3. QUIC 0-RTT / TLS 1.3 early data — saves the 15.3 ms setup **only on reconnect**
4. TCP Fast Open — the TCP-side equivalent, and widely broken by middleboxes

QUIC's value for us is **not** latency on the steady path. It is reconnect and
[connection migration](https://www.gocodeo.com/post/quic-vs-tcp-why-quic-is-critical-for-low-latency-web-applications)
— surviving WiFi-to-cellular without a new handshake. That is real for a phone
and it is a different argument from "fastest transport".

## Idle gap: what a reconnect actually costs on a phone
| idle before request | latency |
|---|---|
| 0 s | 27.6 ms |
| 2 s | 36.7 ms |
| 5 s | 34.6 ms |
| 15 s | 34.7 ms |

A gap of even 2 s adds ~9 ms and then plateaus — the radio leaving its active
state. **0-RTT cannot remove this**: it is the modem waking, not a handshake.
Worth stating because it caps what any transport change can buy on the
reconnect path, and the MQTT literature makes the same point from the other
side — [keepalive traffic versus reconnection latency is the real
tradeoff](https://www.simplexwireless.com/2025/06/02/understanding-mqtt-over-cellular-networks-keep-alive-behavior-and-timeout-realities/).

## Blocked on
Enabling keep-alive requires removing `Connection: close`, which exists to work
around the okhttp fault (`spikes/M1_8_quorum3/APP_WORKER_BLOCKED.md`). So the
2.5x is available to the shell agent today and to the app only after that fault
is fixed. That raises the priority of a defect I twice judged to block nothing.

---

# Taken: 17.8 ms -> 6.5 ms. The workaround was for a misdiagnosis.

**Falsifier stated:** *the `Connection: close` workaround is still needed now
that auth is fixed.* **Refuted.** The app returns 8/8 with keep-alive on.

```
PRODUCTION server, 20 requests on one connection:
  connects > 0        1/20        (reuse working)
  per-request median  6.5 ms      (was 17.8 ms)
  min                 5.5 ms
```

Two lines: remove `Connection: close`, set `disable_nagle_algorithm = True`.
**2.7x, and it is the floor** — 6.5 ms against a 6.4 ms measured RTT.

## The full chain of the mistake, because it is the useful part
1. The app failed with okhttp's `unexpected end of stream`.
2. I diagnosed it as stale pooled sockets and added `Connection: close`.
3. **That diagnosis was wrong.** The real cause, found much later, was a
   missing `Authorization` header — the app was getting 401s.
4. The workaround stayed, silently costing 2.5x on every request.
5. It then corrupted a *different* measurement: the keep-alive falsifier
   compared fresh-vs-fresh and concluded reuse was not worth having.
6. That conclusion became the surviving reason to defer QUIC.

**A workaround for a misdiagnosed fault is worse than the fault.** The fault was
visible; the workaround was not, and it went on to produce a wrong measurement
and a wrong architectural conclusion.

## Both controls could have failed, and say how
| control | can fail because | observed |
|---|---|---|
| reuse actually happened | if the server still sent `Connection: close`, `time_connect` would be non-zero on all 20 | 1 of 20 |
| app still works | if the workaround were required, the app would return 0 envelopes as it did for ~15 cycles | 8/8 |

The first exists because the previous keep-alive measurement had no such
control and was void for exactly that reason: **I did not assert that the
mechanism under test was active.**

## Shared-module rule applied
`server.py` changed, so every entry point importing it was run:

| driver | result |
|---|---|
| `run_app.py` (app, JNI) | 8/8 |
| `run.py` (shell agent, adb) | 8/8, byte-identical to host |
| `run_lan.py` (WiFi + TLS) | 8/8, auth control fired 401 |
| `q3.py` (quorum) | 4/4 agree, gate refused later on thermal 45.5C — correct |

## Consequence for the blocked item
`APP_WORKER_BLOCKED.md` said the okhttp fault "blocks nothing". That was true
when written and false by the time I acted on it: the workaround it forced was
costing 2.7x. **A blocked item's cost is not fixed at the moment you block it**,
and nothing in the process re-examines that. The trigger here was measuring
something unrelated.
