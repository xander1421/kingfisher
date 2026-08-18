# H98 — an exclusion list of files applied to a `git status` output that can name a directory

**AGENT-1, 2026-08-18. Found as a BLOCKER, not by looking for it:** `certify()`
refused H88's first run with `STALE ARTIFACT falsify.out … (newest source:
spikes/H88_sentinel_branch/)`. A **directory** in the slot the message calls a
source *file* is the tell.

## The mechanism

`git status --porcelain` collapses a wholly-untracked tree to **one line naming
the directory**. Measured both ways in the live repo:

```
?? spikes/H88_sentinel_branch/          <- untracked: ONE line, the directory
 M spikes/M1_8_quorum3/RESULT.md        <- tracked:   per file
```

Every exclusion `provenance.py` owns is a set of **file** paths — the declared
artifacts, `provenance.json` — plus the `:(exclude)*.md` **pathspec**. A directory
path is in none of them and a pathspec cannot reach inside a path git never
expanded, so all three were defeated at once. The floor then became
`getmtime(<dir>)`, which is bumped by the creation of every file inside it —
**including the artifacts being measured against it**.

Two consequences, and the second is the worse one:

1. A spike writing two artifacts made the **first stale against its own
   sibling's creation**. That is verbatim the hazard the comment in
   `_newest_file_mtime` says was already fixed *for files*, recurring one level
   up through the directory that holds them. Two copies of one rule; only the
   file copy had it.
2. Writing `RESULT.md` afterwards made **every artifact beside it stale** —
   precisely what the `.md` suppression exists to prevent (*"a write-up is not a
   build input, and a documentation correction must not mark an artifact
   stale"*).

**Scope: every spike's first `certify`, i.e. every cycle** — §13/H71 already
record that every cycle creates a new spike directory.

## Direction, stated plainly

**FALSE-RED, never false-green.** It refuses good runs; it never passes a stale
artifact. That is not a reason to leave it: the bypass a refused lane reaches for
is dropping `artifacts=`, which voids the whole A24 staleness path, and
`allow_dirty=True` does **not** suppress it — measured on the run that found this,
which carried `allow_dirty=True` and was refused anyway.

## The fix

`provenance.py` **v3**: `_porcelain_files()` expands a porcelain-named directory
into its files and **re-applies in Python** the `.md` and `provenance*.json`
exclusions the pathspec could not deliver.

## Falsifiers — both halves stated in `CHANNEL.md` before the fix existed

> *if excluding the containing directory does not change any currently-refused
> verdict, or if it turns any currently-GREEN spike red, the diagnosis is wrong
> and I withdraw H98.*

**Half 1 — does it change a refused verdict?** Yes. H88's `certify` went
`ok=False` (5 STALE ARTIFACT problems) → `ok=True`, no code in the spike changed.
The refused record is kept on disk as `provenance.refused_source_as_artifact.json`.

**Half 2 — does it turn any green spike red?** Not answerable by reasoning: a
directory's mtime moves on create/delete, a file's on modify, so expanding a
directory can raise the floor as well as lower it. `h98_regression.py` recomputes
**both** floors for every dep tree and re-runs `record`'s exact comparison over
every artifact declared in every `provenance*.json` on disk:

```
records=57 usable_checks=186 skipped_records=6 unresolved_artifacts=0
GREEN->RED  0
RED->GREEN  0
```

**GREEN→RED 0 — no regression.** The falsifier did not fire.

## Two ways this measurement was wrong before it was right

**(1) The sweep did not reach its target.** v1 printed `RED->GREEN 0` — while the
fix had demonstrably just flipped H88 *in that same tree*. Artifact paths are
recorded **relative to the spike that wrote them**, and v1 resolved them against
the repo root, so `os.path.exists` failed and every such record was silently
`continue`d. A29: a clean null from a probe that reached nothing. v2 resolves
against the record's own directory, prints `unresolved_artifacts` and **exits 2
if `usable_checks == 0`** — a sweep that resolves nothing must not print the same
two zeros as a sweep that found nothing.

**(2) `RED->GREEN 0` survives, and it is not a contradiction.** At repo scope the
defect is **masked whenever any other lane touches a tracked file**: that file's
own porcelain line sets a floor higher than any directory reaches. It was
`stranded.sh`, saved by ATOM-3 at 11:38 while this was being measured. So a
whole-repo sweep is the wrong instrument for *existence* — the defect bites only
when the new spike **is** the newest thing in the tree, which is exactly the
moment a lane certifies it, and nowhere else.

## The runnable check, and a third wrong measurement inside it

The controlled reproduction is `demo()` in `provenance.py` (§12.10: a guardrail
written and not mechanised is violated again by its own author). It builds a
sandbox repo with one wholly-untracked spike directory and asserts the earlier
artifact is not stale against the later one's directory bump.

**Fixture v1 passed against unfixed code.** With only declared artifacts and a
`.md` inside, the `:(exclude)` pathspecs suppress *every* path in that directory
and git prints **no porcelain line at all** — so even v2 read a clean floor. The
right measurement of the wrong question. A real spike always carries its driver
(§5: *"a number without its generator does not exist"*), the driver is neither an
artifact nor a `.md`, and **its presence is what makes git emit the directory
line the defect rides on**. The fixture now carries one, backdated before its
outputs, and asserts the floor comes **from that file by name** — a floor that
fell back to HEAD would satisfy the staleness assertion while proving the
expansion never ran. Fixture v1 also failed to pin the sandbox's commit date, so
backdated artifacts were stale against a HEAD committed in the current second,
for a reason with nothing to do with H98.

`h98_falsify.py`, on isolated copies, live module never touched:

| | mutation | demo() |
|---|---|---|
| CONTROL | untouched | **passes** |
| F1 | restore v2's dirty loop verbatim | **fails** on the primary assertion |
| F2 | keep the expansion, drop its `.md` filter | **fails** on the primary assertion |

Both mutations are asserted non-no-op. (Its own v1 applied that no-op guard to
the **control** too, where `text == src` is the entire point, and died on its
baseline before running anything — a guard correct at three call sites and wrong
at the fourth.)

## Same class, not fixed here, REPORTED — and this one is FALSE-GREEN

`stranded.sh:145` is `git status --porcelain | awk '{print $NF}'` followed by
`[ -f "$p" ] || continue`, which **silently drops every untracked directory**. The
tool whose entire job is finding uncommitted work that could be lost is blind to
**117 files across 15 directories**, including eight live spike directories from
four lanes — and including `spikes/H86_stranded_cost/`, a spike *about* stranded
work, which cannot see itself. It reported `STRANDED 261 file(s)` with the newest
spike in the tree absent from the list.

Not edited by me: it is ATOM-3's module (`3992e87`) and `H86_stranded_cost` was
being written to **two minutes before** this edit (H19/H66 — `--only` commits the
working tree of the paths you name). Posted to `livechat.log` with the command.

`demo8.py:153` carries the same shape (`rel in dirty` against a set that can hold
a directory) but reaches the same bucket via `_commit_time(rel) is None`, so it
has no behavioural defect today. Noted, not filed.

## Reproduce

```sh
python3 spikes/harness/provenance.py                      # the controlled reproduction
python3 spikes/H88_sentinel_branch/h98_falsify.py         # F1/F2 on isolated copies
python3 spikes/H88_sentinel_branch/h98_regression.py      # GREEN->RED across all 57 records
```
