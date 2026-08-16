# REPORT — `acurast-substrate/pallets/compute` (Unlicense, public domain)

**Read, not copied.** 6,742 LOC across 8 files. Public domain, so §7 imposes no
constraint at all — this is the only elder we could lift verbatim without even an
attribution line.

## First correction: this is not our fuel metering counterpart

It was recommended to me as *"the direct counterpart to our fuel metering."* It is
not. `staking.rs` is the largest file at 2,072 lines and the extrinsic list is
unambiguous:

```
create_pool  modify_pool  offer_backing  withdraw_backing_offer  accept_backing_offer
commit_compute  stake_more  cooldown_compute_commitment  end_compute_commitment
delegate  delegate_more  cooldown_delegation  redelegate  end_delegation
kick_out  slash  withdraw_delegation  withdraw_commitment
compound_delegation  compound_stake  enable_inflation
```

**`pallets/compute` is the economic security layer** — commit capacity, back it
with stake, let third parties delegate to it, slash it. It is the answer to *"how
do you make a device honest without replication"*, which is a different and more
load-bearing question than metering.

## The trust boundary, exactly

`heartbeat_with_metrics(origin, version, metrics)` at
`pallets/processor-manager/src/lib.rs:559` — `ensure_signed(origin)`, the device's
own key. `pallets/acurast/common/src/types.rs:558`:

> *"A list of metrics are committed after deriving them from **performed benchmarks
> on processor**."*

**Device benchmarks itself and self-reports.** Nothing re-measures it, nothing
compares it to peers. The entire weight rests on the attestation chain proving that
key lives in genuine TEE silicon running unmodified code, plus stake it can lose.

This is the sharpest possible contrast with BOINC, which trusts no self-report and
normalises every claim against the fleet (`GUARDRAILS.md` B4), and it is a genuine
architectural fork:

| | BOINC | Acurast | us |
|---|---|---|---|
| device speed claim | never trusted; fleet-normalised, 100-sample floor | self-reported, hardware-attested | *undecided* |
| result correctness | majority of a quorum | TEE + slash, **no second run** | 3-rung replication ladder |
| cost of being wrong | wasted redundant compute | slashed stake | wasted redundant compute |

## What they have that we lack

### 1. Metrics are exact rationals — and this independently confirms S49
`MetricInput = (PoolId, u128, u128)`, *"transformed into a `FixedU128` defined by
`numerator / denominator`"* (`types.rs:560-561`).

S49 found this the hard way: the quantisation boundary sat on `.5`, float-vs-double
splits two honest verifiers, and `rint` in a spec is insufficient because rounding
modes differ across Python/C/Go/JS. The conclusion was *"transmit the scale as an
exact rational, never a float"*, grade B.

**A production chain at 260k devices does exactly this.** One of our few surviving
measured claims matches shipped practice. That is the first independent
confirmation any claim in this workspace has received from outside it — and
`hyperjob_v1.proto` still declares `quant_scale` as a `double`, which is listed in
`LEDGER` under NEVER MEASURED and is now unambiguously a defect.

### 2. Delegation solves a problem we never posed
A phone has no capital. Requiring devices to post stake excludes exactly the
population the project targets. Acurast's answer: `offer_backing` /
`accept_backing_offer` / `delegate` — **third-party capital backs a device's
commitment**, and delegators share rewards and slashing.

Nothing in `PORT_PLAN` or `PROPOSAL_DRAFT` addresses who funds a phone's stake.
It is a hole, and there is a public-domain implementation of the fix.

### 3. Cooldown is chosen by the staker and priced
`lib.rs:107-110` — `MinCooldownPeriod` / `MaxCooldownPeriod`, with:

> *"Delegator's weight is linear as `Stake::cooldown_period / MaxCooldownPeriod`."*

You pick your own lockup, and your weight scales linearly with it. Plus a
`WarmupPeriod` (`lib.rs:145`) so capital must be in place *before* it counts.
Together these stop capital arriving to farm one epoch and fleeing before slashing
lands. We have no lockup concept whatsoever.

### 4. Slashing is permissionless
`slash(origin, committer)` at `lib.rs:947` is `ensure_signed` — **anyone** may
submit it; `do_slash` decides whether the conditions hold. No privileged slasher,
no committee. Cheap, and it means detection can be crowdsourced.

### 5. Extrinsics are versioned by call index, never broken
`heartbeat` (index 3) → `heartbeat_with_version` (5) → `heartbeat_with_metrics`
(11). Each capability arrived as a **new extrinsic**; the old ones still exist.
That is the schema-evolution discipline `hyperjob` will need and does not have.

## Counting, which is the cleanest evidence

Across `pallets/{marketplace,acurast,compute}/src`:

```
slash / slashed / slashing / slashable    366+
replicate                                    4
quorum · redundancy · challenge · dispute    0
```

**Zero.** There is no second run anywhere in this codebase. `FINAL_REPORT` calls
*"who pays for the second run"* the project's biggest risk; Acurast deleted the
question, and their answer generalises to any workload rather than only
deterministic ones.

## Two claims of ours this falsifies

1. **`STATE_OF_THE_UNION`: metering time is *"the wrong unit for a device you
   cannot audit."*** Acurast prices by time —
   `update_min_fee_per_millisecond` (`marketplace/src/lib.rs:877`). Our claim is
   true *only under our own trust model*; TEE attestation makes time auditable. It
   was a conditional statement published as a general one.

2. **`GAP_MATRIX` §46: the worker-bound seal is the gap the mission's capability
   list missed.** Covered in `ELDERS_ROUND2.md` — `DuplicateSourceInMatch` handles
   the echo attack with a storage-map check and no cryptography.

## Two more things to steal

- **Two-phase matching.** `propose_matching` (`lib.rs:542`) →
  `acknowledge_match` (`:556`). A device *confirms* before it is bound. For a
  fleet of phones that can be unplugged mid-negotiation this is essential, and
  `hyperjob_v0.proto` has no acknowledgement step.
- **Four `cleanup_*` extrinsics**, roughly a third of the marketplace surface,
  purely garbage-collecting assignments that never completed. On a phone fleet,
  abandonment is the common case, not the exception. Nothing in M3 budgets for it.

## What is closed to us
Acurast's **on-device runtime is not published** — the coordination layer is fully
open, the processor binary is not. So there is nothing here about how a job is
actually sandboxed and executed inside the TEE. Logged in `BLOCKED.log`.
