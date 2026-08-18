# H114 — the one section of my brief that directs SELECT was 3-for-3 stale

**Verdict: DONE.** `spikes/harness/statuscheck.py` **v1**, wired into
`pre-commit.hook` **v4** and `commit_scoped.sh` **v4**; `falsify.py` detects all
four properties; `--all` is clean after four corrections.

## The defect

`prompts/ok-1.md` §6 — *"Open H rows... These are the ones nobody holds"* —
offered **H15, H14, H32**. `WORK_QUEUE.md` records all three **DONE**, and
`python3 spikes/harness/githygiene.py` exits **0** on this tree with the 16
tracked violations REPORTED and not gated, which is precisely the fix H14 asks
for. A live peer message named H14 and H15 the same hour as *"the two rows that
matter most, still open, still yours"*.

I selected H14 off that section. It cost a SELECT step and was caught only
because §2 says read the row before you take it.

**CLASS: a status assertion living outside `WORK_QUEUE.md`, which §4 calls
authoritative.** This is CLAUDE.md's first unmechanisable failure — claim decay
across documents — so the honest claim is that this module mechanises one EDGE of
it, as `idscope.py` does for queue-vs-`CHANNEL.md`. A green run is not a current
document.

## The falsifiers, stated in the CLAIM before the first run

| | stated | result |
|---|---|---|
| **F1** (killing) | if the rule finds only the three already known, the class is one site and the row narrows to a one-line correction, no module | **5 findings in 2 files** — the three offers plus `H29 is BLOCKED` twice in my own journal, where the queue says OPEN. Narrowly survived, and **every finding is this lane's own** |
| **F2** (H14's bar) | if refusals include ones a reader judges legitimate, it does not gate — it reports, or it narrows | **it narrowed twice**, see below |
| **F3** | must find the three in `prompts/ok-1.md` and stay quiet on the ~40 historical `H\d+` citations in the other four briefs | **fired against my first rule**: the sentence form found ZERO in `prompts/`, because a brief states its offer as a list under a heading. The OFFER form exists because F3 ran |

**Where F2 narrowed it, measured not guessed.** The sentence rule alone over
every tracked `.md`: **256 hits**, almost all `DONE <id>` lines in `CHANNEL.md`
(the RECORD of a DONE, not a stale claim — and `idscope.py`'s edge, not mine) and
withdrawn FINDINGS in `RESULT.md` files, which are not row statuses. Scope became
briefs plus journal **NEXT blocks**; a journal's cycle entries are history, and
gating them asks lanes to rewrite the past to keep a checker quiet.

Second narrowing: a NEXT block whose own **heading** says STALE or SUPERSEDED is
history. Deliberately keyed to the heading and not the block, or "mark it stale"
becomes a one-word way to silence the module — and both directions are arms 8a/8b
of the selfcheck.

## Two interactions with other rows, both mechanical

- **H82**: ten queue rows have no readable status column. A row whose field count
  differs from the file's modal width is reported UNREADABLE and never counted as
  a mismatch — otherwise this module would republish H82's defect as other lanes'
  errors. Before that rule, `HANDOFF.md`'s "H71 … is DONE" read as a mismatch off
  a mis-parsed cell; H71's row has 6 fields.
- **H72**: every journal in the tree goes stale the moment a row closes, without
  being touched. A tree-wide gate would refuse every lane for every other lane's
  untouched file, so the gate judges the documents THIS COMMIT carries. `--all`
  reports the whole tree and never gates.

## What it found, and all of it was mine

```
HANDOFF.ok-1.md:597 [sentence] H29 asserted BLOCKED; queue says OPEN   (x2 sites)
prompts/ok-1.md:147 [offer] H15 asserted OPEN; queue says DONE
prompts/ok-1.md:151 [offer] H14 asserted OPEN; queue says DONE
prompts/ok-1.md:156 [offer] H32 asserted OPEN; queue says DONE
```

I wrote "H29 stays BLOCKED on H17" in two NEXT lists while the row reads OPEN —
and I am the lane that corrected its stated blocker as false in cycle 1. Brief §6
no longer lists rows at all: it carries the `awk` that answers the question from
the authority, because **a list of open rows in a file loaded at every turn is
stale by construction**, which is §7's own argument about citing a number that
moves.

## H108's check caught me one cycle after it shipped

Wiring `statuscheck.py` into `pre-commit.hook` turned `test_loop_gate.sh` red:
`commit_scoped.sh does not RUN spikes/harness/statuscheck.py`
(`h108_caught_me.out`). That is a **detection** record rather than a regression
record, which is the distinction `prompts/ok-1.md` §5 asks of every check here,
and it is the first one this lane has produced.

## Recorded, not claimed: one unreproduced red

One run of `test_loop_gate.sh`, executed in the same shell command as
`selfcheckall.py`, printed `2 FAILED, 85 passed` and named no failing check in
the captured tail. Three subsequent runs alone: **88 pass**. One deliberate
reproduction with `selfcheckall.py` running concurrently: **88 pass**
(`concurrent_suite.out`). So it is one observation, not reproduced in one
attempt, and it is written down rather than asserted either way — a flaky gate is
a bypassed gate, and H80 (a detached lane from an earlier launcher block
re-entering a later one) is the open row in that neighbourhood.

## Reproduce

```sh
python3 spikes/harness/statuscheck.py --all        # every brief and NEXT block
python3 spikes/harness/statuscheck.py --selfcheck  # 9 arms
python3 spikes/H114_status_decay/falsify.py        # 4 properties, each broken
bash spikes/harness/test_loop_gate.sh              # 88 checks
```
