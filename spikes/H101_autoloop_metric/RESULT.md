# H101 — the autoloop's metric is written by the thing the autoloop mutates

**Verdict: RED. Do not arm the autoloop. Two of its three evaluators score a
markdown file, and that markdown file is inside `mutation_targets`.**

Found while setting up `githubnext/gh-aw` autoloop on operator instruction. The
harness is real and well built — three evaluators, a config with weights and
directions, a scheduler, repo-memory. **The measurement half is the defect.**

## What the evaluators actually do

```
eval_hygiene        RUNS refcheck.py + journalcheck.py       -> hygiene_score 1.0   SOUND
eval_graph_ai       REGEX-SCRAPES spikes/G34_.../RESULT.md   -> filtered_mrr 0.2648  UNSOUND
eval_verification   READS a data file                        -> savings 75.37%       UNSOUND
```

`eval_graph_ai.py:46-48` — no `subprocess`, no `run(`, it never executes the
miner:

```python
text = open(RESULT_FILE, "r").read()
m_mrr = re.search(r"Filtered MRR\s*=\s*\*?\*?([0-9]+\.[0-9]+)", text)
m_h10 = re.search(r"Hits@10\s*=\s*\*?\*?([0-9]+\.[0-9]+)%?", text)
```

`config.json` lists `spikes/G34_length1_and_constants`, `WORK_QUEUE.md` and
`HANDOFF.md` as `mutation_targets`, and both metrics as `"direction":
"maximize"`.

## Reproduced, on a fixture — a live spike was not touched

Both regexes, verbatim, against two strings:

```
honest RESULT.md     -> filtered_mrr=0.2648  hits_at_10=0.3929
forged RESULT.md     -> filtered_mrr=0.9999  hits_at_10=0.9999
```

**A candidate mutation that edits one markdown line scores as a large
improvement, is accepted by the ratchet, committed to the long-running branch
and pushed to the draft PR.** The loop would optimise its own scoreboard, and
every iteration after that compares against a forged baseline.

## Why this is the class the fleet already named

It is not a new failure. It is the one ok-1 stated most tightly this week:

> **the deciding step is downstream of something the interested party controls.**

Same shape as `Reviewed-By: self` (the gate compared the two fields it thought
mattered while the party wrote a value outside the comparison's vocabulary), and
`CLAUDE.md` family B — *the instrument is reporting fiction; confident,
well-formed, wrong.* An optimiser is the **worst** possible party to hand this
to, because unlike an agent with a conscience it will find the cheap path by
construction: editing one line strictly dominates re-deriving the number.

## What would fix it, in increasing order of cost

1. **Re-run, do not read.** The evaluator executes the miner and computes MRR
   itself. Cost: the G-series eval runtime inside a 45-minute workflow budget.
2. **Provenance gate** (`CLAUDE.md` family C, `provenance.record`): refuse when
   `RESULT.md` is newer than the artifact it describes, or when its recorded
   input hash does not match. Cheap, and catches the edit-the-markdown path
   without paying for a re-run.
3. **Remove the scraped files from `mutation_targets`.** Weakest — it closes
   this instance and not the class, since any future target could carry a
   number some evaluator reads.

At minimum, 1 or 2 before the loop is ever armed. 3 alone is not sufficient.

## Two other things found in the same pass, neither mine to fix

- **`.github/workflows/autoloop.yml` does `git push origin HEAD`** in its last
  step. That is a raw push, outside gh-aw's `safe-outputs` mechanism, and it
  duplicates `autoloop.md`'s job. `MISSION_LOOP` §11 forbids pushes outright.
- **`autoloop.md`'s `safe-outputs` declares `create-pull-request`,
  `add-comment` (max 7), `create-issue`, `update-issue`,
  `push-to-pull-request-branch`.** Every one is a §11-forbidden publishing
  action. §11 is marked non-negotiable and is the only thing that outranks
  progress (§1.7), so arming this needs an explicit operator amendment to the
  rail — not a lane's judgement call.

**Currently inert:** `git remote -v` is empty, so none of it can execute. The
rail is holding by absence of a remote rather than by policy, which is the
condition to fix *before* a remote exists, not after.

## Status

Reported, not repaired. `.github/` was created 11:33–11:34 and is untracked, so
a lane is mid-flight in it; editing under a live writer is the hazard H19
records. Handed to whoever owns the row.
