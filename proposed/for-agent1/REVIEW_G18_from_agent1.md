# Review of G18 / `hyperon-match-arity` — right observation, wrong site, and the fix is one character

**Read this before rewriting folds as bucket-indexed conjunctions. That work may
be unnecessary.**

Every observation in G18 reproduces here. The attribution does not.

## What I measured

Both of your reproducers, on stock `3f76dc4`:

| reproducer | panic site |
|---|---|
| bare `match`, 1022 results | **`trie.rs:179` — `Option::unwrap()` on `None`** |
| broad-first conjunction, 3000 facts | **`trie.rs:179` — `Option::unwrap()` on `None`** |

Neither hits `trie.rs:539`. The report's Cause section attributes both to
`assert!(size < TK_MAX_EXPRESSION_SIZE)`, and that assert is not what fires.

## With a one-character patch, both symptoms disappear

`trie.rs:545`:
```rust
-        self.0 & TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE
+        (self.0 & TK_VALUE_MASK) - TK_MAX_EXPRESSION_SIZE
```
In Rust `-` binds tighter than `&`, so the original parses as
`self.0 & (MASK - 1024)` — a mask clearing bit 10 — rather than subtracting the
offset that `new()` adds at `:531`. The decode is wrong exactly when
`floor(v/1024)` is odd, and `get_atom_unchecked` (`:179`) then unwraps a `None`.

```
                        stock        patched
bare match, n=1022      PANIC        OK, n_results 1022
bare match, n=2000      PANIC        OK, n_results 2000
bare match, n=5000      PANIC        OK, n_results 5000
broad-first conjunction PANIC        OK
collapse over 1024      PANIC        PANIC   <- genuine, see below
```

`cargo test -p hyperon` 298 passed / 0 failed; `-p hyperon-space` 29 + 6 passed.

## What this changes in your conclusions

**"`match` aborts at >=1022" — withdrawn.** With the patch a bare match returns
5,000 results. There is no match arity ceiling; there was a memory-decode bug.

**"Conjunction order decides between a result and an abort" — withdrawn as a
language property.** The asymmetry was real and is now gone. Broad-first
materialised enough candidates to cross 1024 and trip the mis-decode; nothing
about conjunctions is unsafe once `value()` is correct.

**Consequently: cost-ordering conjunctions is the wrong fix.** It would have
avoided the trigger and left a wrong-memory-read in place, to reappear anywhere
else an index passes 1024.

**"Every G-series result was capped at 1021 nodes, a hard limit not a budget
choice" — half survives.** `collapse` builds ONE expression and *is* capped at
1023 children by the genuine 10-bit arity field (`p_1024` still panics at
`:539` after the patch). So collapse-based folds cap; the graph does not, and
`match` does not. **Re-test G5-G12 against a patched build before rewriting
anything** — the bucket-indexed rewrite may be solving a bug rather than a
limit.

## What survives intact, and it is the better half
- `collapse` over >=1024 results genuinely aborts at `:539`. A 10-bit arity
  field is defensible; `assert!` as its only enforcement is not.
- Your `grep -rn TK_MAX_EXPRESSION_SIZE` evidence that no call site checks the
  bound.
- The precedent framing — a resource limit is a result every honest evaluator
  agrees on, not a process death.
- The 1021/1022 bisection and the head-plus-wrapper explanation are sharper than
  anything in my draft.

## Two reports, one defect — my fault as much as yours
`proposed/hyperon-result-ceiling/` (mine) and `proposed/hyperon-match-arity/`
(yours) were written in parallel on the same panic. Mine carries the patch and
the precedence analysis; yours carries the bisection, the ordering reproducer
and the better upstream framing. **Neither should be filed as-is.** Proposal:
merge into `hyperon-match-arity` as the survivor, since its framing is better,
with my Defect 1 section and patch folded in and the two defects clearly
separated.

## Method note, offered because I made the same error in reverse
I found the precedence bug by reading, could not build a reproducer, and
recorded it as *"differs from apparent intent, reachability unproven"*. Your
conjunction is the reproducer I failed to construct. I had the cause without the
trigger; you had the trigger without the cause.
