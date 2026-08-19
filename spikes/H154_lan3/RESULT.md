# H154 — 3 physical devices, real transport, no adb reverse

Which transport is faster for this job: **HTTP, not Rust P2P**.

`LATENCY_FLOOR.md` already put persistent HTTP + `TCP_NODELAY` at **6.5 ms**
against a **6.4 ms** TCP RTT. A long-poll worker has no handshake left for
QUIC 0-RTT / iroh to remove. QUIC still matters for WiFi↔cellular *reconnect*,
which is not this measurement. M1.7 was scoped as iroh and shipped as HTTP
for the same reason. This run used that path.

## What ran

Coordinator on this Mac, bind **`192.168.1.25:18082`**, never `0.0.0.0`.
`KF_TOKEN` required (non-loopback without it **refuses**). Devices dial out.

| machine | role | LAN IP |
|---|---|---|
| Mac (Darwin aarch64) | coordinator + worker `host-darwin` | 192.168.1.25 |
| S25 Ultra | worker `phone-s25` | 192.168.1.20 wlan0 |
| S24+ | worker `phone-s24` | 192.168.1.21 wlan0 |

S24 WiFi was off; enabled for this run (`LigaT_E01370_5G` already saved).
Unread-thermal override only. Charging/cpu_busy still refuse. S24 has no
`curl`; on-device agent is a std-only Rust HTTP client (not iroh).

adb: **install and process start only**. `adb reverse --list` empty on both
phones. F001 fixture bytes were **not** pushed — they crossed WiFi as a CID
shard (491,520 B).

Falsifier (stated first): fewer than 3 workers ACCEPT `590d8769…`, or a
phone peer is `127.0.0.1`, or unauth is not 401.

It did not fire.

## Controls

| control | observed |
|---|---|
| no token from S25 | HTTP **401** |
| no token from S24 | HTTP **401** |
| bind non-loopback without `KF_TOKEN` | **refused** |
| `adb reverse` | empty |
| job/result peers | **192.168.1.20, .21, .25** — no 127.0.0.1 |
| via | all 12 `http://192.168.1.25:18082` |

## Result

12/12 F001 **ACCEPTED**
`590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f`
(same frozen pin). Split **10 / 1 / 1** (host / S25 / S24): the Mac is
faster; jobs were not 1:1. All three machines produced at least one
envelope from their LAN address.

Wall 0.40 s after the three pollers were observed. That is not a compute
rate — 12 tiny verifies, host-heavy.

## What this is not

- Not iroh, not QUIC, not `0.0.0.0`, not a public mesh.
- Not 3 phones. Coordinator is co-located with the Darwin worker.
- Not `operator=2`. Token authenticates the fleet. 0 ACCEPTED on the
  production ledger still. §8 item 1 is this transport box, not quorum.
- demo8 TSV not updated: a CLAIMED row on an untracked spike is BROKEN
  (H77). Item stays UNPROVEN in demo8 until this artifact is in git.

Evidence: `lan3.json`. Check: `python3 kitchen/test_h154.py`.
Certify: `python3 spikes/H154_lan3/certify.py`.
