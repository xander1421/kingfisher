# H213 — the §10 rail census could not see the one file a cycle is writing

**Row:** `WORK_QUEUE.md` H213 · **Lane:** AGENT-1 · **2026-08-19**
**Check:** `python3 spikes/H213_census_scope/probe.py` — **12 arms, 12 pass**,
pre-fix arm pinned to `5a4bfae` (scratchcheck v4) and guarded.

## The defect

`scratchcheck.py --scan` with no explicit targets seeded from
`git ls-files '*.sh' '*.py' '*.hook'` — **tracked paths only**. A cycle's own new
probe is **untracked by construction until that cycle commits**, so the file most
likely to be carrying a fresh §10 violation was the one file the census could not
look at, and its absence read as clean.

**The classifier was never the problem — A5 asserts that.** Handed the path
explicitly, pre-fix and post-fix give identical findings. It is the census.

**This is `allocid.sh` v1's class in a second module**: *an instrument whose
bootstrap reads fewer sources than the thing it is deciding about lives in.*
There it cost duplicate ids; here it cost a rail — and §10 is the
highest-standing rail in this repo (H89).

## All four falsifiers ran before the patch. None of them killed it.

**F1** (is `--scan` specified as a tracked-tree census, making this a docs
defect?) — no: the `--hook` gate classifies the agent's *Bash command* and never
reads a file, so nothing else covers a violation that is only ever written *into*
a file.

**F2** — *the one that could have killed the fix.* Adding untracked files must
not drag in `.scratch/`, `elders/` or build trees. **Measured:
`--exclude-standard` already honours `.gitignore`, so `.scratch/` contributes 0
and `elders/` contributes 0.** The untracked set is 95 kitchen, 21 fixtures, 18
spikes, 2 `.github`, 1 `.codex`, 1 root script — all real source. The explicit
`elders/` filter is kept anyway, because a rail should not depend on a file any
lane can edit.

**F3** (is the fix inert on a clean tree?) — no: **138 untracked vs 544 tracked.
20% of the population was invisible.**

**F4, mine** (is it live or merely latent?) — **live.** The same classifier over
the untracked half finds **four write positions in four files that the tracked
census has never once reported**:

```
fixtures/run_all.sh:30                                   /tmp/kf_trace_verifier
fixtures/webgrok-pack/run_all.sh:20                      /tmp/kf_trace_verifier
spikes/H185_launcher_generation/sandbox/bringup.sh:418   $HOME/Library/LaunchAgents
spikes/H236_retirement_undone/sandbox/bringup.sh:492     $HOME/Library/LaunchAgents
```

## The fix

One git invocation: `git ls-files -c -o --exclude-standard`. Census goes
**18 → 22** write positions over **127 → 143** shell files, with 541 non-shell
files counted rather than silently dropped. `scratchcheck --selfcheck`: **56
passed, 0 failed.**

**A6 is the arm that matters** and it reproduces a live cycle's conditions
exactly: a file written that second, never committed, containing a real `/tmp`
write. Pre-fix a bare `--scan` does not see it; post-fix it does.

## Two defects of my own in this probe, and the second is the instructive one

1. **The first draft wrote its module copy into `spikes/harness/`** — a declared
   dep subtree for five spikes, so every one of them would have gone red on a
   dirty tree for the probe's duration. **That is H216's class, and H216 is this
   lane's own row.** A7 now asserts the directory was never written to.
2. **Moving it into a tempdir under this spike broke it silently.** scratchcheck
   derives `ROOT` as `dirname(__file__)/../..`; this spike dir is at the same
   depth as `spikes/harness`, but a tempdir *under* it is one level deeper and
   resolves `ROOT` to **`spikes/`** — re-running the whole census over a fifth of
   the tree. **The only symptom was a smaller number** (A3b went 4 → 0, A4 went
   127→143 into 123→134). My comment said "same depth" while the code added a
   level: *the sixth arm this span to name one condition and build another.*
   **A0b now asserts the derived root instead of trusting that comment**, because
   a wrong root is invisible except as an unremarkable count.
