# REPORT: Bittensor (bittensor SDK + subtensor chain)

## 1. Identity
| repo | commit | date | licence |
|---|---|---|---|
| `opentensor/bittensor` | `84152b5dbcc3f87d63ae0e4be25433aa22d88700` | 2026-07-10 | **MIT** © 2025 The Opentensor Foundation / Yuma Rao |
| `opentensor/subtensor` | `1f090af85d1771c5d8ece1f0910576fbd129906e` | 2026-08-14 | **Apache-2.0** |

Gate: both permissive; **PORT allowed with attribution**. In practice we want the *mechanism*, not the code — it is inseparable from Substrate.

## 2. Shape
- `bittensor` (the client SDK): 264 Python files. `bittensor/core/`, `bittensor/utils/`, `extras/`. Wallet, axon/dendrite networking, metagraph, extrinsic construction.
- `subtensor` (the chain): 792 Rust, 680 MDX docs, 260 Python, 170 TS. A **Substrate** chain with pallets: `subtensor` (the big one), `admin-utils`, `alpha-assets`, `commitments`, `crowdloan`, `drand`, `limit-orders`, `proxy`, `shield`, `swap`, `transaction-fee`, `utility`.
- The consensus we care about: **`pallets/subtensor/src/epoch/run_epoch.rs` (1,694 LOC) + `epoch/math.rs` (1,594 LOC)**.

## 3. How validators score miners — Yuma Consensus (`run_epoch.rs:337-400`)
Per epoch, per subnet, in fixed-point (`substrate_fixed::I32F32`):

1. **Weights.** Each validator submits a weight vector over miners — its opinion of who is doing useful work. Weight-setting is the whole scoring interface; *what* a validator measures is subnet-specific and off-chain.
2. **Consensus = stake-weighted median.** `consensus = weighted_median_col(&active_stake, &weights, kappa)` where `kappa` is "consensus majority ratio, e.g. 51 %". For each miner, the consensus weight is the value at which stake-weighted opinion crosses κ.
3. **Clipping.** `inplace_col_clip(&mut clipped_weights, &consensus)` — every validator's weight for a miner is **clipped down to the consensus value**. A validator cannot inflate a miner above what the stake-weighted majority believes. This is the anti-collusion core: over-reporting buys nothing.
4. **Validator trust** = row sum of a validator's clipped weights — how much of its opinion survived clipping.
5. **Ranks / incentive.** `ranks = matmul(&clipped_weights, &active_stake)`, normalised into `incentive` — the miner's share of server emission.
6. **Bonds and dividends.** Validators accumulate **EMA bonds** toward miners (`compute_bonds`, `inplace_col_normalize`), with a `bonds_penalty` interpolating between raw and clipped weights. `dividends = row_sum(ema_bonds_norm × incentive) × active_stake`. Bonds reward validators who backed a miner *early*, before consensus formed — the mechanism that pays for honest discovery rather than herding.
7. Output per neuron (`EpochTerms`): `dividend`, `incentive`, `validator_emission`, `server_emission`, `stake_weight`, `consensus`, `validator_trust`, `new_validator_permit`, `bond`, `stake`, `active`.

## 4. Emission (docs level, as the mission allows)
Emission is minted per block into each subnet and split between `validator_emission` and `server_emission` according to the epoch terms above; stake determines voting power and dividend share; `new_validator_permit` gates who may set weights next epoch. `recently_registered` neurons are masked out of bonds so a fresh registration cannot instantly farm dividends. Alpha/TAO subnet token mechanics live in `pallets/alpha-assets` and `pallets/swap`.

## 5. What this is worth to us — rung 3, and only rung 3
Our verification ladder puts peer scoring last, for jobs with no ground truth. Bittensor is the reference design for that rung, and three of its ideas transfer cleanly:

1. **Clip every scorer's opinion to the stake-weighted median.** This is the entire defence against a validator who wants to overpay a friend. If we ever score shaping jobs or growth-agent output by peer opinion, this is the arithmetic to use. Cheap: one weighted median and one clip per round.
2. **Pay for early correct opinions via bonds.** Without it, rational scorers copy the consensus and the system learns nothing. With it, being early and right pays more than being safe. Directly relevant to scoring *shaping* quality, where "this layout will make future jobs cheaper" is a prediction, not a measurement.
3. **Mask the newly-registered.** Sybil defence that costs nothing.

**What does not transfer:** the assumption that scoring is the *primary* mechanism. Bittensor peer-scores because ML output has no ground truth. Our rungs 1 and 2 have exact ground truth (byte-identical MeTTa reduction; exact INT8 arithmetic), so peer scoring should be confined to the small set of jobs that genuinely lack it — and even shaping has an objective measure (block density before vs after), so rung 3's real domain may be almost empty. **That is a finding worth putting in the proposal**: our workload demotes the most expensive verification mechanism in the field to a corner case.

Also non-transferable: everything is per-epoch on a Substrate chain. Our equivalent must run off-chain in the coordinator (see `reports/REPORT_PoCo.md` §5 for the same conclusion reached from the other direction).

## 6. Verdict for the mission
Read for mechanism, cite in the design, copy no code. The clipped stake-weighted median is a two-line idea we should keep in our pocket; the rest is a chain we are not going to run for a rung we intend to rarely use.
