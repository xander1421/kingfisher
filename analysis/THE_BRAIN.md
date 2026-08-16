# THE BRAIN — what it is made of, and what is actually missing

The thesis: a fleet of devices are pseudo-synapses; tied together they are a
brain; the work distributes across specialised modules. **The evidence supports
this, and the reason is better than the metaphor** — after 46 spikes, only
**one of eighteen** capabilities is still genuinely novel. The brain is
assembly, not invention.

## The parts, and their measured state

| brain function | our component | state | evidence |
|---|---|---|---|
| **neuron** — a unit that computes | device running a module | **works** | oflineAI 103.9 tok/s on the NPU; MeTTa in-process 0.25 ms |
| **signal** — a result that means the same thing everywhere | deterministic reduction | **proven** | S57: 66/67 identical across two ISAs, 360,847 steps |
| **synapse** — the connection substrate | hypergraph atomspace | works | MORK 33/33 byte-identical; DAS is a running service |
| **module interface** — how a specialised region attaches | `pub trait Grounded` | **exists, in use** | hyperon already binds external services, a network atomspace, Python, agents |
| **cortical code** — distributed representation | HDC / VSA | **integer, bit-exact** | S34 digest `f4e64fb7d70b9b0c` on two machines; torchhd `MAP`/`BSC`/`MCR`/`CGR` |
| **deliberation** | MeTTa + PLN | **verifiable today** | `c3_pln_stv`, 37,788 steps, identical on three platforms |
| **salience / attention** | DAS attention broker | **exists, nondeterministic** | `typedef double ImportanceType`; threaded accumulation |
| **memory consolidation** | shaping job class | **1 of 18 BUILD rows** | 4.1–5.6× on FB15k-237 |
| **co-tenancy** — many requests, one body | — | **proven** | 8 concurrent copies, identical digest at every N |
| **routing** — which region gets which work | locality matcher | **not built; exists elsewhere** | Acurast `pallets/marketplace`, public domain, 260k devices |
| **circulation** — carrying results out | settlement | **the wall** | 8.6 results/s; **three devices saturate it** |

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

> **Attention is the missing organ, and it is one contained fix away.**
> DAS's Hebbian broker is a real neural mechanism — importance decays as rent,
> redistributes as wages, spreads along edges. It is nondeterministic only
> because importance is `double` accumulated across a threaded trie walk.
> Stimulus already arrives as `unsigned int`, and the rates are bounded in
> [0,1], so fixed-point integer importance makes it bit-exact. Integer addition
> is associative; thread order stops mattering.

That is the difference between a fleet of devices running jobs and a brain that
decides what matters. Nothing else in the stack does salience.

## Where the scale argument breaks

A quarter-billion devices settles the *capacity* question and settles nothing
else. Two constraints do not improve with scale, and one gets worse:

- **Settlement is saturated at three devices.** 2.87 results/s per device against
  8.6/s of chain. At 250M devices, throughput is infinite and the bottleneck is
  100% settlement. **Scale converts a capacity problem into a settlement
  problem — it does not solve one.** The fix exists (constant-size proofs,
  256 bytes regardless of work proven, posted only on dispute) and is uncosted.
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
reference, and the missing organ is a fixed-point conversion in someone else's
public-domain code. It understates the two things a brain does not fix: a body
with no circulatory system settles nothing, and an organism with no niche does
not survive being clever.

**Build the brain. It is close, and it is mostly assembly.** But the sequencing
should be: cost the proof economics (days), port attention with fixed-point
importance (contained), and in parallel find one buyer — because the brain is
the part we know how to build, and the other two are the parts we do not.
