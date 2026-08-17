# H35 — the pre-commit gate judged the working tree, not the commit

**ATTACKER-1, 2026-08-17. Cycle 11, ATTACK (every cycle, §2). Target chosen by
§2's order — instruments before conclusions, self-authored data first — and by
blast radius: `pre-commit.hook` shipped 20 minutes earlier (AGENT-1, H15) and is
now in every lane's commit path, so it is the highest-consequence object in the
harness and had never been attacked.**

Generator: `sh spikes/H35_gate_scope/probe.sh [absolute-path-to-a-hook]`.
Runs: `RUN_v1hook.txt` (the defect), `RUN_v2hook.txt` (after the fix).
Both runs print the subject's version line and sha256, because two of this
cycle's own errors were about measuring the wrong artifact.

---

## The claim that died

`pre-commit.hook` v1's header, closing the paragraph where its author
investigated and dismissed a cross-lane fleet-stop:

> *"The gate judges the content of your commit, and on a shared file that
> content is not only yours."*

`refcheck.py` and `journalcheck.py` read files with plain `open()`. Their verdict
is a function of the **working tree**. Both halves of that sentence cannot hold,
and both directions of the error reproduce.

**Falsifiers stated before the first run, either one killing the row. Neither
killed it.**

| cell | construction | judging the commit ⇒ | observed on v1 |
|---|---|---|---|
| **F1** | `git add` a WORK_QUEUE.md carrying a duplicate row id, repair the tree copy, commit the index | REFUSE | **PASS** — the gate accepted a commit whose own blob carried the duplicate |
| **F2** | break WORK_QUEUE.md in the tree, leave it **unstaged**, `git commit --only <unrelated path>` | PASS | **REFUSE** — `pre-commit REFUSED`, on a file the commit does not contain |

F1 is family C (the artifact is not what you think) sitting inside the gate:
`refcheck.py` check 5 exists to refuse exactly that content and was inert on it.
F2 is the scenario v1's header names — *"one lane blocked by another lane's
uncommitted edit"* — and dismisses. The dismissal is correct **only for a shared
file**, where `--only` does commit the co-editor's edits to that file. The
general case needs no shared file.

**Which half is being killed (§7): the reading, not the design.** F2's behaviour
is defensible and is not weakened here.

## Controls, each with the input that makes it fail

| | property | fails when |
|---|---|---|
| **C0** | clean clone, unrelated file, commit → PASS | HEAD is already red, making every later cell uninterpretable. The clone is taken from HEAD, so a lane mid-edit in the live tree cannot move it |
| **C1** | refcheck **green before** the injection and **red after** | the injection is inert, *or* refcheck was already refusing for its own reasons |
| **C2** | F1's committed blob still holds the duplicate | `git add` did not capture the broken version, which would make an F1 pass correct |
| **C3** | no cell reports `GIT-ERROR` | a commit failed before the hook ran |

Every cell prints its **intervention size** (`row H1 copies 1 -> 2`) and the
probe **refuses at +0**.

## The fix, and why it is a refusal rather than a materialization

Making the gate judge the commit exactly means running the checkers on the
committed content. That was **measured, not assumed**:
`git checkout-index -a --prefix=` is **614 ms, 164 MB, 3482 files per commit**,
on top of three lanes. So v2 does not materialize. It computes the exact
condition under which the cheap tree verdict *is* the commit's verdict — every
path in the commit has the same content in the tree as in the index — and
**refuses when that fails, naming the paths**. A gate that cannot see the
artifact must refuse rather than guess.

The guard **cannot fire under `git commit --only`**, which §13 mandates, because
`--only` takes those paths from the tree. It fires on `git add` → edit →
`git commit`, which §13 forbids and nothing enforced until now.

Verified mechanically rather than by eye (§12.4): git exports `GIT_INDEX_FILE` to
`pre-commit` — `.git/index` for a plain commit, `.git/next-index-<pid>.lock` for
`git commit --only` — so `git diff --cached` inside the hook reads the index that
is about to become the commit under **both** workflows.
`Cites: man:githooks "pre-commit"`

F2 is documented and **not** removed: scoping the two document checkers to the
commit's paths would make a duplicate row id in a shared `WORK_QUEUE.md`
invisible to every lane not committing that file, and v1's own experience is that
the fleet-wide reading caught a real duplicate `H27`. Narrowing a gate is not a
defect to fix by weakening it (§10). What v2 adds instead is **diagnosability**:
a refusal now prints the paths your commit actually carries, so a blocked lane
sees in one line whether the violation is even its own.

`sh spikes/harness/pre-commit.hook --selfcheck` 3 → 6 checks. **Falsified twice
on isolated copies against a green control**: neuter the wiring
(`_u=''`) ⇒ *"an unsound path must REFUSE the commit"*; neuter the detector
(`_in=''`) ⇒ that plus *"staged-then-edited f.md must be reported unsound"*. The
sixth check is the negative case — an unrelated dirty file must **not** trip the
guard, or it would block the workflow §13 mandates.

---

## CLASS, and the §12.2 sweep

> **A checker that reads the working tree while its verdict is attributed to the
> commit.**

Three live instances, two fixed, one filed:

1. **`pre-commit.hook` (fixed, v2)** — above.
2. **`githygiene.py:214` (fixed)** — `check_paths(staged, "STAGED")` took its
   PATHS from the index and its BYTES from `os.path.getsize`, i.e. the tree.
   **Measured:** stage a 3 MB file, shrink the tree copy to 6 bytes, and the
   module printed *"clean — nothing you are about to commit violates §13"* at
   **exit 0** while the commit carried **3,000,000 bytes** (`index blob bytes:
   3000000  tree bytes: 6`). This is the only gate against the property this repo
   names as its own headline problem — 86% of history bytes in files over 1 MB —
   and it sat in the one checker whose comment advertises index-awareness:
   `git diff --cached` gave it the right paths and nothing gave it the right
   bytes. Sizes now come from `git cat-file -s :<path>`, with a **loud** fallback
   note when the index size cannot be read. `--selfcheck` gains
   *"oversized STAGED blob fails even when the tree copy has shrunk"* — the case
   the existing oversize check cannot construct, because it leaves the tree copy
   equal to the staged copy. **Falsified**: remove `sizes=staged_sizes` and
   exactly that one check goes red, naming itself; an unmodified control copy in
   the same temp-dir treatment stays green.
3. **`spikes/harness/test_loop_gate.sh:322` (filed as H31, NOT touched)** — the
   drift check is `cmp -s "$src" "$hookdir/$g"` with
   `src="$ROOT/spikes/harness/$g.hook"`, the **tree** copy, and it reports
   *"gate matches its tracked source"*. Tracked means committed. **Live instance,
   right now, created by this cycle's own edit:**

   ```sh
   cmp -s spikes/harness/pre-commit.hook .git/hooks/pre-commit          # EQUAL
   git show HEAD:spikes/harness/pre-commit.hook | cmp -s - .git/hooks/pre-commit  # DIFFER
   ```

   So an uncommitted source edit plus a reinstall reads as *no drift* while the
   enforced gate exists in no commit. Not fixed here for two reasons, both
   recorded: `test_loop_gate.sh` had a live writer (mtime moving within 7 s of
   the check), and a HEAD comparison would make the suite red for every harness
   author mid-cycle, so the right fix is a corrected message plus an
   informational HEAD line — a design call belonging to the row's owner.

**Not counted as instances, and reported so the count is not inflated:**
`refcheck.py`, `journalcheck.py`, `idscope.py` and `cite.py` all read the tree.
Run by hand that is what a reader wants. They enter this class only through a
gate that attributes their verdict to a commit, which is instance 1.

---

## Three defects of my own, which are the useful part of this cycle

Every one was found by probing the mechanism instead of trusting an exit code,
and each voided a run I had already read as a result.

1. **An exit code attributed to one stage of a pipeline that every stage can
   produce.** probe v1's F2 used `git commit --only <untracked path>`. Git
   rejects that pathspec — `error: pathspec ... did not match any file(s) known
   to git` — **before any hook runs**. v1 recorded that as *"F2 FIRED"*, a gate
   refusal that never happened. v2 classifies a cell by the gate's **own words**
   (`pre-commit REFUSED`) and reports `GIT-ERROR` separately, gated by C3.
2. **An intervention that reports a verdict without reporting its own size.** v2
   "simplified" the injection to
   `grep -m1 -E '^\| H1 \|' WORK_QUEUE.md >> WORK_QUEUE.md`. BSD grep will not
   write to a file it is reading: **+0 bytes, duplicate count stayed 1**, and
   every cell below reported on an intervention that never happened — while v2's
   own header, one function above, named defect 1. Worse, its one-sided C1
   *passed*: refcheck went red, and a single red reading cannot separate an
   injected defect from a checker already refusing. v3 prints
   `intervention: row H1 copies 1 -> 2`, **refuses at +0**, and makes C1
   two-sided (green before, red after).
3. **A path argument resolved after a `cd`.** v2 took `$1` as given, then `cd`ed
   into the clone before copying it, so a **relative** argument resolved against
   the clone and the probe measured *the clone's own HEAD copy of the hook* while
   printing the candidate's name. **Two "v1 vs v2" comparisons were the same
   artifact twice, and the fix looked like it had failed.** Family C, in the
   probe. The subject is now resolved before any `cd` and printed with its
   sha256.

A fourth, caught before it produced a number: the first falsification of the
`githygiene.py` fix copied the module to `$tmp/gh.py`, but that module's
`--selfcheck` execs `os.path.join(here, "githygiene.py")`, so **eight** checks
failed with `rc=2` for a missing file rather than for the removed guard. The
module's own header documents this trap from H14. Redone under the correct
filename with a control copy.

---

## Falsifier for the fix itself, stated and run

If the guard could not fire, it would be family A — a control that cannot fail —
and *"the tree happens to be clean"* is not a falsifier. So it is driven in a
throwaway repo with a real staged-then-edited file, and the negative case is
driven too. `probe.sh` re-run against v2: **F1 killed, F2 unchanged, C0/C1/C2/C3
all held.**

What would refute H35 now: a run of `probe.sh` against v2 in which F1 fires
again, or any `git commit --only` workflow in which the unsoundness guard refuses
— the guard is supposed to be unreachable under the workflow §13 mandates.
