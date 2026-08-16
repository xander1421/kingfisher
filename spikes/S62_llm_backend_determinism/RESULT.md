# S62 — LLM inference determinism on real hardware: the equivalence class is the **backend**

**Verdict: GREEN, and it settles the neural half of the verification question. Every backend is byte-deterministic with itself. No two backends agree. Homogeneous redundancy is required for neural work — and it is sufficient.**

Ran on the operator's existing stack (`~/alex/oflineAI/bench/llama.cpp/build-snapdragon`, already staged at `/data/local/tmp/llama.cpp` on the S25 Ultra) with models already on the device. Nothing needed building.

`SmolLM2-135M-Q4_0`, prompt *"The capital of France is"*, `-n 32 -s 42 --temp 0 --samplers greedy`, 4 runs per configuration.

## Measured

| backend | 4 runs | distinct | verdict |
|---|---|---|---|
| CPU, `-t 1` | `4e5b2619c0fb` ×4 | 1 | self-deterministic |
| CPU, `-t 4` | `4e5b2619c0fb` ×4 | 1 | self-deterministic |
| CPU, `-t 8` | `4e5b2619c0fb` ×4 | 1 | self-deterministic |
| **Hexagon NPU (HTP0)** | `81cef5aacba9` ×4 | 1 | self-deterministic |
| **Adreno 830 (OpenCL)** | `028aee58fa2d` ×4 | 1 | self-deterministic |

## 1. Thread count does not change the CPU result
`-t 1`, `-t 4` and `-t 8` all produce the **same hash**. llama.cpp's CPU backend uses a reduction order independent of thread count — a deliberate design choice, not something you get for free. Contrast `das/src/attention_broker`, which accumulates `double` across a threaded trie walk and does not have this property (`analysis/GRAPH_AI.md`).

**So multithreading is not inherently the enemy of determinism. Unspecified reduction order is.**

## 2. Every backend is byte-deterministic with itself
Four runs each, zero variation, across CPU, DSP and GPU. **Neural inference on this hardware is replicable** — a second device running the same backend should produce the identical token stream, and the verification mechanism is a byte comparison, exactly as for symbolic work.

## 3. No two backends agree, and not subtly
This is not last-ULP drift. The generations are entirely different text:

```
CPU     "Yes, that's correct, the capital of France the capital city, …"
HTP     "Valence with her beautiful appareices, Flamènes! Done so eas…"
Adreno  (third distinct value)
```

Greedy sampling amplifies small numeric differences: one flipped argmax early in the sequence sends generation down a different path forever. So a 1-ULP difference in a logit becomes a completely different answer, and no tolerance model saves you.

## What this means for the architecture

**The equivalence class is the backend — not the ISA, not the thread count.**

This is precisely BOINC's homogeneous redundancy (`sched/hr.cpp`), and it corrects a claim made repeatedly in this workspace. S57 proved MeTTa reduction is bit-identical *across* ISAs, and I concluded we could delete `hr.cpp`. That holds for **symbolic** work. It does **not** hold for neural work: there we need HR, with the class keyed on backend rather than on CPU model.

The good news is that HR is cheap and well-understood, and BOINC already gives us the pattern — including `hr_unknown_class()`, which excludes a host whose class cannot be determined rather than guessing (`GUARDRAILS` C3).

> **Neural inference is verifiable by byte comparison, provided replicas are matched on backend.** No TEE, no ZK proof, no tolerance model. A `backend_class` field in the job spec and a matcher constraint are the whole mechanism.

## Instrument validation — which took four attempts and is the real lesson

The first three versions of this measurement were worthless, each in a way this workspace has already been burned by:

1. **Hashed a loading spinner.** `tr -d '\r'` concatenated animation frames whose count varies with load time. CPU appeared *non*-deterministic and the NPU appeared deterministic — **both artefacts, and the conclusion was backwards.**
2. **`--log-disable` did not suppress an ASCII-art banner**, so 700–780 bytes of the hashed content was decoration.
3. **Redirecting to a host file captured 19 bytes** — generation goes to the tty; the redirect had to happen on-device.
4. Only after extracting strictly between the `> prompt` echo and the `[ Prompt:` timing line did the content become real (140 chars of actual text), and only then did a **sensitivity check** — different prompt must give a different hash — pass.

I asked an adversarial reviewer to check for exactly this class of defect in S57 (*"is the harness capable of detecting a difference at all?"*) and then walked into it myself two spikes later. `GUARDRAILS` A7 and the S58 `b4` degeneracy say the same thing. **Validate that the instrument emits real, varying content before trusting any comparison** — it is now four for four as the most expensive recurring mistake here.

## Caveats
- **One device.** Same-backend agreement *across* devices is the claim that matters for a fleet and it is untested — it needs a second phone.
- One model (135M), one quantisation (Q4_0), one prompt, 32 tokens, greedy only.
- Self-determinism measured within one boot; not tested across reboots or thermal states.
- Larger models spanning more memory may behave differently, and `-ngl 99` on a 135M model may not exercise the same kernels a 4B would.
