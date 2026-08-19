# G106 — the null barely moves across the leak, so the leak is entirely in the SYSTEM: +0.1300 of lift, and G102's +0.1290 was right for a reason nobody had checked

F1–F4 stated in `CHANNEL.md` before this directory existed. **None fired.**
`certify ok=true`, **4 controls fired**, 10 s.
Run: `PYTHONUNBUFFERED=1 python3 spikes/G106_shuffle_null/run.py` ·
`shuffle_null.json`

## 1 · The measurement `config.json` marks NEVER MEASURED

| split | null (no-rules prior) | system | **lift** |
|---|---|---|---|
| 70/15/15 shuffle (30.01% leaked) | **0.172163** | 0.264807 | **+0.0926** |
| pair-disjoint (leak-free) | 0.173226 | 0.135800 | **−0.0374** |
| | | **the leak, as lift** | **+0.1300** |

Every other split had its null — pair-disjoint 0.1732 (G49, reproduced by G104
to six places), official 0.2334 (G59 `A_prior`). The shuffle's was the gap, and
the shuffle is the split that produced **0.2648**, the number `PROGRAM.md:40`
still derives its `>= 0.2500` bar from and that the operator has withdrawn.

## 2 · THE FINDING IS THAT THE NULL DOES NOT MOVE

**0.172163 against 0.173226 — a difference of 0.001 across a split that leaks
30.01% of its test triples.** The frequency prior is **leak-insensitive**, and
that is not obvious in advance: it is what makes the raw comparison legitimate.

**A same-pair leaked test triple hands you an `(s, o)` edge that already exists
in train under some other predicate. A predicate-conditional frequency prior
cannot use that — it never looks at `s` when ranking `o`. A rule system can, and
does.** So the entire +0.1300 sits in the system.

**This confirms G102's +0.1290 raw MRR gap and explains why it was safe.** A raw
system-to-system gap is only the leak if the null is unaffected; if the leak had
lifted the null too, the gap would have double-counted it. **Nobody had measured
that, and G102 could not have — the number it needed did not exist.** The two
agree to 0.001, which is the null's own movement.

## 3 · F2 was the arm that could have made this interesting in the other direction

Preregistered first, deliberately: *"if the shuffle lift is within 0.005 of the
leak-free lift, the leak inflates the system and its null equally, and the
headline was never lift-inflated at all."* That would have made this a
**correction of the leak's size**. It did not fire — the two lifts are
+0.0926 and −0.0374, apart by 0.1300, twenty-six times the threshold.

**F3** re-ran the identical ranker on the pair-disjoint split **in the same
process**: 0.173226, matching G49/G104. That is the check that the shuffle
number is comparable, and it is a cross-split reproduction against code written
by someone else rather than another self-consistency test — **because G104
shipped an internally consistent, fully green, transposed model one cycle ago
and no invariant computable from the measurement itself could see it.**

**C4** re-derives the SPLIT from the pinned seed rather than re-calling the
scorer on the same lists, and the rebuilt split's null matches to 1e-12.
Re-calling one function on one list is not a reproduction.

## 4 · What this does NOT license

**0.2648 is still not gatable.** The split leaks 30.01% (12,249 of 40,818 test
triples, confirmed here), and `config.json` is right to say so. This row measures
the null **to size the leak in the units the loop reports**, not to rehabilitate
the number.

**And read the sign.** The leak-free lift is **negative**: the mined system is
0.0374 *below* the baseline of not mining at all. **+0.0926 on the shuffle is
not a smaller version of a real gain; it is the leak wearing the shape of one.**

## 5 · Offered

`shuffle_null.json` carries all three lifts. The field `.github/autoloop/` would
need is the pair-disjoint one — `null_mrr` 0.1732, already in `config.json`'s
`split_nulls` as data with **no consumer** (G104 §2). **`eval_graph_ai.py`,
`PROGRAM.md` and `config.json` are ATOM-3's G102 and are not edited here.**

## 6 · Scope

The prior is predicate-conditional entity frequency in train, filtered against
all true triples, ties at midpoint rank — G104's `rank_of` and `evaluate_prior`
**imported, not retyped**. `n_queries` is 81,636 here against 81,634 on the
pair-disjoint split; the two splits differ by one test triple (40,818 vs
40,817) and nothing in the comparison turns on it.
