# Both bugs verified, both fixed, zero regressions — 2026-08-16

Patches in `patches/`, applied to `elders/hyperon-experimental` at `3f76dc4`.
**Not filed** — mission §11 forbids publishing. Filing is a human action.

## Verification: how true were the claims?

**Bug 1 was understated.** I had described `intersection-atom` as returning
"different results". It returns **wrong** results. 15 runs of
`!(intersection-atom (A $x B $y C) ($y C A $x B))`, whose correct answer is all
five atoms:

```
 9 x  card=5  (A $x B $y C)     <- correct
 4 x  card=3  ($x B C)          <- two members dropped
 2 x  card=3  (B $y C)          <- two different members dropped
```

**40% of runs silently lose members of a set intersection.** Not ordering, not
cosmetic — a pure function returning different cardinality on identical input.

**Bug 2 confirmed exactly as described.** `!(new-space)` alone, no imports:
5 distinct output hashes in 5 runs. Also reachable accidentally through error
atoms: `(Error (random-int RandomGenerator-0x954d94918 5 0) RangeIsEmpty)`.

## Root cause — deeper than "a HashMap is iterated in address order"

My first two attempts fixed the wrong thing, and measuring after each is what
found the real defect.

1. **Made `end_of_expr` insertion-ordered** (patch 03). Still 5/3/3. Not it.
2. **Searched all matching buckets instead of `.next()`.** Improved to 5/4 — but
   still wrong, now dropping a single element.
3. **The actual cause:** `atom_to_trie_key` maps *every* variable to the same
   `TrieToken::Wildcard`, and a wildcard query matches any stored key. So during
   **index construction**, `get(&k).next()` merged an unrelated bucket — symbol
   `A`'s — under the wildcard key, after which `A` could not be found under its
   own key. A second instance of the same defect sat in the lookup loop, where
   `remove(&k, &bucket)` removed under the *candidate's* key, evicting a
   different atom's bucket.

It needs **two** variables to show: `(A $x C)` against `($x C A)` is correct;
`(A $x B $y)` against `($y A $x B)` is not.

## The fix

`intersection-atom` and `subtraction-atom` become straightforward multiset
operations over a consumed-index set. The `MultiTrie` was only ever a lookup
index — correctness never depended on it, and the wildcard collapse is what made
it unsafe here.

**This trades sub-quadratic lookup for O(|lhs|·|rhs|).** That is a real cost and
is called out in the code comment: if it matters, the index must be keyed so
distinct variables do not collide. Upstream may prefer that route; the patch is
written so the correctness fix is separable from the performance question.

Patch 02 replaces address printing with a creation-ordered `stable_id()`.
Patch 03 is optional hardening — no longer required by patches 01/02, but
`end_of_expr`'s pointer-keyed iteration is still a latent nondeterminism source
for any other `MultiTrie` consumer.

## Results

| | before | after |
|---|---|---|
| `(A $x B $y C)` ∩ `($y C A $x B)` | 5/3/3 across 15 runs | **`(A $x B $y C)` 30/30** |
| `!(new-space)` | 5 distinct hashes in 5 runs | **`GroundingSpace-#1` 6/6** |
| error-atom path | 3 distinct in 3 runs | **`RandomGenerator-#1` 3/3** |

Correctness suite, all passing: `(A B C D)∩(B D E)=(B D)`, `(A A B)∩(A B B)=(A B)`,
`(X Y)∩(P Q)=()`, `()∩(A B)=()`, `(A $x)∩($x A)=(A $x)`, `($x $y)∩($y $x)=($x $y)`,
`(A A A)∩(A A)=(A A)`, `((f $x) A)∩(A (f $x))=((f $x) A)`.

## Regressions: none

- `cargo test -p hyperon` — **319 passed, 0 failed**
- `cargo test -p hyperon-common` — 20 passed, 0 failed
- **S57 corpus, 67 programs**: 0 rows differing against the committed baseline;
  **235 passing assertions and 29 error atoms unchanged**

## What this unblocks
`out/LEDGER.md` records these two defects as blocking three things at once:
S58's replication oracle, S60's bisection commitment, and the R-NEW settlement
route. All three depend on hashing MeTTa output, which was unsound while either
bug stood.

**Still open, and not addressed here:** variable naming in `match` is
`HashMap`-iteration dependent (`hyperon-atom/src/matcher.rs:193-756`) — `(pair $z $z)`
matched by `(pair $x $y)` returns `($x $x)` or `($y $y)`. Arguably alpha-equivalent
rather than incorrect, but it has the same effect on an output-hashing pipeline.
S60's attacker also found `Variables({…})` hash-set ordering leaking into the
`Debug` representation of `RunnerState`. Neither is fixed.
