# `collapse` aborts the process on any result set of 1024 or more

**Not a nondeterminism bug — an availability one.** A library that calls
`abort()` on a data-dependent condition cannot be embedded in a service, and
this condition is chosen by whoever writes the query.

## Reproduce
```metta
(f 0)
(f 1)
...
(f 1023)
!(collapse (match &self (f $x) $x))
```

```
n=1023   exit 0     status OK
n=1024   exit 101   panicked at hyperon-space/src/index/trie.rs:539:9:
                    assertion failed: size < TK_MAX_EXPRESSION_SIZE
```

Reproduced on `3f76dc4`, host arm64-macos and aarch64-android, both from a
prebuilt `fuelrun.v2` and from a fresh `cargo build --release`. On Android the
process takes SIGABRT (exit 134).

## Cause
`TK_MAX_EXPRESSION_SIZE = 1 << 10` (`trie.rs:511`). `TrieKey` packs an
expression's child count into the low 10 bits, so **an expression may hold at
most 1023 children**, enforced by a bare `assert!` at `:539`.

`collapse` builds a single expression containing every result, so the limit is
not on the space, the program or the fuel — it is on the **cardinality of one
result set**.

## Why this matters beyond a crash
The threshold is result cardinality; cardinality depends on the data; the query
author chooses the program. In a replicated setting that is exploitable: a job
can be authored to cross 1024 against one node's shard and not another's, so
some workers abort while others return. A panicking worker produces no result
envelope at all, which shrinks a quorum rather than disagreeing within it.
Measured consequence in `spikes/M1_8_quorum3/QUORUM_SHRINK.md`.

## Requested change
Return an error atom rather than aborting. `RESULT_FUEL_EXHAUSTED` already
establishes the pattern: a resource limit reached is a *result* every honest
evaluator agrees on, not a process death. A 10-bit size field is a reasonable
design; `assert!` as its enforcement is not.

If the limit is intended to be permanent, document it as a language-level bound
on `collapse` so callers can bound result sets before evaluating.

## A second thing we looked at and could NOT substantiate
`trie.rs:545`:
```rust
fn value(&self) -> usize {
    self.0 & TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE
}
```
In Rust `-` binds tighter than `&`, so this parses as
`self.0 & (TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE)` — a mask that clears bit 10
— rather than `(self.0 & TK_VALUE_MASK) - TK_MAX_EXPRESSION_SIZE`, which is
what `new()` (`:531`, `value += TK_MAX_EXPRESSION_SIZE`) implies. Arithmetically
the two differ for any stored value where `floor(v / 1024)` is odd.

**We could not build a program that observes the difference.** A 3,000-atom
space with small result sets returns identical, correct output with and without
parentheses. So this is reported as *"differs from apparent intent, reachability
unproven"* — it is **not** the cause of the panic above, and we are not claiming
a defect on a reading alone.
