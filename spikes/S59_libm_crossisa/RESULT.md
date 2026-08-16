# S59 — transcendental libm diverges across ISAs. The no-float branch has a hole.

**Verdict: RED, bounded and actionable. 11/197 evaluations differ between aarch64 and x86-64; 14/197 between macOS libSystem and Android bionic. Max 2 ULP. `sqrt`, `log` and `pow` were clean; `sin`/`cos`/`tan`/`asin`/`acos`/`atan` were not.**

This closes the last open cross-ISA risk, named by the S58 reviewer and left open by S57. It matters because `GUARDRAILS.md` C2 says bitwise validation is sound only under **no-float** *or* homogeneous redundancy, and this workspace claims the no-float branch — the property that lets us delete BOINC's entire `sched/hr.cpp` host-classification subsystem.

## Measured — 197 evaluations, three platforms

| op | n | arm64 vs x86-64 | macOS vs bionic | max ULP |
|---|---|---|---|---|
| **`sqrt`** | 20 | **0** | **0** | 0 |
| **`log`** | 60 | **0** | **0** | 0 |
| **`pow`** | 25 | **0** | **0** | 0 |
| `sin` | 20 | 3 | 0 | 1 |
| `cos` | 20 | 4 | 0 | 1 |
| **`tan`** | 20 | 4 | **9** | **2** |
| `asin` | 6 | 0 | 1 | 1 |
| `acos` | 6 | 0 | 1 | 1 |
| `atan` | 20 | 0 | 3 | 1 |
| **total** | **197** | **11 (6%)** | **14 (7%)** | **2** |

Concrete: `cos(7.0)` is `-0.5440211108893698` on arm64-macOS and
`-0.5440211108893699` on x86_64-macOS. `tan(0.1)` is `0.10033467208545054` on
macOS and `...55` on bionic.

## 1. The divergence is per-implementation, not per-ISA
`sin` and `cos` differ between arm64 and x86-64 **but agree between macOS and
bionic**. `atan` does the opposite — identical across ISAs, divergent across
libms. `tan` fails both, worst on bionic (9/20).

So "cross-ISA determinism" is the wrong frame. **Every distinct libm build is its
own equivalence class**, which is precisely the situation BOINC's `hr_class()`
exists to manage. A fleet of Android devices with different vendor libms could
diverge among themselves without any ISA change at all — untested and now the
obvious follow-up.

## 2. `sqrt` is safe by specification, not by luck
IEEE-754 *requires* `sqrt` to be correctly rounded, so its 0/20 is guaranteed
rather than observed. `sin`/`cos`/`tan`/etc. carry no such requirement — last-ULP
drift is **permitted by the standard**, so this is libms behaving correctly, not a
bug in any of them.

## 3. `log` and `pow` were clean, and I will not call them safe
0/60 and 0/25 in this sample. But `pow` is notoriously the hardest function to
round correctly, and my sweep was 5 bases × 5 exponents. **Absence of divergence in
a small sample is not a correctness guarantee**, and these two must be treated as
untested-clean, not proven-safe. A wide sweep is cheap and should be run before
either is allowed in a verifiable job.

## 4. S57's clean result never tested this path
S57 reported 66/66 programs identical across three platforms. Checking the corpus:
**it contains zero transcendental evaluations.** The only file matching
`sin-math|cos-math|…` is `stdlib.metta`, where every hit is an `@doc` block, and
S57 measured that file as producing 0 results.

S57's cross-ISA claim is not wrong, but its scope was narrower than it read: it
established determinism for symbolic reduction and basic `+ - * /` arithmetic, on
a corpus that avoids exactly the operations that break. Both S57's and S58's
"identical across two ISAs" results stand — for the paths they exercised.

## 5. The product's hot path is unaffected
The HDC prefilter is integer popcount over packed bitplanes (S34, bit-exact on
both machines, digest `f4e64fb7d70b9b0c`). No transcendental appears anywhere in
the query path. **This is a constraint on the MeTTa job class, not on the engine
we are shipping.**

## Instrument validation — and it caught two defects before the real run
`ulp_probe.metta` checks the harness can *see* a 1-ULP difference. First siting
used `sin(π/2)`, which is flat at its maximum: 1 ULP in gave 0 ULP out and the
probe read as "harness insensitive" when it was badly placed. Second defect:
`log-math` takes **two** arguments (base, value) and every call was erroring.

Re-sited at steep-derivative points, 4 of 5 probe pairs show the difference:
```
sin(1000.0)          0.8268795405320025
sin(1000.0 + 1ulp)   0.8268795405320665
```
Full precision reaches the output because `Number::Float` displays via `{:?}`
(shortest round-trip), so **identical text ⟺ identical f64 bits**.

This is the check S58's `b4` lacked — there, the instrument was degenerate and
nobody noticed until an attacker read it. Probing the instrument first is now the
habit.

## Rule this adds to the job class

> **Ban `sin-math`, `cos-math`, `tan-math`, `asin-math`, `acos-math`,
> `atan-math` from any job requiring byte-identical replication.** Statically
> checkable over the transitive `include`/`import!` closure, alongside S58's
> `flip` / `&rng` / `reset-random-generator` ban.
>
> `sqrt-math` is permitted — IEEE-754 guarantees it. `log-math` and `pow-math`
> are **provisionally permitted pending a wide sweep**, not cleared.
>
> The alternative, if a workload genuinely needs transcendentals, is to ship a
> **software libm** (e.g. the `libm` crate) compiled into the runner so every
> device evaluates the identical implementation. That converts a per-platform
> equivalence-class problem into a versioned-dependency problem, which we already
> have to solve for `rand` (S58).

## Caveats
- 197 evaluations at 20 hand-picked inputs. Not a systematic domain sweep, and
  argument reduction for very large arguments (the classic divergence site) is
  represented by only `1e6` and `1e15`.
- Three platforms, two libms, two ISAs. **Android vendor-libm variation across
  devices is untested** and is the more product-relevant question.
- x86-64 runs under Rosetta, so it is the x86-64 libSystem slice reached through
  translation.
- `f32` untested; hyperon's `Number::Float` is f64 throughout.
