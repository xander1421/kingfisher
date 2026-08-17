# M1.7 — phone-initiated transport. The device always dials.

**66/66 envelopes over HTTP, byte-identical to host on `fuel_used` AND
`sorted_hash`. Zero inbound connections to the phone, zero external network
surface.**

## Shape
```
device                              host (127.0.0.1 ONLY)
  GET  /job?worker=W   ───dial──▶   long-poll, 204 on timeout
  GET  /shard/<cid>    ───dial──▶   bytes by CID, 404 if unknown
  POST /result         ───dial──▶   envelope
```
S8's finding was that the DAS bus dials clients back and a phone cannot accept
that — no stable address, no inbound port, asleep most of the time. Every
connection here is outbound from the device.

The coordinator binds **127.0.0.1 only**, never `0.0.0.0`. The phone reaches it
through `adb reverse tcp:PORT tcp:PORT`, which forwards a device-local port to
the host loopback. That gives a real dial-out transport with **no LAN exposure
and nothing leaving the machine** — §10 satisfied by construction rather than by
policy, which matters because nothing in this transport authenticates anything.

## Measured
```
66 jobs, cold device cache
  returned  66/66 envelopes in 20.8 s
  status    65 OK, 1 FUEL_EXHAUSTED (mkdocs.metta, expected)
  polls 67 · jobs_out 66 · shard_bytes 177,369 · misses 0
  phone-over-HTTP vs host: 66/66 byte-identical (fuel_used AND sorted_hash)
```

## The control failed first, and it caught a real bug
Queue a job for a CID the coordinator does not hold, and see whether the
transport reports a miss or fabricates a result.

**First run: FAILED.** `misses 1` **and** `results 1` — the agent posted an
envelope for a shard it never received.

```sh
curl -s -m 60 -o "$F" "$BASE/shard/$CID" || { rm -f "$F"; continue; }
```
Without `-f`, curl writes the empty 404 body to `$F` and **exits 0**. So the
file existed, the guard passed, `fuelrun` ran on an empty file, and its output
was posted as a result. That is the empty-capture failure — the same shape as
S57/S62's `da39a3ee` empty hash — arriving through a new door.

**Fixed:** `curl -fsS` so an HTTP error is a failure, plus an empty-file check
before running. Re-run: `misses 1, results 0`.

**The part worth keeping:** M1.8's `device_fetch` already verified shard bytes
on the device. I wrote a second transport and did not carry the check across.
A check that exists is not a check that applies — every new path needs it
re-established, and only a control that can fail will tell you.

## Limits
- **No authentication of any kind.** A job dispatcher on loopback is safe
  because it is on loopback; the moment this binds wider it needs the
  attestation root that `operator=1` is already blocked on.
- **`adb reverse` is a stand-in for a real network.** It proves the dial-out
  *shape* and the byte-identity of results delivered over HTTP. It does not
  measure latency, loss, retry, or metered-network behaviour — the UNMETERED
  constraint is untested here.
- **The CID check on device is presence-and-nonempty, not a full re-hash.**
  `sha256sum` is computed but the multibase decode needed to compare it to the
  CID is not done in shell; M1.8's Python worker does the full comparison. This
  agent catches an empty or missing body, not a substituted one.
- One device, so this is transport plus one worker, not a fleet.
