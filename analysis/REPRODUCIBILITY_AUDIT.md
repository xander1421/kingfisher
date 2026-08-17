# Can the A-grade claims be re-run? Mostly not, and that is the finding.

**Falsifier stated:** *every A-grade claim with a runnable reproducer still
reproduces.* The audit could not even reach that question for most rows,
because **the link from claim to reproducer does not exist in the record.**

```
A-grade claims                     35
  naming a command that exists      8   (all annotated today)
  naming a command that is gone     0
  naming no command at all         27
```

## Why this matters more than it sounds
Two headline drivers broke silently this week and were found only by a sweep
(`spikes/REGRESSION_SWEEP.md`). They could break unnoticed because **no claim
named the command that produced it** — the link lived in whoever wrote the row.

Two A-grade claims have already gone stale for exactly this reason:

- **S57's stored baseline** no longer reproduces: `fuel 107` in
  `v2_aarch64_android.tsv`, `fuel 580` from the current binaries, because a
  Cargo feature changed. Nothing in the row said which build produced it.
- **The 29x in-process ratio** is 1.09x at 59 ms of work. The number was right
  and its operating point was not recorded, so the rule outlived its scope.

Neither was caught by reading the LEDGER. Both were caught by accident while
doing something else.

## The convention, and the checker
A row may carry `repro: \`<path> [args]\`` in its evidence cell.
`spikes/harness/reprocheck.py` verifies the path exists and reports rows that
name nothing. It **cannot** check the command still produces the claimed number
— only running it does, which is the point: the annotation is what makes running
it possible.

Eight rows annotated, all from this session where I know the exact command.
**I have deliberately not guessed at the other 27.** A `repro:` pointing at the
wrong script is worse than none — it converts "unverifiable" into "verified
against something else", which is the S57-baseline failure in a new place.

## What this does not claim
This is an audit of *whether claims can be re-run*, not of whether they are
true. Every unannotated row may be perfectly correct. The finding is narrower
and harder to argue with: **35 A-grade claims, and until today none of them
told you how to check it.**

## Method note
The first version of this audit reported "0 of 36 have a runnable script" —
wrong, caused by `os.path.basename()` returning `''` for a path ending in `/`,
so every lookup key was empty. Caught because 0-of-36 is an implausible number,
not because the code was reviewed. A sweep that returns a suspiciously clean
answer has not been understood.
