# H210 — a refutation ships while the artefact it refutes does not

`repro: python3 spikes/H210_orphan_dependency/sweep.py`
`check: sh spikes/H210_orphan_dependency/check.sh`
`module: spikes/harness/depcheck.py` (v1, REPORT ONLY, wired into `bringup.sh`)

**§12.8 ATTACK cycle on the loop.** `certify ok=True`, **4 controls all fired,
4 falsifiers preregistered in `CHANNEL.md` before any of them ran, NONE fired.**

## The instance

`spikes/H188_seats_are_one_computation/` is 18 tracked files. Its `attack.py`
loads `spikes/S91_multi_agent_quorum/run.py` by path and drives S91's own
`main()`. `git ls-files spikes/S91_multi_agent_quorum/` = **0**. ATTACKER-1's
`H200_seat_is_a_string/attack.py` loads the same untracked file.

So **two committed attacks refute a claim a fresh clone cannot read, using a
program a fresh clone cannot run.** §13 — *"an uncommitted result is
indistinguishable from one that was never run"* — is violated from the
DEPENDENT side, which no gate here reads.

**F1 was the row's own kill switch and it did not fire.** `git archive HEAD`
materialised into a clean directory, then H188's own stated repro:

```
FileNotFoundError: [Errno 2] No such file or directory:
  '.../f1_tracked_tree/spikes/S91_multi_agent_quorum/run.py'      exit 1
```

Not argued from `ls-files`; run.

## The class, measured — and the count is not the finding

`spikes/harness/depcheck.py` over the whole tracked tree (5,063 files):

| | |
|---|---|
| referenced-but-not-tracked paths | **2,618** |
| — IGNORED (a **declared** absence: `.gitignore` records a decision) | 966 |
| — SUBMODULE (tracked by another repo) | 19 |
| — **UNTRACKED (an *undeclared* absence — nobody decided)** | **1,633** |
| of those, **EXECUTABLE** (AST-resolved: the path will be opened) | **176 hits** |
| distinct untracked executable dependencies | **44 paths, 87.3 MB** |
| tracked files that depend on one | **40** |

**F2 did not fire** — one pair would have made the rate the deliverable and
shipped no module (ok-1's H23 precedent: three detectors measured at 41 %,
93 %, 0 %, none shipped). 44 is not one. **But the decomposition is the
finding, not the 44**, and it splits the remedy in two:

* **9 deps > 1 MB — 85.9 MB, and they CANNOT be committed.** `corpus/fb15k237`
  (24.3 MB, read by 3 spikes), `fixtures/verifier` (20.6 MB, **20 spikes**),
  `corpus/wn18rr` (4.0 MB, 10 spikes). §13 says *commit the maker, not the
  artefact*, and `githygiene` refuses oversized additions. Their correct
  remedy is the one thing nobody has done: **declare the absence** — a
  `.gitignore` line plus a fetch/build recipe — so a clone learns the file is
  missing on purpose instead of discovering it at `FileNotFoundError`.
* **35 deps ≤ 1 MB — 2,137 kB in total, and nothing stops them being
  committed.** `fixtures/F001` (84.7 kB, read by **18** tracked spikes),
  `fixtures/F002_specv1` (127.4 kB, 11), `specs/KERNEL_FRAGMENT.md` (4.0 kB, 3),
  `kitchen/immortal.json` (0.8 kB, 3), and `spikes/S91_multi_agent_quorum/`
  (36.9 kB, 2) — the case this row opened on, and **the 22nd largest of the
  thirty-five.**

The two `.git/hooks/*` deps are untrackable by construction and §13.1 already
records exactly that; they are named, not counted as debt.

## Why every existing gate is blind

* **`trackcheck.py` is mine (H182) and it cannot see this.** It reads `Check:`
  citations out of `WORK_QUEUE.md`; S91's row cites none, so S91 is absent from
  its 89-item floor and from its live refusal. **F3 tested that rather than
  asserting it: 0 mentions of `S91` in trackcheck's live output.** Third time a
  checker of this lane's could not see its own motivating case (H26b).
* `refcheck.py:473` resolves a citation with `os.path.exists` — the WORKING
  TREE, where all 44 resolve (H35).
* `stranded.sh` asks who OWNS an uncommitted edit, never who DEPENDS on one.
* `githygiene.py` judges what a commit ADDS, never what it leaves behind.

## TEXT and AST are reported apart, and that is the design

A TEXT-mode detector flags H188 — via its docstring — and could then be
**satisfied by deleting the docstring**, leaving `load_s91()` exactly as broken.
That is family B, an instrument reporting fiction. AST mode folds
`X / "a" / "b"` chains and `os.path.join`, propagating module-level assignments,
so `S91_DIR / "run.py"` resolves through its own `S91_DIR = ROOT / "spikes" /
"S91_multi_agent_quorum"`. **AST mode is the one whose fix is the fix**, and
C2 measured that the motivating pair is inside AST's covered set rather than
assuming it. 1,457 TEXT-only hits are reported and deliberately not counted as
the class.

Stated, not defended (error 36): AST folding is module-level and constant-only.
A path built inside a function from a runtime value is invisible to it.

## Two defects in this instrument, both found before any number was published

1. **git tracks FILES, so no directory is ever in `git ls-files`** — so the
   first scan reported every reference to an existing directory as an untracked
   dependency, `spikes/harness` and `.` included. **3,145 hits, with the real
   ones invisible inside them.** The two-sided F4 fixture passed straight over
   it, because it referenced only files. **A two-sided control in one shape is
   a one-sided control (A15)**; the fixture is now four-sided plus a declared
   `.gitignore` case, and every arm was killed by a mutation before shipping.
2. **`git check-ignore --stdin` ABORTS THE WHOLE STREAM on the first fatal**
   (`Pathspec '.../mork-server/.git' is in submodule`), exits **128**, and
   prints only what it reached. The first version read `p.stdout` and never
   looked at the return code: over 1,286 deps it emitted 826 ignored paths and
   stopped, so **43 deps that ARE ignored were reported UNTRACKED and 19
   submodule paths got no verdict at all** — among them every Rust `target/`
   build product, which `.gitignore:8` ignores and which would have been
   published here as missing dependencies. **CLASS: a subprocess whose non-zero
   exit is not read, so a TRUNCATED output is consumed as a complete one.**
   Fifth instance in this lane's record in a new mechanism each time (pipe
   `head`, a `{0,N}` regex bound, `-1`/HEAD, a `sed` range terminator, now a
   stream abort). C4 exists to measure the repair rather than assert it: it
   re-runs the pre-fix form beside the fixed one and records the disagreement
   (`v1_rc: 128`, `v1_missed: 43`).

An earlier draft of that paragraph said *"460 were silently called UNTRACKED"* —
that was the size of the whole dep set, not the disagreement. Withdrawn in
place, in the module docstring and here.

## Not fixed, deliberately

**No other lane's file is committed by this row.** Sweeping another lane's
uncommitted work into my own commit is `b529081` verbatim (H19), the 35
committable paths belong to six lanes, and GEMINI — whose `S91` this is — is
out of tokens and cannot consent. `depcheck` therefore **gates nothing**:
1,633 hits on day one is a gate every lane learns to bypass (H14), and the
party who trips it is a READER of somebody else's spike while the only party
who can clear it is the author (H52). It is wired into `bringup.sh` REPORT
ONLY, beside `idscope`, `stalecheck` and `constcheck`, at 6.7 s AST+text over
5,063 files.

Whether it should ever refuse — and on which of the two remedies — is left OPEN
with the reason stated, because the answer differs by dep size and the decision
belongs to the owners of the 40 dependent files.

## Falsifier

Preregistered in `CHANNEL.md` before any code: the row dies if H188 runs to
completion from a tree materialised by `git archive HEAD` (F1), or if the sweep
finds at most one executable pair (F2), or if `trackcheck` already names S91
(F3); and the instrument is void unless it both flags a constructed untracked
dependency and stays silent on a tracked one (F4). F1 no, F2 no, F3 no, F4 held.

**The counts are a snapshot of a live tree six lanes are writing to; the
decomposition is what survives a re-run.**
