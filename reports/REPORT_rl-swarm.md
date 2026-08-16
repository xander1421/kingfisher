# REPORT: RL Swarm (Gensyn)

## 1. Identity
- URL: https://github.com/gensyn-ai/rl-swarm
- Commit: `9c95410b1ac0d0a6005513c276b6b84f6db13bcd` (2026-01-05)
- License: **MIT**, © 2025 Gensyn (`LICENSE.TXT`). Gate: **PORT allowed with attribution.**
- README states: *"There are no official swarms running right now."* The live Gensyn environment has moved to **CodeZero** on the Gensyn Testnet, powered by the same RL Swarm + [GenRL](https://github.com/gensyn-ai/genrl) stack.

## 2. Shape
31 Python files, 17 TypeScript (`modal-login`, `web`), Docker/compose, `run_rl_swarm.sh`, and a checked-in `technical_report.pdf`. Core: `hivemind_exp/{chain_utils,dht_utils,hivemind_utils,name_utils}.py` + `contracts/SwarmCoordinator_0.4.2.json` (an ABI, not source).

## 3. Coordination topology
A **round/stage state machine, coordinated on chain, with data exchanged over a Hivemind DHT.**

`hivemind_exp/chain_utils.py` — `SwarmCoordinator` (ABC) is the whole on-chain surface:
```python
register_peer(peer_id)
submit_winners(round_num, winners, peer_id)
submit_reward(round_num, stage_num, reward, peer_id)
get_bootnodes()                      # peer discovery, on chain
get_round_and_stage() -> (round, stage)   # batched call; the global clock
```
`WalletSwarmCoordinator` implements it with web3 transactions at a fixed 2,000,000 gas / 5 gwei.

`hivemind_exp/dht_utils.py` — everything bulky lives in the DHT under derived keys: `outputs_key(node_key, round, stage)`, `rewards_key(round, stage)`, `leaderboard_key(round, stage)`, plus `hash_keys(outputs)`. Nodes publish their outputs to the DHT and read peers' outputs from it.

`hivemind_exp/hivemind_utils.py` — per-node state: `round_num`, `stage_num`, a `round_cache` keyed by `(round, stage) → {question: (score, payload)}`, a `round_winner_fn`, `max_rounds = 100`, and **`round_timeout = 60*60*4`** (four hours).

So: **the chain is the clock and the registry; the DHT is the bulletin board; peers do the work and score each other; winners and rewards are written back on chain.** In CodeZero the roles are explicit — *Solvers*, *Proposers*, and *Evaluators*, with a frozen larger model (Qwen2.5-Coder-1.5B) as Evaluator.

## 4. Verde — pointers, and the honest answer
The mission asks for "any Verde implementation pointers". **There is no Verde implementation in this repository**, and no source-level reference to it: a case-insensitive grep for `verde` across all `.py` and `.md` files returns nothing. The verification story here is peer scoring inside the round/stage loop (`round_winner_fn`, `submit_winners`, `submit_reward`), i.e. Bittensor-shaped rung 3, not the referee-and-bisection protocol Verde describes. The Verde design lives in Gensyn's paper (arXiv) and, if implemented anywhere public, in the `genrl` repo or their testnet contracts — neither of which is in this manifest. Recorded as a gap in `BLOCKED.log` rather than filled in with a guess.

What *is* here that echoes Verde's assumptions: the four-hour `round_timeout` is the same order of magnitude as a challenge window, and `submit_winners` shows that the on-chain footprint of a dispute-resolution system can be tiny — one call per round, not one per result.

## 5. What transfers
1. **Split the coordinator: a cheap authoritative clock plus a cheap bulletin board.** Round/stage on chain (or, for us, in the coordinator), bulk payloads by content address in a DHT. Our design already separates `result_hash` from `result_cid`; this is the same instinct, and rl-swarm shows how little needs to be authoritative — a round number, a peer registry, and a winners list.
2. **Bootnodes fetched from the registry** (`get_bootnodes()`), not hardcoded. Small thing, avoids a class of ops pain.
3. **A generous round timeout is a feature, not sloppiness.** Four hours for a swarm of consumer GPUs; our charge-time phone fleet needs a window at least that long (S6: expect one multi-hour window per device per night).
4. **Roles beat symmetry.** CodeZero's Solver/Proposer/Evaluator split, with the Evaluator frozen and larger, is the shape our fleet already has by hardware: phones solve, desktops evaluate. Worth naming explicitly in the architecture rather than treating all devices as interchangeable.

## 6. Verdict for the mission
Small, MIT, and useful mainly as a worked example of "the least you can put on chain". Its verification is peer scoring, not the bisection protocol we want; the Verde design must be sourced from the paper (see `papers/`) rather than from this code.
