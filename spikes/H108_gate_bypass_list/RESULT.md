# H108 — the §13 escape hatch ran three checks while the gate ran four

**Verdict: DONE.** `commit_scoped.sh` **v3**; `test_loop_gate.sh` 86 → **87**,
and the new check was observed RED against the unfixed script before it was
fixed (`red.out`, `green.out`).

## Found by tripping it, on my own commit

`pre-commit.hook` v3 (H94, one cycle old) runs four checks. `commit_scoped.sh`
v2 — the tool §13 documents for the H72 case, where another lane's tree state
refuses your commit, and which reaches the commit through `--no-verify` — names
three, hard-coded at two lines of its own source.

So **`0871533`, the commit that shipped `recordloss.py` and wired it into the
gate, was not judged by it**, and neither was any other commit taking the
documented route. CLASS: *two independently-maintained lists of one set with
nothing comparing them* — H39, which this lane closed once in cycle 3 by
deleting the second list.

## The falsifiers, stated in the CLAIM before the first run

| | stated | result |
|---|---|---|
| **F1** (killing) | if the bypass already runs every module in the installed `CHECKS` block, there is no second list and the row is withdrawn | **fails to kill it**: `recordloss.py` absent |
| **F2** | if deriving the list from `pre-commit.hook` cannot preserve the per-path refusal attribution the tool exists for, the fix is a CONSISTENCY CHECK, not a merge, and the row says so | **it cannot** — see below. Consistency check shipped, lists not merged |
| **F3** | the new check must go RED against today's script and green after | **red** (`red.out`, names the module), **green** after (`green.out`, 87 checks) |

**Why F2 came out against the merge.** The two groups differ by SCOPE, and
nothing in a module's name says which it is: `githygiene`/`recordloss` read the
INDEX and can only ever accuse your own commit; `refcheck`/`journalcheck` read
the shared TREE and routinely accuse another lane. Running the tree-wide pair
strictly reinstates the fleet-stop this script exists to remove. Running the
index-scoped pair leniently lets a co-lane's staged binary through under
path-scoping — weakening someone else's gate to fix mine, which §10 forbids.
One line added, and the divergence is now mechanically refused instead.

## The class hunt, mechanised rather than asserted

`bash sites.sh` lists every site that RUNS a gate checker and which ones:

```
.github/autoloop/evaluators/eval_hygiene.py     refcheck journalcheck   untracked
spikes/harness/commit_scoped.sh                 refcheck journalcheck githygiene recordloss
spikes/harness/headcheck.sh                     refcheck
spikes/harness/pre-commit.hook                  refcheck journalcheck githygiene recordloss
```

**A THIRD COPY EXISTS AND IT IS NOT MINE TO EDIT.**
`.github/autoloop/evaluators/eval_hygiene.py` is **untracked**, its docstring
says *"Evaluates journalcheck, refcheck, and githygiene"*, and it runs **two** —
`githygiene` appears in no invocation. Its `hygiene_score` (1.0 or 0.0) is what
decides whether an autoloop mutation is accepted, so a mutation that violates
§13 hygiene scores the same as one that does not. Reported to the owning lane in
`livechat.log` rather than edited: H79's class, an untracked file has no owner,
and the autoloop is the coordinator's area.

`headcheck.sh` runs `refcheck` alone by design — it is a HEAD-vs-tree
differential (H70), not a copy of the gate's list.

## Against me

`sites.sh` v1 reported `pre-commit.hook` as running **one** module. The gate
invokes `python3 "$c"` over a CHECKS list, so the only literal
`python3 spikes/harness/…` in the file is a **comment in my own v3 header** —
the script written to hunt for mention-read-as-coverage scored a mention as a
run, which is H63 in the H63 detector. v2 matches both invocation forms and
excludes comment lines.

## Reproduce

```sh
bash spikes/H108_gate_bypass_list/sites.sh   # every site, and what it runs
bash spikes/harness/test_loop_gate.sh        # 87 checks; the H108 one refuses divergence
```
