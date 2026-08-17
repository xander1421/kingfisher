# Proposed upstream report — hyperon-experimental

**A `match` returning ≥1022 results aborts the process, and conjunction order
decides whether that happens.**

Found while scaling an attention algorithm written in MeTTa
(`spikes/G18_ecan_ceiling`). Reproducible on unmodified `hyperon-experimental`
at `3f76dc4`, release build, on `aarch64-apple-darwin` and
`aarch64-linux-android` — **identical on both**.

**Draft only — nothing filed**, per mission §11 "no publishing".

> Supersedes `proposed/hyperon-collapse-panic/`, which attributed this to
> `collapse`. That was wrong: a bare `match` with no `collapse` panics
> identically.

## Symptom

```
thread 'main' panicked at hyperon-space/src/index/trie.rs:539:
  assertion failed: size < TK_MAX_EXPRESSION_SIZE
```

Process aborts with `SIGABRT` (exit 134). A MeTTa program cannot observe it, a
caller cannot distinguish it from any other crash, and an application embedding
`libhyperonc` loses the host process.

## Minimal reproducer — no `collapse` involved

```metta
(imp 0 n0 1000)
...
(imp 0 n1499 1000)
!(match &self (imp 0 $c $v) $c)
```

Bisected exactly:

```
1021 results  ->  OK
1022 results  ->  PANIC
```

1022 rather than 1024 because the expression carries a head and a wrapper
alongside the payload.

## The part we think is the real defect: order changes the outcome

Same conjunction, same denotation, 3000 facts, 400 per bucket:

```metta
; selective pattern first — returns normally
!(let $r (collapse (match &self (, (bucket b0 $c) (imp 0 $c $v)) $v))
   (foldl-atom $r 0 $a $b (+ $a $b)))          ; OK

; broad pattern first — aborts the process
!(let $r (collapse (match &self (, (imp 0 $c $v) (bucket b0 $c)) $v))
   (foldl-atom $r 0 $a $b (+ $a $b)))          ; PANIC
```

Both forms denote the same set. The first materialises 400 candidates; the
second materialises 3000 before the second pattern filters.

So a program's survival depends on a property that has **no effect on its
meaning**, is invisible in the source without knowledge of matcher internals,
and flips at a data-dependent threshold — which pattern is "broad" depends on
the contents of the space, not on the program.

A documented limit can be designed around. This can be tripped by reordering a
conjunction for readability.

## Cause

```rust
hyperon-space/src/index/trie.rs:511
    const TK_MAX_EXPRESSION_SIZE: usize = 1 << 10;

hyperon-space/src/index/trie.rs:537-540
    const fn start_expr(size: usize) -> Self {
        assert!(size < TK_MAX_EXPRESSION_SIZE);
        Self(TK_STORE_HASH | TK_MATCH_EXACT | size)
    }
```

`TrieKey` packs an expression's child count into 10 bits. `grep -rn
TK_MAX_EXPRESSION_SIZE` finds no call site that checks the bound before calling
`start_expr` — the `assert!` is the only guard.

A 10-bit arity field is a defensible design decision. `assert!` as its
enforcement is the part that makes it unusable from a library: **a data-dependent
condition should not abort the host process.**

## Precedent from your own design

MeTTa already treats a resource limit as a *result* rather than a death: a step
ceiling yields a normal value that every honest evaluator agrees on, and an
unresolved symbol yields an `(Error …)` atom a program can inspect. This
condition is the same category and is handled differently.

## Suggested directions, increasing effort

- **Return an `(Error …)` atom** rather than asserting. Smallest change,
  preserves the current limit, makes the failure observable and recoverable.
- **Cost-order conjunctions** so the most selective pattern is evaluated first.
  Removes the ordering asymmetry, which is the surprising half, and is a normal
  query-planner move.
- **Widen or remove the arity field.** `TK_VALUE_MASK` needs re-layout; a real
  cost and the only change that removes the cap rather than reporting it.

Reporting rather than choosing — the right trade depends on why the field is 10
bits, which the code does not say.

## Environment

`3f76dc4`, release. `aarch64-apple-darwin` and `aarch64-linux-android` panic at
the same threshold with the same message, and the ordering asymmetry reproduces
on both.
