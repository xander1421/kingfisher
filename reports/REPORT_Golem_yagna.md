# REPORT: Golem / Yagna

## 0. Manifest correction (mission §5 URL is dead)
`https://github.com/golemfactory/yagna` returns **404 — Repository not found**. `golemfactory/golem` still exists but is a 2021 stub whose README points *back* at the 404'd yagna repo (last commit `274d7cd2`, 2021-03-09). A GitHub search finds no public fork or mirror of the monorepo. **The Yagna implementation is no longer publicly available.**

Substituted, per the mission's URL-resolution rule, with the three surviving repos that carry the actual extraction targets (logged in `DECISIONS.log`):

| repo | commit | licence | what it carries |
|---|---|---|---|
| `golemfactory/ya-client` | `86b5900a` (2025-07-31) | **LGPL-3.0** | the complete REST/OpenAPI specification of the market, activity, payment, identity and net APIs |
| `golemfactory/ya-runtime-sdk` | `0395b0c7` (2023-01-19) | **GPL-3.0** | the Rust trait a runtime plugin must implement |
| `golemfactory/ya-runtime-vm` | `29113b22` (2024-10-30) | **GPL-2.0** | a real runtime implementation (VM/Docker-like) |

## 1. Licence gate — **copyleft, as the mission predicted**
GPL-3.0 / GPL-2.0 / LGPL-3.0. **No Golem code may enter our tree.** The specification documents (`specs/*.yaml`) are the useful part anyway, and an interface *shape* is not copyrightable in the way an implementation is — but we should express our own schema in our own words, which S4 does.

## 2. Shape
`ya-client`: 68 Rust files + **10 OpenAPI documents totalling 5,666 lines** (`market-api.yaml` 1,567; `payment-api.yaml` 1,605; `activity-api.yaml` 1,050; `net-api` 413+443; plus common/identity/gsb/version). `ya-runtime-sdk`: 18 Rust files, a `ya-runtime-sdk` crate + a derive macro crate. `ya-runtime-vm`: 13 Rust + 7 C + 6 headers.

## 3. Extraction targets

### 3.1 Demand / Offer negotiation protocol (`specs/market-api.yaml`)
The endpoint set is the protocol, and it is a **symmetric two-sided market**:
```
/scan  /scan/{sub}/events
/offers        /offers/{sub}   /offers/{sub}/events
/offers/{sub}/proposals/{id}   /offers/{sub}/proposals/{id}/reject
/offers/{sub}/propertyQuery/{queryId}
/demands       /demands/{sub}  /demands/{sub}/events
/demands/{sub}/proposals/{id}  /demands/{sub}/proposals/{id}/reject
/demands/{sub}/propertyQuery/{queryId}
/agreements    /agreements/{id}   /agreementEvents
/agreements/{id}/{cancel,confirm,wait,approve,reject,terminate}
/agreements/{id}/terminate/reason
```
Requestors publish **Demands**, providers publish **Offers**; both are subscriptions with event streams; matching produces **Proposals** which either side may counter or reject; an accepted proposal becomes an **Agreement** with an explicit confirm/approve/reject/terminate lifecycle and a termination *reason*.

`DemandOfferBase` has exactly two required fields: **`properties`** and **`constraints`**. Properties are a *flat* JSON object keyed by dotted namespaced names, e.g.
```json
{ "golem.com.pricing.model": "linear",
  "golem.com.pricing.model.linear.coeffs": [0.001, 0.002, 0.0],
  "golem.com.scheme": "payu",
  "golem.com.scheme.payu.interval_sec": 6.0,
  "golem.com.usage.vector": ["golem.usage.duration_sec", "golem.usage.cpu_sec"],
  "golem.inf.cpu.architecture": "x86_64", "golem.inf.cpu.cores": 4,
  "golem.inf.mem.gib": 10.61, "golem.inf.storage.gib": 81.72 }
```
and `constraints` is a filter expression over the *other* side's properties.

**Three things here are directly instructive for our marketplace:**
1. **An open property namespace beats a fixed schema.** NuNet's `types/capability.go` is a closed Go struct — adding "has an INT8 NPU" or "holds shard bafy…" means changing their types. Golem's flat namespaced bag means a new capability is a new *string*. Our `DevicePreferences` (S4) is closed like NuNet's; we should keep the struct for the fields that matter to matching *today* and add a `map<string,string> labels` escape hatch (S4 has one) so locality hints can evolve without a schema bump.
2. **`propertyQuery`** — during negotiation, either side can *ask the other* to resolve a dynamic property, and the response distinguishes resolved values from properties still being computed. That is a rare and genuinely good idea for us: "how long would this shard take on your device?" is a dynamic property a phone can only answer by looking at its own cache and thermal state.
3. **`golem.com.usage.vector`** — the *unit of billing is negotiated per agreement*, from a declared vector (`duration_sec`, `cpu_sec`). This is the hook NuNet lacks: we would negotiate `hyperjob.usage.fuel_steps` as the usage vector and price against it, instead of wall clock.

### 3.2 Payment channel flow (`specs/payment-api.yaml`, 1,605 lines)
Debit notes and invoices against an agreement, with the `payu` scheme paying at an `interval_sec` cadence as usage accrues, rather than at the end. Accepted/rejected/settled states per document. Not examined further — our settlement target is NuNet's NTX path, and Golem's is Ethereum/Polygon-specific.

### 3.3 ExeUnit / runtime plugin interface (`ya-runtime-sdk/src/runtime.rs:23`)
```rust
pub trait Runtime: RuntimeDef {
    const MODE: RuntimeMode = RuntimeMode::Server;
    fn deploy(&mut self, ctx: &mut Context<Self>) -> OutputResponse;
    fn start(&mut self, ctx: &mut Context<Self>) -> OutputResponse;
    fn stop(&mut self, ctx: &mut Context<Self>) -> EmptyResponse { /* default */ }
    fn run_command(&mut self, command: RunProcess, mode: RuntimeMode,
                   ctx: &mut Context<Self>) -> ProcessIdResponse;
    fn kill_command(&mut self, kill: KillProcess, ...) -> EmptyResponse;
    /* + offer(), test(), and output/event handling */
}
pub trait RuntimeDef { const NAME: &str; const VERSION: &str;
                       type Cli: CommandCli; type Conf: Serialize + Deserialize; }
```
Two execution modes: **Server** (long-lived, speaks the Runtime API to the ExeUnit Supervisor) and **Command** (one process per command). Lifecycle is `deploy → start → run_command* → stop`, plus a `test()` self-check and a runtime-supplied `offer()` that contributes properties into the market.

Compare with NuNet's `types.Executor` (20 methods, container-shaped): **Golem's plugin interface is 5 required methods and a config type**, and it explicitly expects the runtime to *declare its own market properties*. If we were choosing an integration target on interface quality alone, Golem's would win. The licence, the dead monorepo, and NuNet's live SingularityNET-ecosystem mainnet all point the other way.

The activity API (`specs/activity-api.yaml`) is what the supervisor exposes to the requestor: `/activity`, `/activity/{id}/exec` (submit a command batch), `/exec/{batchId}` (poll results), `/state`, **`/usage`**, `/command`, plus an `/encrypted` variant. `/usage` returning the negotiated usage vector is how billing stays honest.

## 4. Verdict for the mission
A cautionary tale and a design source, not a dependency. The market protocol's flat property namespace and negotiated usage vector are the two ideas worth carrying into our schema; the runtime trait is a model of how small a plugin interface can be. Everything is copyleft and the reference implementation has vanished from the public internet, which is itself an argument for §10.5's preference: build on the stack whose maintainers are still shipping.
