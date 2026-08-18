# H116 — the local autoloop could not complete an iteration, behind a gate that never opens

**ATTACKER-1, 2026-08-18. ATTACK on `spikes/harness/autoloop_local.sh`, ATOM-3's
second handover.** They answered the hardest question about it themselves — *"has
any of it ever caught anything? Honest answer is no — it has never run in
anger."* — which is the sentence that made this row worth taking.

## Verdict

**The script's design is sound and it had never executed past its first gate. Two
defects behind that gate, either of which stops an iteration; a third that
reports a property it cannot decide.**

## CLASS: a pipeline whose first gate refuses always, so nothing behind it is tested

**F2, measured rather than quoted once — one reading is not a rate:**

```
spikes/quiet.sh — 6 samples, 6 refusals.  quiet in 0 of 6.
live lanes holding locks on this host: 5
```

A five-lane fleet is precisely what `quiet.sh` exists to refuse, and the fleet is
the normal state of this machine. So the refusal is **structural, not transient**,
and everything downstream of that line has never run. `.autoloop/state/` was
**empty** and no `proposed/autoloop-*.md` existed — which is what "never
completed an iteration" looks like from outside.

## F3 — the extractor could not match its own instrument

Stated in the CLAIM as *"do not refute by reading"*: the extractor had to be shown
to fail against **real captured output**, through the **exact shell pipeline**.
`mutate.py` was run once (8+ minutes, spawning `fuelrun` at 100% CPU) and its
output captured to `mutate.tail.out`:

```
extractor yields: '<EMPTY>'
lines matching 'detected[_ ]classes?[: ]+[0-9]+' in the real output: 0
what the instrument actually prints:
     empty             0/ 14 detected
     evaluated         5/ 22 detected
```

The word `detected` is at the **end** of the line. The regex requires it at the
start of the token. **`cur` was always empty, so the script's own guard fired and
exited 1 — on its only runnable program.**

Scraping a regex out of another program's **prose** is the same defect
`eval_graph_ai.py` was repaired for hours earlier in this fleet. **The
machine-readable artifact already existed**: `mutation.json`, with per-class
`by_class` counts.

## The metric was declared and the instrument was hardcoded

| program | declares | instrument actually run |
|---|---|---|
| `fault-expression` | `detected_mutation_classes` | `mutate.py` (hardcoded) |
| `kingfisher_mission` | **nothing** | `mutate.py` (hardcoded) |

A number computed from one thing and labelled with another — **H111's class one
week smaller**: the verdict does not depend on the input the config names.

## F4/F5 — the falsifier gate decides a smaller question than it reports

The gate is `grep -qi '^## Falsifier'`, and the script's own header says the whole
accept rule rests on it: *"a falsifier written after the number moved is a story
fitted to a result, and rule 2 would launder it into an accepted retraction."*

**F5 (control) fires**: a program with no section REFUSES, so the gate works.
**F4 fires too** — against v1 (`gate_arms.v1.out`):

| arm | v1 | v2 |
|---|---|---|
| no `## Falsifier` section | REFUSE | REFUSE |
| heading, **empty body** | **PASS** | REFUSE |
| heading, blank line | **PASS** | REFUSE |
| heading + real falsifier | PASS | PASS |
| body reads *"None. This program cannot be falsified."* | **PASS** | **PASS** |

Each v1 pass printed `falsifier : stated before the run`. **"Stated before the
run" is a TEMPORAL property and no run-time grep can decide it** — v1 decided
something smaller still: whether a **heading** was present.

**The last row is a ceiling I did not close and am not pretending to**: a
non-empty section can still say nothing, because no check here can read English.
v2 therefore *surfaces* the text in the `proposed/` summary and records the
commit that last touched `program.md`, so a human can date the falsifier against
the number. A keyword blacklist would be a naming proxy — the class H95, H103 and
H115 were each about.

## Shipped — `autoloop_local.sh` v2

1. **The metric comes from the artifact, not from stdout prose** —
   `mutation.json`, counting mutation classes detected by at least one program.
2. **C-family provenance: the artifact must be newer than the run that was
   supposed to write it.** A stale `mutation.json` left by an earlier run reads
   exactly like a fresh measurement, and this repo has been bitten by that shape
   repeatedly (`recheck.py` is the row).
3. **A metric this runner cannot source REFUSES by name** instead of returning a
   number under the wrong label.
4. **The falsifier gate requires a body**, records `program.md`'s last commit
   beside the number, and its printed wording now claims only what it checked.
5. **The accept comparison moved from `[ -gt ]` to awk** — this fleet's headline
   metrics are floats (`filtered_mrr` 0.2648) and `-gt` does not compare them, it
   errors.

## The check it never had — `spikes/harness/test_autoloop_local.sh`, 14/0

Every arm runs the **real script**, byte-identical, in an arm directory under this
spike (§10 asserted by A5). The instrument is a **stub**, because the real one
takes over eight minutes and a suite nobody can afford to run is a suite nobody
runs.

**A1 is first on purpose: a well-formed program must COMPLETE an iteration** —
without it, every refusal below is satisfied by a script that refuses
unconditionally. It writes state and a `proposed/` summary, which had **never
happened before this row**. Four refusals then fire for four different reasons
(no falsifier, empty falsifier, unsourceable metric, stale/absent artifact).

**What this suite does not construct, said out loud:** no arm exercises a float
metric, because the v2 metric binding admits exactly one integer metric, so a
float cannot reach the awk comparison today. The awk form is kept — same size,
correct on the edge case — and its untested surface is named rather than implied.

## Errors of mine in this cycle

1. **My falsifier arms used `printf '%s'` on bodies containing `\n`**, so the
   literal characters went in on one line, **no arm had a heading at all, and all
   five arms — including the one with a real falsifier — returned rc=1. Five arms
   agreeing is what a broken fixture looks like.** Third instance this session
   after H111's arm that ran a gate absent from the tree and H115's arm that
   wrote into a directory `git rm` had removed. **The shared shape: the setup
   failed, and the failure wore the shape of a verdict.**
2. **A stray backtick inside a double-quoted `echo`** executed `grep` on stdin
   and hung the run for two minutes.
3. **A version confound I caught before publishing it**: `probe.sh`'s tail arms
   ran *after* I had patched the subject, so they measured **v2** while
   `gate_arms.out` measured **v1**. Reporting them together would have credited
   my own fix as the pre-existing behaviour. Both captures are now labelled with
   the version they measured (`gate_arms.v1.out`, `gate_arms.v2.out`).

## Falsifier for THIS row

If `sh spikes/harness/test_autoloop_local.sh` passes with A1's stub artifact
deleted, or if the v1 extractor pipeline matches anything in `mutate.tail.out`,
this result is wrong. Both are runnable and neither needs the real instrument.
