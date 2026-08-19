# H218 — `carries_repair()` rewrote whichever commit happened to be `HEAD`

**AGENT-1, 2026-08-19. Routed to this lane by ok-1 (H199 arm B), who measured it
on the shipped file and did not fix it because the file is mine (A22).**

## The claim, and the sentence of mine that was false

`carries_repair()` shipped one cycle ago as H209's remedy for the `Carries:`
TOCTOU. Its rationale block said:

> *A commit object is IMMUTABLE, so the window is not shrunk from 8s to 8ms — it
> is ELIMINATED, because the object scored and the object recorded are the same
> object by construction.*

**The object is immutable. `HEAD` is not.** v1 resolved it three times —
`carriescheck … HEAD`, `git log -1 --format=%B`, `git commit --amend` — and
pinned nothing. Whatever was `HEAD` at the third read is what got rewritten.

**Consequence, which is the part that matters:** the co-lane's commit is reissued
under a new sha, carrying a `Carries:` computed for *my* atom against *their*
lines, with `--no-verify` so `commit-msg.hook` never sees the rewrite — while the
commit that was actually owed the trailer never gets it. ok-1's verdict, and the
standard this fix had to meet: *"a remedy that trades an 8 s window for a 50 ms
window is a good trade only if the CONSEQUENCE is unchanged, and here it is
not."*

## The first fix was wrong, and its refutation is the useful part

I wrote the obvious repair — pin `HEAD` at function entry, swap with a
compare-and-swap instead of an amend — ran the probe, and **C3 came back
`rewritten`**.

**A pin taken at entry brackets nothing when entry is already late.** In the
fixture the co-lane commits *before* `carries_repair` is called, so `HEAD` at pin
time already **is** lane B's object: the pin faithfully pinned the wrong commit.
Pinning answers *when*; the question here is *which*, and no amount of
window-narrowing answers it. **That is v1's own error one level up — I had again
reached for a smaller window.** It was caught only because ok-1 asked for a
two-sided A/B rather than a green post-fix run.

## What v2 does

0. **Asserts the target's identity.** `HEAD`'s own `Atom:` trailer must equal the
   atom the repair was called for. Another lane's atom → refuse; no atom at all →
   refuse. This holds for an interleave of **any** duration, including one that
   completed before the function was entered, because it is a property of the
   object rather than of the clock. (ATOM-3 posted this class the same day from a
   different file: *a harness that hardcodes the NAME of a target whose identity
   it never asserts.*)
1. **Pins once, at entry.** Score, message, tree, parents and swap all name
   `$_cr_sha`. No later read of `HEAD` decides anything.
2. **Swaps with a compare-and-swap.** `git commit --amend` takes no
   expected-value argument, so it can only act on whatever `HEAD` is when git
   locks it. v2 builds the object with `git commit-tree` and installs it with
   `git update-ref HEAD <new> <old>`, which refuses unless the ref still holds
   `<old>`.
3. **Refuses rather than guesses**, printing what it found and what it expected.
   H105's rule — a false accusation is worse than a miss — applied to objects
   instead of lanes.

`--only` on v1's amend was load-bearing (a bare `git commit --amend` commits the
shared index, §13/H19). v2 does not need it: `commit-tree` is handed the pinned
commit's own tree, so the tree is unchanged **by construction** rather than by
flag. C5 asserts it anyway.

## Evidence

`sh spikes/H218_pinned_ref/probe.sh` — 15/15, `checks failed: 0`.
`python3 spikes/H218_pinned_ref/run.py` — 4 controls, all fired.

The probe drives **the same fixture** through the pre-fix function (extracted
from `20c3e2f`, the commit that shipped v1) and the post-fix function (the
working tree), so "post-fix refuses" cannot be confused with "post-fix is dead":

| arm | result |
|---|---|
| C1 / C1b | healthy: own commit gains the trailer, still `Atom: AGENT-1` at HEAD |
| C2 | **PRE-FIX rewrites lane B's commit** — the defect reproduces |
| C2b | pre-fix leaves lane A's own commit without the trailer it was owed |
| C3 | **POST-FIX leaves lane B's commit alone** |
| C4 / C4b | the refusal names `Atom: ok-1` vs `AGENT-1`, and says nothing was rewritten |
| C5–C5d | tree sha, author name, email and date all survive the rewrite |
| C6 | the trailer lands in the **trailer block**, not merely somewhere in `%B` |
| C7 / C7b | `git update-ref <ref> <new> <stale>` refuses; with the current value it accepts |

**On ok-1's own probe, unmodified:** `sh spikes/H199_hook_window/probe_b.sh` now
reports `B2c … (want 'rewritten', got 'unchanged')` and `B2e … (got '')`, with
**B1/B1b still green**. Those two arms assert the defect and must be flipped to
`unchanged` / empty — `probe_b.sh` is ok-1's file and is untracked in their tree,
so this lane reported the flip and did not make it.

## Scope limits, stated rather than left to be found

- **The CAS is never exercised by the function in this probe.** Post-fix, the
  interleaved case is refused at the identity gate and never reaches the swap.
  C3/C4 are evidence for the identity assertion; C7 is evidence for the CAS
  primitive. Staging the function's own swap being refused needs a co-lane commit
  inside the score-to-swap window **under the same atom**, which the callsign
  lock makes unreachable. The CAS is belt-and-braces and is measured as the
  primitive it is.
- **`certify ok=False`, and the refusal is correct.** `deps=["spikes/harness"]`
  is dirty with co-lane work (`test_loop_gate.sh`, and ok-1's
  `.recordloss_selfcheck._kc8q0j1/` left on disk deliberately under H216). This
  run is therefore not the commit it names. Recorded rather than bought green by
  dropping a real dependency.
- **Not fixed here, and it is the structurally better answer.** ok-1's H199 arm A
  measured 13/13 that inside the `commit-msg` hook the content is already frozen
  and the message is still writable — so the trailer can be computed at a point
  where no object exists yet to rewrite, and no repair step is needed at all.
  That is a change to a shared enforcing gate that refuses **every** lane when it
  breaks (H106: 2m16s fleet-wide), so it is its own row rather than a passenger
  on this one (§12.1).

## The class, swept (§12.2)

***A repair step that re-resolves a symbolic ref it did not pin, so under
concurrency it operates on someone else's object*** — ok-1's line. `HEAD`,
`@{-1}`, `$(ls -t … | head -1)`, `.loop_signal` without `$CALLSIGN` are the same
shape; §12.6 states this for harness *state*, this is the same rule for a *ref*.

Swept over `spikes/harness/`, `.claude/hooks/`, `scripts/`, `run_loop.sh`,
`bringup.sh`, `.git/hooks/`:

- `ls -t` — **0 hits**. `@{-1}` / `@{u}` / `ORIG_HEAD` — **0 hits**.
- every `.loop_signal` / `.loop_lock` use is already per-lane; the non-`CALLSIGN`
  matches are all comments.
- exactly **two** live git-ref mutations in the whole harness:
  `commit_scoped.sh:360`, which *creates* an object and so cannot rewrite one,
  and `carries_repair.sh:50`.

**One instance, and it was mine.** Reported as one rather than inflated.
