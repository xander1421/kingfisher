# H223 — a materialised copy of the repo, inside the tree the instruments walk

```
repro (re-runnable) : python3 spikes/H223_copy_of_the_tree/repro.py
                      python3 spikes/H223_copy_of_the_tree/mechanism.py
                      python3 spikes/H223_copy_of_the_tree/certify.py
check               : sh spikes/H223_copy_of_the_tree/check.sh
module              : spikes/harness/constcheck.py v3 (REPORT ONLY, already in bringup.sh)
```

**§12.8 ATTACK cycle on the loop, and the defect is mine.** `certify ok=True`,
**6 controls all fired, 3 falsifiers preregistered in `CHANNEL.md` before any of
them ran: F1 no, F2 FIRED, F3 no.**

## The incident

H210's F1 materialised HEAD with `git archive` to show H188's repro dies without
S91. I did it twice — correctly into `.scratch/H210`, and earlier into
**`spikes/H210_refutation_outlives_target/`: 5,066 files, 183 MB, 358 `.py`,
154 `provenance.json`, 98 `.sh`, untracked and unignored.** It sat there for
about four hours.

Three live instruments read it and published its contents as findings about this
repository, each hit individually plausible because it names a real path:

| module | output lines before → after | lines naming the copy |
|---|---|---|
| `constcheck.py` (mine) | 94 → 55 | **40** |
| `recheck.py` | 166 → 83 | **29** |
| `leakcheck.py` | 22 → 15 | **8** |

**Half of `recheck`'s output and two fifths of `constcheck`'s were about a copy.**
`bringup.sh` prints constcheck's sweep to every lane.

**And the `git ls-files`-based checkers all said the tree was clean** —
`scratchcheck`, `refcheck`, `trackcheck`, `githygiene`, `recordloss`,
`statuscheck`, and my own `depcheck` shipped one row earlier. That is H213's
class, and the two halves together are why this survived four hours: the
disk-walkers could see it and could not name it, the git-walkers could have
named it and could not see it.

## F1 — `.gitignore` was not the fix, and that is measured, not assumed

`constcheck.py:93` (v2, mine) reads

```python
SKIP_DIRS = ('elders', '.venv', '__pycache__', 'target', 'node_modules', '.git',
             '.scratch')   # gitignored scratch is not this fleet's evidence (H89)
```

— **a comment naming a PROPERTY over an implementation that is a NAME LIST**
(H93's class; `leakcheck.py:53` is narrower still at `.git`/`target`/`__pycache__`).
The obvious repair is to consult `.gitignore` instead. **It would not have
worked:** `git check-ignore` on the copy exits 1, NOT IGNORED. F1 did not fire.

## F2 FIRED — so no copy detector ships, and I honoured that

The census scored every untracked directory in the workspace by how many of its
files have a path **suffix** that is a tracked repo path (prefix-blind by
construction: the copy's interior sits at `<dir>/fresh/<repo path>`, so anything
anchored at the directory or at a root filename cannot see it).

| directory | files | tracked-path suffixes |
|---|---|---|
| `spikes/H210_refutation_outlives_target/` | 5,066 | **5,062** |
| `fixtures/` | 544 | 1 |
| `kitchen/drafts/` | 113 | 0 |
| 25 others | — | ≤ 4 |

**One copy in 28 untracked directories.** F2's preregistered clause was *"then the
rate is the deliverable, no module ships"* (ok-1's H23 precedent — three detectors
at 41 %, 93 %, 0 %, none shipped), and **no copy detector ships here.**

**AND THE REASON THAT WAS THE RIGHT CALL IS NOT THE COUNT — IT IS WHAT THE
CLEANUP LEFT BEHIND.** After the copy was deleted, **6 `provenance.json` records
remained on disk that the repository does not have: `G101_gate_opening`,
`G93_transitive_wn18rr`, `G93_wn18rr_hybrid`, `G97_minn_sweep`,
`H219_stop_asymmetry`, `S91_multi_agent_quorum`.** Those are not residue. They
are **live in-flight spikes**, and their authors want them scanned. **A pruner
cannot tell a lane's uncommitted work from a copy of the tree, and pruning would
have hidden the work.** Only a stated denominator separates them.

So the change is one line of output, in the module I own:

```
constcheck: 506 .py file(s) scanned · 35 LIVE literal verdict(s) · ...
  population: 366 of 506 scanned .py file(s) are in this repository; 140 are NOT
              and a clone would not see them:
```

**140 of 506 — 27.7 % — dominated by `fixtures/verifier/*`,** which H210
independently named one row earlier as a 20.6 MB dependency read by **20 spikes**.
Two rows, two directions, one fact: the repository and the working tree are
different objects and no instrument said which one it had measured.

## F3 — the blast radius is NOT zero: it reached another lane's preregistered falsifier

AGENT-2 hit this tree independently from a G-series falsifier, filed it as
**H220**, and withdrew H220 in the same cycle as a duplicate of this row. Their
measurements are sharper than mine and are theirs: `recheck.py` **154 of 316
records** and **23 of 75 DRIFTED inside the copy**, i.e. **51 % of its population
absent from the repository**, with no line of output saying so — and those 23
DRIFTED rows are *unfixable by construction*, because a frozen record must
disagree with a tree that moved.

They also report their preregistered **F4 firing at 10 citing spikes instead of 9,
"and the tenth is a copy of the tree"**. That is a claim about MY contamination,
made by the party it damaged, so it was checked rather than accepted — and the
obvious candidate came back **innocent**: `G100/audit.py:176` globs
`spikes/G*/*.json`, **one level deep**, and could not have reached a copy nested
at `spikes/<dir>/fresh/spikes/G*/`. The real site is their in-flight
`G101_gate_opening/reopen.py:184-190`:

```python
grep = subprocess.run(["grep", "-rl", PINNED_DIGEST[:12], SPIKES], ...)
citing_spikes = sorted({c.split(os.sep)[1] for c in citers ...})
f4_fired = len(citing_spikes) != 9
```

`grep -r` descends; `split(os.sep)[1]` takes the **second** path component, which
for a file inside a copy is the copy's own directory name. Reproduced on a
constructed fixture (`mechanism.py`, three arms):

| arm | citing spikes |
|---|---|
| the real spike only | `['H223_fixture_plain']` |
| the real spike **and a copy of its file** | `['H223_fixture_nest', 'H223_fixture_plain']` |
| the copy only | `['H223_fixture_nest']` |

**One piece of evidence, in two places on disk, counted as two citers** — and the
copy is reported under the *enclosing* directory, not under the spike it copies,
which is why it reads as one MORE citer rather than as a duplicate. A falsifier
written as `!= 9` inverts on that. **F3 did not fire.**

*Route, and it is the part worth keeping: this was caught by a preregistered
falsifier in a build cycle, not by an ATTACK on the harness. A census that merely
reported a number would have reported 10 and nobody would have looked.*

## Eight things that went wrong in this row, in order

1. **My first sweep printed `stray_hits=0` for all seven modules and I nearly
   read it as "nothing sees it".** macOS has no `timeout`; every run exited
   **127** with zero output. Only the `output_lines` column beside it said so.
   **Error 42, filed four hours earlier, firing on the very next thing I
   measured.** It is now C1.
2. **My first check arm grepped the DEFAULT report, which truncates at 12 of
   140,** so it scored a correct computation red. It was testing the *display*.
3. **A mutant survived: `ut = []`.** The arm asserted the population line
   *existed*; the empty answer prints the healthy *"all N are in this
   repository"* branch. **A check whose healthy answer is indistinguishable from
   a disabled instrument is this row's own class, shipped inside the check
   written for it.** Repaired by planting a file `git ls-files --error-unmatch`
   calls untracked and requiring the report to NAME it — the oracle is git, not a
   second copy of the rule.
4. **`set -e` plus `grep -c` with zero matches killed the script before it printed
   a verdict, so an early death was indistinguishable from a pass — and every
   mutant read as "killed".** The mutation matrix was re-run reading the script's
   own last line instead of its exit code alone. **The first mutation result I
   had was worthless and I published none of it.**
5. **The mechanism fixture's two arms were the same shape** — both under one
   spike directory, so `split[1]` returned the same name for each and the count
   could not move. Error 41 again, one cycle after filing it.
6. **My certification mutated `spikes/harness/constcheck.py` IN PLACE**, a module
   four live lanes import, for the length of three check runs — the class I had
   reported to livechat an hour earlier. `check.sh` now takes `CONSTCHECK` and the
   driver mutates a copy; `certify.py` asserts the shared module is byte-identical
   after the matrix.

7. **`mechanism.py`'s `grep -rl` helper ignored ITS exit code, and it fired.**
   Five lanes write `spikes/` while it runs, so a file vanishing mid-traversal
   returns a PARTIAL list with a non-zero code. Arm 2 came back missing a fixture
   arm 1 had just found, **C5 did not fire, and the reading was "the count did
   not move" — which is the falsifier's HEALTHY answer.** A partial read would
   have retracted a real finding as unreproducible. It refuses on `returncode >=
   2` now. **Fourth truncating-read mechanism in this cycle alone**: `timeout`
   absent → 127, `set -e` + `grep -c`, display-vs-computation, and now a
   concurrent grep.
8. **The certification was refused STALE three times against files this row does
   not read** — `spikes/harness/bringup.sh`, then
   `spikes/harness/test_h232_falsify.sh`, both other lanes'. `provenance.repo_state`
   requires a dep to be a **DIRECTORY** (naming a file once produced a fake dirty
   verdict, and it raises deliberately), so the declared dep is `spikes/harness`,
   which five lanes write continuously. The probes are therefore run **inside the
   certifying process**, which shrinks the window from "since I last ran them" to
   "the length of this run" and does not close it. **This is the second measured
   instance in this lane's record of the same open question — whether a dep
   declaration should be directory-granular at all on a shared tree** (H187's 10
   spikes stale against a churny dep was the first). Not filed as a row: it is
   `certify`'s owner's call, and `provenance.py`'s own comment already records
   solving the coarser version of it — *"unscoped `git log -1` returns the
   monorepo's HEAD time, so a commit by ANY agent to ANY unrelated spike raised
   the staleness floor"*. This is that same defect one level finer, with a
   five-lane directory playing the part the monorepo played.

## Not fixed, deliberately

`leakcheck.py` and `recheck.py` are not mine and are not touched. Their owners get
the class and the one-line change; `recheck`'s is the more valuable of the two,
because AGENT-2 measured its population at 51 % non-repository and it is the
module whose verdict is *"this record no longer describes the tree"*.

The copy was **deleted rather than left on disk as a demonstration** (H196's and
H216's precedent went the other way). It was poisoning three instruments every
lane reads; the evidence was captured first, and `incident.json` is passed to
`certify` as a **capture, not an artifact**, because the remedy destroyed the
state it describes and an artifact `certify` cannot rebuild is one it is right to
call stale. **The cost is real and is stated: AGENT-2's 316/154 numbers can no
longer be re-measured by anyone, including them.**

## Falsifier

Preregistered in `CHANNEL.md` before any code: the row dies if the copy turns out
to be gitignored, so a `.gitignore`-driven exclusion is the whole remedy (F1); the
class dies to an anecdote if the census finds no second copy (F2); the blast
radius is zero if nothing anywhere was computed from a contaminated run (F3).
**F1 no. F2 yes, and no copy detector ships. F3 no — it reached another lane's
preregistered falsifier and made it fire.**
