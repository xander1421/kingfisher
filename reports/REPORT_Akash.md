# REPORT: Akash Network (node)

## 1. Identity
- URL: https://github.com/akash-network/node
- Commit: `096bff578d5041b87a3f06ef0337d214a3d452ec` (2026-07-24)
- License: **Apache-2.0**. Gate: **PORT allowed with attribution.**

## 2. Shape
310 Go files, 45 YAML, 37 Rust (CosmWasm-adjacent), 22 markdown. A **Cosmos SDK** application (`app/`, `x/` modules, `cmd/`), with `wasmvm.go` for CosmWasm support.

Modules under `x/`: `deployment`, **`market`**, `escrow`, `provider`, `cert`, `audit`, `take`, `bme`, `epochs`, `oracle`, `wasm`. Each follows the Cosmos layout `keeper/ handler/ query/ simulation/ genesis.go module.go`.

## 3. Entry points
`cmd/akash` → a Cosmos node. The interesting logic is in `x/market/keeper/keeper.go` and the `EndBlock` handler that closes auctions.

## 4. Extraction targets

### 4.1 SDL manifest grammar (`x/deployment/testdata/deployment-v2-*.yaml`)
Four top-level sections, `version: "2.0"`:
```yaml
services:                # what to run
  web:
    image: anapsix/webdis
    env: [REDIS_HOST=redis-server]
    expose:
      - port: 7379
        as: 80
        to: [{global: true}]
        accept: [webdistest.localhost]
profiles:
  compute:               # resource shape, per service
    web:
      resources:
        cpu:     {units: 0.1}
        memory:  {size: 16Mi}
        storage: {size: 128Mi}
  placement:             # where, and at what price
    global:
      pricing:
        web: {denom: uakt, amount: 10000000}
deployment:              # the cross product: service x placement
  web:
    global: {profile: web, count: 1}
```
The structural idea worth stealing: **`services` (what) / `profiles.compute` (how big) / `profiles.placement` (where + max price) / `deployment` (the cross product, with a count)**. Placement groups can carry signed attribute requirements (`signedBy`, `attributes`) so a requestor can insist on providers audited by a particular auditor — that is what `x/audit` and `x/cert` exist for. NuNet's `EnsembleConfig` mixes all four concerns into one `allocations` map; Akash's separation is cleaner and makes "same workload, three different price/placement policies" expressible without duplication.

**The price is in the manifest.** The requestor declares a maximum they will pay, per service per placement group, denominated in `uakt`. That is a reverse auction's reserve price and it belongs in a job spec — ours does not have one yet (S4 deliberately deferred pricing).

### 4.2 Auction / bid state machine (`x/market/`)
Objects: **Order** (created from a deployment group), **Bid** (a provider's offer against an order), **Lease** (the matched pair).

States, from `keeper.go`:
- Bid: `BidOpen → BidActive` (`OnBidMatched`), `→ BidLost` (`OnBidLost`), `→ BidClosed` (`OnBidClosed`).
- Order: `OrderOpen → OrderActive` (`OnOrderMatched`) → closed.
- Lease: `LeaseActive → LeaseClosed`, with a typed `LeaseClosedReason`.

Message surface (`x/market/handler/server.go`): `CreateBid`, `CloseBid`, `CreateLease`, `CloseLease`, `WithdrawLease`, `LeaseStartReclaim`, `UpdateParams`.

`CreateBid` (keeper.go:213) stores `{ID, State: BidOpen, Price: DecCoin, CreatedAt: BlockHeight, ResourcesOffer, ReclamationWindow}` and emits `EventBidCreated`. `CreateLease` (keeper.go:252) is explicitly commented **"Should only be called by the EndBlock handler or unit tests"** — i.e. the auction does not settle when a bid arrives; it settles at a **block boundary**, atomically, having seen every bid submitted during the window. Losing bids are transitioned to `BidLost` in the same sweep.

**This is the single most reusable idea in Akash for us: batch the auction to a tick, not to arrival order.** A continuous first-come-first-served matcher on a phone fleet would systematically award work to whichever devices happen to be awake and fast to respond, which is the opposite of what a charge-time fleet wants. A tick-based sealed window lets a scheduler consider *all* currently-eligible devices — including data locality — and pick the best assignment, not the first.

Also present and relevant: `ReclamationWindow` on a bid and `LeaseStartReclaim` — an explicit protocol for reclaiming resources from a lease that has gone quiet, with a typed close reason. A phone fleet needs exactly this, because devices vanish constantly and silently.

`x/escrow` holds the payment account per deployment and drains it per block over the lease; `x/take` is the network fee cut; `x/audit` and `x/cert` are the provider-attestation story (auditors sign provider attributes, requestors filter on `signedBy`) — a useful precedent for our device attestation being a *signed attribute another party vouches for*, rather than something the device asserts about itself.

## 5. Verdict for the mission
Docs-level reading was sufficient, as the mission allowed, and two ideas justify the visit: **the four-section manifest separation** (workload / size / placement+price / count) and **the block-boundary sealed auction**. Both are directly applicable, both are Apache-2.0, and neither requires taking on a Cosmos chain. The rest — CosmWasm, escrow-per-block, the take rate — assumes an L1 we are not going to run.
