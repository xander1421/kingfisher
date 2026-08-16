# GRAPH AI IN THE ELDERS — three families, and which of them stay deterministic

The modular-brain architecture needs graph-native learning, not just graph storage.
The elder set has **three distinct families**, and they map cleanly onto brain
functions. The question that decides whether each can live inside a trustless
fleet is the same one throughout: **is the arithmetic integer?**

| family | brain analogue | elder | arithmetic | verifiable by byte comparison? |
|---|---|---|---|---|
| **Hebbian attention spreading** | salience / ECAN | `das/src/attention_broker` | `typedef double ImportanceType` | **No, as built** |
| **Hyperdimensional / VSA** | distributed cortical code | `torchhd` | **model choice decides it** | **Yes, if you pick right** |
| **Symbolic reduction + PLN** | deliberative reasoning | `hyperon` MeTTa | integer + `+ - * /` on f64 | **Yes** |

---

## 1. Hebbian attention spreading — the most brain-shaped, and the only one that fails

`das/src/attention_broker/` is genuinely a neural mechanism, not a metaphor:
`HebbianNetwork.{h,cc}`, `HebbianNetworkUpdater`, `StimulusSpreader`, plus an
economic layer — importance decays as **rent** and is redistributed as **wages**.
The client interface is a service:

```cpp
static void stimulate(const map<string, unsigned int>& handle_count, const string& context);
static void set_parameters(float rent_rate, float spreading_rate_lowerbound,
                                            float spreading_rate_upperbound);
```

**Stimulus arrives as `unsigned int` counts** — integer, deterministic. Then:

```cpp
typedef double ImportanceType;                                  // HebbianNetwork.h:17
ImportanceType rent = data->rent_rate * node->importance;       // StimulusSpreader.cc:51
data->total_rent += rent;                                       //                   :52
```

Two failure modes, and the second is the fatal one:
1. Importance is `double` throughout (35 uses), rates are `double` in [0,1].
2. `total_rent += rent` accumulates over a **trie traversal**, and `WorkerThreads.cc`
   sits in the same directory. **Float summation across threads is order-dependent**,
   so two honest nodes running the same stimulus produce different importance.

> **This is nondeterministic by construction**, and it is exactly the failure class
> `GUARDRAILS` C2 exists for. Note it is *not* the transcendental problem S59 found —
> multiply and add are correctly rounded. It is purely **accumulation order**.

**The fix is cheap and the design is already half-way there.** Stimulus is already
integer and the rates are bounded in [0,1], so importance can be a fixed-point
integer (u64 at 2⁻³² scale) with integer multiply-shift. Integer addition *is*
associative, so thread order stops mattering and the result is bit-identical
everywhere. This is a contained change to one subsystem, not a redesign.

---

## 2. Hyperdimensional / VSA — torchhd hands you the choice explicitly

`torchhd/tensors/` is a menu of VSA algebras, and **the dtypes they support are the
determinism decision**:

| model | supported dtypes | verdict |
|---|---|---|
| **`cgr`** Cyclic Group Representation | `int64` **only** | integer by construction |
| **`mcr`** Modular Composite Representation | `int64` **only** | integer by construction |
| **`bsc`** Binary Spatter Codes | `bool, uint8, int8, int16, int32, int64` (+float) | integer-capable |
| **`map`** Multiply-Add-Permute | `bool, int8, int16, int32, int64` (+float) | integer-capable |
| `bsbc` Binary Sparse Block Codes | bool + ints (+float) | integer-capable |
| `hrr` Holographic Reduced Rep. | `float32, float64` **only** | **float-only** |
| `fhrr` Fourier HRR | `complex64, float32/64` | **float-only, and it FFTs** |
| `vtb` Vector-derived Transformation Binding | `float32, float64` **only** | **float-only** |

Two conclusions:

- **`fhrr` is the worst possible choice for us** — complex FFT is float, and FFT
  accumulation order varies by implementation and by length factorisation.
- **We already independently built the right one.** The prefilter in this workspace
  is bipolar ±1 with majority bundling and popcount similarity — that is `MAP`
  with an int8/bool tensor. S34 measured those kernels bit-exact on two machines
  (digest `f4e64fb7d70b9b0c`). We arrived at the integer branch by accident and
  should now choose it on purpose.

VSA is also the family that most directly answers *"train a new kind of model"*:
`torchhd/classifiers.py` and `models.py` ship learning algorithms over these
algebras, MIT-licensed. Binding, bundling and permutation give compositional
structure without gradients or floats.

---

## 3. Symbolic reduction + PLN — already verified, and safer than it looks

MeTTa reduction is bit-identical across ISAs (S57: 67/67 fuel, 66/67 results,
360,847 steps). PLN rides on top of it: `c3_pln_stv.metta` in hyperon's corpus does
exact-compared f64 truth-value chains — `0.9 * 0.87 == 0.783`, then `* 0.9 == 0.7047`
— across 37,788 steps, and **those matched on all three platforms**.

That is not luck. S59 established the rule: `+ - * /` are IEEE-754
**correctly rounded** and therefore bit-identical on any conformant unit;
the divergence lives in transcendentals. PLN as written uses only the safe four,
so **probabilistic logic is verifiable today**. It stops being verifiable the moment
a confidence formula reaches for `log` or `exp`, which is the specific thing to
forbid in the job class.

---

## What this means for the modular brain

Every one of the three families has an integer formulation, and in two of the three
the integer path is what the hardware wants anyway:

1. **Attention** → fixed-point importance. Contained fix, input is already integer.
2. **Perception / representation** → `MAP`/`BSC` at int8, or `MCR`/`CGR` at int64.
   Also what the NPU runs natively.
3. **Deliberation** → MeTTa + PLN, restricted to `+ - * /`. Verified.

> **The determinism requirement does not force us out of graph AI. It selects a
> sub-family of graph AI — and that sub-family is the one that runs fastest on an
> integer NPU.** Speed and verifiability point the same way a second time.

## Gaps
- **No GNN anywhere in the elder set.** Message-passing networks are absent; torchhd
  is VSA, not graph convolution. If message passing is wanted, nothing to port.
- The attention broker's fixed-point conversion is **proposed here, not measured**.
- torchhd's *learning* algorithms have not been read, only its tensor algebras.
- Whether `MAP` at int8 retains accuracy at our dimensionalities is a separate
  question from whether it is deterministic. S17's worst-case recall (0.97 mean,
  **0/100 minimum**) is the open concern and it is unrelated to arithmetic.
