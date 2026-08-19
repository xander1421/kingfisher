# H239 — "did it reproduce" and "does it hash the same" are different questions

**Row:** `WORK_QUEUE.md` H239 · **Lane:** AGENT-1 · **2026-08-19**
**Check:** `python3 spikes/H239_wallclock_reproduction/probe.py` — **20 arms, 20 pass**

## The defect, in the sentence that is better than my write-up of it

AGENT-3's, kept verbatim because it states the whole thing:

> when a hashed artifact carries a wall clock, "did it reproduce" and "does it
> hash the same" are different questions and only one of them is about the
> science

A reproduction answers the first. `recheck` v1 only ever asked the second, so it
called an honest reproduction `DRIFTED` and could not tell it from a regression.
**That is aimed at the one asset this mission has** — a result is trusted because
anyone can re-run it and compare bytes — because a field that cannot be re-run
makes the comparison always fail.

## The fixture is a real reproduction, and that was verified before anything was built

G54's `slice_gated.json` is the artifact behind `C_dev_gated 0.2313`, which
`--eval` names as source. A live lane force-recomputed it in a clean
`git archive HEAD` tree: corpus re-read, split rebuilt (leak=0), 1,410 rules
re-mined, 628.7 s, **no cache path anywhere in the spike**.

**F3 asked whether the "302 of 303 leaf fields identical" headline was true, and
it is discharged harder than a re-run would have discharged it.** Rather than
spend 628 s reproducing another lane's reproduction — and rather than overwrite a
published artifact in a shared tree, which `slice_gated.py:646` hardcodes and
which is H234's class — the claim was made to answer for itself:

```
published slice_gated.json               67a5de046597b0f1   8648 B  elapsed_sec 886.92
re-serialised unchanged                  67a5de046597b0f1   8648 B  <- round-trip control
same file, elapsed_sec -> 628.72         411731fbcec3224d   8648 B
AGENT-3's forced recompute published     411731fb…                  MATCH
```

The whole 8,648-byte recompute is **byte-reconstructible from the published
artifact by changing that one field.** That is strictly stronger than a leaf
differ's report: not "302 fields agreed" but "the entire file is accounted for".
F3 does not fire. The round-trip control on line 2 is there because without it a
match would only show that my serialisation happened to agree with itself.

## F1 FIRED against my first design, and the fix is what survived it

The predicate I preregistered was *"a field is MEASURED if the spike's own
certification consults it"*. **Measured before building: it misclassifies 2 of 3.**

| spike | leaf | certification cites it? | truth |
|---|---|---|---|
| H203 | `.w9_falsifier_wallclock_term.median_latency_us_now` | yes | measured ✓ |
| S84 | `.wall_us_citable` | **no** | **the measurement ✗** |
| H86 | `.timings.*.wall_s` | **no** (word-boundary) | **the measurement ✗** |

And the matcher itself moved the answer: **two of five verdicts flip on
substring-vs-word-boundary alone** (`wall_us` is a substring of `wall_us_citable`,
so substring matching caught H86's `wall_s` for the wrong reason and invented an
S84 hit that is not there). An arm that names one condition and tests another —
the third time this lane has hit that this span.

**What survived is two arms, and the second is the one that answers A30.** A leaf
may not be excluded if either its **NAME** or its **VALUE** is cited by the
spike's own certification or prose. H86's `wall_s` is invisible to the name arm
and caught on its published value; `elapsed_sec` and `wall_us_citable` are the
same shape to a grep and get opposite verdicts. Arm A5 asserts that the value arm
is load-bearing rather than decoration.

## The fix is a second hash, not a weaker one

`provenance.py` **v5**: `sha256` is untouched and still covers every byte.
`repro_sha256` covers the artifact with the **declared** leaves removed, and the
removed leaves are recorded in the clear as `repro_excluded` — D2 rule 2,
*"anything stripped before hashing is named in the record"*. `recheck.py` **v2**
runs the byte compare first and consults the second hash only when it fails.

**It is a GATE, not an ORACLE, and the A22 exposure is stated rather than
discovered.** A spike declaring which of its own fields do not count is a party
supplying the input to a check applied to itself. The veto is what makes that
survivable; it answers *"may this be excluded"* and never *"is this incidental"*.
**Its residual is real: a leaf that is load-bearing but cited nowhere — not by
name, not by value, in neither certification nor prose — will be allowed.**
`H86.wall_citable` is exactly that shape. Nothing excludes it because H86 declares
nothing, and the default is that nothing is excluded.

**Not a weaker gate (§5), and this is the arm that decides it:** all **302** other
leaves of G54's own artifact were mutated one at a time, on top of the honest
`elapsed_sec` change. **302 of 302 still read `DRIFTED`.** Zero went quiet.

**Inert for everything already on disk, measured rather than argued:** all **175**
provenance records under `spikes/` were run through v1 and v2. `OK 155 ·
DRIFTED 17 · MISSING 3` under both. **Zero verdicts moved.** A record with no
declaration has `repro_sha256 == sha256`, so it can reach `REPRODUCED` only by
being byte-identical.

## The class, and its size

**CLASS: a hashed artifact carries a field that no re-run can reproduce, so the
reproduction check can never pass.**

**102 of 188 hashed `.json` artifact entries** under `spikes/` carry at least one
timing-shaped leaf today — none of them reproducible byte-for-byte by anyone,
ever. Narrow and wide token sets give the same 102.

**AGENT-3 measured 90 of 185 earlier tonight and I do not supersede that number.**
Restricted to the records present at their measurement point (`1204a61`) my
sweep gives **93 of 177**. Ten records post-date their sweep, which explains the
denominator but not all of the numerator; **a residual gap of ~3 stands
unreconciled and is recorded as unreconciled** rather than quietly replaced. It
does not move the finding: roughly half of all hashed JSON artifacts here carry
the hazard.

## What this does not do

* It does not remove a field from any artifact, does not touch a published
  number, and does not move `recheck`'s byte hash.
* **It does not by itself fix G51 or G54.** Each needs a one-line declaration in
  its own `certify(...)` call, and both spikes belong to other lanes — editing
  them would change their generator's sha256 and drift their records. The line is
  posted to `livechat.log` for their authors.
* `result.json` here carries **no wall clock**. `elapsed_sec_published` and
  `elapsed_sec_recomputed` are constants describing *another* spike's run, so they
  are reproducible and belong in the hash — which is the row's own distinction
  applied to its own artifact. A duration of this probe's run would have made this
  file the 103rd instance of the defect it is about.
