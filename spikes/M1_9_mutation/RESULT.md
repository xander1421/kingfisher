# The corpus cannot detect a broken `<`

`repro: spikes/M1_9_mutation/mutate.py`

**Falsifier, stated before running:** *the corpus detects these mutations
broadly — a wrong evaluator changes many agreement keys.*

**Refuted.**

| mutation | what it breaks | detected |
|---|---|---|
| `sub-is-add` — `def_binary_number_op!(SubOp, +, …)` | `(- a b)` computes `a + b` | **4 / 64** |
| `less-is-lesseq` — `def_binary_number_op!(LessOp, <=, …)` | `(< a a)` returns `True` | **0 / 64** |

A replica whose `<` is wrong at every boundary agrees **byte-identically with an
honest replica on all 64 admitted programs**. Quorum would return UNANIMOUS.

## Detection by corpus class

```
                  sub-is-add   less-is-lesseq
empty        14      0/14           0/14
import-fail  24      0/24           0/24
error-only    4       0/4            0/4
evaluated    22      4/22           0/22
             --      ----           ----
             64      4/64           0/64
```

All detection lives in the 22 `evaluated` programs, which is what
`CORPUS_COMPOSITION.md` predicted. The four detectors are
`c1_grounded_basic`, `d2_higherfunc`, `d3_deptypes`, `d4_type_prop`.

## The two controls, because 0/64 is an ambiguous number

**`mutant-is-live`.** A dead mutant, a failed rebuild, and a missed anchor all
produce 0/64 as well. Each mutation carries a probe it *must* change, run
against the same binary as the sweep:

```
!(- 5 3)   '2'      -> '8'        (live)
!(< 1 1)   'False'  -> 'True'     (live)
```

If a probe does not move, the harness reports **VOID** and no rate — a 0 that
means "the harness did not work" must never be printed next to a 0 that means
"the corpus did not notice".

**`noise-floor-measured`.** A program whose result varies run to run scores as a
detector by chance. Four identical unmutated sweeps:

```
python__sandbox__test_gnd_conv.metta   3 distinct keys
all 63 others                          stable
```

Exactly one noisy program, and it is the `flip` program **already refused by
`bansurface` at admission**. This mattered: the first run of `less-is-lesseq`
scored 1/67 and the second 0/67, and the difference was entirely that program
firing randomly. Excluding the three admission-refused programs — which the
quorum never dispatches anyway — gives a stable 0/64.

## Why `<` is invisible

`sub-is-add` survives in 4 programs because they do arithmetic whose result
reaches the output. `less-is-lesseq` reaches nothing: of the admitted corpus,
the programs that compare numbers either do not print the comparison, or
compare values that are never equal — and `<` and `<=` differ **only** at
equality. A mutation that is wrong on a measure-zero slice of inputs needs a
program that hits that slice, and the corpus has none.

This is the general shape and it is worse than a coverage gap. `<` is *executed*
by the corpus; executing a faulty line is not the same as observing its fault.

## The bug this harness shipped with, caught after the first writeup

The first version restored the mutated file with `shutil.move` of a
`shutil.copy2` backup. `copy2` **preserves mtime**, so restoring moved the
source clock *backwards*: cargo saw nothing newer than the mutated build,
skipped the rebuild, and left **the mutated binary on disk**. The final
`build()` was a no-op.

That is not cosmetic. `baseline.json` is recorded by a separate invocation that
also starts with `build()` — so the baseline could have been swept with a
`less-is-lesseq` binary, and comparing a mutated baseline against a mutated
mutant yields `0/64` for exactly the reason that looks like the finding.

Caught by running `!(< 1 1)` against the binary after the run and getting
`True`. Two fixes:

- `os.utime(path, None)` + an explicit `build()` immediately after every
  restore, so the clock always moves forward;
- `assert_clean_binary()` — the baseline now refuses to be recorded unless
  `!(- 5 3)` is `2` and `!(< 1 1)` is `False`.

**Re-run from a verified-clean baseline: `4/64` and `0/64`, unchanged.** The
numbers above are the re-run. The bug did not alter the result, and it could
have; the writeup that stated them before the check was luckier than it was
careful.

This is family C — the artifact is not what you think — inside a harness whose
whole purpose is deciding what a binary is. It is also the same mtime mechanism
`provenance.artifact_time` exists to police, reached from the other side: not a
stale artifact next to fresh source, but fresh source made to *look* stale.

## Scope — what this does NOT license

- **Two mutations, both evaluation-semantic.** A mutation to stdlib
  initialisation would shift `fuel_used`, which is in the agreement key
  `(status, fuel_used, hash)`, and would likely be caught by nearly all 64
  including the import-failures. Untested here; do not assume 4/64 generalises
  to every fault class.
- It says nothing about whether hyperon is correct. Both mutants were injected
  deliberately into a correct evaluator.
- It does not say quorum is worthless. Quorum catches a replica that *diverges*.
  This measures how much of the fault space produces a divergence at all, and
  the answer for comparison operators is: none of it.

## What it means for the headline

`DETECTION_FLOORS.md` already recorded that quorum is blind to a **shared** bug.
This is narrower and sharper: quorum is also blind to an **unshared** bug when
the corpus cannot express it. A single dishonest or miscompiled replica with a
wrong `<` passes 64/64.

Corpus discriminating power is now a measured quantity rather than an
assumption, and the measurement is cheap: two rebuilds, ~30 s.
