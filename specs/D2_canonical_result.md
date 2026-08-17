# D2 — Canonical result serialization, per job class

**Status: spec, falsifiable. Last P0 freeze-gate item.**

## What a result envelope binds
A replica's output is compared byte-for-byte against its peers. The bytes must
therefore be a **canonical function of the computation**, not of the machine.
The envelope is:

```
result := ( job_id, binary_hash, canonical_form, fuel_used, digest, status )
```

- `binary_hash` — the runner's build identity. S63: **the equivalence class is
  the binary**, so this is what makes replicas comparable. Per C1 it is a
  **matching hint, not a security control**: a device reporting one build and
  running another produces a different result and loses 2-of-3.
- `fuel_used` — the step count. S58 established it is invariant under
  grounded-atom nondeterminism *that does not reach control flow*, and varies
  4.5× when it does. It is compared as an equal, not as a tolerance.
- `status` — `OK` / `FUEL_EXHAUSTED` / `UNREGISTERED_SYMBOL` / `MISSING_WITNESS`.
  **A fault is a result, not an error.** All honest replicas reach the same
  fault, so quorum resolves it and it is payable. This is the shape that keeps
  a D5 violation from becoming a 1-1-1 split.

## Canonical forms, per job class

| class | canonical form | why |
|---|---|---|
| `SORTED_SET` | results sorted by encoded bytes, duplicates removed | MORK's space is a set (S35) |
| `SORTED_BAG` | sorted, duplicates retained | hyperon's `match` is a bag (S35) — the two engines differ and the class must say which |
| `VERBATIM` | interpreter emission order | only where evaluation order is itself the claim; **currently no job class uses it** |

Order-sensitivity is a per-class decision because S57 could not establish
evaluation-order reproducibility: exactly one deterministic corpus program has
enough distinct results to detect a reordering. **Default to `SORTED_SET`.**

## Exclusions — Tier A is not available until these land upstream
The following make a byte comparison unsound today. Each is either patched-and-
unfiled or reported-without-patch in `proposed/hyperon-nondeterminism/`:

| defect | effect on serialization | status |
|---|---|---|
| `intersection-atom` / `subtraction-atom` wrong cardinality (~40% of runs) | the *result set itself* differs between honest replicas | **patched**, unfiled |
| `Display` printing heap addresses | address text enters the hashed bytes; `!(new-space)` gave 5 digests in 5 runs | **patched**, unfiled |
| `VariableAtom.id` from `NEXT_VARIABLE_ID` in the derived `Hash` | binding-map iteration order depends on **process history**, so job N ≠ job 1 in one runner | **reported, no patch** |
| `Variables({…})` hash-set ordering in `Debug` | blocks any state-level commitment (S68) | **reported, no patch** |

**Consequence:** `SORTED_SET` over `Display` output is sound only once the first
two land. The third is why `PORT_PLAN` M1.3 requires **fork fresh per job** —
two independent derivations, this and S60/A8's atomspace pollution.

## Encoding rules
1. **No floats in the canonical bytes.** Where a numeric parameter must cross
   the wire it is an **exact rational** (`num`, `den`) — S49 measured a boundary
   sitting on `.5` where float-vs-double split two honest verifiers, and D3
   records Acurast shipping exactly this at 260k devices. `hyperjob_v1.proto`
   still declares `quant_scale` as `double`; that is a **defect**, not a gap.
2. **Declare the exclusion list.** Anything stripped before hashing is named in
   the spec, as BOINC's bitwise validator names its 10-byte gzip header. MORK's
   `--timing` writes nanoseconds into the hashed space (S35) — the same bug
   class, twenty years apart.
3. **Length-prefix every variable-length field** before concatenating, so no two
   distinct results share a preimage. S49's `verifier2.py` does this; v1 did not.
4. **Pin the `rand` crate version** alongside any seed. `StdRng` is not stable
   across crate versions.

## Falsifiers
| # | falsifier | test |
|---|---|---|
| F1 | Two honest replicas on the same `binary_hash` produce different bytes for the same job | the S57 corpus across 3 platforms — currently 66/67, the exception being a `(flip)` program D5 bans |
| F2 | Two *different* computations produce the same bytes | length-prefixing must make preimages injective; construct a collision attempt |
| F3 | A fault does not compare equal across replicas | run a banned-symbol job on 3 replicas; all must reach the identical `status` and bytes |
| F4 | `fuel_used` differs between honest replicas | S58's branching-randomness case, which D5 excludes; must not occur inside the admitted class |
| F5 | Canonicalization hides a real divergence | **the danger direction.** A canonical form that sorts away an ordering difference makes divergent replicas agree. Test: inject a reordering that *should* matter and confirm the class detects it |

**F5 is the one to watch.** S62's comparator fabricated agreement by dropping
generated lines; a canonical form is a deliberate version of the same operation
and needs the same suspicion.

## Open
- No job class uses `VERBATIM`, so order-sensitivity is untested in production
  shape.
- The exclusion list (rule 2) is not written; it must enumerate every field
  stripped before hashing, and nobody has audited what MeTTa emits that is
  environment-derived beyond the three `Display` sites.
