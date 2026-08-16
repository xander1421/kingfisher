# Proposed upstream reports — hyperon-experimental

Two defects found while measuring cross-ISA determinism of MeTTa evaluation
(`spikes/S57_hyperon_corpus`, `spikes/S58_fuel_branching`). Both are reproducible
with stock `fuelrun`-style harnesses on unmodified `hyperon-experimental` at
`3f76dc4`. **Drafts only — nothing filed, per mission §11 "no publishing".**

The first is a correctness bug. The second is a reproducibility bug that matters
for anyone hashing MeTTa output.

---

## Issue 1 — `intersection-atom` returns different results, with different cardinality, on identical input

### Reproduce
```metta
!(intersection-atom (A $x B $y C) ($y C A $x B))
```
Ten runs, unmodified binary, no randomness anywhere in the program:

```
1c6f9da9 8d80a7c0 1c6f9da9 8d80a7c0 a2430baa 1c6f9da9 1c6f9da9 8d80a7c0 1c6f9da9 1c6f9da9
```
(SHA-256 prefixes of the result set.) Observed bodies include `(A $x B $y C)`,
`(B $y C)` and `($x B C)` — **not merely reordered, different lengths.**

### Cause
`hyperon-common/src/multitrie.rs:308`:
```rust
end_of_expr: HashMap<*mut Self, Shared<Self>>,
```
The map is **keyed by raw pointer**. `:363` iterates `self.end_of_expr.values()`
in the wildcard arm, so traversal order follows allocation addresses, which vary
per process. `lib/src/metta/runner/stdlib/atom.rs` then takes results off that
unordered traversal.

Triggered whenever either argument contains a variable. Via `stdlib.metta:644-663`
the same path backs `subtraction-atom`, `intersection` and `subtraction`.

### Why it is a correctness bug and not a cosmetic one
Set intersection is a pure function of its arguments. Returning a different
*cardinality* on repeat calls means results are being dropped or added depending
on heap layout. Any program branching on `(size-atom (intersection-atom …))` is
nondeterministic today.

### Suggested fix
Key the map by a content-derived identifier, or use `BTreeMap`/`IndexMap`, or sort
before consuming the iterator. Address-derived ordering should not be observable
from the language.

---

## Issue 2 — `Display` for `GroundingSpace`, `RandomGenerator` and `FileHandle` prints heap addresses

### Reproduce
```metta
!(new-space)
```
Five runs, five distinct outputs — no imports, core stdlib only:
```
2e6458f1 1dd286f0 db166c1d 5201ba4f d2fc6a41
```

### Cause
- `lib/src/space/grounding/mod.rs:217-227` — `{self:p}` → `GroundingSpace-0x…`
- `lib/src/metta/runner/builtin_mods/random.rs:64` — `self.0.as_ptr()`
- `lib/src/metta/runner/stdlib/fileio.rs:94` — `FileHandle-0x…`

### Impact
Any pipeline that hashes or diffs MeTTa output — regression corpora, differential
testing across builds, replicated execution — sees spurious differences. It is
also reachable **accidentally**, because a grounded atom is printed inside error
atoms:
```
(Error (random-int RandomGenerator-0xb34ddc018 5 0) RangeIsEmpty)
```
so a program that never intends to print a handle still emits an address whenever
it hits an error involving one.

### Suggested fix
Content-derived or stable-counter identifiers. If a unique tag is needed for
debugging, a per-runner monotonic id is stable and just as useful.

---

## Related non-bug, recorded for completeness
Variable naming in `match` is also `HashMap`-iteration dependent
(`hyperon-atom/src/matcher.rs:193-756`): `(pair $z $z)` matched by `(pair $x $y)`
returns `($x $x)` or `($y $y)` across runs. Arguably alpha-equivalent and therefore
not a correctness bug — but it has the same practical effect on any output-hashing
pipeline, and the same fix (ordered traversal) addresses it.

## What is NOT affected — checked, and worth stating
Atomspace iteration, `match` result order, `superpose` and `unique-atom` are
deterministic and byte-identical across aarch64-macOS, x86_64-macOS and
aarch64-Android: `hyperon-space/src/index/trie.rs` walks insertion-ordered
`SmallVec`s, and its `HashMap` at `:204` is lookup-only. The problem is specific
to the two sites above.
