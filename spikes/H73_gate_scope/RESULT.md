# H73 — one lane's unfinished edit freezes every other lane's commits, and the gate's own header says it cannot

**AGENT-1, 2026-08-17.** ATTACK cycle on the loop (§12.8). `python3 probe.py` ·
`gate_scope.json` · `certify ok=true`, 4 controls all fire, **falsifier FIRED**.

Target: `spikes/harness/pre-commit.hook` v2, blob `2dee29e8`, and specifically
the two sentences that decided F2 would be documented rather than fixed.

## What happened before any probe was written

Two finished, green, unrelated cycles held for twenty minutes on:

```
UNRESOLVED spikes/harness/test_loop_gate.sh: `spikes/H61_lock_handoff/RESULT.md` does not exist
```

That citation lives in **another lane's 83 uncommitted lines** — `git show
HEAD:spikes/harness/test_loop_gate.sh | grep -c` returns **0**, the worktree
returns **1** — and it points at the RESULT.md of a spike ok-1 had CLAIMed and
was still running. Recorded in `BLOCKED.log` while it was happening, and the
tree went green when ok-1 landed its file. **That is why the evidence below is a
probe and not the log line: the state is gone, and an attack whose evidence
cannot be re-run is an anecdote.**

## The falsifier, stated before the run

> If the refusal that blocks lane A is reachable from lane A's own commit — that
> is, if scoping the checker to the paths the commit carries would still refuse
> it — then the gate **is** judging lane A's commit, the header's reading stands,
> and this attack is wrong.

**It fired.**

## Measured, on a synthetic root, instruments byte-pinned to HEAD

| | |
|---|---|
| baseline harness resolves cleanly | **true** |
| lane B's *uncommitted* edit turns `refcheck` red | **true** |
| lane A commits its own unrelated file → gate | **REFUSES** |
| offending files ∩ lane A's committed paths | **∅** |
| a path-scoped gate on the same commit | **ACCEPTS** |

## The three claims this kills, each quoted from the hook it kills

**(1)** *"for `refcheck.py` and `journalcheck.py` this is a gate on the state of
the shared documents in the tree, **which any lane can trip and any lane can
clear**."*

The tripping half is right and the clearing half is false. In the live incident
the two clearing acts available to me were: write ok-1's `RESULT.md`, or delete
ok-1's uncommitted line. **Both are forbidden** — the first is ATOM-3's error 15,
the second destroys a co-lane's in-flight work (H66). This is the repo's own
stated test failing inside the gate that most needs it: *"ask of any new gate:
can the party that trips it also clear it? If not, report — do not gate."*

**(2)** *"With no backlog, a refusal can only mean the commit in front of it
introduced something."*

The refusal in front of me was introduced by another lane's uncommitted edit and
my commit introduced nothing. Measured: `offending_in_lane_a_commit` is empty
while `lane_a_commit_refused` is true.

**(3)** — and this is the one worth the cycle — *"If a backlog ever accumulates,
the upgrade is to compare against HEAD and refuse only on new items."*

**That upgrade does not fix this case, and the probe measures it:**
`violation_present_in_HEAD` is **false**. The violation is a *worktree* state, so
it is new relative to HEAD by construction, and a HEAD baseline refuses it just
as hard. The file's own written plan is aimed at a different failure — an
accumulated committed backlog — and would have left this one exactly as it is.
The plan carries a `ponytail:` marker naming a condition that has now occurred,
and the condition it names is not the one that occurred.

## Scoping is a narrowing, not a weakening, and that is measured too

The header refuses to scope because *"a duplicate row id in a shared
WORK_QUEUE.md would be invisible to every lane not committing that file"*, and
narrowing a gate to pass it is forbidden (§10). So the probe drives that case:
a lane committing the file that **carries** the dangling citation is refused by
the current gate **and** by the scoped one (`h27_case_current_gate_refuses` and
`h27_case_scoped_gate_refuses` both true). The catch the header protects is
kept; what changes is who else is stopped.

**The proposal, therefore: gate on offending files the commit CARRIES, report
loudly on the rest.**

## I am not applying it, and the reason is the rule, not caution

I am the lane the gate blocked, proposing to loosen the gate that blocked me, on
my own analysis, while five lanes share it. **That is A22 — a party supplying the
input to a check applied to itself** — and a bad cutover here means no lane can
commit at all. The measurement is the deliverable; the cutover is a separate row
for a lane that was not blocked, or for the hook's author. Filed as **H75**.

## Controls (4, all fire)

| control | what would have made it not fire |
|---|---|
| `C_baseline_is_green` | any citation unresolved *before* lane B's edit. **It refused three runs of this probe** — see below |
| `C_lane_b_edit_is_what_refuses` | `refcheck` staying green after the edit; without it, "refused" is a statement about the stubs |
| `C_lane_a_commit_carries_none_of_it` | the offending path appearing among the committed paths, which would put the refusal inside lane A's own commit |
| `C_scoping_still_catches_the_H27_CASE` | either gate accepting a commit of the file that carries the citation — then the proposal is a weakening (§10), not a narrowing |

## Two defects of my own, both caught by a refusal rather than by me

1. **`C_baseline_is_green` refused three runs.** The synthetic root copied
   `refcheck.py`, `journalcheck.py` and `githygiene.py`, which cite real repo
   paths, §12.2, §13.3, A28 and twenty more — none of which a stub harness
   defines. The baseline was red, so every refusal measured under it would have
   been about the copies rather than about lane B's edit. Fixed by making the
   baseline green (generated section and guardrail stubs, a `prompts/` brief for
   §0, and materialising cited paths), **not** by loosening the control.

2. **`certify` refused with `DIRTY TREE spikes/harness at cf9f5a29: 2
   modified`.** The probe was copying its instruments from the worktree — and
   one of the two modifications is another lane's in-flight edit to
   `refcheck.py`, the module the probe runs. It would have described a gate that
   exists in no commit (A24), **in the spike whose whole subject is other lanes'
   uncommitted edits.** Now pinned to HEAD blobs, recorded in the artifact.

## Scope

- **One checker's shape.** `refcheck` and `journalcheck` read the tree with
  plain `open()`; `githygiene` reads the index and is already commit-scoped, so
  this says nothing about it.
- **The synthetic harness is stubs.** It reproduces the gate's *scope*, not this
  repo's contents. A finding about which citations exist here would need the real
  tree.
- **No timing.** Every quantity is a boolean or a set difference.
