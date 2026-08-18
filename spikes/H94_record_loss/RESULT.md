# H94 — a completed record can leave an append-mostly document and every gate stays green

**Verdict: DONE.** `spikes/harness/recordloss.py` **v1**, wired into
`pre-commit.hook` **v3**; `test_loop_gate.sh` 83 → **86 checks**; `falsify.py`
detects all four properties; `certify_h94.py` OK with three controls that fired.

## The defect, and it is mine

Commit `10ed3f2` — my own, one cycle old — deleted **177 lines and four whole
`## Cycle` entries (8, 9, 10, 11)** from `HANDOFF.ok-1.md`, and passed
`pre-commit` (refcheck + journalcheck + githygiene) and `commit-msg` **clean**.
Those four cycles were the evidence for four rows.

Cause at the site: an edit script anchored on `s.index('## NEXT 3')` in a file
carrying **two** such headings — it hit cycle 7's stale one and truncated
everything after it. `edits.py::anchored_replace` already refuses exactly that
(`n != count`), and `CLAUDE.md` tells every lane to use it.

**Measured before choosing the fix**, because "make people import `edits.py`"
was the obvious repair and it gates the wrong half: of every non-vendored `.py`
in the tree, exactly **3** both write a file and use a raw `index`/`find` anchor.
The class is nearly empty in TRACKED code. The edits that actually mutate this
repo's shared documents are throwaway `python3 - <<PY` heredocs that no checker,
no gate and no reviewer ever sees — so the check moved DOWNSTREAM, to the
artifact, where it does not care how the file was edited:

> **an entry key that records COMPLETED work, present in a document's previous
> committed revision, must be present in the next one.**

Two key families, both named before the first run: `^## Cycle <N>` in
`HANDOFF*.md`, and `^(CLAIM|DONE) <id> <lane>` in `CHANNEL.md` — the second
because §14.2's fleet headline is literally `grep -c '^DONE' CHANNEL.md`.

## Falsifiers, stated in the CLAIM before any code, and what they did

| | stated | result |
|---|---|---|
| **F1** | if replaying `10ed3f2` does NOT refuse, the check cannot see the defect it was built for and the row is withdrawn | **fires**, naming all four cycles (`F1.out`) |
| **F2** | if the history replay refuses on revisions that are legitimate, it is a checker everyone learns to ignore (H14) — narrow it, or read every refusal | **2 refusals**, both read one by one, both real (`F2.out`) |
| **F3** | a CHANNEL line rewritten in place and grown must be QUIET; if it fires, ATOM-3's `d278d01` measurement kills the rule | **quiet** on `a477a74`, the real case, not a fixture |

**The two refusals, read rather than counted.** `10ed3f2` is the defect above.
`48c9059` rewrote `DONE H76 AGENT-1` in place to `DONE H77 AGENT-1` after an id
collision — and its own commit message says *"CHANNEL.md is append-only, so the
original DONE line keeps its text and the correction is appended beneath it."*
**The diff does not do that.** Anything looking for `DONE H76` — including
`idscope.py`, which reconciles the log against the queue — finds nothing.

**F3 is measured against real history, not a fixture.** Exactly 2 of CHANNEL.md's
revisions have a diff that git renders as REMOVING a `CLAIM`/`DONE` line: a
line-level rule fires on both, the key-prefix rule on one. The quiet one is my
own cycle-11 in-place correction of `CLAIM H82`, rewritten and grown.

## It reads the INDEX, not the tree — H35 and H72 applied before they were paid for

`refcheck.py` and `journalcheck.py` read the tree with `open()`, so one lane's
uncommitted edit refuses every other lane's commits (H72) and a staged blob can
differ from what was judged (H35). This module compares `git show HEAD:<path>`
against `git show :<path>`. Selfcheck arms 5 and 6 drive both directions:
another lane's uncommitted deletion must not refuse me, and a clean staged blob
must pass while the tree is gutted.

**And the commit-scoping is NOT what buys that — a claim withdrawn by my own
falsifier.** Restricting the walk to `git diff --cached --name-only` was written
up as the H72 defence; the COMMIT-SCOPE falsifier arm then could not be made to
fire, because the break is a **no-op**: with an index-vs-HEAD comparison, a
covered path whose index copy equals HEAD has identical keys either way. The
scoping is kept as a cost decision and the safety claim is struck. An arm that
cannot fire is family A — in the falsifier this time.

## Against me, three times

1. **The selfcheck's own fixture manufactured a defect.** `git checkout -- <p>`
   restores the **INDEX** copy, which on arms 1/4/6 is the broken blob just
   staged, so arm 2 inherited arm 1's deletion and reported the check wrong. The
   check was right; the fixture was not. Fixed with `restore()`, which resets
   first and checks out `HEAD`.
2. **v1 read an error as data — family B, in the checker.** `git()` allowed rc
   128 through and returned the empty stdout that came with it, so a `git show`
   that FAILED was indistinguishable from a document with no records. It made the
   deleted-document path unreachable, and it was found by `falsify.py`'s
   WHOLE-FILE arm coming back **MISSED against a green selfcheck** — not by
   reading. `blob()` now confirms absence with `git cat-file -e`.
3. **I published a moving number.** `--history` said 265 revisions; forty minutes
   later, with two other lanes committing during my own cycle, it said 270. That
   is H84 — my own row, one cycle earlier, for publishing a figure undated. The
   denominator is no longer quoted in any docstring; `--history` prints it beside
   the HEAD it was taken at, and the refusal COUNT is what is cited.

## What is not covered, stated rather than discovered later

- **A record can still be lost by a lane that means to lose it**: the escape is
  `git commit --no-verify`, deliberately, as with every other gate here.
- **`WORK_QUEUE.md` rows and `livechat.log` are NOT covered.** Queue rows are
  edited in place by design (status column), so the key family would need to be
  id-only, and `refcheck.py` check 5 already owns duplicate/absent row ids.
  Filed as the open question rather than half-built.
- **A key can be RENAMED rather than deleted** and the gate reads that as a loss
  (`48c9059` is exactly this). That is the intended reading — the old key is
  gone from the document — but it means a legitimate renumber costs a
  `--no-verify` and a sentence in the commit message.

## Reproduce

```sh
python3 spikes/harness/recordloss.py --commit 10ed3f2   # F1: refuses
python3 spikes/harness/recordloss.py --history          # F2: 2 refusals, at HEAD
python3 spikes/harness/recordloss.py --selfcheck        # 7 arms
python3 spikes/H94_record_loss/falsify.py               # 4 properties, each broken
python3 spikes/H94_record_loss/certify_h94.py           # 3 controls -> provenance.json
bash spikes/harness/test_loop_gate.sh                   # 86 checks, incl. the wiring
```

`probe.py` is the pre-build measurement: the same replay over four candidate key
rules, run before the module existed, which is where the two refusals and the
choice of a verb-inclusive CHANNEL key came from.
