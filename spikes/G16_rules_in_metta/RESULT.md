# G16 — cross-engine check found a hyperon panic at exactly 1024 results

**Verdict: 1/5 agreement, and the four failures are two of my bugs plus one
upstream defect that caps every query in this workspace.**

```
     rule   edges   python   metta  agree       fuel  device
(157, 73)     746      123     123    YES     251431  IDENTICAL
(197, 64)     915      128       0     NO   PANIC     IDENTICAL
(130,  4)    5762       31       0     NO   PANIC     IDENTICAL
(130,  5)    5765       27       0     NO   PANIC     IDENTICAL
(114,114)     100      132     144     NO     223275  IDENTICAL
```

## The upstream finding

```
thread 'main' panicked at hyperon-space/src/index/trie.rs:539:
  assertion failed: size < TK_MAX_EXPRESSION_SIZE
```

```rust
trie.rs:511   const TK_MAX_EXPRESSION_SIZE: usize = 1 << 10;   // 1024
trie.rs:537   const fn start_expr(size: usize) -> Self {
trie.rs:539       assert!(size < TK_MAX_EXPRESSION_SIZE);
```

Bare `assert!` in a `const fn`, **no guard anywhere in the tree**. Bisected
exactly:

```
1020 atoms  ->  status OK
1023 atoms  ->  status OK
1024 atoms  ->  PANIC
```

Minimal reproducer is 1024 facts and one `collapse`:

```metta
(e x0) … (e x1023)
!(collapse (match &self (e $a) $a))
```

### Why this matters beyond G16

**`collapse` is the primitive every G-series spike uses**, and 1024 is small —
any query over a real KG exceeds it immediately. `(197,64)` had 915 edges and
overflowed on the *results*.

For the verification design it is worse than a limit. `hyperjob_v0.proto`
separates `RESULT_FUEL_EXHAUSTED` (deterministic, agreed by every honest device,
payable) from `RESULT_DEADLINE_EXCEEDED` (infrastructure, unpaid). **A panic is
neither.** It is deterministic — both devices abort identically — but it
produces no envelope at all, so there is nothing to hash, nothing to compare and
nothing to pay. A job class that can panic has an outcome the schema cannot
represent.

Drafted for upstream in `proposed/hyperon-collapse-panic/`.

## Two of the four failures were mine

**`(114,114)`: 132 vs 144, difference 12.** The MeTTa program had **no `c != a`
guard** while the Python reference did. Twelve self-loops. My emitter, not a
disagreement.

**`(130,4)` and `(130,5)`: `fuel = ?`.** My field parser returned `?` because the
process had panicked and printed no `fuel_used` line. I reported "metta 0,
disagree" when the truthful report is "the engine crashed". A missing field read
as a wrong answer — the same shape as an empty hash read as agreement.

## What did work

`(157,73)`: **123 = 123**, exact agreement between a Python index walk and
hyperon's matcher over 746 edges, and the run is **byte-identical on desktop and
phone**. That is a genuine cross-engine control in MORK's `differential/run.py`
tradition — two independently written implementations over one corpus.

**Device identity held on all five**, including the three panics: the phone
panicked identically. Determinism extends to crashing.

## What this does NOT show

- **1/5 is not a validation.** One rule agreed; three could not run and one
  exposed my own missing guard. The cross-engine check is a good instrument that
  has barely been used.
- The scoped subgraph (body-predicate edges only) tests agreement, not scale.
- G15's mining is still Python. This shows hyperon can *apply* a discovered rule
  and agree, not that it discovered anything.

## Reproduce

```sh
cd spikes/G16_rules_in_metta && python3 apply.py
../S30_speed_duel/bin/fuelrun.v2.host lim_1024.metta 50000000   # the panic
```
