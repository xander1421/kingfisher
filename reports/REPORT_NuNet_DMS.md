# REPORT: NuNet Device Management Service (DMS)

## 1. Identity
- URL: https://gitlab.com/nunet/device-management-service
- Commit: `9f75a0bf72abf1c87016bad4b789a7fb0cb00f46` (2026-07-20)
- License: **Apache-2.0** (`LICENSE`, plus a per-file Apache header — `copyright.txt` and a `lint-license` make target enforce it). SPDX: Apache-2.0. Gate: **PORT allowed with attribution + NOTICE**.
- Go module `gitlab.com/nunet/device-management-service`, **go 1.26.3**.

## 2. Shape
- 669 Go files, **164,969 LOC** — by far the largest permissively-licensed elder. Plus 67 `.md`, 44 PlantUML `.puml` specs, 26 Gherkin `.feature` acceptance tests, 6 `.proto` (388 lines, all PRISM/Identus DID related).

| dir | role |
|---|---|
| `actor/` | **NuActor** — the secure actor framework (dispatch, handle, limiter, capability check at dispatch) |
| `dms/` | the service: `jobs/` (ensembles), `orchestrator/` (bid, commit, deployments store, manifest diff), `onboarding/`, `node/`, `resources/`, `behaviors/` |
| `executor/` | `docker/`, `containerd/`, `null/`, `specs/` — pluggable execution backends |
| `types/` | the whole vocabulary: `capability.go` (894), `hardware.go` (579), `executor.go` (283), `allocation.go` (231), `resources.go` (185), `comparator.go` |
| `lib/` | `ucan/` (4,793 LOC), `did/`, `crypto/`, `hardware/` (cpu, gpu, ram, disk) |
| `network/` | `libp2p/` + `vnet` |
| `tokenomics/` | contracts, payment processors, pricing oracle, billing scheduler/trigger |
| `prism/`, `identus/` | PRISM (Cardano) DID integration, NeoPRISM interop |
| `api/`, `gateway/`, `cmd/`, `client/` | REST (gin) surface and CLI |

## 3. Entry points
- `main.go` → `cmd/` (cobra-style CLI). Notable command group `cmd/cap/` — `new`, `grant`, `delegate`, `revoke`, `anchor`, `broadcast`, `list`: the capability lifecycle is a first-class CLI concern.
- Node lifecycle: `dms/dms.go`, `dms/node/`, onboarding via `dms/onboarding/onboarding.go` (`Onboard`, `Offboard`, `IsOnboarded`, `Info`).
- Packaging: `maint-scripts/nunet-dms/{DEBIAN,etc,usr}` — a **Debian package with a systemd unit**.

## 4. Extraction targets

### 4.1 Job / deployment manifest schema — `EnsembleConfig`
Documented in `dms/jobs/ensemble.md`, sample at `dms/jobs/sample/ensemble.yaml`, parser in `dms/jobs/parser/`. Versioned (`version: "V1"`). Three top-level concepts:

- **`allocations`** (named): `executor` (docker|firecracker|…), `resources` {cpu{cores,clockspeed,model,vendor,threads,architecture,cachesize}, gpus[{vendor,model,vram}], ram{size,clockspeed,type}, disk{size,model,vendor,type,interface,readspeed,writespeed}}, `execution` {type,cmd,entrypoint,environment,image,working_directory}, `dnsname`, `keys`, `provision[]`, `healthcheck`, `failure_recovery` (stay_down|one_for_one|one_for_all|rest_for_one), `depends_on[]`.
- **`nodes`** (named): `allocations[]`, `redundancy` (integer!), `failure_recovery` (stay_down|restart|redeploy), `ports{public,private,allocation}`, `location{accept[{region,country,city,asn,isp}],reject[]}`, `peer` (pin to a peer ID).
- **`edge_constraints`**: per-edge `rtt`, `bw`, `symetric` [sic]. Plus an Erlang-style `supervisor` tree (OneForOne | AllForOne | RestForOne) and named `keys`/`scripts`.

**Fit with our hyperjob tuple** `(shard_cid, metta_program, fuel_limit, seed, replication_policy)`:
| ours | theirs | verdict |
|---|---|---|
| `replication_policy` | `nodes.<n>.redundancy` + `supervisor.strategy` | already there, integer-only; needs "N-of-M must agree" semantics |
| `metta_program` | `execution.cmd` / `image` | needs a new `execution.type: metta` |
| `shard_cid` | — | **missing**: no content-addressed input concept at all; inputs are container images and volumes |
| `fuel_limit` | `resources.cpu.cores` + time-based billing | **missing**: no deterministic work unit, only wall-clock and hardware |
| `seed` | — | **missing** |
| locality/data-affinity matching | `location{region,country,city,asn,isp}` + `edge_constraints{rtt,bw}` | **network** locality exists; **data** locality does not |
The manifest is the right *shape* to extend — `version: "V1"` and named maps make additive extension natural. Per §10.5 our schema should mirror these names (`allocations`, `redundancy`, `failure_recovery`) rather than invent parallel ones.

### 4.2 Actor & capability model (DID / UCAN)
`actor/README.md` is the design doc; `lib/ucan/token.go` (886 LOC) + `lib/ucan/{cap,context,store}.go` the implementation; `cmd/cap/*` the operator surface.
- Zero-trust: **every message carries capability tokens and is checked at dispatch** (`actor/dispatch.go`), not at connection setup.
- Capabilities are a **hierarchical UNIX-like namespace** — root `/` implies everything; `/A` implies `/A/B`; `/A` does not imply `/B`. Behaviors are named in that namespace.
- Identity is a **DID**; anyone can issue tokens and anchor trust anywhere; no central authority; trust is revocable and ephemeral. `TrustContext` holds providers (signers) and anchors (verifying keys).
- Two DID methods interop: `did:key` and `did:prism` (Cardano, via Hyperledger Identus **NeoPRISM 0.9.1**, W3C resolution at `/api/dids/{did}`) — see `prism/PRISM_UCAN_DOCUMENTATION.md`.
- `actor/limiter.go` gives per-actor rate limiting.
**This is the single most valuable portable asset in the elder set for us**: a working, Apache-2.0, DID-anchored capability system. Our device attestation (Play Integrity / Secure Enclave) slots in as *another anchor* — an attestation becomes a capability token from a marginally-trusted issuer, exactly the "KYC vetting entity" role the README already describes. No new trust model needed.

### 4.3 Executor interface — what a "metta runtime" must implement
`types/executor.go`. 20 methods: `GetID, Start, Run, Pause, Resume, Wait, Cancel, Remove, Cleanup, GetLogStream, List, GetStatus, WaitForStatus, Exec, Stats, GetInfo, GetNetInfo` (+ more). Container-shaped: `Exec(ctx, containerID, cmd)`, `GetNetInfo` returning interfaces and port mappings, log streams.
**`executor/null/executor.go` is the proof that a non-container executor is allowed** — it is a complete no-op implementation of the interface, ~150 LOC. A `executor/metta/` would be the same skeleton with `Run` driving `interpret_step` over `libhyperonc`, `Stats` reporting fuel instead of CPU%, and `Pause`/`Resume` genuinely implementable (unlike containers) because the interpreter is stepwise. The interface is wider than we need but not hostile.

### 4.4 Onboarding flow
`dms/onboarding/onboarding.go`: `populateOnboardingConfig` → `validatePrerequisites` → `Onboard`. Prerequisites are: `Hardware.GetMachineResources()` must be ≥ the resources being onboarded (`validateCapacity`, `ErrUnmetCapacity`), and `Hardware.GetFreeResources()` must show enough headroom right now (`validateUsage`, `ErrHighUsage`). Resources onboarded are a **static reservation** — CPU cores, RAM GB, GPU VRAM, disk.

### 4.5 Settlement hook points
`tokenomics/`: `contract_host.go`, `billing_scheduler.go`, `billing_trigger.go`, `contracts/payment_processor.go`, `contracts/payments.go`, `pricing/oracle.go` + `pricing/converter.go`.
- `PaymentType`: `fiat` | `blockchain`. `PaymentModel`: `pay_per_allocation`, `pay_per_deployment`, `pay_per_time_utilization`, `pay_per_resource_utilization`, `fixed_rental`, `periodic`.
- **Every payment model is time- or resource-metered. There is no "pay per verified result".** For a fleet of untrusted phones that is the wrong unit — paying for wall-clock on a device you cannot audit is exactly the attack surface replication was supposed to close. We need a seventh model, `pay_per_verified_result`, keyed to the result envelope. `payment_processor.go` + `processors/*.go` show the extension shape: one file per model implementing a common processor interface.

### 4.6 **What blocks an Android port** (a key mission output)
Verified against the tree, not assumed:

| # | blocker | evidence | severity |
|---|---|---|---|
| 1 | **No Android build target.** Matrix in `Makefile:31` is Linux{amd64,arm64,arm32v6l,arm32v7l} and Darwin{arm64,amd64}. Nothing sets `GOOS=android`. | `Makefile` `all:` / `dist-linux:` | M — Go supports `GOOS=android` but it requires cgo + NDK, and cgo deps (gopsutil, go-nvml) must all cross-build |
| 2 | **Packaging assumes a daemon.** `.deb` + systemd unit under `maint-scripts/nunet-dms/{DEBIAN,etc,usr}`. Android has no systemd and kills background processes; a DMS must become a bound `Service`/`WorkManager` worker with no persistent process guarantee. | packaging tree | **H — architectural** |
| 3 | **No executor can run on stock Android.** docker and containerd both need a root daemon; firecracker needs KVM. Only `null` remains. | `executor/` | **H — this is precisely our opening** |
| 4 | **Root/privileged operations.** `network/libp2p/subnet_linux.go`, `utils/sys/net_linux.go`, `install-kata-and-cni.sh`, and a `setcapstorage` make target (`setcap`). Unrooted Android permits none of this. | build-tagged files + Makefile | H for subnets; the rest is optional |
| 5 | **Hardware detection is desktop-shaped.** `gopsutil/v4` + `go-nvml`/amdsmi/xpum. Android restricts `/proc` visibility (API 26+), so `GetFreeResources()` will misreport, and `validateUsage` will make bad admit/reject decisions. | `lib/hardware/*`, `dms/onboarding` | H — silently wrong, worse than failing |
| 6 | **The resource model has no power/thermal dimension at all.** `types/capability.go`, `types/hardware.go`, `types/resources.go` model CPU/RAM/GPU/disk/`Connectivity{Ports,VPN}`. There is no battery, no charging state, no thermal headroom, no metered-network flag. Charge-time scheduling has nothing to bind to. | `types/` | **H — this is the schema gap our scheduler needs filled** |
| 7 | **Static resource reservation vs a phone's variable capacity.** Onboarding reserves a fixed slice once; a phone's usable slice changes minute to minute with thermal state, foreground app, and battery. | `dms/onboarding/onboarding.go` | H — needs a dynamic/renegotiable allocation |
| 8 | **No NPU/accelerator concept.** GPUs are enumerated by vendor/model/VRAM via NVML/AMD-SMI/XPUM. There is no Core ML, no NNAPI/LiteRT, no TOPS or quantisation capability. | `lib/hardware/gpu/` | M — additive to `types/capability.go` |
| 9 | libp2p under Doze/App Standby: connections drop, inbound dialing is unreliable behind CGNAT. Not a code blocker; a protocol assumption blocker (a phone is a client, never a server). | `network/libp2p/` | M |

Zero occurrences of `android` in any `.go` file. The port is unbroken ground.

## 5. Verdict for the mission
This is the right coordination layer to extend, and the licence permits it. Three of the four things we need — DID/UCAN capabilities, a versioned deployment manifest with redundancy and locality, a pluggable executor interface with a working no-op reference — exist and are usable as-is. The fourth, a device model that knows about batteries and NPUs and a payment model that pays for verified results rather than elapsed time, is missing entirely, and that absence is the wedge: it is additive to their type system, not a fork of it.
