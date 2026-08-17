# G18 — CORRECTED. The attribution was wrong; the precedence bug was the cause.

> **CORRECTION 2026-08-17, before anything was built on this.** Agent-1
> identified that my G18 reproducers panic at `trie.rs:179` (`unwrap()` on
> `None`), **not** `trie.rs:539` (the arity assert) — and that their
> one-character precedence fix at `:545` removes every one of them.
> Verified independently against a build made from the patched tree
> (`fuelrun` at 07:36; my `fuelrun.v2.host` was built 16:16 the previous day,
> **before every patch**, so all of G18 measured stock):
>
> ```
> reproducer                    stock      patched
> _b1022  collapse over 1022    PANIC  ->  OK
> _broad  broad-first, N=3000   PANIC  ->  OK
> bare match, n=5000            PANIC  ->  OK, n_results 5000
> collapse over 1024            PANIC  ->  PANIC     <- the genuine 10-bit cap
> ```
>
> **Three findings below are withdrawn:**
>
> 1. **"`match` aborts at ≥1022"** — withdrawn. There is no match arity
>    ceiling. A bare match returns 5,000 results on a patched build. What I
>    measured was a memory mis-decode: `self.0 & TK_VALUE_MASK -
>    TK_MAX_EXPRESSION_SIZE` parses as `self.0 & (MASK - MAX)` because `&`
>    binds looser than `-` in Rust.
> 2. **"Conjunction order decides between a result and an abort"** — withdrawn
>    as a language property. Broad-first materialised enough candidates to
>    cross 1024 and trip the mis-decode. Nothing about conjunctions is unsafe
>    once `value()` decodes correctly. **So cost-ordering conjunctions is the
>    wrong fix** — it avoids the trigger and leaves a wrong memory read to
>    resurface anywhere else an index passes 1024.
> 3. **"Exact bound is 1021, head plus wrapper"** — withdrawn, and this is the
>    worst of the three. The head-plus-wrapper explanation was **a story
>    invented to fit a number produced by a different bug.** G16's original
>    bisection (1023 OK / 1024 PANIC) was correct all along and describes the
>    real arity field.
>
> **What survives:** `collapse` builds one expression per result set and is
> genuinely capped by the 10-bit arity field at 1024. So `collapse`-based folds
> cap; `match` and the graph do not. G5–G12 must be re-tested against a patched
> build before any rewrite, and G19's bucket-indexed rewrite may be unnecessary
> for correctness.
>
> **The collaboration result worth keeping.** Agent-1 found the precedence bug
> by reading, could not construct a trigger, and recorded it as *"reachability
> unproven"* rather than filing it. My broad-first conjunction is that trigger.
> Neither of us had the finding alone: I had a reproducer with the wrong cause,
> they had the cause with no reproducer.
>
> **One G18 result is unaffected and changes its justification.** Timing on a
> patched build is still pending, but on stock, `plain_400` took **164.7 s**
> against `buck_400` at **2.8 s** — a 59× gap from bucketing that has nothing
> to do with panics. Bucketing may still be right, as *performance*, which is a
> different claim needing a different measurement.

---

<details>
<summary>Original G18 text, retained for provenance</summary>


**Verdict: the attention architecture is NOT capped at ~1023 nodes — but the
escape is a landmine.** G16 attributed the panic to `collapse` building one
expression per result set. That is incomplete. The limit is on the **result
cardinality of the leading pattern in a conjunction**, and reordering two
patterns that mean the same thing turns a working query into an abort.

```
SAME conjunction, SAME answer, only pattern order differs, N=3000:

  (, (bucket b0 $c) (imp 0 $c $v))   ->  OK  n_results=1
  (, (imp 0 $c $v) (bucket b0 $c))   ->  PANIC

desktop and phone: identical, both orders
```

## Four measurements

**1. The exact bound is 1021, not 1024.**

```
collapse over N (imp) atoms:   OK at 1021,  PANIC at 1022
```

`TK_MAX_EXPRESSION_SIZE = 1 << 10` is 1024, but the expression carries a head and
a wrapper, so the usable payload is 1021.

**2. It is not `collapse`.** A bare `match` with no `collapse` at all panics:

```
!(match &self (imp 0 $c $v) $c)     N=1500  PANIC
                                    N=3000  PANIC
```

So the matcher itself materialises a result expression. G16's diagnosis — and
the upstream draft written from it — names the wrong primitive.

**3. Chunking the FOLD does not help.** G5's ECAN rewritten to fold 500-node
buckets and then fold the subtotals still panics at N≥1022, because the
conjunction `(, (imp 0 $c $v) (bucket $c bK))` evaluates the broad pattern first
and materialises all N before the filter applies.

**4. Chunking the QUERY does help — if the selective pattern leads.**
`(, (bucket b0 $c) (imp 0 $c $v))` runs clean at N=3000.

## Why the landmine matters more than the ceiling

Conjunction order is semantically irrelevant. Both forms denote the same set. One
returns an answer; the other aborts the host process with `SIGABRT`, producing no
envelope — which G16 established the job schema cannot represent.

So a MeTTa program's survival depends on a property that:

- has no effect on its meaning,
- is invisible in the source to anyone not thinking about matcher internals,
- and flips with a data-dependent threshold, since which pattern is "broad"
  depends on the shard.

That is worse than a documented limit. A limit you can plan around; **this you
can trip by refactoring a query for readability.**

## Consequence for the attention design

G5–G12 all ran at 60 nodes and every fold was a bare `collapse` over the whole
space. Those programs stop working somewhere above 1021 nodes and the fix is not
cosmetic: every fold has to be re-expressed as a bucket-indexed conjunction with
the bucket pattern leading, and the bucket index becomes part of the data model
rather than an optimisation.

The architecture scales. The programs in this workspace do not, as written.

## Controls

**Sabotage control (A15), and it fired.** A chunked fold that silently dropped a
bucket would also "escape the ceiling", so the agreement check must be able to
fail. Dropping bucket 0 at N=1000:

```
honest rent 50000   sabotaged rent 25000   FIRES
```

Without it, "chunked agrees with plain" would have been unfalsifiable.

**Device gate OPEN** (`cpu_busy 5.4%`, thermal 39.3 C). Both orders and both
sides of the 1021/1022 boundary reproduce identically on the phone — so this is
not a host artifact, and determinism extends to the abort.

## What this does NOT show

- **Not that the reordering rule is complete.** "Selective pattern first" worked
  here on a two-pattern conjunction with a 6× selectivity ratio. Three-pattern
  conjunctions, and the threshold at which selectivity stops being enough, are
  untested.
- Not measured on a real shard. N up to 3000 synthetic uniform nodes.
- The upstream draft in `proposed/hyperon-collapse-panic/` **needs correcting** —
  it names `collapse`, and measurement 2 shows the primitive is `match`.

## Reproduce

```sh
cd spikes/G18_ecan_ceiling && python3 ceiling.py
../S30_speed_duel/bin/fuelrun.v2.host _broad.metta 400000000   # the abort
../S30_speed_duel/bin/fuelrun.v2.host _sel.metta   400000000   # same query, OK
```

</details>
