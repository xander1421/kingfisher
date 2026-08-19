# H203 — `rnd.choice(list(set_of_bytes))`, and F2 fired

`repro: python3 spikes/H203_stream_order_determinism/probe.py`
`check: python3 kitchen/test_h203.py`

**`certify ok=True`, 3 controls all fired. F1 did not fire. F2 FIRED, was
investigated to a verdict before anything shipped, and the investigation produced
a second finding.** This is the repair H197 measured and deliberately left open.

## THE CAUSE, AND IT IS FOUR LINES

```
W7/streaming_verifier.py:337,343        rnd.choice(list(live_set))
W9/bound_streaming_verifier.py:610,615  rnd.choice(list(live_set))
```

`live_set` is a `set` of **bytes**, and CPython randomises `bytes`/`str` hashing
per process. **The RNG is perfectly seeded and the sequence it indexes into is
not**: `rnd.random()` returns the same float on every run while
`list(live_set)[i]` is a different key. That is why recording `'seed': SEED` in
the artifact meant nothing — the seed was never the uncontrolled input.

Class swept tree-wide: `grep -rn 'choice(list(\|sample(list(\|shuffle(list('`,
`--include=*.py`, `.venv` excluded → **those four sites and nothing else.**
Fix is `sorted(live_set)`.

## F1 — DELIBERATELY STRONGER THAN THE TEST THAT FOUND THE BUG

H197 proved stability by running `PYTHONHASHSEED=0` twice, which only shows that
a *fixed* hash seed gives a fixed answer. **F1 runs `PYTHONHASHSEED=1` against
`PYTHONHASHSEED=2` and requires identical 64-hex values.**

```
W7   16 hashes   differ across hash seeds = 0    moved vs HEAD = 10
W9   13 hashes   differ across hash seeds = 0    moved vs HEAD =  3
```

**F1 does not fire.** `C1` is what stops that green being the *old* stability:
sorting reorders the stream, so the hashes **must** move against HEAD — **13
did**. An edit that never executed would leave them byte-identical and C1 would
refuse.

## F2 FIRED: `W9/falsifier_fired` WAS `true` AT HEAD AND IS `false` NOW

Preregistered: *if any invariant changes, the fix altered the experiment and not
just its ordering, and it stops for review rather than shipping with a quietly
different benchmark.* It stopped. Here is the review.

W9's falsifier is a **disjunction of five terms**, and one of them is a
**wall-clock threshold**: `shard_res['median_latency_us'] > 500.0`.

```
committed at HEAD   median_latency_us = 508.71   -> term TRUE  -> falsifier_fired: true
today, fixed code   median_latency_us = 206.79 / 210.21 / 205.88 / 208.58
```

Every other term is unchanged: `all_72b` true, `bound_fork_rejected` true,
`bound_inflation_defeated` true, and the depth-20 bandwidth comparison.

**THE A/B THAT SEPARATES LOAD FROM THE FIX, because the argument was not
good enough.** The two `sorted()` lines were temporarily reverted in place, W9
run twice on the *pre-fix* code today, and the file restored:

```
PRE-FIX code, today    median_latency_us = 205.92,  212.27   falsifier_fired = false
POST-FIX code, today   median_latency_us = 205.88 – 210.21   falsifier_fired = false
```

**The pre-fix code produces the same latency as the fixed code.** So the flip is
**not** caused by this change: HEAD's `508.71` was recorded while this machine was
running five lanes, 1.7% over the threshold. `C3` licenses that reading rather
than leaving it to prose — it refuses if today's median sits within ~20% of 500,
because then the attribution would be undecided. Today's headroom is **2.4x**.

**VERDICT: F2 fired, the review clears the fix, and the fix ships.** The falsifier
did its job — it stopped a change I was confident about until I had measured the
thing I was assuming.

## THE SECOND FINDING, WHICH IS W9'S AND NOT MINE

**A preregistered falsifier containing a wall-clock term fires or does not
depending on machine load at the moment of the run.** W9 published
`falsifier_fired: true` — its own headline refutation — on a **1.7% threshold
crossing of a timing**, and the same code returns `false` on an idle machine.
That is family **E**: a threshold applied to a load-dependent quantity, published
without its operating point.

**I am not touching it in this row** (§12.1, and it is W9's row, not this one).
It is filed OPEN. What this row owes it is the measurement above, so whoever
takes it starts from numbers rather than from my opinion.

## I TURNED MY OWN CHECK RED ON PURPOSE, AND UPDATED IT WITH A REASON

`kitchen/test_h197.py` asserted `n_unstable_default == 10` and `== 1`. Fixing W7
and W9 drives both to **0**, so it had to go red — **that polarity was designed
and stated in H197's docstring**, and it is the only thing that would have made
someone re-read the row. It is updated to assert the post-fix state with a block
naming H203, **not silently relaxed**, and H197's measurement is preserved in its
own `RESULT.md` as the pre-fix record.

## C2 REFUSED MY FIRST INVARIANT LIST, THE SECOND TIME IN TWO CYCLES

The first run returned `certify ok=False — CONTROL C2_invariants_were_found DID
NOT FIRE — run is VOID`. My `INVARIANTS` tuple was hand-typed from memory
(`honest_all_passed`, `mutations_rejected`, …) and matched **nothing** in W9's
artifact, so F2 would have passed having checked zero fields. **Same failure as
H197's C2 an hour earlier, same cause: a name list typed rather than derived.**

Fixed structurally, not by adding names: **every boolean field is a verdict by
construction and cannot be mis-typed**, so the verdict set is now collected by
walking the artifact. `total_events` is named explicitly as the one int that must
not move. **Byte counts are deliberately NOT invariants** — sorting changes which
keys the stream touches, so `cum_witness_bytes` and friends legitimately move,
and asserting on them would make F2 fire on the fix *working*.

## SCOPE

The published chain heads in W7 and W9 **change with this commit** — 13 hashes.
That is the point of the fix, not a side effect, and no document quoted the old
values (H197 measured: 0 of 11 quoted anywhere). Nothing here addresses W9's
wall-clock falsifier term, and nothing here claims the streams are deterministic
across Python *versions* — only across processes of one version.
