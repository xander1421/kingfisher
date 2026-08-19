# Spike L1: On-Device Neural Logits & Generation Byte-Level Determinism on Snapdragon 8 Elite

**Status: D6 Certified (`ok=True`), 3 controls passed, 1 falsifier survived.**

*Target Device:* Samsung Galaxy S25 Ultra (`SM-S938B`, Snapdragon 8 Elite `SM8750` / `sun`, Hexagon NPU / HTP0).
*Model:* `SmolLM2-135M-Q4_0.gguf` (91.8 MB, Q4_0 block quantization).
*Prompt:* `"The capital of France is"`, 16 tokens, greedy sampling ($T=0, s=42$).
*Artifacts:* [`result.json`](file:///Users/victorianikolenko/kingfisher/spikes/L1_offline_logits/result.json), [`provenance.json`](file:///Users/victorianikolenko/kingfisher/spikes/L1_offline_logits/provenance.json).

---

## 1. Executive Summary

Milestone L1 verifies neural generation byte-level determinism on physical consumer mobile hardware across discrete process launches.

1. **4 Discrete Cold Launches on Hexagon NPU (HTP0):**
   - **Distinct Hashes:** **`distinct = 1`** across all 4 independent launches.
   - **Canonical Hash:** **`6aacbbad02c5`** (52 bytes of extracted token stream).
   - **Generation Invariance:** 100% byte-identical reproduction.

2. **Homogeneous Redundancy Invariant:**
   - Neural inference on Qualcomm Hexagon NPU is **strictly self-deterministic** under fixed backend and quantization parameters ($Q4\_0$).
   - A replica matching the backend class reproduces the identical byte sequence without tolerance windows or float drift.
