# What each domain axis actually captures — and which way it errs

Fourth time a domain key has been found flattering itself, so this is the
standing reference rather than another one-off correction.

## The falsifier, stated and run
*"The `manifest` hash distinguishes builds that differ in how they were
compiled."* **False.**

```
manifest a7317d3b3f94dc27   binary f52d98196ad048fc   (default flags)
manifest a7317d3b3f94dc27   binary fdcb39477e7464c0   (RUSTFLAGS=-C target-cpu=native)
```

Same manifest, different binaries. And S63 established that compiler flags
change *results*, not just codegen — `-ffp-model=fast` plus `+i8mm+dotprod`
produced a real divergence.

A first attempt at this falsifier was **vacuous**: `--no-default-features` on
`fuelrun` changes nothing, because `fuelrun` declares no features of its own.
Identical binary, so the test could not have distinguished anything. Recorded
because a test that cannot fail is the thing this project keeps catching.

## What each axis actually means

| axis | captures | does NOT capture |
|---|---|---|
| `binary` | the exact artifact: source, features, flags, toolchain | nothing — it is ground truth for "compiled identically" |
| `manifest` | the **declared** dependency graph and features in Cargo.toml/lock | compiler flags, CLI feature overrides, workspace feature unification |
| `host` | which machine executed it | anything about the build |
| `os` | kernel/libc family | patch-level differences within it |
| `isa` | instruction set, normalised | microarchitecture (Apple M-series vs Snapdragon are both `aarch64`) |
| `operator` | pinned `UNATTESTED` — no attestation root exists | everything. This is a placeholder, not a measurement |

## Which way each error goes — the part that decides whether it is safe
A safety property must fail closed. For a domain count, **undercounting
independence is safe** (refuse work that might have been fine); **overcounting
is not** (accept work from replicas that share a fault).

- **`manifest` errs SAFE.** Two binaries with different compile flags but one
  Cargo.toml count as *one* domain. They may in fact be more independent than
  that. We under-credit, and refuse.
- **`isa` errs SAFE after normalisation** — `arm64` and `arm64-v8a` collapse to
  one. Before the fix it erred *unsafe*, counting one ISA as two.
- **`binary` errs UNSAFE if read alone.** Three distinct digests read as three
  independent implementations; they may share every dependency-class fault.
  This is exactly why `manifest` exists, and why the verdict binds on the
  **weakest** axis rather than any single one.
- **`operator` is not an error, it is an absence.** Pinned to 1 by construction
  until an attestation root exists.

## The rule that follows
**Never read one axis.** The vector binds on its minimum, and each axis is only
itself. A reader who takes `binary = 3` as "three independent builds" is making
the same mistake four different keys have now made in their own construction.

## Not fixed
Recording `RUSTFLAGS` and the resolved feature set (`cargo tree -e features`)
would let `manifest` cover compilation as well as declaration. Not implemented:
it errs safe today, and the binding axes are `operator` and `manifest` at 1
regardless, so it changes no verdict. Logged rather than done.
