# REPORT: DAS (Distributed Atomspace)

## 1. Identity
- URL: https://github.com/singnet/das
- Commit: `f9c6aca54b35582cdc97f4bcede9e2bd5b829a2a` (2026-08-13)
- License: **Apache-2.0** (`LICENSE` + a `NOTICE` file). Gate: **PORT allowed with attribution + NOTICE entry.**
- Companion repo (submodule): `singnet/das-proto`, also **Apache-2.0** — cloned separately as `elders/das-proto`, because the two `proto/` submodule paths in the DAS tree are empty gitlinks.

## 2. Shape
- 717 tracked files. **C++ 192 `.cc` + 160 `.h` (≈14,400 header LOC)**, Python 50 / 6,035, Rust 25 / 4,090 (the `metta-bus-client` used by hyperon), 49 shell.
- Build: **Bazel** (`MODULE.bazel`, per-directory `BUILD` files) wrapped in a top-level `Makefile`; everything is built and run inside Docker (`src/docker/`).

| dir (`src/`) | role |
|---|---|
| `agents/` | `query_engine`, `link_creation_agent`, `evolution`, `context_broker`, `atomdb_broker`, `command_router` |
| `attention_broker/` | Hebbian network, stimulus spreading, importance/rent economy |
| `atomdb/` | the storage abstraction + backends: `redis_mongodb`, `inmemorydb`, **`morkdb`**, `remotedb`, `adapterdb` |
| `db_adapter/` | bulk load/persist: `AtomPersister`, `ContextLoader`, `DatabaseMapper`, `DatabaseOrchestrator` |
| `service_bus/` | `ServiceBus`, `BusCommandProcessor`, `BusCommandProxy`, `PortPool` |
| `distributed_algorithm_node/` | `StarNode`, `BusNode`, `MessageBroker`, `LeadershipBroker` |
| `main/` | one binary per role: `attention_broker_main.cc`, `bus_node.cc`, `db_loader.cc`, … |
| `3rd_party_slots/` | `rust_metta_bus_client`, `python_client` (each with an empty `proto/` gitlink) |

## 3. Entry points
`src/main/*.cc` — one `main` per service. `attention_broker_main.cc` listens on **:40001** by default; query agents register a `BusCommandProcessor` with a `ServiceBus` and are addressed by command name.

## 4. Extraction targets

### 4.1 Protobuf service definitions — smaller than expected
All of `elders/das-proto`, 4 files, **161 lines total**:

- `common.proto`: `Empty`, `Ack{error, msg}`.
- `attention_broker.proto` — service `AttentionBroker`: `ping`, **`stimulate(HandleCount)`**, `correlate(HandleList)`, `asymmetric_correlate(HandleList)`, **`get_importance(HandleList) → ImportanceList`**, `set_determiners(HandleListList)`, **`set_parameters(Parameters{rent_rate, spreading_rate_lowerbound, spreading_rate_upperbound})`**, `save_context`/`drop_and_load_context(ContextPersistence{context, file_name})`.
- `distributed_algorithm_node.proto` — service `DistributedAlgorithmNode`: `ping`, `execute_message(MessageData{command, args[], sender, is_broadcast, visited_recipients[]})`.
- `echo.proto` — a health-check toy.

**The important negative finding:** there is no typed RPC schema for queries. The inter-node protocol is `MessageData{command: string, args: [string]}` — a **stringly-typed command bus**. `ServiceBus.h` names the commands as static strings: `PATTERN_MATCHING_QUERY`, `QUERY_EVOLUTION`, `LINK_CREATION`, `CONTEXT`, `ATOMDB`, `BUS_COMMAND_ROUTER`. Good news for us: adding a `HYPERJOB` command is a one-line registration, no schema negotiation. Bad news: no versioning, no wire-level type safety, and nothing to generate clients from.

### 4.2 The agents and their responsibilities
| agent | files | responsibility |
|---|---|---|
| **query_engine** | `PatternMatchingQueryProcessor`, `QueryAnswer`, `QueryNode`, `MettaParserActions`, `query_element/` | executes pattern-matching queries as a tree of query elements; parses MeTTa-syntax patterns directly |
| **link_creation_agent** | `LinkCreationProcessor`, `link_creators/{LinkCreator.h, LinkCreatorRegistry}` | a **registry of pluggable link creators** — the graph *grows itself* by rule |
| **evolution** | `QueryEvolutionProcessor`, `fitness_functions/{FitnessFunction.h, MultiplyStrengthFunction, InferenceToyFunction, CountLetterFunction}` | evolutionary search over query results, scored by a **pluggable fitness function registry** |
| **context_broker** | `ContextBrokerProcessor` | named contexts — the unit the attention economy is scoped to |
| **atomdb_broker** | | serves AtomDB operations over the bus, so a node without local storage can still query |
| **command_router** | | routes bus commands, incl. an HTTP API (`tests/cpp/command_router_http_api_test.cc`) |

Both the link creators and the fitness functions are **registries**, i.e. the extension points are already there. Our "growth agents" and "shaping jobs" do not need new machinery in DAS — they need entries in these registries.

### 4.3 DB adapter boundary — what a shard host minimally needs
`src/atomdb/AtomDB.h` is a pure-virtual interface, ~40 methods, grouped:
- **Read**: `get_atom/get_node/get_link(handle)`, `get_matching_atoms(is_toplevel, key)`, `query_for_pattern(LinkSchema) → HandleSet`, `query_for_targets(handle) → HandleList`, `query_for_incoming_set(handle) → HandleSet`.
- **Existence**: `atom_exists`, `node_exists`, `link_exists`, and batch `atoms_exist/nodes_exist/links_exist(vector<handle>) → set<handle>`.
- **Write**: `add_atom/add_node/add_link(atom, Merger*)`, batch `add_atoms/add_nodes/add_links`, `delete_*` with `delete_link_targets`.
- **Maintenance**: `re_index_patterns(flush_patterns)`, `node_count/link_count/atom_count`, capability flags `allow_nested_indexing()`, `composite_type_enabled()`.

Backends shipped: `redis_mongodb` (the production one), `inmemorydb`, **`morkdb`** (`MorkDB.cc/.h`, `MorkDBAPITypes`), `remotedb`, `adapterdb`. **The MORK-backed AtomDB already exists**, which means the "MORK as the shard engine behind DAS" integration is not hypothetical.

For our purposes, a phone-side shard cache implementing the *read* subset plus `atoms_exist` is enough to serve queries; writes can be refused. That is a much smaller surface than the full interface suggests.

### 4.4 Attention broker logic — an economy, and we should read it as one
`attention_broker/{HebbianNetwork,StimulusSpreader,HebbianNetworkUpdater,RequestSelector}.{cc,h}`.
- Importance is a `double` per atom per **context**, held in a `HandleTrie`.
- Each cycle (`StimulusSpreader.cc:50-98`): **collect rent** — every node pays `rent_rate × importance`; then `consolidate_rent_and_wages` subtracts rent, adds wages, and computes what to spread: `spreading_rate = lowerbound + range × arity_ratio`, `to_spread = importance × spreading_rate`, deducted from the node and delivered to neighbours (`deliver_stimulus`).
- The Hebbian network itself has `Node` and `Edge` types with `merge()` semantics and `add_symmetric_edge`; edges accumulate co-occurrence counts from queries. It is `Serializable` and can be saved/loaded per context (`save_context`).
- The README states the purpose plainly: *"DAS query engine can use those importance values to control caching policies and to better process pattern matcher queries."*

**This is the attention-driven replication policy the mission asks for, already implemented and already exposed over gRPC.** `get_importance(HandleList) → ImportanceList` is exactly the input a replication scheduler needs: replicate the shards holding high-importance atoms to more devices, evict cold ones. We do not need to build this; we need to *consume* it — and to feed it, because `stimulate()` is how a device tells the network which atoms its jobs actually touched. Note the arity-weighted spreading rate: high-arity atoms spread more, so importance concentrates on hubs, which is exactly where locality-aware layout pays off most.

## 5. Notes and risks
- **Everything runs in Docker and builds with Bazel.** There is no supported path to a native macOS build, and the phone-side story is not a port of DAS but a small client that speaks its bus.
- Rust client `metta-bus-client` (in `3rd_party_slots/`) is what hyperon's `das` feature consumes; it **cross-compiles for Android already** (verified in S2), so a phone can speak the DAS protocol today if we want it to.
- The empty `proto/` submodules mean a naive `git clone` of DAS yields a tree that cannot build. Anyone reproducing this must clone `singnet/das-proto` too.

## 6. Verdict for the mission
The knowledge layer is in better shape than the mission assumed: Apache-2.0, a MORK-backed store already written, extension registries for exactly the growth-agent and shaping behaviours we want, and an attention economy that already produces the per-atom importance signal our replication policy needs. The weak point is the wire protocol — a stringly-typed command bus with a 161-line proto file — which is simultaneously the reason integration is easy and the reason it will be fragile.
