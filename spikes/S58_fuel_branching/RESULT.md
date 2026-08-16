# S58 — fuel under branching randomness, and the rule that makes nondeterministic jobs verifiable

**Verdict: GREEN, with a matched control that fires. Fuel does NOT survive branching randomness — but a job that pins its generator is byte-identical and fuel-identical across two ISAs and three platforms. The rule is mechanical and belongs in the job spec.**

S57 claimed *"fuel is deterministic even when output is not."* An attacker scoped it correctly: the one program measured (`test_gnd_conv`) never **branches** on the random value, so its control-flow graph is fixed and fuel *cannot* vary. That left the load-bearing question open, and it gates more than billing — **if two honest replicas of a nondeterministic job disagree on step count, rung-1 verification breaks too**, because rung 1 bisects over step counts.

## Measured — 12 runs each, aarch64-macOS

| program | fuel | output hash |
|---|---|---|
| `b1_nobranch` — random consumed, never branched (S57's shape) | **571, constant 12/12** | 4 distinct |
| `b2_branch` — random selects between arms of different cost | **954 / 2059 / 3164 / 4269** | varies |
| `b3_seeded` — same, with `(set-random-seed &rng 42)` | **1083 / 2188 / 3293 / 4398** | varies |
| `b4_seeded_gen` — draws via `(new-random-generator 42)` | **1948, constant** | **`16b0e4996b`, constant** |
| `b5_unseeded_gen` — identical to b4 but draws via `&rng` | **1467 / 2572 / 3677 / 4782** | varies |

The spacing is exactly **1105** in every varying case: `fuel = base + 1105 × (heads)`. Fuel is measuring real work, precisely.

## 1. Fuel does not survive branching randomness. S57's claim is now bounded.
`b2` varies 954→4269, a **4.5× swing on the same program**. Corrected statement:

> Fuel is invariant under grounded-atom nondeterminism **only when that nondeterminism does not reach control flow.** Where it does, fuel varies with the work actually performed — which is fuel behaving correctly, and which makes any unpinned nondeterministic job unbillable *and* unverifiable.

## 2. `set-random-seed` does not fix it, because `flip` is unseedable by construction
`b3` pins a seed and still varies. Reading the engine explains why —
`lib/src/metta/runner/builtin_mods/random.rs:186-188`:

```rust
// NOTE: flip is absent in Python intentionally for conversion testing
fn flip(_args: &[Atom]) -> Result<Vec<Atom>, ExecError> {
    Ok(vec![Atom::gnd(Bool(rand::random()))])
}
```

`flip` takes **no generator** and calls the global `rand::random()`. `set-random-seed` reseeds a *specific generator instance* (`:161-166`), which `flip` never consults. **`flip` cannot be made reproducible by any means available from MeTTa.**

`&rng` is no better: `:127-128` registers it as a token bound to `RandomGenerator::from_os_rng()` — OS entropy, fixed at module load, unpinnable. That is why `b5` varies.

## 3. The rule: pin the generator and the job is fully replicable, across ISAs
`random-int` and `random-float` take a generator as **argument 0**. Given one built by `(new-random-generator 42)`:

| platform | runs | fuel | raw_hash |
|---|---|---|---|
| aarch64-macOS | 12 | 1948 | `16b0e4996b` |
| x86_64-macOS (Rosetta) | 5 | 1948 | `16b0e4996b` |
| aarch64-Android | 5 | 1948 | `16b0e4996b` |

**22 runs, three platforms, two ISAs, one value.** And the control fires: `b5`, byte-identical except for the generator, varies on the device too (3677/3677/2572/2572/3677).

> **Spec rule.** A MeTTa job that draws randomness is replicable and fuel-auditable **if and only if every draw goes through an explicitly-seeded generator.** Therefore the job class must **ban `flip` and `&rng`**, and `hyperjob` must carry the seed as a declared field so a verifier can reproduce the run.

This converts nondeterministic workloads from unverifiable to verifiable at zero cost, and it is a *static* check — a validator can reject a program containing `flip` before scheduling it, no execution required. That is the cheapest possible enforcement point.

## Why this is a mechanism test, not the self-authored-data failure mode
`GUARDRAILS.md` records that every spike fitting a magnitude to data I wrote was retracted, while every spike using an elder's corpus survived. These five programs are self-authored — deliberately — but they **choose no magnitude**. Each asks a yes/no question with a predicted answer and ships a matched negative control (`b1` for b2, `b5` for b4) that differs by one token. The engine source then explains the result independently. That is the distinction: authoring an *instrument* is fine, authoring the *data that sets a constant* is what failed.

## Caveats
- The 1105-step arm cost is an artefact of my `(expensive)` definition and means nothing beyond confirming fuel tracks work.
- `random-float` untested; only `random-int` was exercised.
- Untested: whether two *different* seeds produce different-but-each-reproducible runs across ISAs — i.e. whether the RNG algorithm itself is ISA-stable for all seeds. One seed was tested. `RandomGenerator` wraps `StdRng`, whose algorithm is portable but is explicitly **not** guaranteed stable across `rand` crate versions — so the **rand version must be pinned in the job manifest alongside the seed.** Unverified.
