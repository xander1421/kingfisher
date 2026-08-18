# The corpus cannot detect a broken `<`

`repro: spikes/M1_9_mutation/mutate.py`

> **CORRECTED 2026-08-18 (M17, AGENT-1 — this page was stale about its own
> data).** The table below listed **four** mutations; `mutation.json` has carried
> **five** since 14:13 on 2026-08-17, while this page was written at 12:20 and
> never revisited. The fifth is **`stdlib-if`**, and it is not a footnote: it
> **answers the question this very page leaves open** two sections down, where it
> asks *"is a stdlib rule programs DO invoke detectable?"* — **yes, 5/64**. The
> answer had been sitting in the artefact, unread, for a day.
>
> **So `detected_mutation_classes` is 3 of 5, not 2 of 4.** That matters outside
> this page: `.autoloop/programs/fault-expression/` optimises that quantity and
> took "2 of 4" from this stale table. A ratchet climbing toward a target derived
> from a superseded document is claim decay wired into an optimiser.
>
> **How it was found:** `provenance.json` recorded `mutation.json` at sha256
> `576884aa…` and the file on disk is `c658f184…`. A24 in its stated form — *a
> digest pins WHICH artifact, not what is in it* — with the record honest and
> nothing having re-checked it. The digest was the symptom; the cause is in
> `mutate.py`'s v2 block.

**Falsifier, stated before running:** *the corpus detects these mutations
broadly — a wrong evaluator changes many agreement keys.*

**Refuted.**

| mutation | what it breaks | detected |
|---|---|---|
| `sub-is-add` | `(- a b)` computes `a + b` | **4 / 64** |
| `less-is-lesseq` | `(< a a)` returns `True` | **0 / 64** |
| `resolver-message` | the text a missing `import!` produces | **24 / 64** |
| **`stdlib-if`** | **`(if True a b)` returns `b` — an INVOKED rule** | **5 / 64** |
| `stdlib-init` | one extra (unused) stdlib rule | **0 / 64** |

**`stdlib-if` vs `stdlib-init` is the pair that carries the meaning.** Both mutate
the stdlib. The unused rule is invisible (0/64) and that is *correct* — a rule
nothing invokes cannot change a result, and `fuel_used` does not move when the
stdlib merely grows. The INVOKED rule is caught 5/64, by
`lib__tests__test_stdlib`, `c1_grounded_basic`, `c3_pln_stv`, `d4_type_prop` and
`e3_match_states`. So the stdlib is not a blind spot as a layer; **reachability
is the whole variable**, which is the same lesson `less-is-lesseq` teaches from
the other side — there, the rule *is* reached and its fault still is not observed.

A replica whose `<` is wrong at every boundary agrees **byte-identically with an
honest replica on all 64 admitted programs**. Quorum would return UNANIMOUS.

## Detection by corpus class

```
                  sub-is-add  less-is-lesseq  resolver-msg  stdlib-init
empty        14      0/14         0/14            0/14         0/14
import-fail  24      0/24         0/24           24/24         0/24
error-only    4       0/4          0/4             0/4          0/4
evaluated    22      4/22         0/22            0/22         0/22
             --      ----         ----           -----        -----
             64      4/64         0/64           24/64         0/64
```

**The classes partition by layer, and each polices something the others cannot.**
The 24 import-failures catch the resolver mutation **24/24** — perfectly, and
they are the only class that catches it at all. They are not padding: they are
the only evidence in the corpus that module resolution is deterministic across
ISA and OS. Equally, no evaluation mutation touches them, which is why they
looked inert until something in their own layer was broken.

The 14 `empty` programs detected **nothing, in any of the four**. They remain
padding on the current evidence, and they already adjudicate `NO_RESULTS`.

The four `sub-is-add` detectors are `c1_grounded_basic`, `d2_higherfunc`,
`d3_deptypes`, `d4_type_prop`.

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

## A mutation can be applied, compiled, and still not exist

The first `resolver-message` targeted `mod.rs:871`:

```rust
#[cfg(not(feature = "pkg_mgmt"))]
return Err(format!("Failed to resolve module {absolute_mod_path}"));
```

We build **with** `pkg_mgmt`, so that line is never compiled. The anchor
matched, `anchored_replace` applied the edit, cargo rebuilt without error, and
the mutant was inert — it would have been logged as `resolver-message 0/64`,
which reads exactly like "the corpus cannot see resolver faults". The truth is
the opposite: the live site is `mod.rs:916`, and the corpus catches it 24/24.

The probe control reported **VOID** and no rate.

`anchored_replace` guarantees the anchor **exists**, never that the line is
**live**, and a feature-gated site is indistinguishable from a reachable one by
reading the source. On this project that is a standing hazard rather than a
one-off: the `manifest` domain axis exists precisely because feature flags
change which code is in the binary.

## A second harness defect, from the same run

Certifying this kept refusing with `STALE ARTIFACT ... cannot have been built
from the tree recorded here` — about artifacts that had *just* been rebuilt.

Cause: a **deterministic** pipeline regenerates its artifact byte-identically,
so git creates no new blob and the file keeps an older last-commit than a source
file that did change. The commit clock then reports the success case of
reproducible output as a failure. On this project that is the *common* case, and
a gate that refuses forever is a gate that gets bypassed with `allow_dirty` —
which voids it entirely, the exact failure recorded one cycle earlier.

`provenance` now takes a second opinion on **one** clock — artifact mtime
against the newest source mtime, never mtime-against-commit-time, which was the
E1 bug — and reports stale only if both clocks agree. Stated hole: after a fresh
clone every mtime is the checkout time, so the fallback passes for everything;
the commit clock remains primary and is unaffected.

Both artifacts also now carry the elders `HEAD` + patch sha256, so a baseline
swept from a different tree is identifiable as such.

## Scope — what this does NOT license

- ~~**Two mutations, both evaluation-semantic.** A mutation to stdlib
  initialisation would shift `fuel_used` … and would likely be caught by nearly
  all 64 including the import-failures.~~ **WITHDRAWN 2026-08-17 — run and
  refuted.** `stdlib-init` is detected by **0/64**. Adding a rule to
  `stdlib.metta` changes `!(kf-canary)` from `(kf-canary)` to `1`, so the mutant
  is live, and yet not one program's agreement key moves. **`fuel_used` counts
  program reduction only; it does not move when the stdlib grows.** So a replica
  carrying extra or altered stdlib rules agrees byte-identically on all 64,
  provided no dispatched program invokes the changed rule. That is a second
  blind spot of the same shape as `<`, and it was written here as a confident
  prediction one cycle before being measured.
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

---

## M17 addendum, 2026-08-18 — what re-running this taught, including a sweep I threw away

**Three sweeps were run.** The first two reproduced the committed rates
**exactly** (`4/64 · 0/64 · 24/64 · 5/64 · 0/64`). The third did not:

| mutation | committed | sweep 1 | sweep 2 | **sweep 3** |
|---|---|---|---|---|
| `sub-is-add` | 4/64 | 4/64 | 4/64 | **5/64** |
| `less-is-lesseq` | 0/64 | 0/64 | 0/64 | **2/64** |
| `resolver-message` | 24/64 | 24/64 | 24/64 | **26/64** |
| `stdlib-if` | 5/64 | 5/64 | 5/64 | **3/64** |
| `stdlib-init` | 0/64 | 0/64 | 0/64 | **2/64** |

**Sweep 3 is discarded, and `certify` refused it before I decided to.** Every
rate moved, `detected_mutation_classes` would have read a flattering **5 of 5**,
and the cause is in the baseline: two programs changed their agreement key
between two consecutive baselines taken minutes apart.

```
python__tests__scripts__c1_grounded_basic.metta   OK fuel 50794  ->  TIMEOUT
lib__tests__test_stdlib.metta                     OK fuel 48584  ->  error-only, fuel 11413
```

`quiet.sh` at that moment: **`REFUSED — loadavg(8.20>3.50) containers(4)`**, with
`mds` at 135% CPU and another lane's Python at 100%.

**THE CORRECTION IS TO THE SELECTION RATIONALE, AND IT WAS MINE.** This row was
picked *because* it was believed load-insensitive — my own journal said so, and
so did the livechat note recommending it while `quiet.sh` refuses. **That is
false. The sweep has a TIMEOUT, so it is load-sensitive by construction:** under
load a program stops producing its result, its agreement key changes, and it
scores as a "detector" of whatever mutation happened to be applied. Load does not
add noise symmetrically here — it manufactures detections, so **contamination
makes the corpus look BETTER at expressing faults than it is.**

`e3b0c442…` and the `flip` program were already known noise sources and are
banned. This is a different one and it is not in `BANNED`, because it is not a
property of the program: **the same program is deterministic on a quiet machine
and nondeterministic on a busy one.** A banned-list cannot express that.

**What still stands, and on what evidence.** The `stdlib-if` correction above
rests on the **committed artefact plus one exact reproduction**, not on sweep 3.
Nothing in the corrected table comes from the discarded run.

**What is NOT done, split out rather than folded in (§2: PARTIAL is not a
verdict).** `mutate.py` **v2** now persists each mutation's probe observations
(`probe_base`, `probe_mut`, `void`) — the control that separates *"the corpus did
not notice"* from *"the harness did not work"*, which until now was **printed to
stdout and never written to the artefact**. That is `Control.observe`'s own
refusal — *a null reported only in prose cannot be rechecked* — in the spike whose
entire finding is a set of zeros. `certify_m17.py` is written and driven from
those observations. **Neither can produce a clean record until `quiet.sh` passes**,
so `provenance.json` is left stale and openly so rather than regenerated from a
run this page would have to disown. Filed in `BLOCKED.log`.
