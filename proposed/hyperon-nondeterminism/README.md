# `intersection-atom` / `subtraction-atom` return wrong cardinality on ~40% of runs

Two defects in `hyperon-experimental`, found while measuring cross-platform
determinism of MeTTa evaluation. The first is a **correctness** bug: a pure
function returns a different number of elements on identical input, depending on
heap layout. The second breaks output reproducibility for anything that hashes
or diffs MeTTa results.

Reproduced against `3f76dc4`. Patches attached; all three apply clean to a
pristine tree. `cargo test -p hyperon` — **319 passed, 0 failed**.

---

## Issue 1 — set intersection silently drops members

### Reproduce
```metta
!(intersection-atom (A $x B $y C) ($y C A $x B))
```
Both sides contain `A`, `B`, `C`, `$x`, `$y`, so the intersection is all five
atoms. Fifteen runs of the same binary on the same machine:

```
 9 x  card=5  (A $x B $y C)     <- correct
 4 x  card=3  ($x B C)          <- two members dropped
 2 x  card=3  (B $y C)          <- two different members dropped
```

**40% of runs return the wrong answer.** Not a reordering — a different
cardinality, so elements are being lost. `subtraction-atom` shares the code path
and the defect.

It needs **two** variables to show. `(A $x C)` against `($x C A)` is correct;
`(A $x B $y)` against `($y A $x B)` is not.

### Root cause
`atom_to_trie_key` maps **every** variable to the same `TrieToken::Wildcard`, and
a wildcard query matches any stored key. Two consequences, in
`lib/src/metta/runner/stdlib/atom.rs`:

1. **During index construction.** The build loop calls `rhs_index.get(&k).next()`
   to find an existing bucket to merge into. With a wildcard key that returns an
   *unrelated* bucket — symbol `A`'s, say — which is then removed and re-inserted
   under the wildcard key. `A` is no longer findable under its own key and is
   lost from the result.
2. **At lookup.** `get(&k).next()` picks one of several matching buckets in
   `HashMap` iteration order and gives up if that bucket holds no equal atom.
   `remove(&k, &bucket)` then removes under the *candidate's* key — again the
   shared wildcard — evicting a different atom's bucket.

Both paths are order-sensitive, which is why the result varies between
processes rather than being consistently wrong.

### Fix (patch 01)
Both operations become straightforward multiset operations over a consumed-index
set. The `MultiTrie` was only ever a lookup index; correctness never depended on
it, and the wildcard collapse is what made it unsafe here.

**Cost, stated plainly:** this is `O(|lhs| * |rhs|)` rather than sub-quadratic. If
that matters for large inputs, the alternative is to key the index so distinct
variables do not collide — the wildcard collapse is the problem, not the trie.
The patch is written so the correctness fix is separable from that decision.

### A negative result, recorded so nobody repeats it
**Making the trie's iteration order deterministic does not fix this.** We tried
it first — `end_of_expr` is a `HashMap<*mut Self, Shared<Self>>` iterated in
pointer order, which looks like the obvious culprit. Converting it to an
insertion-ordered `Vec` left the failure completely unchanged at 9/4/2. A second
attempt, searching all matching buckets instead of taking `.next()`, improved it
to 5/4 but still dropped one element.

Ordered iteration only makes the *wrong* answer consistent. The wildcard collapse
has to be addressed directly.

Patch 03 ships that ordering change anyway, as optional hardening — it is no
longer required by patches 01/02, but pointer-order iteration remains a latent
nondeterminism source for any other `MultiTrie` consumer.

---

## Issue 2 — three `Display` impls print heap addresses

### Reproduce
```metta
!(new-space)
```
No imports, core stdlib only. Five runs, five different outputs:
```
GroundingSpace-0xbf0df03d8   GroundingSpace-0x9aee2c158   GroundingSpace-0x9ccd943d8
GroundingSpace-0x90ee1c3d8   GroundingSpace-0xa60d943d8
```

Sites:
- `lib/src/space/grounding/mod.rs` — `{self:p}`, in both `Debug` and `Display`
- `lib/src/metta/runner/builtin_mods/random.rs` — `self.0.as_ptr()`
- `lib/src/metta/runner/builtin_mods/fileio.rs` — `FileHandle-{:?}`

### Impact
Any pipeline that hashes or diffs MeTTa output — regression corpora, differential
testing across builds, replicated execution — sees spurious differences. It is
also reachable **accidentally**, because grounded atoms are printed inside error
atoms:

```
(Error (random-int RandomGenerator-0xb34ddc018 5 0) RangeIsEmpty)
```

so a program that never intends to print a handle still emits an address the
moment it hits an error involving one.

### Fix (patch 02)
`Display` carries **no address-derived identity at all**: an unnamed
`GroundingSpace` prints `GroundingSpace`, and the generator and file handle print
their type names. `Debug` keeps the pointer for interactive use.

We first tried a creation-ordered `stable_id()` and it was wrong — a
process-global registry keyed by address, never reset, so ids drifted with
allocator reuse across runs in one process (5 runs, 5 different digests). An
identity that is not reproducible is not worth printing into a hash, and no
counter keyed by address can be. Removing it is both simpler and correct.

---

## Verification

| check | result |
|---|---|
| `cargo test -p hyperon` | **319 passed, 0 failed** |
| `cargo test -p hyperon-common` | 20 passed, 0 failed |
| Issue 1 after patch, 30 runs | `(A $x B $y C)` **30/30** |
| Issue 2 after patch, 5 runs **in one process** | `GroundingSpace` **5/5** — the multi-run case that defeated the first attempt |
| 67-program regression corpus | **0 rows differing**; 235 passing assertions and 29 error atoms unchanged |

Correctness suite, all passing after the fix:
`(A B C D)∩(B D E)=(B D)` · `(A A B)∩(A B B)=(A B)` · `(X Y)∩(P Q)=()` ·
`()∩(A B)=()` · `(A $x)∩($x A)=(A $x)` · `($x $y)∩($y $x)=($x $y)` ·
`(A A A)∩(A A)=(A A)` · `((f $x) A)∩(A (f $x))=((f $x) A)`

## Issue 3 — variable binding order depends on process history (reported, not patched)

`(pair $z $z)` matched by `(pair $x $y)` returns `($x $x)` or `($y $y)` across
runs. That is usually described as `HashMap`-iteration dependence, but the cause
is more specific and worth stating:

```rust
// hyperon-atom/src/lib.rs:229-233
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct VariableAtom { name: UniqueString, id: usize }

// :222,:226,:330
static NEXT_VARIABLE_ID: AtomicUsize = AtomicUsize::new(1);
fn next_variable_id() -> usize { NEXT_VARIABLE_ID.fetch_add(1, Ordering::Relaxed) }
pub fn make_unique(mut self) -> Self { self.id = next_variable_id(); self }
```

`id` participates in the **derived `Hash` and `Eq`**, and the doc comment at
`:236-240` notes `VariableAtom` is used as a key in `matcher::Bindings`. So the
counter determines bucket assignment, and therefore iteration order, of the maps
holding bindings. **Binding-map layout depends on how many variables the process
created beforehand.**

Scope, so this is not overstated:
- `VariableAtom::new` leaves `id: 0`; only `make_unique()` draws a fresh id, so
  the hazard is confined to atoms that have been through
  `make_variables_unique` — the rule-instantiation path.
- The id **never reaches printed output** (`Display for VariableAtom` at `:335`
  prints `${name}` only), which is why a 67-program output-hash corpus shows
  nothing. This is an ordering hazard, not an output-content one.

Two practical consequences for anyone embedding hyperon:
- **A long-lived runner is not equivalent to a fresh one.** The same program run
  as job N occupies a different id space than as job 1.
- `Ordering::Relaxed` keeps ids unique but leaves *which* thread gets which id
  scheduling-dependent, so in-process concurrent evaluation is exposed in a way
  separate processes are not.

## Not addressed here
- `Variables({…})` hash-set ordering leaks into `RunnerState`'s `Debug` output.
- Issue 3 above is reported without a patch: fixing it means either excluding
  `id` from `Hash` (changing `Bindings` semantics) or using an ordered map, and
  that is upstream's call, not a drive-by change.
