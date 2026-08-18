# S40 — what the oracle cutoff costs: 4×–122× in rows checked, and it is survivable

**Verdict: GREEN, and the news is good in the direction that matters.** A cutoff
computed from the **query alone** holds **recall 1.0000 at every B tested on a
clustered store**. The design does not need an oracle. But it pays **4×–122×
more rows checked** than the fitted cutoff every published magnitude in this tree
was measured with.

Closes the `out/LEDGER.md` "NEVER MEASURED" row: *"A fixed (non-oracle) cutoff —
every bundling result uses a cutoff fitted to the ground truth. A deployed
prefilter cannot."*

Code `cutoff.py`, data `cutoff.json`. n=60,000, D=1024, 60 queries per cell,
2-bound pattern `(p s ?o)`, seed `0xC0FFEE`, host, `spikes/S5_hdc_prototype/.venv`.

## The two cutoffs

| | how it is chosen | deployable? |
|---|---|---|
| **ORACLE** | swept down until it retrieves every answer bucket | **no** — needs the answer |
| **FIXED** | `nnz(Q)/√B`, from the query, before any data is read | **yes** |

`ORACLE` recall is **1.0 by construction** — it is *defined* as the cut that
retrieves everything, so its only informative column is rows checked.

## Measured

```
   B  layout     buckets |  ORACLE checked%  |  FIXED recall   FIXED checked%
   1  random       60000 |          0.0112   |      1.0000           0.0112
   1  clustered    60000 |          0.0117   |      1.0000           0.0117
   4  random       15000 |          4.9599   |      0.2852           0.3642
   4  clustered    15000 |          0.0614   |      1.0000           7.5066
  16  random        3750 |         37.2453   |      0.6595          18.5311
  16  clustered     3750 |          0.5947   |      1.0000          10.0471
  64  random         937 |         68.2480   |      0.9368          83.9808
  64  clustered     937 |          2.7357   |      1.0000          11.2949
```

## Three findings

### 1. At B=1 the fixed cutoff is not an approximation of the oracle — it IS the oracle
`0.0112` vs `0.0112`, recall 1.0 both, on both layouts. S5/S10's analytic bound
(a matching triple scores exactly `nnz(Q)` on the halved ternary query) is exact,
and nothing is bought by knowing the answer. **The unbundled prefilter has never
needed an oracle**, and S43/S44's numbers were never oracle-assisted.

### 2. Clustering is what makes a DEPLOYABLE cutoff possible, and that is a stronger claim than the tree had
Random layout, fixed cutoff: recall **0.2852** at B=4 — it loses 71% of answers.
Clustered: **1.0000 at every B**. S11/S17/S47 established clustering matters
*with a fitted cutoff*; this shows it matters more, because it is the difference
between a prefilter that can be deployed and one that cannot be.

### 3. The oracle's price, and it SHRINKS as B grows

| B (clustered) | oracle | fixed | penalty |
|---|---|---|---|
| 4 | 0.0614% | 7.5066% | **122×** |
| 16 | 0.5947% | 10.0471% | **17×** |
| 64 | 2.7357% | 11.2949% | **4.1×** |

So every bundled magnitude in this tree is **oracle-assisted in rows checked**,
by between 4× and two orders of magnitude, and the assistance is largest exactly
where the published figures look best. S47's 54× total-query-cost at B=64
clustered was measured with the fitted cut checking ~2.7%; a deployable prefilter
checks ~11.3% — the shaping benefit shrinks but does not vanish.

The penalty **falling** with B is the counter-intuitive part and it has a clean
reading: bundling already forces the oracle to loosen, so there is less advantage
left for knowing the answer to buy.

## What this does NOT show

- **Synthetic uniform graph.** S52 measured every shaping magnitude shrinking
  ~10× when moved from exactly this generator to FB15k-237, so treat the
  *ratios* as the result and expect the absolutes to move on real data. The
  fixed-vs-oracle comparison is internal to one store, which is the part that
  should transfer.
- One query class (`(p s ?o)`, m=2), one D, one seed, one B-ladder. **One draw is
  not a rate** (LEDGER standing rule 6); this is one draw per cell over 60 queries.
- `nnz(Q)/√B` is the analytic random-walk estimate. It is not *derived* — S17
  called it "a guess above B=1" and this shows the guess holds recall on a
  clustered store, not that it is optimal. A tighter fixed rule would reduce the
  4×–122× penalty and nobody has looked for one.
- Host only. No device, no NEON, no bundled-store timing — this counts rows, it
  does not time them.

## Reproducing

```sh
./spikes/S5_hdc_prototype/.venv/bin/python spikes/S40_fixed_cutoff/cutoff.py 60000 1024
```
