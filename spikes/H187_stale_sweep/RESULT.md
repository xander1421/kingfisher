# H187 — nothing re-runs a green spike, so a certified result rots silently

`certify ok=True`. 3 controls, all fired. 3 preregistered falsifiers: **F1 did
not fire** (the class is real), **F2 did not fire** (the instrument agrees with
`certify`), **F3 FIRED** (21 records cannot be checked at all, and that is the
finding, not a defect in the sweep).

Run: `python3 spikes/H187_stale_sweep/sweep.py` · Check: `sh spikes/H187_stale_sweep/check.sh`

## The defect

`certify` runs when a lane **executes** a spike. A finished spike is never
executed again. So a green result rots the moment a dependency moves, and
nothing anywhere says so.

Found by re-running W5 on a gate that had lifted. It had been refusing

    STALE ARTIFACT epoch_bisect.py predates W2_witnessed_trie source by 50.3h

**for two days, with nobody informed.** `kitchen/test_*.py` cannot see it — those
re-assert a recorded `result.json` rather than re-deriving it, so they stay green
straight over the rot.

## Method — nothing re-executed, no rule reimplemented

`stalecheck.py` reads each `provenance.json` already on disk and calls
`provenance`'s own helpers — `newest_source_mtime`, `artifact_time`,
`_newest_file_mtime` — then applies `record()`'s two-clock rule verbatim: commit
clock first, mtime second opinion, stale only if **both** agree. That measures
`certify`'s verdict, not a rule of mine.

Re-running 147 spikes would take hours, execute six lanes' arbitrary code, and
**overwrite their `provenance.json`**. That last one is disqualifying on its own:
an instrument that destroys the record it measures is not an instrument.

## The numbers, at one sha, because they move while you read them

At `9ae3da9f`, 2026-08-19:

| | |
|---|---:|
| directories under `spikes/` | **310** |
| carrying a `provenance.json` (i.e. ever certified) | **147** |
| CLEAN | 99 |
| **STALE — would REFUSE if `certify` ran today** | **27** |
| UNDECIDABLE — the record cannot be reconstructed at all | 21 |

Four lanes commit continuously. Across three runs inside one cycle the census
moved 305 → 310 dirs and 144 → 147 records, and `UNDECIDABLE` went 19 → 21 as
other lanes landed spikes declaring no deps. **Every number here is "at that
sha", never "the number".**

## READ THE DECOMPOSITION BEFORE QUOTING THE 27

The 27 do not mean the same thing, and publishing the total would be
`CLAUDE.md`'s second unmechanisable failure — every figure correct, pointing at
the wrong site.

| mode | n | what it actually means |
|---|---:|---|
| **quiet dep** | **13** | the W5 shape. A separate, rarely-touched dep whose source moved. **Only this mode means what the refusal text says.** |
| churny dep | 10 | stale against a directory this fleet edits continuously — `spikes/harness` took **20 commits in 24h**, `kitchen` 3. These re-rot inside the hour; "the owner re-runs it" clears nothing durable. Dep granularity, not rot. |
| SELF | 4 | stale against the spike's **own** directory, because a *second* experiment was added beside the first — `S77_proof_bytes/attack.py` (14:06) against `probe_out.txt` (12:39). Not rot either. |

`stalecheck` v2 prints the dep's 24h commit count and an exact `SELF` marker on
every row, so the split is visible without trusting this table. **No taxonomy
and no threshold live in the checker**: any live/static cutoff is a knob nobody
measured (G97's own finding) and a hardcoded `harness|kitchen` list is a scope
that narrows itself green the next time somebody adds a shared directory (H26b).
The buckets above are a reading aid computed in `sweep.py` from the printed
detail; the raw detail is persisted in `sweep.json` so a reader can disagree.

**One worked example of why the total is the wrong headline.** `G77` and `G78`
are stale against `G76_distmult_min10` — because `G76/distmult.json` changed. The
diff is two fields: `used_cached_embeddings false → true` and
`elapsed_sec 323.15 → 47.71`. **G76 was re-run from cache and every published
number is identical.** The staleness rule is mtime/commit-based, not
content-based, and it cannot tell that apart.

## Corrections to my own CLAIM

1. The CLAIM asked *"how many of this fleet's **~262 certified spikes**"*. Wrong
   in both directions: **310** directories exist under `spikes/`, and **147**
   carry a `provenance.json`. 163 were never certified at all. The 262 was a
   remembered number, not a measured one — `CLAUDE.md`'s claim decay, in the
   opening sentence of a row about stale records.
2. The CLAIM's F2 said I would validate against **W5**. I did, and then
   **demoted that arm**, because its failure mode is *"another lane edited
   `W2_witnessed_trie`"* — which says nothing about whether this module computes
   `certify`'s rule correctly (A15). `selfcheckall.py`'s own header records the
   cost of exactly that: `demo8.py --selfcheck` sat exiting 1 for days because
   its positive control depended on a live spike directory. The pass/fail
   agreement arm now runs **real `kfcheck.certify()`** on synthetic ground this
   module owns, both directions. W5 is still printed, as an observation.

## The defect mutation found in v1, before it shipped

v1's arms were all green with **half the rule deleted**. Replacing

    if src_mt and int(os.path.getmtime(a)) >= src_mt:

with `if False:` — removing the mtime second opinion, the half that separates
this from a naive mtime compare — changed **no arm's verdict**. Every synthetic
case cleared on the *first* clock, so the second was never reached: a control
that cannot fire (A15), inside the module written to reproduce that exact rule.

Fixed by building the case where the two clocks **disagree**: an artifact
committed in 2020 (commit clock says stale) whose file mtime is newer than
anything under the dep (mtime clock clears it). `record()` calls that CLEAN.
That case is arm 2b, and it is now C2 of this spike — the mutant is generated,
run and deleted on every execution, so the arm cannot rot into a comment.

## The other half: a check nobody runs

v1 had **no call site**. `selfcheckall.py` discovers every harness module and
runs `--selfcheck`, which judges the **checker**; the **scan** — the mode that
judges the tree — is invoked automatically for exactly five modules
(`pre-commit.hook`'s `CHECKS`) plus `idscope.py` in `bringup.sh`.

That class is already written down, in H103's own rationale block in
`bringup.sh` (grep `SELFCHECK is not a SCAN` — a line number into a file four
lanes edit is stale by construction, §12.4): *"a mention is not an invocation,
and a SELFCHECK is not a SCAN."* Citing it rather than opening a second id
(H18/H28).

`stalecheck` is wired into the same reporting block, on the same two grounds
H103 gives: **report only**, because it exits 1 on the shared tree today and the
party who trips it is a *reader* of someone else's spike while only the author
can clear it (H14, H52); and **bounded at 60s**, because the full scan is ~31s of
git calls and launchd re-runs `bringup.sh` every 600s — an unbounded git loop
there is `selfcheckall.py`'s preregistered F3. A truncated scan prints
`PARTIAL SCAN` and exits 2, never a short total: fewer stale rows than exist is
not better news.

## Filed, not fixed

- **H192** — `versioncheck.py` matches a version header only as a `#` comment
  (`^#\s*(\S+?)\s+v(\d+)`). Every Python module in this harness puts its header
  in a docstring, so the 16 files it checks are **16 shell scripts and zero
  Python modules** — including `refcheck.py`, `journalcheck.py`, `recordloss.py`
  and `statuscheck.py`, four of the five checkers in `pre-commit.hook`'s CHECKS list, and `versioncheck.py`
  itself. It prints `OK — every version header equals its newest rationale
  block` over 16 of 34 versioned files. Filed rather than patched (§12.1), and
  the patch is not trivial: switching on 18 files at once may surface drift in
  four lanes' trees at once.
- **The 27 STALE rows themselves.** They are six lanes' spikes. This row is the
  measurement; repairs belong to the owners, and for the 10 churny ones a repair
  is not even durable — that is a `certify` scope question, not a spike defect.

## Falsifiers

| | preregistered in `CHANNEL.md` before the run | outcome |
|---|---|---|
| F1 | zero spikes would refuse today → the class is theoretical and this row closes WRONG | **did not fire** — 27 |
| F2 | this recomputation disagrees with a real `certify` run → no count it produces means anything | **did not fire** — agrees both directions |
| F3 | `provenance.json` does not record enough to reconstruct the inputs → those spikes are counted and NAMED as undecidable, never scored clean | **FIRED** — 21, all named in `sweep.json` |
