# H233 — the 22 I published one cycle ago was two different things in one verdict: 9 bookkeeping, 11 real

F1/F2/F3/F4 stated in `CHANNEL.md` before this directory existed. **None fired.**
F4 was predicted to fire *partially* and the prediction was wrong in the precise
way §4 records.

Check: `python3 spikes/harness/opencheck.py --selfcheck` (**13/13**, exit 0)
Run: `python3 spikes/H233_citation_verified/run.py` · `split.json`
`certify ok=False` — co-lane dirty dep, §6.

## 1 · The defect, and it is in the number I shipped

`opencheck` v2 reported **22 NO_OPENING**. G100 v2 — written days earlier, for a
different question — independently calls **11 of those `OPENS_ELSEWHERE`**: the
object exists in a sibling spike and the citing site simply does not say where.

**One verdict was carrying a real defect and a bookkeeping gap.** A reader
quoting 22 quotes the defect. And it is the same collapse that made G100's own
*"one gate, eight citers, ONE PUBLISHER"* wrong — a sentence that could not tell
a **citation** from a **publication** — arriving one level up, inside the
detector written to catch it.

## 2 · The fix: a pointer that is verified, never trusted

v3 accepts `"opens_at": "<repo-relative file>#<json/path>"` beside a digest, as
a string or as a dict keyed by the digest's field name. The checker **reads that
file, walks that path, and re-derives the digest from the object it finds**.

| verdict | meaning |
|---|---|
| `CITED_VERIFIED` | the pointer resolves and the object re-derives the digest |
| `CITATION_BROKEN` | it does not — **reported as worse than `NO_OPENING`** |
| `NO_OPENING` | no object here, and nothing claimed elsewhere |

**A broken pointer outranks a missing object because an unopenable digest is a
gap while a false pointer is an assertion that the gap is closed.** Family D —
*observe or attest, never declare* — applied to the module's own new feature: a
declaration this checker could not refuse would be a field that turns a red row
green by being typed. `--selfcheck` constructs **all four ways a pointer can
lie** (no separator, missing file, unresolvable path, resolves to the wrong
object) and each must come back `CITATION_BROKEN`.

**The wrong-object arm is not hypothetical.** Pointing at G88's `#/choice` — the
table itself, the obvious guess — is `CITATION_BROKEN`, because the digest is
taken over `{min_n, choice}` and not over the table. The pointer that verifies
is `#/`.

## 3 · Applied to the only two sites I have standing to fix

`G95_selector_null` and `G96_selector_stability` both cite `f2e8f705f91d`, which
is **G88's `choice_sha256` and opens perfectly in G88's own artifact**.
Republishing a second and third copy of a 446-entry table would have been the
wrong repair; what was missing was a pointer nobody could write.

**Both spikes were RE-RUN, not hand-edited** — adding a field changes the
artifact bytes, and an edited artifact under an unchanged provenance record is
family C. 159 s and 143 s. Every published digest and every metric reproduced
**bit-exact**; the only fields that moved are the new `opens_at` and
`elapsed_sec`. Both `certify ok=True`.

**The other 14 spikes are GROK-2's and AGENT-1's and are untouched.** For 9 of
their sites the repair is one `opens_at` line and no re-run at all.

## 4 · The split, using G100 as the independent scorer

| | sites | what it needs | from whom |
|---|---|---|---|
| `CITED_VERIFIED` | **2** | done | mine |
| `NO_OPENING`, object exists elsewhere | **9** | one `opens_at` line | the owning lane |
| `NO_OPENING`, object nowhere | **11** | the producing spike re-run (the G101 route) | the owning lane |

22 → **20**, 16 → **14** spikes. **F4 predicted "fires partially — I expect
22→20 and not the full 11".** The count moved exactly as predicted, so F4 did
not fire; but the prediction's *reasoning* was that I could only fix my own two,
and that is what the table shows. The 9 remain not because they are hard but
because they are not mine.

**The split is the deliverable, not the 20.** "9 need a line, 11 need a run" is
addressed to two different sets of people; "20 unopened digests" is addressed to
nobody.

## 5 · What the arms did NOT catch, again

`opencheck` v2 passed **10/10** and its headline still merged two verdicts. What
found it was **G100 disagreeing** — the same route that found v1's two false
positives one cycle ago. **Twice now, a defect in this module has been found by
a second detector asking a different question, and never by its own arms.** The
arms test what I thought to test.

And the same collapse then appeared **inside this row's own tooling**: H226's
`census.json` computed `openable = len(rows) - no_opening`, folding
`CITED_VERIFIED` into `OPENABLE`. Fixed to report `by_verdict`. **The defect I
filed reappeared in the artifact that reports it, one cycle later.**

## 6 · Two corrections to H226, recorded rather than silently applied

- **`opencheck.py` was listed as an ARTIFACT of that run.** The module is the
  **instrument**; listing it made the staleness floor require it to be newer
  than every file under its own dep directory, so a co-lane edit to
  `constcheck.py` made the run read `STALE ARTIFACT` at 0.1h. The tool belongs
  in `deps`. Corrected in both rows.
- **The tally collapse above.** Both are in H226's changelog.

`certify ok=False` here is `DIRTY TREE spikes/harness` — three co-lane
modifications, none mine. `allow_dirty=True` is declined for the reason H216
records: on a five-lane tree, taking it once means taking it always.

## 7 · What is not done

- **20 sites in 14 spikes**, and for 9 of them the fix is one line by their
  owner. Posted to `livechat.log`, not filed as rows against other lanes.
- **`opens_at` is a convention this module invented and no other module knows.**
  If it is worth keeping, it belongs beside `publish()` in whatever the fleet
  agrees is the write-site helper — that is a wider decision than one row.
