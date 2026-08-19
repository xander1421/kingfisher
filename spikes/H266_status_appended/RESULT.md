# H266 — a row whose verdict is appended after the word every reader takes

**ok-1, 2026-08-19.** Found by selecting: H41 appeared in `--open`, and reading it
showed the work finished two days earlier — by me, in `refcheck.py` v5.

## The finding

A status cell here is prose, and a lane recording a verdict often **appends** it:

```
| H41 | ... | OPEN — not taken by ATTACKER-1: it is ok-1's module (v4 landed in
`2c9d277`) and the repair has a real false-positive surface ...  **DONE (ok-1)** —
`refcheck.py` **v5**, and THE ROW NAMED ONE OF TWO DEFECTS ... |
```

Every reader takes the **first** status word. `**DONE` sat at character **223 of
2014**. So the row announced `OPEN` for two days while its work was committed —
and under H261 it was *also* invisible to the `awk` line the brief handed lanes,
so nothing offered it and nothing closed it either.

> **CLASS: a verdict appended after the status word every reader takes.**

**Census (`measure.out`), 349 rows: two.** H41, mine, corrected in place — the
leading word moved, the original prose kept verbatim underneath. **S37 is another
lane's and is routed, not edited.**

## The check, and why it REPORTS rather than gates

`statuscheck.py --open` now prints, under the count:

```
NOTE (H266): 1 row(s) parse OPEN while carrying a bold **DONE marker later in the
same cell — read them before selecting:
    S37      **DONE at char 787 of 2397
```

**A gate here would be wrong**, and the false positive is easy to construct: an
OPEN row may legitimately say *"do not close this while H214 is **DONE**"*. Two
rows matched in a 349-row queue; refusing a commit over a sentence would be the
`githygiene` failure — *"exit 1 permanently … so everyone learns to bypass it"*.

## What it does not claim

It cannot tell a **superseded** leading status from a **deliberate** one. It says
*read this row*, which is what §2 asks of a lane at SELECT anyway, and it makes
the two rows in the queue findable in one command instead of by luck.

## Recorded against myself — three times in one turn

**This row's id was typed from memory as `H264` before the allocator was run, and
renumbered mechanically against `.ids/` before anything was committed.** That is
the third time in this turn: `H253`→`H254`, `H262`→`H263`, `H264`→`H266`. All
three were caught by running `allocid.sh` and comparing, none by noticing.

**The pattern is specific and it is mine**: I draft the write-up with an id in it,
then allocate. The habit that would remove it is to allocate first and paste, which
is exactly what three other lanes now write into every CLAIM line — *"read out of
the allocator's output and not retyped after it"*. I have been writing that
sentence while not doing it.
