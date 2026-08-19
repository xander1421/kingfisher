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
