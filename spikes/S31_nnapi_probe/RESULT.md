# S31 — NNAPI on real silicon: answering C1, and finding a hazard S12 could not see

**Answers Agent 1's C1** ("does the backend requantise, can the scale be PINNED by the job?").

**Verdict: YELLOW.** The scale *is* pinnable and the runtime honours it exactly. But two things are worse than the plan assumed: **NNAPI on this device exposes no accelerator at all**, and **the obvious choice of scale silently destroys the pre-filter** — recall 0/8 — through a saturation mode their simulation could not have reached.

Device: Galaxy S25 Ultra, SM8750 (Snapdragon 8 Elite, Hexagon V79), Android 16, NNAPI feature level 1000008.

---

## Finding 1 — NNAPI cannot reach the NPU on this phone

```
NNAPI devices: 1
  [0] nnapi-reference    CPU    feature level 1000008
```

**One device. Type CPU. The reference implementation.** No GPU, no `ANEURALNETWORKS_DEVICE_ACCELERATOR`, no DSP — on a flagship whose `/vendor/lib64` visibly contains `libsnap_qnn.so`, `libSnpeHtpV79Stub.so`, `libcdsprpc.so` and the rest of the Hexagon stack.

This is not a broken device, it is the platform direction: Google has wound NNAPI down, vendors no longer ship NNAPI HAL drivers, and Qualcomm exposes the NPU through **QNN / SNPE / the LiteRT QNN delegate** instead. Any plan that says "NNAPI" as the phone-NPU path is planning against an API that returns a CPU.

**`PORT_PLAN.md` M2.2 says "export the S5 kernel to Core ML and LiteRT".** LiteRT survives — but only with the vendor delegate wired up, which is a materially bigger piece of work than "export a model", and it is a per-vendor piece of work. The NNAPI half of that sentence should be struck.

## Finding 2 — the scale is pinned, exactly as C1 needed

Two runs of the same model with different declared output scales; the runtime honoured both to the bit, and the two devices (runtime's choice vs explicitly-pinned `nnapi-reference`) produced **identical** results.

So the answer to C1's second half is **yes**: `ANeuralNetworksOperandType.scale` / `.zeroPoint` are caller-specified and respected, so a job can pin them and honest replicas will agree. The dispute mechanism does not fire on nothing — *provided* the job carries the scale, which is exactly the schema change S12 called for.

## Finding 3 — the hazard: the natural scale saturates the matches, recall 0/8

The real S5 query shape: `Q` ∈ {−2, 0, +2}, `nnz(Q) = 527`, so the analytic cutoff is `2·nnz(Q) = 1054`, with 8 planted matching rows scoring exactly that.

int8 output has 256 levels. Covering ±1054 needs a scale of at least **8.267**. That is the obvious choice. It is catastrophic:

| declared scale | exact | worst err | **saturated** | grid cutoff | **recall** | false pos |
|---|---|---|---|---|---|---|
| **8.2667** (minimum that "covers" the range) | 471/4096 | 4 | **8** | 128 | **0 / 8** | 0 |
| **16.0** (headroom) | 0/4096 | 6 | 0 | 66 | **8 / 8** | 0 |

At scale 8.2667 the eight matching rows quantise to **127 — the int8 ceiling — and clip**. The grid-snapped cutoff `rint(1054 / 8.2667)` is **128**, which is *outside int8*. Nothing can ever reach it. **Every match is lost, silently, with no error and no saturation warning.** The pre-filter returns an empty candidate set and the CPU stage confirms nothing.

At scale 16 there is headroom below the ceiling, nothing saturates, the cutoff lands at 66, and recall returns to **8/8 with zero false positives** — even though *not one single value* is exactly reproduced (`exact 0/4096`, worst error 6). Which is the S12 lesson restated on hardware: **elementwise exactness is not the requirement; preserving the cutoff's separation is.**

### The rule this produces
S12 derived `cutoff = rint(2·nnz(Q) / scale)`. Necessary, not sufficient. On device it also needs:

> **`rint(2·nnz(Q) / scale) ≤ 126`** — the cutoff must sit strictly below the int8 ceiling, i.e. `scale ≥ 2·nnz(Q)/126`, not `≥ 2·peak/255`.

Choose the scale from the **cutoff**, not from the observed range, and leave at least one code above it. A job that pins `scale = 2·nnz(Q)/126` is safe by construction and independent of the data.

This failure mode is invisible in a float or int32 simulation: it exists only because the *output* type is 8-bit and the analytic cutoff sits at the top of the value distribution by construction. S12 could not have found it without silicon, and it would have shipped as "the NPU pre-filter returns nothing and nobody knows why".

---

## What this does and does not settle
**Settles:** the scale is pinnable (C1 answered); the requantisation rule needs a saturation clause; NNAPI is a CPU-only path on current Qualcomm flagships.

**Does not settle:** nothing here ran on the Hexagon NPU, because nothing *can* via NNAPI. Whether the NPU itself is bit-exact remains open and now requires the QNN SDK or a LiteRT build with the QNN delegate — a much larger spike. The timings (1.4–2.1 ms for 4096×1024) are the CPU reference and are not an NPU claim.

## Reproducing
```sh
$NDK/.../aarch64-linux-android29-clang -O2 -o probe probe.c -lneuralnetworks -llog -lm
adb push probe /data/local/tmp/kingfisher/ && adb shell '/data/local/tmp/kingfisher/probe'
```
API level 29 is required — `ANeuralNetworksCompilation_createForDevices` and `ANeuralNetworksExecution_compute` are unavailable below it, which is why the first build failed against 28.
