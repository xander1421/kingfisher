# PROPOSAL_DRAFT v2 — revised opening

Replaces the problem statement, evidence table, and wedge section of `PROPOSAL_DRAFT.md`. Written after four adversarial agents killed six of the original's numbers. **Every claim below is measured on at least two architectures, or it is not here.**

Provenance rule applied throughout: a number appears only if it survived an attack, and its killer is named where one exists.

---

## Verified distributed symbolic compute

### The problem

Every decentralised compute network has paid the same tax, and it is not a market-design tax — it is an arithmetic one. Floating-point addition is not associative, so the same program on two machines produces two different answers, and the network cannot tell a cheat from a rounding difference.

The bills are on record. Gensyn had to build **RepOps**, a library of bitwise-reproducible operators, before refereed delegation would work at all — *"hardware may provide different numerical results because floating point operations are not guaranteed to be associative"*. BOINC carries **`hr_class`** homogeneous redundancy, twenty years old, whose entire job is to send replicas only to numerically similar hosts. Prime Intellect's TOPLOC commits to top-k activations with an exponent-exact, mantissa-*tolerant* comparison, and a tolerance is a grey zone that disputes must then adjudicate.

All three are paying for the same missing property. We measured what happens when a workload simply has it.

### The result

MeTTa reduction is discrete symbolic rewriting. There is no floating point in the reduction path, so there is nothing to lose.

**Same program, two architectures — macOS 15 / Apple Silicon / libSystem vs Android 16 / Snapdragon 8 Elite / bionic:**

| | desktop | phone |
|---|---|---|
| `fuel_used` | 100,082 | 100,082 |
| `raw_hash` (results in **interpreter order**, not sorted) | `c2940ab5…` | `c2940ab5…` |
| a *non-terminating* job, capped | stopped at exactly 2,000,000 steps | stopped at exactly 2,000,000 steps, identical partial state |

**MORK's corpus, same two architectures:** 33 of 33 programs produce **byte-identical space dumps and identical step counts**, including a single 48,393,277-byte dump.

**Across three compiler configurations** (stock, fat-LTO, and `-C target-cpu=oryon-1`): 12 of 12 measurement cells hash-locked. Making it 1.19× faster did not move a byte.

Four independent adversarial agents have attacked this workspace and killed six of its numbers between them — a throughput figure, a BLAS baseline, a crossover density, a recall argument, a compression justification, and one of my own hardware ratios. **Not one attack has landed on determinism.** Every pass has widened it: across architectures, then across build profiles, then across thermal regimes.

### What that buys, in one sentence

> **MeTTa reduction is byte-reproducible across architectures with identical fuel counts, so verified distributed symbolic compute costs one re-execution and one integer comparison — no tolerance model, no reproducible-operator library, no homogeneous redundancy.**

Concretely, three mechanisms other networks build and maintain, deleted:
- **No RepOps.** Nothing to make reproducible; it already is.
- **No `hr_class`.** Any two devices are comparable, so replicas can be placed for locality, cost, or anti-collusion instead of numeric similarity.
- **No tolerance threshold, therefore no grey-zone disputes.** Agreement is `==`.

And a fourth property nobody else has: **the fuel counter is reproducible to the step.** Two honest devices agree not only on the answer but on how much work it took — so a dishonest one is caught by a cheap integer comparison before any output is examined, and a job that runs out of fuel is a *result* both parties agree on rather than an error to arbitrate.

### The honest scope

This is a verification result. It is not yet a network, and the gap is specific:

- **The compute-and-verify half of milestone 1 is demonstrated; the plumbing is not.** Fuel metering, the wire format, and the desktop verifier exist and have been exercised on hardware. The Android app, the charge-time worker, the shard store, and the phone-initiated transport do not exist. All four are platform plumbing with no research content — which is a schedule, not a risk.
- **Verification costs approximately one full re-execution** (measured: ~85 ms recompute against ~0.7 ms of commitment checking). The commitment shrinks the *envelope* by three orders of magnitude; it does not make checking cheap. Who pays for the second run is the open economic question, and it is the layer that killed the predecessors — BOINC ran twenty years without a market, Golem built one and its monorepo has since been deleted from GitHub, Akash has a real market and rents VMs rather than phones.
- **Replication as currently specified is theatre.** Our own schema lacks a commit/reveal seal binding a result hash to the worker that produced it, so a second replica can echo the first's hash and manufacture agreement. Found by our own review, not by an elder's; being fixed before any replication claim is made.
- **The phone is 3.7× slower than an M-series laptop under sustained load**, 2.2× duty-cycled. The sustained figure is the one that governs fleet capacity, because a device plugged in overnight runs continuously. An earlier 2.7× figure has been withdrawn.

### Two claims withdrawn from the earlier draft

Stated plainly, because the reason they were withdrawn is itself the argument for taking the rest seriously.

**Phone-NPU scheduling is withdrawn as a headline.** On the target silicon, NNAPI exposes exactly one device — `nnapi-reference`, type CPU — on a Snapdragon 8 Elite with the full Hexagon stack present but unreachable; Google has wound NNAPI down and the NPU now requires a per-vendor delegate. More decisively, at the deployable configuration the pre-filter stage costs on the order of 50 µs, so there is no denominator worth accelerating. The NPU is being offered a stage that is already free. It may earn its place later, against a measured CPU baseline; it cannot be in the abstract.

**Shaping-as-a-job-class is withdrawn pending an out-of-sample measurement.** Its original justification was a sparse/dense crossover measured against a BLAS baseline 15× below the machine's real floor. Its replacement justification was a recall argument, which was then shown to be recoverable by loosening a cutoff on any layout. What survives is a work-reduction figure from a synthetic uniform graph — and every constant in that line of work was chosen on a self-authored synthetic case. The rule we now hold ourselves to: **a self-authored case may catch a regression but must never choose a value.** The one out-of-sample datapoint within reach has vector-only retrieval *losing* to lexical BM25.

### What we are asking to fund

The four missing pieces of milestone 1 — app, worker, shard store, transport — plus the commit/reveal seal, on top of a verification result that four adversarial passes have failed to dent. The deliverable is a phone that computes a fuel-bounded MeTTa job overnight and a desktop that reproduces its result hash and its step count exactly, with a market-shaped envelope around it.

Not an AI accelerator story. A **correctness** story, on hardware, with the receipts attached.

---

### Provenance of every number above

| claim | spike | attacked by | status |
|---|---|---|---|
| fuel 100,082 / `raw_hash` identical, 2 architectures | S15 | — | stands |
| MORK 33/33 byte-identical, 48 MB dump | S16 | AGENT-1 re-verified independently | stands |
| 12/12 hash-locked across build profiles, 1.19× | S30 | self (contention + order confound, both fixed) | stands |
| 3.7× sustained / 2.2× duty-cycled | S30 | self — retracts S15's 2.7× | stands, supersedes |
| ~85 ms recompute vs ~0.7 ms check | S7 | S9 (loaded machine — absolutes suspect, ratio robust) | ratio only |
| NNAPI exposes no accelerator; scale is pinnable; naive scale gives recall 0/8 | S31 | AGENT-4 (agreed), AGENT-3 (independent) | stands |
| pre-filter ~50 µs at B=64 | S18 | — | stands |
| crossover ~1.5% not 5–9% | S13 | kills S3 | S3 withdrawn |
| bundling recall argument | S11 → S17 | S17 kills it | withdrawn |
| "26 → 353 GOP/s from locality" | S5 | S9, then AGENT-3 | **withdrawn** |
