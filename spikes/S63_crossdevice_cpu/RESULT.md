> **SUPERSEDED IN PART, 2026-08-16, by adversarial review — read this first.**
>
> **The equivalence class is the binary *plus its runtime environment*, and that is not observable from outside the device.** Same binary/model/seed on one phone, varying only env vars: `81cef5aacba9` (default), `3b3c15512896` (`GGML_HEXAGON_USE_HMX=0`), `01e11bb3e178` (`MM_SELECT=1`), `d3848a54d223` (`ARCH=v75`) — **seven classes inside one "HTP0" label**, and `--fit` adds another by reading free memory at launch. Reproduced independently.
>
> Consequences: S62's claim (D) — `backend_class` plus byte comparison, "no TEE, no ZK" — is **INVALID**; a backend label is self-reported and unverifiable, which reintroduces the trust assumption. S63's "source commit + compile flags" key is **also insufficient**, since these are runtime settings. S62's published "CPU" row is in fact the **Adreno** hash (the CPU row needs an undocumented `-dev none`). And the comparator used by both **fabricated agreement** — see `extract.sh`.
>
> What survives: each configuration is self-deterministic (10/10 per backend, 256-token and 2B-model runs included), the NPU session is genuine (falsification-tested), and thread count does not change the CPU result. **Symbolic determinism (S57) is untouched by all of this.**

# S63 — cross-device LLM determinism: the equivalence class is the **binary**, not the backend

**Verdict: AMBER-GREEN. One decisive clean observation — macOS-aarch64 and Android-aarch64 produce byte-identical LLM output when compile flags match. This corrects S62. Multi-prompt confirmation is pending a quiet device.**

S62 concluded *"the equivalence class is the backend"* and left its biggest caveat as *"one device — same-backend agreement across devices is untested."* The Mac is a second aarch64 device, so that caveat is testable today.

## Setup, controlled
- **Same source commit.** `~/alex/oflineAI/bench/llama.cpp` at `e8e6c7af` — the tree that built the phone binary. (`~/llama.cpp` does *not* contain this commit and would have been a confound.)
- **Same weights, verified.** `SmolLM2-135M-Q4_0.gguf`, sha256 `bcc3af2849ad6095af57e9b5` on both host and device.
- Same flags: `-n 32 -s 42 --temp 0 --samplers greedy -no-cnv -st -t 4`.

## The result

| build | hash |
|---|---|
| Mac, `GGML_NATIVE=ON` | `ae365a87b52c` |
| Mac, `GGML_NATIVE=OFF` | `ae365a87b52c` |
| **Mac, Android's exact `CMAKE_C_FLAGS`** | **`4e5b2619c0fb`** |
| **Android phone, CPU, any `-t`** | **`4e5b2619c0fb`** |

**Byte-identical across two operating systems, two libcs and two devices** — once the compile flags match.

## What actually caused the divergence
Not the platform. The Android build carries:

```
CMAKE_C_FLAGS = -march=armv8.7a+fp16+dotprod+i8mm -fvectorize
                -ffp-model=fast -fno-finite-math-only -flto -D_GNU_SOURCE
```

`-ffp-model=fast` permits reassociation, and `+i8mm+dotprod` selects different matmul kernels. My first Mac build had neither.

**`GGML_NATIVE=OFF` did not reproduce this** — on/off gave the same Mac hash, which briefly looked like it ruled out the build-flag hypothesis. It did not: the Android flags come through explicit `CMAKE_C_FLAGS`, not through `GGML_NATIVE`. **I nearly published "platform divergence" on the strength of a control that tested the wrong variable.**

Also ruled out: `ggml_v_expf` is a self-contained NEON polynomial using `vfmaq_f32`, not libm `expf`, so this is *not* the S59 transcendental-divergence mechanism.

## Why this is much better news than S62

S62 said the equivalence class is the **backend**. The truth is finer and far more tractable: **the class is the binary — source commit plus compile flags.**

| | S62 believed | S63 measured |
|---|---|---|
| class | backend (CPU / NPU / GPU) | **the built artifact** |
| cross-device | untested | **identical, flags matched** |
| `-ffp-model=fast` | assumed hostile | **harmless if both sides use it** |
| fleet mechanism | classify hardware | **ship one binary** |

Fast-math does not break determinism. It only has to be *the same* on both sides. And a marketplace can pin and distribute a binary far more easily than it can classify heterogeneous hardware — which is the whole difficulty BOINC's `sched/hr.cpp` exists to manage.

This also vindicates BOINC's unit of account. `GUARDRAILS` B1 records that a BOINC "version" is *binary + platform + plan class*, with `MIN_VERSION_SAMPLES = 100` before that unit's scale factor may move. **BOINC keys on the binary. So should we.**

## Honest status of the confirmation

The decisive comparison above was taken on a quiet device and is solid. A follow-up across three prompts then produced 1 match and 2 mismatches — **and that run is not admissible**: an adversarial agent was saturating the same phone (`loadavg 10.35` on 8 cores, 49 °C). The mismatches are **length** differences (56 vs 140, 145 vs 162 chars) consistent with truncated generation under load, while the one that matched had identical lengths (126 = 126). No numeric-divergence signature.

**Outstanding: re-run the three-prompt matrix on an idle device.** Until then this is one clean observation, not a sweep. Per `GUARDRAILS` A7, that is a caveat that would change the verdict if it fires, so the verdict stays AMBER-GREEN rather than GREEN.

Method note: I launched a device-using adversarial agent and then ran device measurements concurrently. That is a self-inflicted control failure and belongs in the same family as S60's shared-`Metta` bug — **the harness must own the machine it measures.**

## Also fixed along the way
`zsh` does not word-split unquoted `$1`, so `genmac '-t 4'` passed `-t 4` as a single argument and llama-cli rejected it — silently, via an empty capture that hashed to `da39a3ee5e6b` (SHA-1 of the empty string). The instrument check caught it immediately. **Hashing an empty string is the failure mode that has now appeared in S57, S58, S60, S62 and S63.** A non-empty, sensitivity-checked capture is not optional.

## Caveats
- One model (135M), Q4_0, 32 tokens, greedy, one clean prompt.
- CPU backend only. Whether an NPU binary reproduces across two *phones* is the fleet question and needs a second device.
- `-flto` and `-D_GNU_SOURCE` were not replicated on the Mac; the match was achieved without them.
