# S8 — stand DAS up locally and run one query end to end

**Verdict: GREEN for DAS itself, YELLOW for the phone-relevant path.** A full local Atomspace was deployed, loaded, and queried successfully. The one thing that did *not* work — driving it from the MeTTa REPL on the host — failed for a reason that matters more than the spike did: **DAS's service bus requires the agent to dial back to the client.**

## What ran

Docker was not running at the start of the session (`Cannot connect to the Docker daemon`); `colima start --cpu 4 --memory 8` brought up a Linux VM (Docker 29.5.2, Ubuntu 24.04).

```
das-cli config set                     # defaults, then one hand-patch (below)
das-cli database start                 # redis :40020, mongodb :40021
das-cli attention-broker start         # :40001
das-cli query-agent start              # :40002
das-cli metta load .../animals.metta   # syntax check + load, exit 0
```
Containers: `das-cli-redis-40020`, `das-cli-mongodb-40021`, `das-attention-broker-40001`, `das-query-engine-40002` (image `trueagi/das:1.2.0-rc`, all `--network host`).

Query, executed with the image's own `busclient` inside the VM:
```
busclient --client=query-engine --config=~/.das/config.json \
          --query='(Similarity "human" $S)' --context=default \
          --use-metta-as-query-tokens=true --populate-metta-mapping=true
```
```
Received answer: QueryAnswer<1,1> [[(Similarity "human" "monkey")]] {(S: "monkey")}
Received answer: QueryAnswer<1,1> [[(Similarity "human" "chimp")]]  {(S: "chimp")}
Received answer: QueryAnswer<1,1> [[(Similarity "human" "ent")]]    {(S: "ent")}
```
Three correct answers — the exact result the hyperon `das` module's docstring advertises (`lib/src/metta/runner/builtin_mods/das.rs`). Saved as `query_output.log`.

## Two friction points worth recording

**1. `das-cli` config schema drift.** `das-cli database start` refused to run:
```
[ValueError] Your configuration file doesn't have all the entries this version
of das-cli requires. Missing entry: 'agents.command_router.http_api'.
```
even though `das-cli config set` had just been run and had never prompted for it. The defaults exist in `das-cli/src/common/config/core.py:163-175` but the interactive prompt never asks for them, so a fresh install cannot produce a valid config. Worked around by writing the block into `~/.das/config.json` by hand.

**2. Docker socket discovery.** The `docker` CLI used the `colima` context, but das-cli's Python docker SDK went to `/var/run/docker.sock`, which on this machine symlinks to a stopped Docker Desktop. Fixed with `DOCKER_HOST=unix://$HOME/.colima/default/docker.sock`. Any macOS contributor without Docker Desktop hits this.

## The finding that matters: the bus dials backwards

Driving the same query from the host's `metta-repl` (built in S1, `das` feature on):
```
> !(import! &self das)                                                    [()]
> !(bind! &das (new-das! (localhost:52000-52099) (localhost:40002)))      [()]
> !(match &das (Similarity "human" $S) ($S))
ERROR metta_bus_client::bus_node] Bus: no owner is defined for command <pattern_matching_query>
[]
```
The query agent's own log shows it *did* take ownership and *did* see us arrive:
```
BUS node 0.0.0.0:40002 is taking ownership of command pattern_matching_query
New element localhost:52000 joined the service BUS
```
So the client→agent direction works. The failure is the reverse: the agent answers by **connecting out to the client's advertised endpoint** (`localhost:52000`), and the agent lives in the colima VM where `localhost` is the VM, not macOS. Every DAS participant is a *peer* that must be dialable, not a client.

**This is the same constraint as NuNet blocker #9, arrived at independently, and it is decisive for the architecture:**
- A phone can never be a DAS bus peer. It is behind CGNAT, it sleeps, and Android will not let it hold a listening socket in the background (see `spikes/S6_scheduler/SCHEDULER_SPEC.md` §4).
- Therefore the device agent must talk to a **desktop shard host that fronts the bus**, over a phone-initiated, request/response transport. The phone pulls jobs and pushes envelopes; it never gets dialled.
- This also independently justifies dropping the `das` cargo feature from the phone build (S1: 2.4 MiB / 40 % of `libhyperonc`). We were going to drop it for size; we must drop it for topology.

## Cleanup
All four DAS containers stopped (`das-cli {query-agent,attention-broker,database} stop`). The colima VM was left running because pre-existing unrelated containers on this machine came up with it; `colima stop` will shut everything down. Logged in `DECISIONS.log`.
