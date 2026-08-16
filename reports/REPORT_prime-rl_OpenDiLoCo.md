# REPORT: prime-rl and OpenDiLoCo (Prime Intellect)

## 1. Identity
| repo | commit | date | licence |
|---|---|---|---|
| `PrimeIntellect-ai/prime-rl` | `b8d9553c0fd9e5deade39b1757287808ed5767dc` | 2026-08-15 | **Apache-2.0** |
| `PrimeIntellect-ai/OpenDiLoCo` | `2d750e58a692ce1424d2a2366b2b3de1f42c9bf1` | 2025-01-13 | **Apache-2.0** |

Gate: both **PORT allowed with attribution**. OpenDiLoCo's README states plainly: *"OpenDiLoCo is no longer maintained"*, superseded by `PrimeIntellect-ai/prime`.

## 2. Shape
- **prime-rl**: 275 Python files. `src/prime_rl/{orchestrator,trainer,inference,transport,monitors,entrypoints,templates,utils}`. Entry points: `rl.py`, `sft.py`, `trainer.py`, `orchestrator.py`, `inference.py`, `env_server.py`. Docs: `overview/training/algorithms/inference/scaling/configuration/advanced.md`.
- **OpenDiLoCo**: 10 Python files, 2,111 LOC total; the algorithm is `open_diloco/hivemind_diloco.py` (738 LOC), built on Hivemind.

## 3. The async / low-communication pattern

### OpenDiLoCo (`hivemind_diloco.py`)
Two nested optimisation loops:
- **Inner loop**: each worker runs `num_inner_steps` ordinary local optimiser steps against its own data, communicating with nobody.
- **Outer loop**: after those steps, the difference between the worker's parameters and the last synchronised parameters is treated as a **pseudo-gradient**, all-reduced across peers, and applied by a shared **outer optimizer** (Nesterov in the paper). `DiLoCoOptimizer` (line 303), `DiLoCoGradAverager` (line 61), `DiLoCoStateAverager` (line 35).
- **`AllReduceStrategy`**: `WAIT_FOR_ALL` or `NO_WAIT` (line 340) — the fault-tolerance dial. `NO_WAIT` lets the round proceed without stragglers.
- Averaging happens **on CPU** (`opt_param is the param that will be all_reduce, it is suppose to be on cpu`, line 164) so communication does not block the accelerator.
- Progress is tracked as a **target batch size** across peers rather than a step count, so heterogeneous workers contribute unequal amounts to the same round (line 189).

Communication drops by the inner-step factor: sync every N local steps instead of every step.

### prime-rl
The evolution of the same idea, and the more instructive one for us because it is *fully asynchronous* rather than round-based:
- Roles are separate processes: **orchestrator** (dispatch, filtering, advantage computation), **trainer** (FSDP2), **inference** (vLLM). They exchange work over a pluggable `transport/` (`zmq.py` or `filesystem.py`, msgspec-msgpack encoded, `MicroBatchSender`/`MicroBatchReceiver` in `transport/base.py`).
- **Staleness is an explicit, bounded, measured quantity.** `orchestrator.max_off_policy_steps` (default **8**) — *"How many distinct policies may have contributed to one rollout before it's discarded"* (`docs/training.md:62`). Each rollout is **stamped with its true staleness including queue time** (`orchestrator.py:625`), not just in-flight time.
- Staleness is **corrected for, not just tolerated**: importance ratios from sampling logprobs, and a one-sided trust region in `trainer/rl/loss.py:203` "correcting trainer/inference mismatch and staleness".
- Staleness is **monitored**: `mismatch_kl/{all,env}/{mean,std,max}` — *"A sustained, growing mean is the early-warning sign for off-policy collapse"*.
- Versioned artefacts: rollouts from the live policy get **version-salted prefix caches** and age; rollouts from frozen models never go stale (`docs/algorithms.md:57`). Checkpoints are per-step directories written atomically (`orchestrator/ckpt.py`: `mkstemp` + `os.replace`).

### On `shardcast`
The mission asks to look for it. **No occurrence of `shardcast` in either repo** — it lives in the newer `PrimeIntellect-ai/prime` (and its own repo), which is not in the manifest and was not cloned. The weight-distribution mechanism visible here is Hivemind all-reduce (OpenDiLoCo) and orchestrator→trainer transports over ZMQ/filesystem (prime-rl). Logged as a gap rather than guessed at.

## 4. What transfers to a phone fleet
1. **Bounded, stamped, monitored staleness is the whole design.** Our shard replicas are the analogue of their model weights: a phone that wakes at 02:00 holds a shard snapshot that may be hours old. The transferable discipline is (a) put a **version on every shard**, (b) set an explicit **maximum acceptable staleness per job class**, (c) **stamp each result with the shard version it actually used** — which our `ResultEnvelope.shard_cid` already does implicitly, since a CID *is* a version — and (d) **monitor the drift**, not just cap it. `max_off_policy_steps = 8` is the shape of the knob we need.
2. **`AllReduceStrategy::NO_WAIT`.** Never block a round on the slowest participant. On a phone fleet, stragglers are not an edge case; they are the median.
3. **Do the coordination work off the accelerator.** Their CPU-side averaging maps to: never let shard sync contend with the NPU matmul for memory bandwidth, which S5 showed is the binding constraint (26 GOP/s cold vs 353 GOP/s warm on the same code).
4. **A pluggable transport with a filesystem implementation is a great test harness.** `transport/filesystem.py` lets the whole pipeline run without a network. We should copy that pattern for the device agent: the same code path, backed by a directory, is how you test a scheduler without twenty phones.

**What does not transfer:** everything about gradients. Their staleness is *tolerable* because SGD is robust to it; ours is not — a stale shard gives a *wrong answer*, not a slightly worse gradient. So we take the bookkeeping (versions, stamps, bounds, monitoring) and reject the tolerance.

## 5. Verdict for the mission
Apache-2.0, actively developed, and the best available reference for "coordinate untrusted, unreliable, geographically scattered workers without a barrier". Its contribution to our design is a discipline rather than a library: **version everything, stamp what was used, bound the staleness explicitly, and never wait for the slowest peer.**
