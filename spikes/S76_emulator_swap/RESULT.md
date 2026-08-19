# S76 — the emulator reproduces the phone, and costs exactly one domain axis

**Measured while both targets were attached, because after the phone leaves this
comparison cannot be made at all.**

## Verdict

**Determinism: PRESERVED.** 15 of 16 executing corpus programs produce identical
`fuel_used`, `raw_hash` and `sorted_hash` on the Galaxy S25 Ultra and on an
Android emulator. 0 diverged. Fuel spans 107 to 50,794, so this is not a
degenerate sample.

**Domain independence: DEGRADED by exactly one axis.** `host` collapses.

## Method

Same binary (`fuelrun.v2.android`, aarch64 ELF) pushed to both targets, same
program, fuel 4,000,000. Only the target varies.

| | phone | emulator |
|---|---|---|
| abi | arm64-v8a | arm64-v8a |
| uname | aarch64 | aarch64 |
| os release | 16 | 16 |
| model | SM-S938B | sdk_gphone64_arm64 |
| hardware | qcom | ranchu |
| kernel | 6.6.98-andro… | 6.12.38-andr… |

## What the swap costs, per axis

Current vector: `binary 4 | manifest 2 | host 2 | os 2 | isa 2 | operator 1`.

- **`isa` — UNCHANGED.** Both are aarch64. Worth stating plainly because it is
  counter-intuitive: *the phone was never contributing an ISA domain against an
  aarch64 host.* The x86_64 host member is what makes `isa` 2, and it is unaffected.
- **`os` — UNCHANGED.** Both report Android 16. The emulator is a real Android
  userland, not a shim.
- **`host` — COLLAPSES 2 → 1.** The emulator runs on this Mac. Phone-and-host was
  two hosts; emulator-and-host is one.

**Consequence: `host` becomes a second binding axis at 1, alongside `operator`.**
The chain already refuses every job on `INSUFFICIENT_DOMAINS` because `operator`
is pinned at 1 for want of an attestation root, so the *verdict* does not change —
but the reason it refuses gets one term wider, and any future claim that
`operator` is the sole blocker becomes false.

## Controls

- `C_empty_is_not_agreement` — **fires.** 11 of the first 14 corpus programs
  return `e3b0c442…`, sha256 of the empty string. They agree on both targets and
  are *not evidence*; they are excluded and counted separately. A first pass of
  this spike nearly compared two targets on a program that produces no output.
- `C_same_binary` — the identical aarch64 ELF runs on both, so a difference could
  not be a build difference. Fails if either target rejects the binary.
- `C_fuel_varies` — fuel spans 107 → 50,794 across the sample. Fails if every
  program returned the same fuel, which would mean the harness was measuring
  nothing.

## What this does NOT show

- **Nothing about timing.** An emulator's wall clock is not a phone's. Every
  device timing in the LEDGER was taken on the phone and none of it transfers.
  `quiet.sh --device` gates on charging + idle + UNMETERED, all of which are
  **meaningless on an emulator** — the gate must refuse rather than pass, and if
  it passes on an emulator that is a defect, not a green light.
- **Nothing about thermals.** One `mc` run took the phone 37 °C → 52.5 °C. The
  emulator has no such envelope, so a suite that could not run back-to-back on
  the phone will appear to run fine.
- **Nothing about the NPU, the TEE, or 16 KB pages.** The `operator` axis and any
  hardware-attestation path are untouched and remain at 1.
- **n=16 on one corpus with one binary.** `fuelrun.v2.*` predates the
  nondeterminism patches (A24), which is fine for a target comparison — the same
  binary on both sides — and is *not* a claim about the patched engine.

---

## EXTENSION 2026-08-19, ATOM-3 — second engine, 33 programs, and a labelling defect that would have laundered this result

S76 above measured **`fuelrun`, 16 programs**. This extends it to **MORK, 33
programs** — a different engine and a different corpus — while both targets were
still attached, and finds one defect in the harness that carries the comparison.

### Falsifier, stated before the run

> If any of the 33 programs produces a different space dump on the emulator than
> on the phone, the emulator is not a stand-in and every post-phone result run
> against it is uninterpretable.

**It did not fire, and it could have** — see the positive control below.

### Measured

| | phone | emulator |
|---|---|---|
| model | `SM-S938B` | `sdk_gphone64_arm64` |
| SoC | Qualcomm `SM8750` | ranchu / QEMU on **Apple M4 Pro** |
| `CPU implementer` | `0x51` (Qualcomm) | `0x61` (**Apple**) |
| kernel | `6.6.98-android15-8-…S938B…` | `6.12.38-android16-5-…` |
| abi / sdk | `arm64-v8a` / 36 | `arm64-v8a` / 36 |

**33 of 33 space dumps byte-identical.** Concatenated-dump sha256 agrees on the
first 16 hex: `2bb4987526f3080b` on both. `mismatch=0`, `skipped=2` (the `bc0` /
`exponential` pair `BLOCKED.log` already records as exceeding wall clock).

**The binary was deliberately held constant** — the phone's own `mork`
(`sha256 646538779b49…`, 5,947,128 bytes) was pulled and pushed to the emulator,
so `binary` and `manifest` contribute nothing and the only thing varying is the
target. That makes this a clean target test and *not* a domain-count claim.

### The control that makes the agreement mean something (A15)

Agreement is worthless if the comparison cannot report disagreement. Appending
one rule — `(= (kf-canary $x) (S $x))` — to `programs/cross_join_dict.mm2` **on
the emulator only**:

```
UNPERTURBED  phone=a9a693d649d1b298  emu=a9a693d649d1b298   AGREE
PERTURBED    phone=a9a693d649d1b298  emu=d00f68260a17078a   DIFFER
RESTORED     emu=a9a693d649d1b298    back to baseline
```

The comparison fires. The 33/33 is a measurement, not a tautology.

### The defect: `crossrun.py` calls its second target `phone` whichever it is

`crossrun.py:75` writes to `{OUT}/phone/` and `:92` prints `phone`, with no
reference to what `ANDROID_SERIAL` resolves to. **This run — against an
emulator — was recorded on disk as a phone result**, and nothing in the output
says otherwise.

That matters because of the row below it in this table. S76 v1 found `host`
collapses when the emulator replaces the phone, and the `implementer` row now
says why in one number: the emulator guest reports **`0x61`, Apple** — it is
executing on the M4 Pro, the same physical silicon as `crossrun`'s host arm. So
against the emulator, `host` is **1**, not 2; only `os` separates the two arms.
Against the phone it is genuinely 2 (Qualcomm SM8750 vs Apple M4 Pro).

A harness that stores both under `phone/` will therefore report a **one-host**
result in the shape of a **two-host** one, and this repo's verdict vocabulary has
`INSUFFICIENT_DOMAINS` precisely for the case it would now silently skip. That is
family C (the artifact is not what you think) sitting directly upstream of a
domain-independence claim.

Related and still open, same file: `adb shell` is called at `:76`, `:107`, `:124`
with **no `-s` and no serial**, which is what made all 35 programs report
`SKIP no-step-line` for two days when a second device was attached — recorded as
a target failure three times before the cause was found. **Not fixed here**:
`crossrun.py` is AGENT-1's file and the fix is theirs to make. The shape it wants
is `quiet.sh`'s — a precondition that *refuses* when the target is ambiguous,
rather than a run that proceeds and mislabels.

### What this does NOT show

- **Nothing about ISA.** Both targets are `arm64-v8a` and the emulator is
  hardware-virtualised, not translated. S76 v1's finding that the phone was never
  contributing an `isa` domain is unchanged and this run does not improve it.
- **Nothing about the binary.** Held constant on purpose. Two independently
  *built* binaries agreeing is a different and stronger claim, and is S16's.
- **The emulator is a regression target, not an independence target.** It will
  catch a program or binary change — proven above. It cannot restore the host
  axis the phone provides, because it *is* the host.
