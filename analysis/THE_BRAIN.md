# THE BRAIN — what it is made of, and what is actually missing

The thesis: a fleet of devices are pseudo-synapses; tied together they are a
brain; the work distributes across specialised modules. **The evidence supports
this, and the reason is better than the metaphor** — after 46 spikes, only
**one of eighteen** capabilities is still genuinely novel. The brain is
assembly, not invention.

## The parts, and their measured state

| brain function | our component | state | evidence |
|---|---|---|---|
| **neuron** — a unit that computes | device running a module | **works** | MeTTa in-process 0.25 ms (measured here). *oflineAI's 103.9 tok/s is **READ** from `~/alex/oflineAI/ALPHA.md`, not measured in this workspace* |
| **signal** — a result that means the same thing everywhere | deterministic reduction | **proven for the admissible job class** | S57: 66/67 identical across two ISAs, 360,847 steps. **Condition (S59):** that corpus contains **zero transcendental evaluations**, and `sin/cos/tan/asin/acos/atan` diverge across libms. Proven under the ban list, not in general |
| **synapse** — the connection substrate | hypergraph atomspace | works | MORK 33/33 byte-identical; DAS is a running service |
| **module interface** — how a specialised region attaches | `pub trait Grounded` | **exists, in use** | hyperon already binds external services, a network atomspace, Python, agents |
| **cortical code** — distributed representation | HDC / VSA | **integer, bit-exact** | S34 digest `f4e64fb7d70b9b0c` on two machines; torchhd `MAP`/`BSC`/`MCR`/`CGR` |
| **deliberation** | MeTTa + PLN | **verifiable today** | `c3_pln_stv`, 37,788 steps, identical on three platforms |
| **salience / attention** | DAS attention broker | **exists, nondeterministic** — and **inside the verified perimeter**, because importance feeds *state* (consolidation, forgetting, what the graph becomes), not just routing. If it only routed work, nondeterminism would cost efficiency rather than truth and the `double` version could ship today | `typedef double ImportanceType`; threaded accumulation |
| **memory consolidation** | shaping job class | **1 of 18 BUILD rows** | 4.1–5.6× on FB15k-237 |
| **co-tenancy** — many requests, one body | — | **proven, re-measured** | S32a's table was *recovered* from `chat.log` and never re-run, so it was re-measured: 8 concurrent copies on macOS, **8/8 identical and equal to the single-copy baseline** (`4937b20a…`). Now holds on two platforms |
| **routing** — which region gets which work | locality matcher | **ADAPT, not PORT** — Acurast routes by attestation class and has **no concept of shard locality or residency**, which is the half we need | Acurast `pallets/marketplace`, public domain, 260k devices |
| **circulation** — carrying results out | settlement | **a door, not a wall** | Per-job on-chain posting saturates at 3 devices — but that was never the design. Happy path is **Merkle-batched commitments + payment channels**, no ZK; proofs price only the dispute path |

## What the brain actually is, once you stop metaphorising

Not a bigger model. **A scheduler with a per-module verification rung.**

Two decisions repeated forever:
1. **Where does this work go?** — attention and locality. Which shard is resident
   on which device, which module is competent, who is awake and charging.
2. **How do I know the answer is real?** — and the rung differs by module:

| module type | verification | status |
|---|---|---|
| symbolic reduction | byte comparison across replicas | **proven, trustless** |
| integer VSA / HDC | byte comparison | **proven** (S34) |
| quantised neural inference | byte comparison **within a pinned runtime** | **harder than we thought** — the equivalence class includes environment variables and free memory, and is not observable from outside the device |
| float neural inference | not byte-comparable | needs TEE, ZK, or tolerance |

That table is the brain's design. It is also the honest statement of what
determinism bought us: **it does not cover every module, it selects which
modules can be trusted cheaply** — and the cheap ones are the ones an integer
NPU runs fastest anyway.

## The single missing organ

Every row above is either measured, or has a public-domain implementation we have
read and not ported. The exception:

> **Attention is the missing organ.** DAS's Hebbian broker is a real neural
> mechanism — importance decays as rent, redistributes as wages, spreads along
> edges. Nothing else in the stack does salience.

**And "just use fixed point" is wrong, for a reason this project already learned
one rung down.** Integer *addition* is associative, so thread order stops
mattering — but additions were never the danger. The neural rung taught it:
integer matmul was fine, **requantization rounding** was where vendors diverged.
Same law here. Decay, spreading and rent are **multiplications by rates in
[0,1]**, and fixed-point multiply rounds, so `(a·r) + (b·r) ≠ (a+b)·r` by a bit.
Worse, threaded read-modify-write reorders *which* importance a spreading step
reads mid-epoch.

*(An earlier draft of this section blamed the trie walk on hyperon's
pointer-keyed `HashMap`. That is wrong twice over: this workspace **measured and
eliminated** that mechanism — making `end_of_expr` insertion-ordered did not fix
`intersection-atom`, the real cause was every variable collapsing to one
`Wildcard` key during index construction — and DAS's `HandleTrie`
(`elders/das/src/commons/`) is a different structure entirely, with no
pointer-keyed map found. Its fold order is **unaudited**, which is why the spec
below requires content-hash ordering by construction rather than as a fix.)*

The surgery has a spec:

| requirement | why |
|---|---|
| **accumulate wide** — int64/int128 intermediates | keeps the rounding out of the inner loop |
| **round only at canonical points** | one rounding site, not one per edge |
| **BSP double-buffered epochs** — read state *t*, write *t+1* | removes read-modify-write interleaving |
| **fold order keyed by content hash, never by pointer** | the multitrie defect, avoided by construction |
| **one pinned rounding mode** | S49's exact-rational lesson |
| **seeded or removed stochastic selection** | S58's rule |

**Acceptance oracle: N threads and 1 thread must produce an identical per-epoch
state hash.** That is the whole determinism law of this project in one sentence —
**accumulate wide, round canonically, update synchronously** — now covering the
neural rung and the attention organ with the same physics.

## Where the scale argument breaks

A quarter-billion devices settles the *capacity* question and settles nothing
else. Two constraints do not improve with scale, and one gets worse:

- **Settlement — and the wall is a door.** "Saturated at three devices" prices
  *per-job on-chain posting* — which is exactly what `PORT_PLAN` M3.5 specifies as
  written (`pay_per_verified_result`), and is why R-NEW exists to supersede it.
  So the framing was accurate about the specification and stale about the
  recommendation. The happy path is
  **Merkle-batched commitments plus payment channels — no ZK, near-zero chain
  footprint**, and that removes the wall outright. Proofs only price the
  **dispute** path, where bisection over identical fuel counts reduces the job
  to proving **one interpreter step**, not a trace. So "cost the proof
  economics" scopes to exactly two measurements: **one-step proving cost on
  risc0**, and **checkpoint-hashing cadence** — and the second is not optional,
  because one-step proving requires the state at step *k* to be committed, so
  cadence is what defines *what "one step" even means*. Scale still converts a capacity
  problem into a settlement problem; it just turns out settlement has a known
  key.
- **Demand does not scale into existence.** BOINC ran 24 years with volunteers
  and never built a market. Golem built one and deleted the repository.
- **Heterogeneity gets worse.** The AI-module equivalence class already includes
  environment variables no verifier can see. 250M devices is 250M runtimes.

## So: are we still building it?

**Yes** — and the reason is that the hard technical claim held under four rounds
of adversarial review while nearly every number attached to it did not. Bit-exact
distributed computation on untrusted consumer hardware, with verification by
arithmetic anyone can repeat, is real and measured.

**But "we just need the brain" understates one thing and overstates another.**
It overstates what is left to invent — 17 of 18 capabilities have a production
reference, and the missing organ is a **bounded rewrite** of someone else's
public-domain code, to a written spec with an acceptance oracle. (Not merely "a
fixed-point conversion" — see above; that phrasing was the error this document
was amended to remove.) It understates the two things a brain does not fix: a body
with no circulatory system settles nothing, and an organism with no niche does
not survive being clever.

**Build the brain. It is close, and it is mostly assembly** — but assembly of 17
references *is itself the invention*. Systems die in the joints, and the routing
row above is the first joint: Acurast's matcher has no locality keys.

Sequencing:

**0. File `proposed/hyperon-nondeterminism/` upstream — as a correctness bug.**
The patches already exist, are measured, and pass: `cargo test -p hyperon` 319
passed / 0 failed, S57 corpus 0 rows differing with 235 assertions intact
(commit `0c7aec6`). Unfiled only because §11 forbids publishing.

**Frame it correctly or it will be ignored.** *"Your `HashMap` iterates in
address order"* earns a shrug. *"`intersection-atom` returns cardinality 3
instead of 5 on 40% of runs — root cause is every variable collapsing to one
`Wildcard` key during index construction; patch attached, 319 tests pass"* gets
merged. The weaker framing was in this document until it was checked.

It gates checkpoint hashing and bisection.

**1. Cost the two dispute-path numbers** — one-step risc0 proving, checkpoint
cadence. Days.

**2. Port attention** to the spec above, with the N-thread==1-thread oracle.

**3. Find one buyer**, in parallel with all of it.

### The attention port is also the market entry
A deterministic, fixed-point ECAN contributed **upstream to DAS/Hyperon** is
three things at once: the organ this brain is missing, the most legible possible
Deep Funding deliverable, and the ecosystem paying — in money or standing — for
engineering we were going to do anyway. It is the rare item where the
build and the go-to-market are the same commit.
