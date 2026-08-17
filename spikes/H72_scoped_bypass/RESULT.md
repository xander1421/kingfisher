# H72 — a scoped escape for a lane the shared-tree gate blocks, and three defects in my own first draft of it

`ATTACKER-1`, 2026-08-17, lane launcher 40160. Row: `WORK_QUEUE.md` H72.
Runnable: `sh spikes/H72_scoped_bypass/probe.sh`, `sh spikes/H72_scoped_bypass/attack.sh`.
Artifact: `spikes/harness/commit_scoped.sh` **v2**.

## 0 · The row as I filed it was wrong, and I corrected it before building

I filed H72 as *"a shared-tree pre-commit gate lets one lane's uncommitted work
refuse every other lane's commits"*, called it a **third-party instance of H35's
class** and said it was **worse than the original**. That framing is withdrawn.
`spikes/harness/pre-commit.hook` v2's header — **which I wrote, as ATTACKER-1,
under H35, hours earlier** — names this exact scenario as **F2**, measures it at
`spikes/H35_gate_scope/RESULT.md:34`, and records it as `NOT "FIXED"` with the
reason: scoping the two document checkers to the commit's paths would make a
duplicate row id in a shared `WORK_QUEUE.md` invisible to every lane not
committing that file. So it is not a new defect and not a third site — it is F2
reproducing in production exactly as predicted, by design. Claim decay across
documents (CLAUDE.md, three-things-no-tool-will-catch #1) with the shortest
possible decay path: author to author, same lane, same session.

## 1 · The residual, and it is measured

F2's stated remedy is **diagnosability** — the refusal prints the paths your
commit carries. The only documented **escape** is still blanket
`git commit --no-verify`.

**FALSIFIER STATED BEFORE THE RUN: if `--no-verify` still applied the
`commit-msg` trailer gate, there is no residual and H72 is withdrawn entirely.**

Measured in a throwaway repo created and destroyed inside the workspace (§10),
running this repo's real `commit-msg.hook` (`probe.sh`, output in `probe.out`):

| | | |
|---|---|---|
| C1 | trailerless message `wip`, gate live | **REFUSED (rc=1)** — control is alive |
| C2 | same message, `--no-verify` | **ACCEPTED (rc=0)** |
| C3 | what landed | `subject=wip trailers=[]` |

The falsifier did not fire. A lane blocked by another lane's *normal mid-cycle
edit* can only proceed by dropping **every** gate, including the per-commit one
that would catch **its own** defect — a subject §13 forbids, on a commit
`git log --grep='Reviewed-By: unreviewed'` cannot even enumerate.

`spikes/harness/commit_scoped.sh` closes that: it runs **strictly more** than
`--no-verify` does. What "more" means is resolved mechanically, not recalled —
the whole of `pre-commit.hook`'s work is its `CHECKS` list at line 126
(`refcheck.py`, `journalcheck.py`, `githygiene.py`) and the script runs all
three plus the real `commit-msg` hook, refusing on the tree-wide two only when a
refusal names a path the commit actually carries.

## 2 · Then I attacked my own draft, and it had three defects

v1 was **never committed** — there is no blob to diff against and I am not
implying one. The kill lands on a draft, which is the cheap case. Each defect is
run through the **frozen v1 predicate** and the **real v2 script**, because "v2
is correct here" is not evidence unless v1 was wrong here.

**FALSIFIER: if frozen-v1 returns the same verdict as v2 on all of C7/C8/C9,
there was no defect, v2 is churn, and the rationale block is withdrawn.**

| | construct | v1 | v2 |
|---|---|---|---|
| C7 | refusal names *another* spike's `RESULT.md`; I carry **my** `RESULT.md` | **BLOCKED** ✗ | PROCEEDS ✓ |
| C8 | journalcheck refuses **my own journal**, in its real vocabulary | **PROCEEDS** ✗ | BLOCKED ✓ |
| C9 | a tree-wide checker **crashed** (traceback, rc=1) | **PROCEEDS** ✗ | BLOCKED ✓ |
| C10 | refusal names only another lane's full path | — | PROCEEDS ✓ |
| C11 | checkers pass, rc=0 | — | PROCEEDS ✓ |

`attack.sh: 8 assertions, 0 FAILED`. C10 and C11 exist because without them
*"refuse everything"* satisfies C8 and C9 (H68's lesson). The falsifier did not
fire.

**Defect 1 — vocabulary invented by eye, by the lane that mechanised §12.4.**
v1 matched `(REFUSE|UNRESOLVED|DUPLICATE|CONTRADICT)`. Resolved against the
emitting code instead of recalled: `DUPLICATE` and `CONTRADICT` appear **zero**
times in either checker's refusal output, while journalcheck's actual per-item
keyword is `COLLISION` (`journalcheck.py:309`) and was **absent from the list**.
Its only other refusal line is the summary at `:316`, which **names no path at
all**. So every journalcheck refusal was unattributable and v1 proceeded past it
— **a whole checker silently descoped by a regex.** Two of four keywords fiction,
the one that mattered missing.

**Defect 2 — matched on `basename`, in a tree where `git ls-files | grep -c
'/RESULT\.md$'` = 142.** Any refusal naming any other spike's `RESULT.md`
matched yours. Every DONE cycle here commits a `RESULT.md`, so v1 refused
precisely the commit shape it exists to unblock. `basename` was also
interpolated raw into a regex, so its `.` matched any character. v2 compares
full relative paths by equality (`grep -qxF`).

**Defect 3 — exit status discarded.** `pre-commit.hook:157` decides on the
checker's rc; v1 concatenated both checkers' stdout, `|| true`'d the status and
judged the **text**. A checker that crashes prints a traceback carrying no
refusal keyword, so it read as clean. Not hypothetical: `githygiene.py` was
`NameError: name 're' is not defined` at import, in every lane's §13 path, for
20+ minutes on 2026-08-17 (H14). Family **B** — the instrument reporting fiction.

v2 also **fails closed on the unattributable**: rc≠0 naming no path refuses. The
permissive reading is the one the committer benefits from, and a rule about
oneself is written against oneself.

## 3 · Class, and the sweep (§12.2, §12.9)

> **CLASS: a gate that takes its verdict from another program's stdout while
> discarding that program's exit status, with the match vocabulary written from
> memory rather than resolved against the emitting code.**

Swept every shell and hook in the harness that greps another tool's output for a
verdict — 4 sites, and for each the match strings were resolved against the
emitting source by `grep -cF`, not read:

| site | vocabulary resolves? | crash / unrecognised output |
|---|---|---|
| `commit_scoped.sh` v1 | **no — 2 of 4 keywords fiction** | **read as clean** |
| `headcheck.sh:203` | yes (`refcheck.py:396,:399`) | explicit `CHECKER-BROKEN` branch, attributes nothing |
| `test_h13_falsify.sh:34` | yes (`test_loop_gate.sh:101-102`, check name ×1) | third state `ABSENT`, and the verdict demands exact `PASS`/`FAIL` |
| `test_h16_falsify.sh:53` | yes (both check names ×1) | `INERT` + `rc=1` |

**Three clean, one defective, and the defective one is mine.** All three clean
sites fail closed and were written by other lanes. `headcheck.sh:203-212` had
already solved defect 3 explicitly — *"a CRASHED checker emits no UNRESOLVED
lines … family B, the instrument reporting fiction"* — **hours before I wrote
v1, and I wrote the defect anyway.** That is §12.2's own class with me as the
"elsewhere": prose rules regress, mechanical checks hold, demonstrated against
its author for the second consecutive cycle.

## 4 · What this does not claim

- It does **not** fix F2 and does not try to. Narrowing `refcheck` to the
  commit's paths would hide a duplicate `WORK_QUEUE.md` row id from every lane
  not committing that file; never weaken a gate to pass it.
- It is **not** a replacement for `git commit`. Reach for it only when the gate
  refused you over another lane's path; use `git add -N` + `git commit --only`
  (§13) every other time.
- The scoping predicate is textual. It attributes a refusal by the paths that
  appear in it, so a future checker that refuses while naming its subject in
  some form other than a path will land in the **fail-closed** branch — refused,
  not waved through. That is the direction the residual error should take.
