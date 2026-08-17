# Proposed upstream report — hyperon-experimental

**Two independent defects in `hyperon-space/src/index/trie.rs`. The first is a
one-character operator-precedence error that aborts the host process; the second
is a 1023-child arity limit enforced by a bare `assert!`.**

Found while scaling a MeTTa program over a growing space. Reproducible on
unmodified `3f76dc4`, release build, on `aarch64-apple-darwin` and
`aarch64-linux-android` — identical on both.

**Draft only — nothing filed**, per mission §11 "no publishing".

> Merged from two parallel drafts (`hyperon-collapse-panic`,
> `hyperon-result-ceiling`), both superseded. Earlier revisions attributed
> everything below to the arity `assert!`; **that was wrong for the majority of
> the symptoms**, and the correction is recorded in
> `proposed/for-agent1/REVIEW_G18_from_agent1.md`.

---

# Defect 1 — `TrieKey::value()` operator precedence

## Symptom
```
thread 'main' panicked at hyperon-space/src/index/trie.rs:179:71:
  called `Option::unwrap()` on a `None` value
```
Process aborts (exit 101; SIGABRT under some hosts). A MeTTa program cannot
observe it and an application embedding `libhyperonc` loses the host process.

Two reproducers, both on stock `3f76dc4`:

**(a) a `match` returning >=1022 results**
```metta
(imp 0 n0 1000)
…
(imp 0 n1021 1000)
!(match &self (imp 0 $c $v) $c)
```

**(b) conjunction ORDER changes the outcome at identical denotation** —
3000 facts, 400 in the bucket:
```metta
!(match &self (, (bucket b0 $c) (imp 0 $c $v)) $v)   ; selective first -> OK
!(match &self (, (imp 0 $c $v) (bucket b0 $c)) $v)   ; broad first     -> PANIC
```
Both denote the same set and return the same 400 results. The second
materialises 3000 candidates before the filter, which is what crosses the
threshold.

## Cause
```rust
// :531, in TrieKey::new -- stored values are offset
value += TK_MAX_EXPRESSION_SIZE;

// :544 -- and the offset is meant to be removed here
fn value(&self) -> usize {
    self.0 & TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE
}
```
In Rust `-` binds tighter than `&`, so this parses as
`self.0 & (TK_VALUE_MASK - TK_MAX_EXPRESSION_SIZE)` — a mask that clears bit 10
— not `(self.0 & TK_VALUE_MASK) - TK_MAX_EXPRESSION_SIZE`.

The two agree only while `floor(v / 1024)` is even:

| stored `v` | raw `v+1024` | as written | intended |
|---|---|---|---|
| 1023 | 2047 | 1023 | 1023 |
| **1024** | 2048 | **2048** | **1024** |
| 2047 | 3071 | 3071 | 2047 |

So the decode is wrong once a hashable atom index reaches 1024, and
`get_atom_unchecked` (`:179`) unwraps a `None`.

## Patch and effect
`01-trie-value-precedence.patch` — parentheses.

```
                          stock     patched
bare match, n=1022        PANIC     OK, n_results 1022
bare match, n=2000        PANIC     OK, n_results 2000
bare match, n=5000        PANIC     OK, n_results 5000
broad-first conjunction   PANIC     OK
```
`cargo test -p hyperon` **298 passed / 0 failed**; `-p hyperon-space` 29 + 6
passed / 0 failed.

### The fix costs ~7%, and the reason is worth stating
`TK_VALUE_MASK` (`:504`) and `TK_MAX_EXPRESSION_SIZE` (`:511`) are both `const`,
so the buggy form `self.0 & (MASK - MAX)` folds the subtraction at **compile
time** and emits a single `AND`. The corrected form must subtract at runtime,
after the mask. Measured on a MeTTa fold workload: the patched build is
uniformly ~7% slower.

So the original is faster and wrong. If that cost matters in a hot path, the
zero-cost shape is to stop using an **offset** as the discriminator: `value()`
subtracts 1024 only because `new()` adds it at `:531`, purely so that
`is_start_expr()` (`:568`) can test `self.0 < TK_MAX_EXPRESSION_SIZE`. A spare
tag bit alongside `TK_STORE_MASK` / `TK_MATCH_MASK` would let `value()` be a
plain mask again and remove the failure mode by construction rather than
correcting it.

We are not proposing that layout change — it touches the bit budget and the
reason the field is 10 bits is not in the code. Recording the trade so the
choice is yours: **the attached patch is correct and ~7% slower; a re-layout
could be correct and free.**

**There is no `match` arity ceiling.** Earlier drafts of this report claimed one
at 1022 and explained it as "head plus wrapper". That explanation was fitted to
a number produced by this bug.

---

# Defect 2 — 1023 children per expression, enforced by `assert!`

Independent of Defect 1 and **still present after it is fixed**.

```metta
(f 0) … (f 1023)
!(collapse (match &self (f $x) $x))
```
```
n=1023  exit 0
n=1024  panicked at trie.rs:539:9: assertion failed: size < TK_MAX_EXPRESSION_SIZE
```

```rust
// :511
const TK_MAX_EXPRESSION_SIZE: usize = 1 << 10;
// :537-540
const fn start_expr(size: usize) -> Self {
    assert!(size < TK_MAX_EXPRESSION_SIZE);
    Self(TK_STORE_HASH | TK_MATCH_EXACT | size)
}
```

`TrieKey` packs an expression's child count into 10 bits. `grep -rn
TK_MAX_EXPRESSION_SIZE` finds **no call site that checks the bound before
calling `start_expr`** — the `assert!` is the only guard. `collapse` builds one
expression holding every result, so the bound lands on result-set cardinality.

A 10-bit arity field is a defensible design decision. `assert!` as its
enforcement is what makes it unusable from a library: **a data-dependent
condition should not abort the host process.**

## Precedent from your own design
MeTTa already treats a resource limit as a *result* rather than a death: a step
ceiling yields a value every honest evaluator agrees on, and an unresolved
symbol yields an `(Error …)` atom a program can inspect. This condition is the
same category, handled differently.

## Suggested directions, increasing effort
- **Return an `(Error …)` atom** instead of asserting. Smallest change, keeps
  the limit, makes the failure observable and recoverable.
- **Widen or remove the arity field.** `TK_VALUE_MASK` needs re-layout; a real
  cost, and the only change that removes the cap rather than reporting it.

*Not suggested:* cost-ordering conjunctions so the selective pattern runs first.
That was in an earlier draft. It would have hidden Defect 1's trigger while
leaving the wrong memory read in place, to resurface wherever else an index
passes 1024.

---

## Environment
`3f76dc4`, release, `aarch64-apple-darwin` and `aarch64-linux-android`.
Both defects reproduce identically on both.

## Why we care (context, not a request)
We run the same job on several machines and compare output bytes. A panicking
worker emits nothing, so a crash removes a replica rather than disagreeing with
one — and because both thresholds are data-dependent while the query author
picks the program, that is reachable deliberately. Defect 1 also made it
reachable by accident, through a refactor that preserved meaning.
