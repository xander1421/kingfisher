# Proposed upstream report — hyperon-experimental

> **CORRECTION 2026-08-17, before filing.** This report attributes the panic to
> `collapse`. That is wrong. `spikes/G18_ecan_ceiling` shows a **bare `match`
> with no `collapse` at all** panics identically:
> ```
> !(match &self (imp 0 $c $v) $c)     N=1500  PANIC     N=3000  PANIC
> ```
> The limit is on the result cardinality of the **leading pattern of a
> conjunction**, not on `collapse`'s aggregation. Exact bound is **1021**, not
> 1024 — the expression carries a head and a wrapper.
>
> And the sharper defect for a report: **conjunction order decides between a
> result and an abort.** At N=3000, `(, (bucket b0 $c) (imp 0 $c $v))` returns
> normally while `(, (imp 0 $c $v) (bucket b0 $c))` — same denotation — aborts.
> Reordering a conjunction for readability can kill the host process.
>
> Do not file the text below as written. It needs rewriting around `match` and
> around the ordering asymmetry, which is the part a maintainer can act on.

**`collapse` over 1024 or more results panics the process.**

Found while cross-checking rule application against a Python reference
(`spikes/G16_rules_in_metta`). Reproducible on unmodified `hyperon-experimental`
at `3f76dc4`. **Draft only — nothing filed**, per mission §11 "no publishing".

## Symptom

```
thread 'main' panicked at hyperon-space/src/index/trie.rs:539:
  assertion failed: size < TK_MAX_EXPRESSION_SIZE
```

## Minimal reproducer

```metta
(e x0)
(e x1)
...
(e x1023)
!(collapse (match &self (e $a) $a))
```

1024 facts and one `collapse`. Bisected exactly:

```
1020 atoms  ->  status OK
1023 atoms  ->  status OK        <- last working
1024 atoms  ->  PANIC            <- first failing
1030 atoms  ->  PANIC
```

## Cause

```rust
hyperon-space/src/index/trie.rs:511
    const TK_MAX_EXPRESSION_SIZE: usize = 1 << 10;      // 1024

hyperon-space/src/index/trie.rs:537-540
    const fn start_expr(size: usize) -> Self {
        assert!(size < TK_MAX_EXPRESSION_SIZE);
        Self(TK_STORE_HASH | TK_MATCH_EXACT | size)
    }
```

The token layout packs an expression's arity into a field of 10 bits, so any
expression with 1024 or more children cannot be represented. `collapse` builds
one expression containing every result, so the cap becomes a **cap on result-set
size** for the most common aggregation primitive.

`grep -rn TK_MAX_EXPRESSION_SIZE` finds no call site that checks the bound before
calling `start_expr` — the `assert!` is the only guard, and it aborts the
process.

## Why this is worth fixing rather than documenting

1. **1024 is small for a knowledge graph.** A query over FB15k-237
   (272,115 triples) exceeds it immediately; the case that found this had 915
   input edges.
2. **The failure mode is a process abort, not an error atom.** A MeTTa program
   cannot catch it, a caller cannot distinguish it from a crash, and a runner
   embedding `libhyperonc` loses the whole process.
3. Adjacent operations degrade gracefully — an unresolved symbol yields an
   `(Error …)` atom, and a step limit yields a normal result. This does not.

## Suggested directions, in increasing order of effort

- **Return an `(Error …)` atom** instead of asserting, so a program can observe
  and a caller can recover. Smallest change; preserves current limits.
- **Widen the arity field.** `TK_VALUE_MASK` would need re-layout; a real cost
  and a real fix.
- **Chunk inside `collapse`**, so result-set size is not bounded by expression
  arity at all. Largest change, and the only one that removes the cap rather
  than reporting it.

Reporting rather than choosing: the right trade depends on why the field is 10
bits, which the code does not say.

## Environment

`hyperon-experimental` at `3f76dc4`, release build, `aarch64-apple-darwin` and
`aarch64-linux-android`. **Both platforms panic identically** at 1024.
