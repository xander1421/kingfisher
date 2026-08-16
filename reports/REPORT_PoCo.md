# REPORT: iExec PoCo (Proof of Contribution)

## 1. Identity
- URL: https://github.com/iExecBlockchainComputing/PoCo
- Commit: `fd0c823e03f2fb359420bf0fc9bf18039b7d100d` (2026-01-28)
- License: **Apache-2.0**, © 2020-2023 iExec Blockchain Tech. Gate: **PORT allowed with attribution** — though "porting" Solidity into our stack means porting the *mechanism*, not the bytecode.
- Also published as the npm package `@iexec/poco`.

## 2. Shape
72 Solidity files, 54 TypeScript (tests + deploy), 208 JSON (ABIs and deployment artefacts), 10 markdown. Build: Hardhat (`hardhat.config.ts`), Slither config present, and an `audits/` directory — this is audited production code on mainnet.

Architecture is **EIP-2535 Diamond** (`contracts/Diamond.sol` + `contracts/facets/*`):
| facet | role |
|---|---|
| `IexecPoco1Facet` | order matching → creates a **Deal** |
| **`IexecPoco2Facet`** | **contribute → reveal → finalize; the whole consensus and reward machinery** |
| `IexecPocoBoostFacet` | the fast path (single trusted contribution, no consensus) |
| `IexecEscrowNativeFacet` / `IexecEscrowTokenFacet` | stake, lock, seize, reward |
| `IexecOrderManagementFacet` | order lifecycle |
| `IexecCategoryManagerFacet` | task size categories |
| libs | `IexecLibCore_v5` (Task, Deal, Contribution, Consensus structs), `IexecLibOrders_v5`, `PocoStorageLib` |

## 3. Contribution → consensus → finalization flow (`contracts/facets/IexecPoco2Facet.sol`)

**Phase 1 — `contribute(taskid, resultHash, resultSeal, enclaveChallenge, enclaveSign, authorizationSign)`** (line 106)
- Preconditions: task `ACTIVE`, before `contributionDeadline`, this worker has not contributed.
- **Authorization**: the scheduler (or the TEE broker, if the deal's tag requires an enclave) must have signed `(worker, taskid, enclaveChallenge)`. Workers cannot self-select into a task.
- **Optional enclave attestation**: if `enclaveChallenge != 0`, the enclave must have signed `(resultHash, resultSeal)`.
- The worker submits a **hash and a seal, not the result** — commit/reveal. The seal binds the result to *this worker* so a second worker cannot copy the first's hash off-chain and claim it.
- **`lock(worker, deal.workerStake)`** — the stake is escrowed at contribution time.

**Reputation-weighted vote counting** (the comment in-source literally reads `SCORE POLICY 1/3`, `k = 3`):
```solidity
uint256 weight = Math.max(m_workerScores[worker] / 3, 3) - 1;
uint256 group  = consensus.group[_resultHash];
uint256 delta  = Math.max(group, 1) * weight - group;
contribution.weight        = Math.log2(weight);
consensus.group[hash]     += delta;
consensus.total           += delta;
```
A vote's weight grows with the worker's score, and the group weight is *multiplicative*, not additive — the group total becomes the product of members' weights. Two mediocre workers agreeing is worth much less than one high-score worker plus one mediocre one.

**Phase 2 — `checkConsensus(taskid, consensus)`** (line 382). One line carries the whole trust model:
```solidity
if (consensus.group[_consensus] * trust > consensus.total * (trust - 1))
```
`trust` is a per-**Deal** parameter. Rearranged: accept when the winning group holds more than `(trust-1)/trust` of the total weight. `trust = 1` accepts anything; `trust = 100` demands 99 % of weight. **The requestor buys the confidence level they want, per job.** On success the task moves to `REVEALING`, `revealDeadline = now + timeref * REVEAL_DEADLINE_RATIO`, and `winnerCounter` is the count of contributors matching the consensus hash.

**Phase 3 — `reveal(taskid, resultDigest)`** (line 262). The worker now discloses the digest; `require(contribution.resultHash == task.consensusValue)`. Only consensus members may reveal.

**Phase 4 — `finalize`** and reward distribution:
- Winners: rewarded, stake unlocked, **`m_workerScores[worker] += 1`** (`SCORE POLICY 2/3`).
- Losers *and* non-revealers: **`seize(worker, deal.workerStake)`** and **`m_workerScores[worker] = score * 2/3`** (`SCORE POLICY 3/3`). Score decay is multiplicative, gain is additive — reputation is slow to earn and fast to lose, by design.
- The scheduler (workerpool owner) takes a share of `totalReward`.
- `contributeAndFinalize` is the single-contributor fast path: `winnerCounter = 1`, `consensus.total = 1`, no voting — used when the deal's trust is 1 or a TEE is doing the trusting.

## 4. On-chain vs off-chain
**On-chain**: orders and their matching into Deals, the task state machine (`ACTIVE → REVEALING → COMPLETED/FAILED`), every `contribute`/`reveal`/`finalize` call, all stake accounting (`lock`/`seize`/`reward`), worker scores, and the consensus arithmetic. Deadlines are `block.timestamp`-based.
**Off-chain**: the computation itself, the result payload (only hash+seal go on chain), result storage/retrieval, the scheduler's decision about which workers to authorize, and enclave attestation generation.

## 5. What we take, and what we must not
**Take:**
1. **`trust` as a per-job parameter, not a network constant.** Our `ReplicationPolicy` (S4) has a mode enum and a quorum count; PoCo shows the better generalisation — express the requestor's desired confidence as a single number and let the protocol decide how many contributions that needs. Worth folding into v1.
2. **Commit/reveal with a worker-bound seal.** Without it, replication is theatre: the second worker just echoes the first's hash. Neither BOINC nor NuNet has this, because both assume a trusted server sees results first. **Our design needs it and does not currently have it** — a gap this report surfaces and `out/PORT_PLAN.md` picks up.
3. **Asymmetric reputation** (+1 linear on success, ×2/3 on failure) and stake seizure on non-reveal.
4. Stake locked *at contribution time*, not at claim time.

**Do not take:** the assumption that consensus arithmetic must run on chain. Every `contribute` is a transaction; at phone-fleet volumes and micropayment sizes that is economically impossible. Our version keeps the *mechanism* (weighted quorum, staking, reputation) off-chain, in the coordinator, and settles only netted balances — which is exactly what NuNet's `tokenomics/` billing scheduler is shaped for.

## 6. Verdict for the mission
The most rigorous verification-economics design in the elder set, licence-clean, and the only one that models *purchased confidence*. Its cost model is incompatible with ours, so we lift the mechanism into an off-chain coordinator and keep only settlement on chain.
