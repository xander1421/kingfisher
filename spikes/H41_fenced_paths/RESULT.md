# H41 — refcheck v5: a path inside a fence, and a path starting `./`

**Verdict: DONE.** `spikes/harness/refcheck.py` v5, refusing. Falsifier
`spikes/H41_fenced_paths/falsify.py`, rc=0, three reverts all detected.

## The row named one defect; there were two, and the one it named catches nothing

H41 as written: *"refcheck resolves only BACKTICKED path citations, so a path
inside a ```sh fence — the form a lane will literally copy and run — is
unchecked."* True. But the row's own live instance, `./peers.sh`, would have
survived that fix, because check 4's external-tree rule skips any token whose
first path segment is not an existing top-level entry — and the first segment of
`./peers.sh` is `.`.

Measured over all 45 harness files **before writing the repair**, because "a real
false-positive surface" was the row's stated reason nobody had taken it:

| candidate | flagged | false positives |
|---|---|---|
| fence half alone | **0** | 0 |
| dot-slash half alone | 2 | 0 |
| both | 4 | 0 |

All four were the same real defect at four sites. Shipping only the half the row
named would have been a green checker over the row's own evidence — §12.2, in the
module whose v4 rationale block is about exactly that.

## Three findings against my own work, in the order they happened

1. **v5's first run flagged this file three times.** The rationale block I wrote
   for the change backticked three absent paths, and a rationale block naming an
   absent path is indistinguishable from a broken citation of it. `selfcheck()`
   already builds every fixture out of string parts for this reason, in a comment
   I had read. Fixed by writing those paths without backticks and saying so at the
   site.

2. **The scope narrowing, and what it gives up.** v5's first green-tree run showed
   4 red, of which 3 were lanes *reporting this very defect* — one inside
   `HANDOFF.ATTACKER-1.md`, a journal H10 forbids me to write to. A gate that only
   a non-author can trip and only the author may fix is a fleet stop with no legal
   remedy, which is H33 four hours later and mine again. So `HANDOFF.<lane>.md`
   leaves the PATH check and stays in every other check. **Given up: a journal
   claiming evidence at a path that does not exist is now unchecked.** That is a
   real class and it needs a check that reports to the journal's own lane instead
   of to the shared gate. Filed as its own row, not folded in here.

3. **The live instance was closed by another lane while I was writing.**
   `peers.sh` was created at 14:16; the tree is green for a reason that is not
   this change. So the tree proves nothing about v5 and the selfcheck is the only
   evidence — which is why it drives both halves in both directions.

## What runs

```sh
python3 spikes/harness/refcheck.py             # 45 harness files, refuses on any unresolved citation
python3 spikes/harness/refcheck.py --selfcheck # 7 planted breakages fire, 6 resolvable citations stay quiet
python3 spikes/H41_fenced_paths/falsify.py     # revert each of v5's 3 changes: all 3 caught, control green
```

**Falsifier, stated before the run:** if reverting any one of v5's three changes
on an isolated copy leaves `--selfcheck` green, that change is inert and the claim
that it is load-bearing is withdrawn. Run: 3 of 3 fired, control green.

**What this suite still does not construct:** a fenced path in a `.sh` harness
file (deliberately out of scope — the suite's own `./gate.sh` is real in its
scratch ROOT and absent here), and a path citation in `HANDOFF.md` itself, which
is not matched by the per-lane journal pattern and therefore still gates.
