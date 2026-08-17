# W4 — the prefilter's read set. Answer: 100%, by construction, and it cannot be made sublinear without changing what the prefilter is.

**Verdict: the gating question is answered, negatively. The read set is the entire prefilter index on every query, for every shape, because the prefilter is a similarity search and similarity has no key order to skip on. Witnessed re-execution over this structure is not available.**

Opened when W1 was invalidated. Code: `rk_inst.c` (S52's `realkg.c` with bundle-read
counters, host-built, affinity stubbed since this counts reads not time).
Output: `ampl.txt`. Reproduces S52's published table exactly — 0.2% / 1.0% / 8.8%
store-checked for `(pred,subj)` — which is the provenance check.

## 1. Why there is no early exit, and why one cannot be added
`realkg.c:75-84`, `score_row`, is a Hamming similarity over the whole
hypervector:
```c
uint64x2_t x = vandq_u64(veorq_u64(t,s), m);
v = vaddq_u8(v, vcntq_u8(...));
return 2*nnz - 4*(int32_t)vaddlvq_u8(v);
```
Then `:184`: `for(int b=0;b<nb;b++) scores[b]=score_row(...)`. No bound, no test,
no `continue`.

**This is not an omission.** A key lookup on a sorted array can skip because
order in the key *is* order in the file. A similarity search cannot: the nearest
neighbours of a query hypervector are **not contiguous in any key ordering**, so
there is no prefix to bound. W1's invented `if ((qp,qs) < lo || (qp,qs) > hi)
continue` presumed a key lookup. The engine does not do key lookups.

> **Read set = 100% of the prefilter index, per query, for every shape.**

## 2. Measured read amplification — and what it is not
```
bundles in index          4,252
score-pass bundle reads   6,122,880
cutoff-pass bundle reads  475,067,456   over 111,728 cutoff iterations
total / score-pass        78.59x
```

**The 78.59× is harness, not algorithm, and I nearly reported it as a result.**
The cutoff loop (`:187-194`) searches downward for the smallest threshold that
achieves full recall — it reads `truth`. S52 already flags this: *"the cutoff is
still chosen by an oracle reading `truth`, because a fixed cutoff cannot reach
recall 1.0 on a bundled store."*

It is also **outside the timed region**: `pf` is measured across the score pass
only (`:183-185`), and the reported µs is `pf + checked*per_check`. So S52's
timings correctly exclude it, and a deployment using a fixed cutoff would not run
it.

**Deployed read set is therefore 1× the index, not 78×.** Recording the
distinction because the 78× is the more dramatic number and it is not the
answer.

### ATTACK cycle 8 correction — "harness a deployment wouldn't run" is half right
S52 states plainly: *"**a fixed cutoff cannot reach recall 1.0** on a bundled
store."* If that holds, a deployment **cannot** simply drop the oracle loop and
keep S52's results. Three readings, and only one is viable:

| option | consequence |
|---|---|
| fixed cutoff | oracle loop gone, read set 1× — but **recall < 1.0**, and S17 already measured a **0/100 worst case** on the exact scan |
| oracle cutoff | needs ground truth. Not implementable |
| **top-N by score** | no ground truth needed, one pass with a heap, still `O(nb)`. **Recall is whatever top-N gives, and that is unmeasured** |

So the honest statement is sharper than the original: **the deployed read set is
1× the index, but at a recall level nobody has measured.** S52's published µs
figures correspond to a configuration that requires ground truth, and therefore
to a recall no deployment can reach. That is a caveat on S52's timings, not only
on W4.

### ATTACK cycle 8 — probabilistic spot-check does not rescue this
Before concluding "full re-execution or nothing", I tested the obvious
alternative: a verifier samples *m* of *nb* bundles and recomputes only those.

| bundles altered *k* | m=100 | m=425 (10%) | m=850 (20%) |
|---|---|---|---|
| **1** | 2.3% | 9.5% | **18.1%** |
| 5 | 11.1% | 39.4% | 63.2% |
| 20 | 37.6% | 86.5% | 98.2% |
| 100 | 90.7% | 100% | 100% |

Promoting a single false positive is the minimum useful cheat, and at *k*=1 a
verifier reading **20% of the index** still catches it only **18%** of the time.
Spot-checking is not a substitute. **W4's conclusion survives this attack.**

## 3. Can it be made sublinear?
Only by replacing it with an approximate-nearest-neighbour index — LSH, IVF,
HNSW. That is a different data structure with a different contract:

- **It trades recall.** S17 already measured worst-case recall on the exact
  scan at **0.97 mean with a 0/100 minimum** — at least one query loses
  everything. An ANN layer makes that worse by construction, and nobody has
  tuned for worst case.
- **It changes what S52 measured.** The shaping matrix (4.1–5.6×) compares
  clustered against random layout *under a linear scan*. Under an ANN index the
  comparison is between index qualities, not layouts, so the shaping result does
  not carry over. This is the trap the W1 reviewer named.
- **It is not in any elder.** GAP row 6's rewrite covers NPU runtimes; no ANN
  index exists in the 32 repos.

## 4. Consequence for verification
Witnessed re-execution needed a small read set. There isn't one:

| | witness |
|---|---|
| W1 claimed | 4.4 KB |
| actual, B=64 index | **~1.5 MB** |
| actual, B=8 index (the 12.8 MB figure) | **~12.2 MB** |

So **residency coupling is not cut**, the fleet-wide verification pool is not
restored, and C4's rare-shard attack stays live. The S69/S70 *diagnosis* stands
and has no fix.

Three routes remain, none costed:
1. **Verify the exact-match stage only**, treating the prefilter as an untrusted
   accelerator whose output is checked by the (small) exact stage. Changes what
   is being proved.
2. **Resident verifiers** — accept residency coupling and pay C4's cost, with a
   replication floor priced from `Δ` once `Δ` exists.
3. **A commitment to the prefilter's output** rather than its input, which
   leaves the prefilter unverified — the objection W1's reviewer raised.

## Controls — stating the failing input for each, per D6
| control | fails if |
|---|---|
| table reproduces S52 | any cell differs from 0.2/1.0/8.8% for `(pred,subj)` — it would mean the instrumented binary is not the measured engine |
| counters are non-zero | zero score-pass reads would mean the counter is not on the hot path |
| cutoff reads > score reads | if equal, the cutoff loop is not scanning and the 78× claim is wrong |
| amplification is bounded | an unbounded ratio would indicate the counter is inside `score_row` rather than around the pass |

All four pass. Note the first is the one that matters: it ties this binary to
S52's published numbers.

## Caveats
- Host build, FB15k-237, `(pred,subj)` clustering, S52's uniform-over-triples
  query generator — the same artefact `Δ` flagged everywhere else.
- "Cannot be made sublinear" is a structural argument about similarity search,
  not an exhaustive search of index designs. It is falsifiable: exhibit an index
  giving sublinear reads at S17's recall floor without changing S52's layout
  comparison.
