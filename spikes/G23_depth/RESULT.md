# G23 — depth-3 structure is real, materialisation is a bad way to reach it, and depth pays less than width

**Three results, each against its own null.**

```
               real  null mean  null sd      gap  gap/sd  >=real
depth 2      0.4405     0.3249   0.0104  +0.1157    11.1    0/20
depth 3      0.3914     0.2966   0.0204  +0.0949     4.7    0/20

G22 materialisation   0.0956  against its own control  0.1222   gap -0.0266
```

1. **Depth-3 composition structure is real.** +0.0949 above its own null at 4.7
   null-sd, 0/20 shuffles reach it.
2. **Materialisation is a bad way to reach it.** G22's rewrite scored *below*
   its control (−0.0266) while direct depth-3 mining scores well above its own
   (+0.0949). The structure was there; writing deductions back into the graph
   failed to expose it.
3. **Depth pays less than width.** The depth-3 gap (+0.0949) is smaller than
   depth-2's (+0.1157), and its null is twice as noisy (sd 0.0204 vs 0.0104).
   Going deeper finds weaker structure, less certainly.

## Why each depth needed its own null

Comparing depth-3's raw 0.3914 against depth-2's raw 0.4405 would be invalid.
Depth 3 searches a much larger rule space (4,659 rules vs 3,527, over 9,032,120
prefix pairs), and a top-12 taken from more candidates is inflated by selection
alone.

**The measurement proves the concern was real:** the depth-3 null mean is 0.2966
with sd 0.0204, against depth-2's 0.3249 ± 0.0104. The deeper search's baseline
is *twice as variable*, so the same headline number means something different at
each depth. Only the gap to its own null is comparable — which is the same
lesson G21 forced, where a degree-preserving shuffle alone reproduced 74% of the
depth-2 statistic.

## What this does to the G22 explanation

G22 offered: *"a materialised deduction carries no information — `derived` is a
function of `train`, so a 2-hop rule over `train + derived` is a longer-path rule
over `train`, reached badly."* That was written as an explanation fitted to a
number, and flagged as such, to be tested rather than believed.

**The second half survives; the first half does not.**

- *Reached badly* — **confirmed.** Direct depth-3 mining finds real structure
  (+0.0949) exactly where materialisation found less than nothing (−0.0266).
- *Carries no information* — **refuted as stated.** The structure depth-3 mining
  reaches is genuinely there and genuinely predictive. Materialisation's failure
  is not that the structure is absent or informationless; it is that collapsing
  a chain into a derived predicate loses the distinction between the derived
  edges and the real ones, and mines a mixture instead of the chain.

Recording the refutation because the fitted explanation was mine and it was half
wrong in the direction that flattered it.

## The restriction, which biases *against* this conclusion

Full depth-3 mining over 217k edges is unaffordable here, so depth-3 body
prefixes were restricted to the **top 60 depth-2 bodies by support**. That
**favours depth 3**: it searches extensions of the prefixes that already work
best, and it still lost to depth 2. A conservative restriction that fails to
overturn the result strengthens it.

## Cross-implementation agreement

Depth 2 here reproduces **0.4405** — matching `G17_composition_redo` (Python,
different code path) and `G21_null_rust` (Rust) to four decimals. G23's depth-2
nulls (mean 0.3249, sd 0.0104) also sit on G21's null distribution (mean 0.3281,
sd 0.0121, n=500).

**Two independent implementations agree on the baseline, not only the headline.**
That is the stronger check: a shared bug would have to reproduce a whole
distribution, not one number.

## What this does NOT show

- **Not that depth is worthless.** Depth 3 clears its null at 4.7 sd. It finds
  real structure — just less of it, less certainly, than depth 2.
- **Not full depth-3 mining.** Restricted to 60 prefixes. An unrestricted search
  might find stronger rules outside those prefixes, and this cannot exclude it.
- **Not a p-value.** 0/20 at both depths means p is floor-limited at 1/21 =
  0.048 — the same structural floor G21 documented at n=500. The gap and its
  sd carry the information; the p does not.
- **20 draws is few.** Enough for a mean and an sd, not for a tail. Depth-3
  nulls cost ~3 min each because shuffled graphs have far larger top-60 bodies
  than the real graph does.
- Single split, single machine, `0xC0FFEE`, 80/20.

## Reproduce

```sh
cd spikes/G23_depth && python3 depth.py     # ~65 min, dominated by depth-3 nulls
```
