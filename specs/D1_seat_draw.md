# D1+ — Seat draw specification

**Status: spec, falsifiable. Written 2026-08-17 after the S69/S70 demolition.**

## Why this exists
S69's quorum design drew seats from *devices currently online holding the
shard*. Two failures followed, and both were fatal:

- **Duty-cycle capture.** Honest devices run at duty 0.05–0.25 (charge-time,
  WorkManager). An adversary runs at 1.0. Measured: **five always-on devices
  beat an R=25 shard at honest duty 0.25 (P=0.42), and reach certainty at 0.05.**
  Staying online *was* the attack.
- **Residency coupling.** Eligibility required holding the shard, so the pool
  was small, and the "fetch a global replica" fix made the adversary's cheapest
  device the one that holds nothing.

W1 cut the second: a witness is ~4.2 KB regardless of shard size, so
**any staked device can verify any job**. This spec cuts the first.

## The rule
> **Seat selection is proportional to stake over an epoch-committed registry.
> Never over the online set. Availability is never an input to selection.**

### R1 — Registry
At each epoch boundary the coordinator commits `REG_e = {(device_id, stake)}`
and publishes `root(REG_e)`. Membership and stake are **frozen for the epoch**.
Devices joining mid-epoch are eligible from `e+1`.

### R2 — Draw
For job `j`, seats are drawn from `REG_e` with probability proportional to
stake, without replacement, using a seed that no participant controls alone:
`seed = H(root(REG_e) ‖ job_id ‖ beacon_e)`.
Quorum size is 3 unless the job class declares otherwise.

### R3 — No locality term
**Seats carry no residency requirement.** A drawn device that lacks the shard
fetches the witnesses it needs (W1: ~4.2 KB, not the shard). Locality remains a
*scheduling* preference for latency and a *caching* policy — it is not an input
to seat selection, and coverage is therefore not a security parameter (POL).

### R4 — Two-phase: offer, then acknowledge. Penalty attaches to the ack, not to being offline.

**Corrected by ATTACK cycle 4. The first version of R4 was fatal**: it penalised
any drawn device that did not respond, and an honest charge-time device at duty
0.05 is offline **95%** of the time. It would have been penalised on 95% of the
seats it was offered, making honest participation net-negative. Measured across
the honest range:

| honest duty | offered-while-offline | penalised under R4-v1 |
|---|---|---|
| 0.05 | 95% | 95% |
| 0.10 | 90% | 90% |
| 0.25 | 75% | 75% |

Corrected mechanism:

1. **Offer.** The drawn device is offered the seat. Silence within `T_offer` is
   **not a fault** — it is the normal state of a charge-time device. The seat is
   silently **redrawn from `REG_e`, stake-weighted**, excluding devices already
   offered this job.
2. **Acknowledge.** A device that accepts is now **bound**.
3. **Penalty attaches only after ack.** Failing to deliver within `T_seat`
   *after acknowledging* is the fault: stake slashed by `p_timeout`, or
   reputation decremented in the MVP.

This is Acurast's `propose_matching` → `acknowledge_match`
(`marketplace/src/lib.rs:542,556`) — a two-phase shape `hyperjob_v0.proto` lacks
and now needs. It preserves the property that matters: **the draw is still
stake-weighted over the whole registry, so availability is not a selection
input.** Staying online only lets an adversary accept more of the seats its
stake was already going to win.

### R5 — Same rule for every seat
There is no local/global seat distinction. R3 makes the split unnecessary; S69's
version of it was the vector.

## Falsifiers
This spec is wrong if any of these can be shown:

| # | falsifier | how to test |
|---|---|---|
| F1 | An adversary at duty 1.0 with share *s* of **stake** wins more than ~*s* of seats | simulate R2+R4 against honest duty 0.05–0.25; adversary seat share must track stake share, not duty |
| F2 | Redraw lets an adversary raise its seat share by *declining* until favourably matched | R4 offers are stake-weighted without replacement per job; model a declining adversary and require its accepted share to track stake |
| F2b | An always-on adversary captures a larger share of **accepted** seats than its stake | simulate offer/ack against honest duty 0.05–0.25; accepted share must track stake, since offers are redrawn on silence |
| F3 | A device can influence `seed` | `beacon_e` must be unpredictable to any single participant at commit time |
| F4 | Mid-epoch stake changes affect the current epoch's draws | R1 freezing must be enforced, not assumed |
| F5 | W1's witness cost is not bounded for some job class, making R3 unaffordable | W3 measures non-aligned access; if witnesses approach shard size, R3 needs a locality term back |

**F5 is live.** W1 measured `(p ?s o)` and `(?p s o)` touching 100% of chunks —
witness worse than the shard. Until W3 grades that, **R3 holds only for
clustering-aligned job classes**, and non-aligned classes fall back to
re-execution by a resident replica.

## MVP concession, recorded
No chain, no stake, no beacon in M1. The **named coordinator emulates R1–R5**:
holds the registry, draws seats, applies timeouts, logs points instead of
slashing. This is a trust concession and is recorded as one — the coordinator
can bias every draw. What the MVP demonstrates is that the *mechanism* runs, not
that it is trustless.

The spec exists so the coordinator has something to emulate and so the
concession has a named end state.

## Open, not hidden
- `p_timeout`, `T_seat` and the quorum size for each job class are **unset**.
  D3 declares shard demand an unmeasured input; these are in the same category
  and must not be given constants derived from nothing.
- Sybil cost is bounded by stake, and no stake floor has been priced.
