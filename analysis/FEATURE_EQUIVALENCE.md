# A Cargo feature changes `fuel_used`. The equivalence class includes the feature set.

## The measurement
`integration_tests__das__test.metta`, same source, same commit, same machine —
only the `das` Cargo feature differs:

| build | status | fuel_used | sorted_hash |
|---|---|---|---|
| `features = ["pkg_mgmt"]` (S57 baseline) | OK | **107** | `49ba5618…` |
| `features = ["pkg_mgmt","das"]` (today) | OK | **580** | `2a2b9159…` |

**Fuel is the unit of payment, the unit of interruption, and part of the quorum
agreement key.** Two honest devices built with different feature sets disagree
on it, and neither is wrong.

## Why this is a new axis, not a restatement of S63
S63 established that **compiler flags** matter — `-ffp-model=fast` and
`+i8mm+dotprod` caused a divergence, and "fast-math is harmless if both sides
use it". That is codegen: the same program, computed differently.

A Cargo feature is not codegen. It changes **which modules exist**. With `das`
absent, `import! das` fails to resolve and evaluation stops in 107 steps; with
it present, the module loads and evaluation continues to 580. Different amounts
of work were genuinely done.

So the equivalence class is at least:
`source commit + compiler flags + CARGO FEATURE SET + runtime configuration`
and the last two were both discovered the same day, by the same 1-of-66 mismatch.

## Audit of prior claims — nothing invalidated, and here is why
Checked every LEDGER row resting on a cross-binary comparison.

- **S57 (66/67 across ISAs)**: all three `fuelrun` builds came from one
  `Cargo.toml` with `pkg_mgmt` only. Features matched, claim stands.
- **M1.8 quorum**: host and phone workers are the same crate. Matched.
- **S63**: about flags, already correct on its own terms.
- **M1.1 "in-process MeTTa identical to native fuelrun"**: this one was
  **cross-configuration** (app had `das`, fuelrun did not) and happened to hold
  because its three probe programs never touch a module. The conclusion was
  right; the comparison was not controlled. Recorded rather than withdrawn.

**But S57's stored baseline no longer reproduces.** The current binaries give
fuel 580 where `v2_aarch64_android.tsv` records 107. Nothing is wrong with
either number — they are answers from two different equivalence classes, and
the difference is invisible in the binary digest.

## Fix
`provenance.py` now records a **manifest hash** alongside the artifact digest:
every `Cargo.toml` and `Cargo.lock` under each declared dependency, hashed
individually and combined. A digest pins which artifact; a manifest hash pins
the feature set that produced it.

Self-tested: appending a comment to a `Cargo.toml` changes the combined hash.

## The general form, for the ban surface and the schema
Admission already rejects unseeded randomness and the `fileio` surface. Neither
can reach this: **the program is fine, the runtime differs.** The only defences
are (a) pin the feature set as part of the job's declared runtime, or (b) treat
the manifest hash as part of the domain key — two workers with different
manifest hashes are not the same runtime and should not be counted as agreeing
replicas of one.

(b) is the smaller change and fits the existing domain vector. Not implemented.
