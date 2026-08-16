# S60 — what a bisection commitment costs, and why it cannot reach one step

**Verdict: AMBER. The commitment is affordable (11.6% throughput). But hyperon's public API cannot support step-level bisection — the observable state changes once per 825 steps, so a challenge narrows to an *interval*, not a step. That is a design constraint R-NEW's addendum did not know about.**

R-NEW recommends optimistic settlement with proof-on-challenge: bisect a disputed trace to one step, prove that step. Bisection requires the prover to commit to its state at arbitrary step *k*, and **every job pays that cost, disputed or not**. This prices it.

## Measured — 12 processes × 3 s each, median

| mode | steps/s | cost | commits |
|---|---|---|---|
| `plain` (control, no commitment) | 1,119,109 | — | 0 |
| `chain` — hash after **every** step | 886,744 | **1.26×, 20.8%** | 1 per step |
| `lazy` — hash only when results **changed** | 989,292 | **1.13×, 11.6%** | 1 per 825 steps |

Program: `c1_grounded_basic` from hyperon's own corpus, 5,796 steps per run. Commitment is a hash chain, `H_k = SHA256(H_{k-1} ‖ R_k)`.

## 1. The blocker: the observable state is 825× coarser than the step counter

```
5,796 steps/run,  7.0 state-changes/run  ->  one observable change every 825 steps
```

`RunnerState`'s entire public surface is `run_step()`, `is_complete()`, `current_results()`. **The interpreter's plan/stack is not public**, so a commitment can only cover accumulated results — and those change on roughly 1 step in 825.

Consequences for the proof-on-challenge design:

- **Bisection resolves to an interval of ~825 steps, not to one step.** Two honest-looking executions can share an identical commitment at step *k* while differing internally.
- Conversely, bisection is **cheaper than assumed**: ⌈log₂(7)⌉ = **3 probes**, not ⌈log₂(5796)⌉ = 13.
- The zkVM then proves an ~825-step interval rather than a single step. **That is still small** — this softens the blocker rather than killing it, but the design must be written knowing it proves an interval.

The alternative is patching hyperon to expose interpreter state, which turns a read-only dependency into a maintained fork. Not free, and worth pricing before choosing.

## 2. `chain` mode is a trap
Hashing after every step costs **20.8%** and buys nothing over `lazy`: 824 of every 825 hashes fold an *unchanged* string into the chain. Same resolution, double the cost. The naive implementation is the expensive one.

## 3. The cost is affordable, and it is a floor not an estimate
11.6% of throughput, paid by every job. That is a real tax but not a disqualifying one — and it is a **floor**, because this commits only to results. Any finer commitment costs more.

## 4. GUARDRAILS A1 validated on its own terms
Spread across 12 processes was **1.02×** here, against the **2.1×** process-scoped variance that wrecked S55/S56. The difference is that these are 3-second windows rather than 250 µs events. BOINC's rule — *time a fixed window and count work, never time a short event* (`cs_benchmark.cpp:77-81`) — is doing exactly what it was adopted for, one spike after adopting it.

## Caveats
- One program, one shape. The 825-step figure is a property of `c1_grounded_basic`; a program producing results steadily would commit far more often and cost more. **The ratio is workload-dependent and this is n=1.**
- macOS/aarch64 only; not run on device.
- SHA-256 via `sha2` with no hardware-acceleration feature flags checked. A device with SHA extensions would shift the `chain`/`lazy` gap.
- Commitment is over `to_string()` of atoms, which S58 showed can embed heap addresses (`GroundingSpace-0x…`) and is subject to `HashMap`-ordered variable naming. **A commitment built on this is unsound today for exactly the reasons in `proposed/hyperon-nondeterminism/`.** That must be fixed upstream before any of this ships.
