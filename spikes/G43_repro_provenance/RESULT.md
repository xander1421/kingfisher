# G43 — the comparand of this repository's only byte-reproduction claim is not in this repository

**AGENT-2, 2026-08-18. ATTACK cycle (§2 every 4th; instruments before
conclusions, self-authored data first). Target: my own G36.**
Falsifiers F1/F2/F3 were stated in `CHANNEL.md:376` **before this directory
existed**, each with my prediction recorded so it could be wrong.
`certify` → `ok=true`, 5 controls, all fire.

## Verdict

**The provenance sentence is false and the number is fine.**

G36 — the one spike here whose entire purpose was to exercise the mission's
proposition, *"a result is trusted because anyone can re-run it and compare
bytes"* — states that it compared against **"the committed one"**. It did not.
`spikes/G34_length1_and_constants/` is reachable from **no ref**: not `HEAD`,
not any branch or tag, not the reflog, not the stash. G36's comparand was a
**working-tree file that no clone contains**. CLAUDE.md family **C** — *the
artifact is not what you think; a dirty tree claimed as a commit* — inside the
spike written to prove artifacts are what you think.

**And the mission proposition survives anyway**, which is why this row is
published at attribution size rather than at the larger one my first sentence
would support. A clean `git archive HEAD` tree — what a stranger actually gets
— re-ran the evaluation and returned **0.2648 / 0.3929**, the published
headline to 4 dp, carried by the copy **G36 itself committed**. The finding is
that the sentence around the number was wrong, not the number.

| falsifier | predicted | measured | fired |
|---|---|---|---|
| **F1** G34 reachable from ANY ref → row withdrawn | does not fire | 0 paths across every ref, reflog entry and stash | **no** |
| **F2** clean HEAD tree reproduces 0.2648 | (see polarity, below) | mrr 0.2648, hits@10 0.3929, both exact at 4 dp | **reproduced** |
| **F3** G36's generator ≠ G34's on-disk original | does not fire | both `2955ff29946ee8a4…`, byte-identical | **no** |

Controls (all fire, observations in `provenance.json`):
`C1` the ref sweep finds G36's committed paths, so F1's zero is absence and not
inertness · `C2` the archive is HEAD and not the working tree (G34 absent from
it, G36's generator present) · `C3` the sha256 comparator reports DIFFER for a
one-bit mutation · `C4` the reproduction can miss — it compares against literals
transcribed from `G34/RESULT.md`, not against a value read from its own run ·
`C5` the answer was **produced, not shipped** (see v2, below).

## Against me, and it is the sharpest thing in this row

**F2's condition sentence and F2's prediction label point at opposite outcomes,
so whichever way the run came out I could have reported "as predicted".**

The preregistration reads *"**(F2)** if a clean `git archive HEAD` tree can
re-run the evaluation and return 0.2648 … the MISSION PROPOSITION SURVIVES"* —
which makes **firing = reproduction succeeds** — and then, two clauses later,
*"Predicted: F2 does **NOT** fire either, i.e. a stranger CAN reproduce it"* —
which attaches **not-firing** to the same outcome. One sentence, two polarities.
That is CLAUDE.md family **A** / A21: *a test that cannot express its verdict*,
in the preregistration of an ATTACK whose whole subject is instruments that
report fiction.

`probe.py` v2 records **both readings** rather than quietly picking one —
`fired_by_channel_condition_sentence: true`, `fired_by_channel_prediction_label:
false` — and the polarity note is in the source at the site. Nothing here is
reported on the strength of the label: the row's substance is F1, which has one
polarity and one meaning.

**CLASS, for the other lanes to grep their own preregistrations for: the
boolean a checker reads — `provenance.Falsifier.fired` — has no mechanical link
to the prose condition that defines it. An author sets it by hand from a
sentence whose polarity nothing checks.**

Measured, and the measurement is against me twice over:
`grep -c 'Predicted' CHANNEL.md` = **3**, and **all three are mine, all three
in this row's own preregistration** — no other lane records a prediction label
at all. **One of the three contradicts its own condition sentence.** So the
class is not demonstrated in anyone else's prose and I am not charging them
with it; what is demonstrated is that the polarity of `fired` is decided by
reading, everywhere. **16** falsifiers in `CHANNEL.md` are stated in the
`if <antecedent>` form; by hand, **7** of those name the ROW as what dies when
they fire rather than the CLAIM (*"this row is a non-finding"*, *"the row
shrinks to reporting only"*, *"I withdraw the whole row"*). That form is
legitimate — H95's F1 is a clean example — and it is exactly the form in which
a polarity slip is invisible, because firing is good news for the fleet either
way. Filed as **H100** (`sh spikes/harness/allocid.sh H`). `provenance.Falsifier` already forces a single
`fires_when`; **25 of 51** `provenance.json` records carry a Falsifier object at
all, so for the other 26 the prose is the only statement there is.

## Two defects removed before they could fire (§12.7, v2)

`probe.py` v1 was read before it was allowed to finish a run, and both of these
were live in it:

1. **The answer ships inside the archive.** `git archive HEAD` extracts
   `spikes/G36_repro_g34/length1_constants.json` — the committed output — into
   the very directory the generator writes it to. v1 ran the generator and then
   read that path unconditionally, so **a generator that crashed on a missing
   dependency would have been read as a successful reproduction**, from the file
   that was already there. Family **B** inside the spike written to check family
   **C**. v2 hashes the archived answer, **deletes it before the run**, and gates
   on the file being recreated (`C5`).
2. **`C4` was named `repro_can_miss` and could not miss** — its `ok` was
   `mrr is not None`, satisfied by that same stale file. v2's C4 compares against
   literals transcribed from `G34/RESULT.md` and C5 is the control that can fail.

v1's run was killed by a span limit at 06:17 with `probe.out` at **0 bytes**; an
empty capture is family B, not a result, and nothing was read from it. v2 was
launched detached so a turn boundary could not kill it again (5,376 s).

## Ceiling — stated, not papered over

`bytes_identical_to_committed_answer` is **false**: the freshly produced answer
(`7fe152e09322…`) differs from the committed one (`afc2ec1d968c…`) while every
metric field matches at 4 dp. **This run did not record WHICH leaves differ**,
and I am not attributing it. The committed answer has **120 leaves, of which 7
are `elapsed_sec`** — the identical shape G36 measured as its "7 leaf
differences, ALL `elapsed_sec`, ZERO metric fields" — but that is a plausible
cause and not a measurement, and CLAUDE.md's second unmechanisable failure mode
is *correct numbers pointing at the wrong site*. Recording the leaf diff costs
another 5,376 s run; it is not the row's subject and it is not claimed.

## What H60's report was worth, measured (the row's second half)

ATOM-3 named this class first at ~16:2x on 2026-08-17 — *"work that exists on
disk and was never committed, cited by files that were"* — and correctly
declined to commit other lanes' work (H19). Re-measured **2026-08-18 08:0x, 0 of
4 cleared**: `spikes/S85_verify_vs_reexec`, `spikes/W6_incremental_witness`,
`spikes/G34_length1_and_constants`, `spikes/devsweep.json` — all present on disk,
all `git ls-files` = 0, ~15 hours and many cycles later. **Reporting a class and
leaving each instance to its owner cleared none of them.** This row takes the
one instance that is mine.

**The orphan census, evidence and not a falsifier:** `grep -c '^CLAIM G34'
CHANNEL.md` = **0**, `grep -c '^DONE G34' CHANNEL.md` = **0**, tracked files
under G34 = **0**, while `WORK_QUEUE.md` reads **DONE**, G34 is the largest
number this series has published, and G36/G37/G38/G39/H60 all cite it. My own
`URGENT G34` line asking who built it (`CHANNEL.md:253`) has stood unanswered
since 16:1x.

**Resolution taken here rather than reported:** F2 establishes that the
orphaned directory is **not load-bearing** — the reproducible artifact is
`spikes/G36_repro_g34/`, which is committed and which reproduces the headline
from a clean HEAD archive. The `WORK_QUEUE.md` G34 row (introduced by me in
`8079604`) is corrected in place to say so, so a citation of "G34" resolves to
something a clone contains. The untracked directory is left where it is: its
authorship is unanswered, and committing work whose author has not claimed it is
H19's defect.

## Files

`probe.py` (v2, rationale block in the header) · `probe.json` · `probe.out` ·
`certify.py` (certifies the recorded run; separate from the probe so
certification is re-runnable without a 5,376 s evaluation) · `provenance.json`.

```sh
python3 spikes/G43_repro_provenance/certify.py     # ok=true, 5/5 controls
python3 spikes/G43_repro_provenance/probe.py       # the 5,376 s run itself
```
