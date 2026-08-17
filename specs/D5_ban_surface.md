# D5 — Ban surface: build-enforced, versioned

**Status: spec, falsifiable. Supersedes "static ban list" everywhere.**

## Why enforcement is by build, not by analysis
`python/hyperon/stdlib.py:139-140` resolves `py-atom` from a **runtime string**:
```python
name = str(path.get_object().content if isinstance(path, GroundedAtom) else path)
obj  = find_py_obj(name, mod)
```
`!(py-atom math.sin)` returns Python's `math.sin` as a callable atom, and the
path is a value the program constructs at runtime. **No analysis over the
transitive import closure can see it.** Static checking of the ban list is
undecidable on any runtime carrying `py-atom`.

The banned operations are **registrations**, not language features:
`grounded_op!(SinMathOp, "sin-math")` at `stdlib/math.rs:219`, registered at
`:426`, with **zero `cfg(feature` in that file**. Not registered → not
reachable, by any path, static or dynamic. And S63 established the equivalence
class is **the binary**, so pinning the binary hash pins the surface. One field
does both jobs.

## The surface, v1

| class | excluded | evidence |
|---|---|---|
| **transcendental** | `sin-math` `cos-math` `tan-math` `asin-math` `acos-math` `atan-math` | S59: 11/197 differ arm64↔x86-64, 14/197 macOS↔bionic, max 2 ULP |
| **transcendental, pending sweep** | `log-math` `pow-math` | S59: 0/60 and 0/25 **in sample only** — `pow` is the hardest to round correctly and the sweep was 5×5. Provisionally permitted, **not cleared** |
| **permitted by spec** | `sqrt-math` | IEEE-754 *requires* correct rounding. Guaranteed, not observed |
| **unseeded randomness** | `flip` `&rng` `reset-random-generator` | S58: `flip` calls global `rand::random()` and takes no generator (`random.rs:186-188`); `&rng` is `from_os_rng()` bound at module load (`:127-128`); `reset-random-generator` re-seeds from OS entropy (`:43-45`) |
| **permitted, conditional** | `random-int` `random-float` via `new-random-generator <seed>` bound **once** | S58: 40 seeds × 3 platforms, bit-exact. `(= (g) …)` re-seeds per call — must be `bind!`/`let` |
| **ambient reads** | all of `fileio`; the eleven `das-*` network ops | `lib/Cargo.toml:47` has `default = ["pkg_mgmt", "das"]`, so `!(match &das …)` is a network query **by default** |
| **not exposed — recorded as a non-risk** | wall clock | S58: no time operation reaches MeTTa at all |

### Carried from this round, unmeasured, provisionally excluded
`float print/parse` round-tripping, and **sort stability** wherever a result
order is observable. Neither has been measured; both are excluded until they
are, because the cost of exclusion is lower than the cost of a silent 1-1-1
quorum split (D3 reasoning).

## Enforcement
1. **Build.** Ship a runner with the excluded ops unregistered. Python bindings
   are simply not built. Excluding `sin-math` needs an upstream
   `#[cfg(feature = …)]` around the registration — the same shape as the M0.2
   minimal-build ask already in the backlog for `builtin_mods/json.rs`.
2. **Version.** The surface is `BAN_SURFACE_V1`, and the runner's **binary hash
   is the version identifier**. A job envelope names the binary hash; the
   verifier compares it against an approved set. **One comparison, no analysis.**
3. **Failure is a result, not an error.** A program naming an unregistered
   symbol fails **identically on every honest device**, so quorum resolves
   cleanly instead of splitting. This is the `RESULT_FUEL_EXHAUSTED` shape from
   `hyperjob.proto`: a deterministic outcome that is agreed and payable.

## Falsifiers
| # | falsifier | test |
|---|---|---|
| F1 | An excluded op is reachable in a built runner | grep the registration table of the shipped binary; attempt each banned symbol and require the unregistered-symbol result |
| F2 | Two honest devices disagree on the *failure* for a banned symbol | run a banned-symbol program on two builds of the same hash, byte-compare |
| F3 | `log-math`/`pow-math` diverge under a wide sweep | ≥10⁴ inputs spanning magnitudes, three platforms |
| F4 | A permitted op reaches an excluded one indirectly | audit the stdlib `.metta` definitions for compositions |
| F5 | Binary hash is forgeable as an enforcement signal | **known and accepted**: it is a *matching hint*, not a security control. A liar produces a different result and loses 2-of-3 (C1) |

## Open
- F3 is unrun; `log`/`pow` stay provisional.
- Float print/parse and sort stability are excluded on precaution, not evidence.
- The upstream `cfg`-gate does not exist yet. Until it does, exclusion of
  `sin-math` is **aspirational** — the shipped runner still registers it.
