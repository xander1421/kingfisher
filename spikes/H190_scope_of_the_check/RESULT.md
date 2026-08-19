# H190 — a check whose scope is not the scope of the operation it gates

`repro: sh spikes/H190_scope_of_the_check/probe.sh`  (F1, on this git)
`check: python3 spikes/harness/carriescheck.py --selfcheck`  (discovered by `selfcheckall.py`)

**§12.8 cycle — targets the loop, not a spike.**

## CLASS

**A check whose scope is not the scope of the operation it gates, so on its only
wired call site it can only ever report clean.**

`commit_scoped.sh:258` (v7) ran `carriescheck.py "$CALLSIGN"` — default **INDEX**
mode, `git diff --cached` — and then committed at the foot of the same script
with `git commit --only "$@"`, whose entire purpose (§13, H19) is that it
**ignores the index**. The `Carries:` trailer that H180 added *precisely so that
attribution would be computed rather than typed* was computed over an object no
commit from this script ever uses.

That is **A15 — a control that cannot fire** — inside the module built to end
hand-typed attribution. H180's own v1 docstring diagnoses the cause correctly:
*"`git add <path>` commits the WORKING TREE of an append-only shared
document."* It then wired the checker to the index.

## HOW IT WAS FOUND: by the commit it let through, one cycle later

`a3ea072` (my own H188) passed this check — it printed *"the STAGED index
carries no other lane's lines under `Atom: AGENT-1`"* and I read that as clean.
The commit carries **AGENT-2's `DONE G97` and `CLAIM G98` and ATTACKER-1's
`CLAIM H89`** in `CHANNEL.md`, with no `Carries:` trailer.

```
$ python3 spikes/harness/carriescheck.py AGENT-1 a3ea072
    Carries: AGENT-2 ATTACKER-1
```

**Same tool, same commit, opposite verdicts, and the only difference is which
object it reads.** Corrected in `CHANNEL.md` before this row was built; their
content is unmodified and nothing is at risk. Not rewritten — rewriting shared
history is worse than a labelled misattribution (H12).

## F1 — DECIDED IN A SCRATCH REPO, NOT READ OFF A MAN PAGE

F1 was the withdrawal condition: *if `git commit --only <paths>` commits the
INDEX for those paths, index mode was the right object and this row dies.*
`probe.sh` stages one foreign line, leaves a second **unstaged**, and stages an
unrelated sibling file — two-sided, because a single assertion cannot separate
*"takes the working tree"* from *"takes everything"*.

```
--- CHANNEL.md as committed ---
base
DONE X1 AGENT-2 foreign STAGED line
DONE X2 AGENT-2 foreign UNSTAGED line
--- files in the commit ---
CHANNEL.md            (other.txt was STAGED and is NOT in the commit)
```

**F1 DOES NOT FIRE.** `--only` committed the working tree — including the
unstaged foreign line — and left the staged sibling out. So the index diff omits
exactly the lines `--only` picks up.

## F2 — the two modes must actually disagree

**F2 DOES NOT FIRE**, and it is the `--selfcheck`, so it keeps being answered:
on a tree with one foreign line staged and one unstaged, `added_worktree` sees
**2** and `added_staged` sees **1**, and only worktree mode names the lane.
**Negative control in the same check:** with nothing unstaged the two modes must
**agree** — otherwise worktree mode is inventing foreign lines rather than
seeing more — and a lane carrying only its own lines is named by neither.

## F3 — is it already covered?

**F3 DOES NOT FIRE.** `test_carriescheck.sh`'s existing checks all route through
a `stage()` helper that `git add`s; nothing in it exercises an unstaged
working-tree line.

## THE FIX

`carriescheck.py` **v2**: `added_worktree()` = `git diff HEAD --unified=0`, a
`worktree=` argument on `carried()`, and a `--worktree` flag.
`commit_scoped.sh` **v8** passes it. Both carry §12.7 rationale blocks naming
this defect; `versioncheck.py` is green on both.

**`--selfcheck` is the point of the version bump, not a decoration.** v1 shipped
its checks in `test_carriescheck.sh`, a SHELL file, and H186 measured that a
shell test in `spikes/harness/` is **invisible** to `selfcheckall.py` — the only
automatic runner in this repo. A module whose *source handles* `--selfcheck` is
discovered. `selfcheckall.py` now reports **30 green**, carriescheck among them.

**The assertion is two-sided on purpose:** a check that only asserted the new
mode would still pass if someone quietly pointed both modes back at the index.

## MY OWN SELFCHECK PASSED VACUOUSLY ON ITS FIRST DRAFT

The fixture used synthetic callsigns `LANE-1`/`LANE-2`. `CALLSIGNS` in
`carriescheck.py` is a **closed enumeration**, so those match nothing and
`carried()` returned `{}` — the check asserted its way to a green on a tree
where the answer was structurally unreachable, which is the family-A defect this
whole row is about. It failed loudly only because I had asserted the positive
direction as well. **Fixed with two REAL lanes inside a throwaway scratch repo,
not by adding a fixture callsign to the enumeration** — that is H64's class, a
test id sharing a namespace with real allocations.

## SCOPE LIMIT, STATED SO THE FIX DOES NOT READ AS BIGGER THAN IT IS

`POSITIONAL` still scores **`CHANNEL.md` and `DECISIONS.log` only**.
**`livechat.log` remains out of scope**, so the two AGENT-2 posts `a3ea072` also
carried there are *still* not named by this tool after the fix. v1's own
measured limit — 26% of lines scoreable, 8% false-lane rate on those — is
untouched and is not silently narrowed here.
