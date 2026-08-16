# S66 — can MeTTa run inside a zkVM? Feasibility, measured without a toolchain

**Verdict: GREEN structurally. The reduction path is already clean; every zkVM-hostile dependency sits in the runner's I/O layer, not the interpreter. The port is bounded, not speculative. Timing deliberately not attempted — `quiet.sh` refuses.**

The dispute path in `RISKS.md` R-NEW rests on proving **one interval** of MeTTa
reduction (S65: 1,025–6,298 steps). That is impossible if the interpreter cannot
compile for the zkVM at all, so this is the gating question — and it is a
build-and-dependency question, load-insensitive, answerable while the machine is
busy.

## First attempt was the wrong test, and it would have given the wrong answer
Building `hyperon-atom` for `riscv32im-unknown-none-elf`:
```
error[E0463]: can't find crate for `std`      (+ transitive: either, bitset)
```
Read alone, that says "hyperon is std-only, therefore no zkVM." **Wrong target.**
`riscv32im-unknown-none-elf` is bare-metal `no_std`. risc0 guests build for
**`riscv32im-risc0-zkvm-elf`**, a custom target with `target_os = "zkvm"` and a
forked std — `risc0/zkvm/src/lib.rs:16` is `#![cfg_attr(not(feature = "std"), no_std)]`,
i.e. std is a supported configuration, not an absent one.

So the real question is not *no_std or not*. It is **which std features hyperon
needs that the zkVM shim lacks** — filesystem, threads, networking, clock.

## Measured — zkVM-hostile std usage, by crate

| crate | filesystem | threads | time | network |
|---|---|---|---|---|
| `hyperon-atom` | **0** | **0** | **0** | **0** |
| `hyperon-common` | **0** | **0** | **0** | **0** |
| `hyperon-space` | **0** | **0** | **0** | **0** |
| `lib` (the runner) | **75** | 0 | 2 | **0** |
| **`lib/src/metta/interpreter.rs`** — the reduction path | **0** | **0** | **0** | **0** |

## What this means

**The interpreter is already zkVM-clean.** Atoms, spaces, the common data
structures and the reduction loop itself touch no filesystem, no threads, no
clock and no network. All 75 filesystem sites are in the runner — module
loading, the catalog, the `fileio` builtin — none of which a dispute proof
needs.

So proving one interval requires: `hyperon-atom` + `hyperon-common` +
`hyperon-space` + `interpreter.rs`, driven by a **stub environment** that hands
the interpreter a pre-loaded space instead of resolving modules from disk. That
is a bounded port of the *runner's* boundary, not a rewrite of the engine.

It also fits how the dispute path works: bisection has already narrowed to an
interval and the committed state at the checkpoint *is* the pre-loaded space. The
guest never needs to load a module, because the disputed interval starts from a
state both parties agreed on.

**Zero thread usage anywhere in hyperon** is worth recording separately. A11's
concern about threaded accumulation applies to DAS's attention broker, not to
this engine — hyperon has no thread-related nondeterminism to remove.

**Two `SystemTime`/`Instant` sites in the runner** must be confirmed out of the
proving path. S58 already found no wall-clock operation is exposed to MeTTa
programs, so these are almost certainly host-side instrumentation, but "almost
certainly" is not a check.

## Not answered here
- **Cycle count for one interval**, and **risc0's proving rate on this machine**.
  Both are timing measurements and `quiet.sh` refuses (11 containers up).
  risc0 publishes no numbers in-repo — it ships a `datasheet` generator
  (`cargo run --release --example datasheet`) to be run on your own hardware,
  with a Metal feature available for Apple Silicon.
- Whether the forked std for `target_os = "zkvm"` actually provides everything
  the four clean crates use. The table above shows what hyperon *avoids*; it does
  not prove the shim supplies what hyperon *needs*. Confirming that requires
  `rzup` and a build.
- `either` and `bitset` failed the bare-metal build as transitive deps. Under the
  zkvm target with std they should be fine, unverified.

## Method note
The first result would have been a false negative. **A build failure is only
evidence against feasibility if you built for the right target** — and the wrong
target here produced an error message (`can't find crate for std`) that reads as
a definitive verdict. Same shape as S15's cross-OS-read-as-cross-ISA: the output
was accurate and the question was wrong.
