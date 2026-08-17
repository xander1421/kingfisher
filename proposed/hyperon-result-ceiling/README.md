# Two defects in `hyperon-space` trie keys: a precedence bug that aborts the process, and a hard 1023 limit enforced by `assert!`

Reproduced on `3f76dc4`, arm64-macos and aarch64-android. **Patch attached for
the first; `cargo test -p hyperon` 298 passed / 0 failed, `-p hyperon-space`
29+6 passed / 0 failed.**

> **Supersedes an earlier draft of this report**, which blamed `collapse` and
> described the bound as "the cardinality of one result set". Both were wrong.
> The bound is on an **intermediate** match, `collapse` is not involved, and
> there are two independent defects rather than one.

---

## Defect 1 — `TrieKey::value()` operator precedence. Query result depends on pattern ORDER.

### The symptom a user sees
Same conjunction, same denotation, **only the order of the two patterns
differs**. 3,000 `imp` atoms, 50 `bucket` atoms, 50 results either way:

```metta
!(match &self (, (bucket b0 $c) (imp 0 $c $v)) $v)   ; OK, n_results 50
!(match &self (, (imp 0 $c $v) (bucket b0 $c)) $v)   ; PANIC
```

```
thread 'main' panicked at hyperon-space/src/index/trie.rs:179:71:
called `Option::unwrap()` on a `None` value
```

Reordering two patterns is a meaning-preserving refactor. Here it is the
difference between a correct answer and a dead process, and which pattern is
"broad" depends on the data, not the source.

### Cause
```rust
// trie.rs:531, in TrieKey::new -- stored values are offset
value += TK_MAX_EXPRESSION_SIZE;

// trie.rs:544 -- and the offset is meant to be removed here
fn value(&self) -> usize {
    self.0 & TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE
}
```
In Rust `-` binds tighter than `&`, so this parses as
`self.0 & (TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE)` — a mask clearing bit 10 —
not `(self.0 & TK_VALUE_MASK) - TK_MAX_EXPRESSION_SIZE`.

The two agree only while `floor(v / 1024)` is even:

| stored `v` | raw `v+1024` | as written | intended |
|---|---|---|---|
| 1023 | 2047 | 1023 | 1023 |
| **1024** | 2048 | **2048** | **1024** |
| 2047 | 3071 | 3071 | 2047 |
| 2048 | 4096-… | 2048 | 2048 |

So the decode is wrong exactly when a hashable atom index reaches 1024, and
`get_atom_unchecked` (`:179`) then unwraps a `None`.

A conjunction evaluates its leading pattern first, so a **broad** leading
pattern is what pushes the index past 1024 — which is why order decides.

### Fix
`01-trie-value-precedence.patch` — parentheses. With it, the broad-first form
returns `n_results 50` at n=3000, and all suites pass.

---

## Defect 2 — 1023 children per expression, enforced by `assert!`

Independent of defect 1 and **still present after it is fixed**.

```metta
(f 0) … (f 1023)
!(collapse (match &self (f $x) $x))
```
```
n=1023  exit 0
n=1024  panicked at trie.rs:539:9: assertion failed: size < TK_MAX_EXPRESSION_SIZE
```

`TrieKey` packs an expression's child count into 10 bits (`:511`), so an
expression may hold at most 1023 children. That is a defensible design; a bare
`assert!` as its enforcement is not — a library that aborts the host process on
a data-dependent condition cannot be embedded in a service.

**Ask:** return an error atom instead. `RESULT_FUEL_EXHAUSTED` already
establishes the pattern — a resource limit reached is a *result* every honest
evaluator agrees on, not a process death. If the bound is permanent, document it
as a language-level limit so callers can bound result sets before evaluating.

---

## Why we care (context, not a request)
We run the same job on several machines and compare output bytes. A panicking
worker produces no output at all, so a crash removes a replica rather than
disagreeing with one — and because the threshold is data-dependent and the query
author picks the program, that is reachable on purpose. Defect 1 makes it
reachable by *accident*, through a refactor that preserves meaning.
