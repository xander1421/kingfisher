# D6 — Discipline: what makes a result exist

**Status: spec, falsifiable. Written 2026-08-17. Transcribes MISSION_LOOP §5 and
DECISIONS 81 ("D6 no RESULT.md without code+seed+controls; S69/S70 numbers
quarantined") into a document with an enforcer and named holes.**

## Why this exists as a spec and not only as prose

§5 has been cited as "the D6 standard" on six `RESULT.md` pages. It was never a
document, so nothing said which of its clauses a machine checks and which rely on
an author's honesty. D5 was graded "only 2/5 enforceable" for the same reason.
This spec states the split explicitly, because a gate whose enforcement is
unstated is a gate that gets read as satisfied.

**Measured, 2026-08-17, at the moment of writing:** of the 6 `RESULT.md` files
that cite D6, **0 have a `provenance.json` beside them**. Across the whole
`spikes/` tree: 89 `RESULT.md`, 4 `provenance.json`. The citation is currently
decorative in every instance where it appears. W1 is the worst case — it claimed
"four controls per D6", had no verification function at all, and shipped no
provenance record.

## The rule

> A number without its generator does not exist.

A result exists when all five hold:

| | clause |
|---|---|
| **R1** | runnable code, committed next to the `RESULT.md` that cites it |
| **R2** | a pinned seed, or a stated reason the result is seed-free |
| **R3** | controls, **each naming the input that would make it fail** |
| **R4** | the controls' **observations** persisted in the artefact, not in prose |
| **R5** | the artefact digest recorded **with** the source state it came from |

And three prohibitions, absolute:

- **P1** Never weaken a gate to pass it. Reading a range like "D1–D6" as "the
  ones we wrote" is an instance.
- **P2** Never delete a test or a control to make progress.
- **P3** Never edit a shipped document silently. Corrections keep the URL and
  gain a changelog line.

Claims built on self-authored inputs are marked as such **at birth**, not on
review (A22: a party must not supply the input to a check on itself).

## The enforcer

`spikes/harness/provenance.py`, via `record(spike_dir, deps, artifacts, controls)`.
It writes `provenance.json` and returns `ok`. **A caller that ignores `ok` and
publishes anyway is doing the thing the module exists to stop.**

| id | machine-enforced clause | refuses when |
|---|---|---|
| E1 | R5 staleness (A24) | an artifact predates the newest source in a dep tree — last commit **scoped to that path**, or any uncommitted file under it |
| E2 | R5 tree state | a dep repo is unclean and `allow_dirty` was not passed |
| E3 | R4 | a declared control was never observed |
| E4 | R4 | a control carries no observations |
| E5 | R3 | a control **did not fire** — the run is VOID, not negative |
| E6 | R1 | a declared artifact is missing from disk |
| E7 | R5 | `deps=()` with no `no_deps_reason` — empty deps skips E1 **and** E2 |
| E8 | R3 | a control declares no `null_must_contain` |

E7 and E8 were added 2026-08-17. Both closed holes where the harness *recorded* a
field that read as enforcement: `deps=()` silently disabled the entire staleness
path (2 of the 4 `provenance.json` on disk were written that way), and
`null_must_contain` was stored and never checked.

**E1 was three-quarters dead until 2026-08-17** and is the reason this section
enumerates rather than summarises:

1. the HEAD floor was the **monorepo's** last commit, so a commit by any agent to
   any unrelated spike marked every artifact in the tree stale — a false positive
   that appeared the moment two agents ran concurrently;
2. the uncommitted-file half never ran at all: `git status --porcelain` prints
   paths relative to the **repo root** and they were joined onto the dep
   directory, so every `getmtime` raised `OSError` into a bare `continue`;
3. the fixed `l[3:]` slice was off by one, because `_run` strips the output and
   eats porcelain's leading status space.

So the exact case A24 was written for — **patch a source, don't commit it, run a
binary built before the patch** — was undetectable for the whole project, which
is how both agents were burned by `fuelrun.v2.*`. `provenance.demo()` now builds a
throwaway git repo and asserts that path specifically. The old self-check used a
year-2020 artifact, which fails on the HEAD floor alone; **a control that
exercises one of two mechanisms cannot detect the other one being broken.**

## What is NOT enforced — named, not implied

| id | hole |
|---|---|
| **H1** | **Vacuity.** E8 catches an *absent* failing input, never a *plausible-filler* one. All four of W1's dead controls had prose. Human-verified, and the most dangerous hole in this spec. |
| **H2** | **R2 is not checked at all.** There is no seed field in `provenance.json` and no clause that looks for one. |
| **H3** | **R1's "committed next to"** is not checked — only that the declared file exists. An uncommitted artifact passes. |
| **H4** | `allow_dirty=True` downgrades E2 from a refusal to a record. Correct for a loop that commits at cycle end; it means E2 is advisory mid-cycle. |
| **H5** | **Nothing ties a `RESULT.md` number to the artefact.** A page can state a figure that appears nowhere in its own JSON, and no clause notices. |

## Falsifiers

| | falsifier | status |
|---|---|---|
| **F1** | Ship a spike whose controls cannot fail but whose `null_must_contain` strings are plausible. `record` must return `ok=false`. | **KNOWN-FAILING** (H1). It returns `ok=true`. W1 is the historical instance. Human review is the only defence. |
| **F2** | Any `RESULT.md` citing D6 with no `provenance.json` beside it means the citation is decorative — **and** any spike with a provenance record that never cites D6 means the standard is met without being claimed. | **2/5 CLOSED, 3/5 STANDING.** Retro-fit 2026-08-17 (`harness/retrofit_d6.py`): Q1 **2/2** and B1 **4/4** are now COMPLIANT; W4 **3/4**, N1 **2/4**, S72 **1/5** record `ok: false` because the remaining controls exist only in prose. On the second direction, 6 spikes comply silently. Runnable: `harness/retrofit_d6.py`, and `W2_witnessed_trie/attack.py` A5. |
| **F3** | Patch a dep source without committing; re-record without rebuilding. E1 must fire. | **PASSES** since 2026-08-17. Asserted in `provenance.demo()`. Would have failed every prior day of this project. |
| **F4** | Record with `deps=()` and a stale artifact. The configuration must be refused. | **PASSES** via E7 — it refuses the *configuration*, which is not the same as detecting the staleness. Weaker than F3. |
| **F5** | Put a number in a `RESULT.md` that appears in no artefact. It must be caught. | **KNOWN-FAILING** (H5). Not enforced anywhere. |

Two of five are known-failing and are recorded as such at birth rather than
discovered later. **A spec that reports 5/5 on its own falsifiers has not been
tested; it has been written to pass.**

## Consequences that bind now

1. **`ok=false` blocks a DONE verdict.** A cycle that records `ok=false` and
   writes DONE anyway is a §5 violation, not an accepted risk.
2. **The retro-fit is DONE, and it produced a harder result than expected.**
   `harness/retrofit_d6.py` extracts observations from each spike's own committed
   artefacts and never retypes a prose number — retyping would be H5 performed
   deliberately. Outcome: **Q1 2/2 and B1 4/4 COMPLIANT; W4 3/4, N1 2/4, S72 1/5.**
   So **R4 is where this project actually failed**: 9 of 20 stated controls across
   five spikes have no observation on disk at all. Two cases are worth naming.
   W4's missing control is the one its own page calls *"the one that matters"*.
   And S72's `gate_green_before_and_after` has **no pre-run gate file in any commit**
   of that directory, and `k4.sh` never invokes `quiet.sh` — so the "before" half
   left no evidence it was taken. **D6 compliance is not retroactively achievable
   where the observation was never written down; only re-running is.**
3. **D6 does not grade evidence.** LEDGER grades are a separate axis. D6 only
   decides whether a number is admissible as evidence at all.
4. **This spec is self-applying.** Its own F2 measurement is a `grep` anyone can
   re-run, which is the minimum standard it imposes on everything else.

## Changelog
- **2026-08-17, ATTACK cycle 4 (AGENT-1).** F2 was **one-directional** as first
  written: it counted citation without compliance and was blind to compliance
  without citation, so it scored the two spikes that actually honour this spec as
  neither pass nor fail. Restated in both directions and the second population
  measured (6 spikes comply silently). No other clause changed. Per P3 this
  document keeps its path and gains this line rather than being edited silently.
- **2026-08-17, same cycle.** E8's enforcement moved from a `record()` problem to a
  hard `ValueError` in `Control.__init__` by another lane, and the field is now
  `can_fail_because` — a control must state what observation would have made it
  *not* fire. E-table wording still says `null_must_contain`; both are required
  and both are refused when absent. H1 is unchanged and still the load-bearing
  hole: absence is catchable, vacuity is not.
- **2026-08-17, D6 retro-fit cycle (AGENT-1).** Consequence 2 discharged, and F2
  strengthened twice in one cycle. First it tested only that `provenance.json`
  *existed*, which after the retro-fit scored W4/N1/S72 as passing while their own
  records say `ok: false` — **file presence is not compliance.** It now reads the
  verdict: **2 of 6 ok:true, 3 PARTIAL, 1 with no record (W1, INVALID).**
- **2026-08-17, same cycle — E1 had a fourth and fifth bug**, both found by the
  retro-fit firing on all five targets at once. (4) It compared an artifact's
  **mtime** against its dep tree's **commit time**; a file is always written
  before it is committed, so every committed artifact inside its own dep tree read
  as stale by the commit latency — Q1's `quorumsim.py` by 43 seconds. Mixing the
  two clocks was the bug; `artifact_time()` now picks last-commit for tracked-clean
  files and mtime otherwise, so both sides of the comparison share a clock.
  (5) `record` writes `provenance.json` INTO `spike_dir`, so when `spike_dir` is
  also a dep, **the tool's own output became the newest "source"** and raised the
  floor above every artifact it was describing. Declared artifacts and the record
  itself are now excluded, and `.md` is excluded from the floor on both halves —
  a write-up is not a build input. That last exclusion was checked, not assumed
  convenient: for B1, W4 and S72 the only later commits touched `RESULT.md` alone,
  while N1's touched `pfx.c`/`pf_pad.c` — **and N1 is still flagged.** The
  suppression keeps the real signal and drops the false one.
