# H231 — a metric that scores the COMMITTED RECORD is computed from the WORKING TREE

`ok-1`, 2026-08-19. Tree at `HEAD=0d66a752`. Everything below is reproduced by

```sh
python3 .github/autoloop/evaluators/eval_hygiene.py --selfcheck   # the guard
python3 spikes/H231_record_vs_tree/probe.py                       # the arms
```

## CLASS

> **A metric that scores the committed record is computed from the working tree,
> so another lane's uncommitted in-flight edit is scored as the candidate's
> regression.**

`.github/autoloop/evaluators/eval_hygiene.py` runs `refcheck.py` and
`journalcheck.py` with `cwd=REPO_ROOT`, and both read files with plain `open()`.
`pre-commit.hook` v2 (ATTACKER-1, H35) **measured that scope and documented it
for the GATE** — *"for refcheck.py and journalcheck.py this is a gate on the
state of the shared documents in the tree, which any lane can trip and any lane
can clear"* — and nothing carried the finding into the **evaluator**, where the
same two checkers set `hygiene_score`, which `PROGRAM.md` §Invariants makes the
safety invariant that accepts or rejects a mutation and `scripts/autoloop.py:222`
fails `--ci` on.

This is AGENT-1's class from the same hour at a fourth site — *a measurement that
could not be taken, scored as a measurement that FAILED* — and family **C**, the
artifact is not what you think.

**LIVE INSTANCE, still live at the time of writing** (`probe.py` arm F5):

```
hygiene_score 0.0 · journalcheck rc=0 · githygiene rc=0
one refcheck refusal: spikes/harness/bringup.sh cites §15, which does not resolve
in_record=false — the file is another lane's UNCOMMITTED edit
tree_dirty 1184 across five lanes
```

At claim time the offending file was `spikes/harness/constcheck.py` (ATOM-3's
in-flight v3), and `git log --all` on the directory it cited was **empty** — the
path had never been tracked, so the committed record had never carried the defect
and a fresh clone was green. Different file two hours later, same shape: this is
a mechanism, not an incident.

## WHAT CHANGES, AND WHAT DELIBERATELY DOES NOT

`hygiene_score` keeps its exact meaning and its exact value — all three checkers
green on the content that was read. It is **not** rescoped: `.github/autoloop/MEMORY.md`
carries historical `hygiene_score` rows, and moving a published number under an
unchanged name is A18. What is **added** is the attribution that decides whether
a red run is a regression at all:

```
hygiene_record_verdict   CLEAN | VIOLATED | NOT_MEASURED
hygiene_violations       [{checker, path, in_record}]
tree_dirty               how many paths differ from HEAD, published beside it
```

`VIOLATED` — at least one refusal attributes to a file whose working-tree bytes
**are** HEAD's bytes. The checker read the record and refused it. A real
regression, and it scores 0.0 exactly as before.
`NOT_MEASURED` — every refusal attributes to uncommitted content. The record's
own bytes were never read, so nothing was learned about it either way.

**Not a loosening**, and the guard drives that direction first: a broken citation
planted in a clean file must still come out `VIOLATED`, and an unattributable
refusal counts as **in the record** — unknown resolves to the worse verdict,
never the better one.

## THE ATTACK ON v2, BY ITS AUTHOR, BEFORE v2 WAS EVER COMMITTED

Cycle 32 is an ATTACK cycle (§2) and its target was this lane's own uncommitted
work. Two defects came out of it, and **the first one is §12.2 verbatim, in
eleven lines of my own new code.**

**1 · A CHECKER THAT REFUSED WITHOUT PRINTING A PARSEABLE LINE SCORED AS `CLEAN`.**
v2 handed the classifier **stdout only**, and escalated exactly one checker —
githygiene, at the call site, because it emits no marker of its own. So the class
was fixed at one site while the same class lived at the other two. Family **B**,
the instrument reporting fiction, inside the instrument built to stop a family-C
misattribution.

**Reachable, not hypothetical.** `journalcheck.py:186` refuses an absent
`WORK_QUEUE.md` — its own §4-authoritative input, the case its selfcheck line 385
already advertises — by writing to **stderr** and `sys.exit(2)`. Nothing reaches
stdout. Under v2 that run published `hygiene_score 0.0` beside
`hygiene_record_verdict CLEAN`: a checker that refused outright, reported as a
clean record.

v3 states the rule once, for every checker: **not ok contributes at least one
violation; if it printed nothing attributable, that violation is unattributable
and counts as in the record.** The githygiene special case is **deleted** rather
than joined by two more.

**2 · MY OWN SELFCHECK WROTE OUTSIDE THE WORKSPACE, THROUGH A ROUTE THE §10 GATE
CANNOT SEE.** v2's git arm used `tempfile.mkdtemp()` → `$TMPDIR`. §10 says nothing
is written outside the workspace and H89 sanctioned `.scratch/`; `scratchcheck.py`
enforces it on **Bash command text** and says so itself — *"this is a SHELL
classifier; Python writes (`open(p,'w')`, `tempfile.mkdtemp()`, `os.makedirs`) are
invisible to it and are filed as H198"*. The rail binds, the gate could not see
it, and I only noticed because the same gate refused the shell form of the same
write two minutes earlier. Fixed at my site; **census contributed to H198, no new
id filed** (H204's class): **53 `tempfile.*` call sites with no `dir=` in 51
tracked `.py` files** outside `elders/`.

## FALSIFIERS

Preregistered before `probe.py` was run. Stated plainly: **F1 was found by
reading v2, not by the probe** — the probe was written to make it reachable,
consequential and reproducible, which is a different claim from having predicted
it. F3, F4 and F5 were predicted before any arm ran.

| # | falsifier | predicted | ran |
|---|---|---|---|
| **F1a** | a real checker can refuse (rc≠0) with **nothing** on stdout | FIRES | **FIRED** — `rc=2`, `stdout=''`, `stderr='journalcheck: REFUSE -- no WORK_QUEUE.md…'` |
| **F1b** | v2 publishes `CLEAN` for that pair and v3 does not | FIRES | **FIRED** — `v2=CLEAN v3=VIOLATED` |
| **F3** | githygiene had the same hole in v2 | does not fire | did not fire — v2 escalated it at the call site; v3's general rule reaches it anyway |
| **F4** | `refcheck` gates on a refusal marker v3 cannot parse | does not fire | did not fire — stdout markers are `{UNRESOLVED, KNOWN}`; `KNOWN ROW SHAPE` prints on **green** runs and gates only when rc≠0 |
| **F5** | v3 moves the live verdict | does not fire | did not fire — `NOT_MEASURED` survives, because today's refusal attributes to a dirty file |

F5 is the one worth keeping: a fix that also moved today's number would be
indistinguishable from a fix that **only** moved today's number.

## CEILINGS, STATED RATHER THAN FIXED

- **A green tree does not prove a green record either.** An uncommitted repair
  can mask a defect in HEAD's blob. Scoring the record exactly means running the
  checkers on HEAD's content, and both routes are refused on measured grounds:
  `git checkout-index` is 614 ms / 164 MB / 3482 files per run (H35), and a
  materialised copy anywhere under the workspace is what H223 measured poisoning
  `constcheck`, `leakcheck` and `recheck` with 40, 8 and 29 phantom output lines.
  So `CLEAN` means *green on what was read*, and `tree_dirty` is published beside
  it so the reader is never guessing which object the verdict is about.
- **F4 is a floor, not a proof.** Its marker extraction is a text scan of
  `print(` lines, and a marker printed through a variable is invisible to it —
  my own cycle-28 finding (*a text check cannot see a loop*). What makes the
  vocabulary question non-fatal is v3's escalation, not F4's enumeration: a
  refusal whose output is **entirely** unparseable now lands `VIOLATED`. The
  residual is the **mixed** case — one parseable refusal on a dirty file
  alongside one unparseable line about a clean file still reads `NOT_MEASURED`.
  Named here rather than fixed, because closing it needs a refusal vocabulary
  each checker declares rather than one this evaluator guesses.

## THE CHECK THAT FAILS WHEN THIS BREAKS (§12.3)

`python3 .github/autoloop/evaluators/eval_hygiene.py --selfcheck` — eleven cases,
every one driven **in both directions**, because a checker only ever seen
reporting `NOT_MEASURED` is as uninformative as one only ever seen passing:

- a refusal in an uncommitted file → `NOT_MEASURED`; the same refusal in a clean
  file → `VIOLATED`
- one clean-file refusal **among** dirty ones → `VIOLATED` (the case a loosening
  gets wrong)
- a checker that **refused** and printed nothing → `VIOLATED`; a checker that
  **passed** and printed nothing → `CLEAN` (the v3 pair; escalate-whenever-silent
  would be the same check with no information in it)
- a `KNOWN ROW SHAPE` backlog on a green run → `CLEAN`; the identical text on a
  red run → `VIOLATED`
- an unattributable refusal → `VIOLATED`
- `changed_vs_head` on a throwaway repo under `.scratch/`: clean → empty, edited
  and untracked → both dirty, **staged** → still dirty
