# G18 — the ceiling is `match`, not `collapse`, and conjunction order decides between working and process death

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
