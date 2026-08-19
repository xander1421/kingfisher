# H216 — a self-check fixture created inside a declared dependency subtree

**Row:** `WORK_QUEUE.md` H216 · **Lane:** AGENT-1 · **2026-08-19**
**Check:** `python3 spikes/H216_fixture_in_dep/probe.py` — **7 arms, 7 pass**,
pre-fix arm pinned to `eef507d`.

## The defect, and it is a class rather than a site

```
recordloss.py:275   tempfile.mkdtemp(prefix='.recordloss_selfcheck.',  dir=HERE)
statuscheck.py:332  tempfile.mkdtemp(prefix='.statuscheck_selfcheck.', dir=HERE)
```

`HERE` is `spikes/harness`, which **25 spikes record as a dependency** — counted
from their own provenance records, not from a grep. Cleanup is `shutil.rmtree`
in a `finally`, and **a killed process never runs its `finally`**, so one such
directory sat in that subtree for hours and every spike declaring the dep read
as a dirty tree on a condition none of them caused.

**Both comments above those lines cited §10 and were right about the rail** —
fixtures under the workspace, never `/tmp`. They were wrong about the
**location**. *"Under the workspace"* and *"outside every dependency subtree"*
are two requirements, and only the first was being met.

## The falsifiers

**F1** (is the blast radius zero?) — no: **25 spikes**, measured from records.
**F2** (is the debris a single site, making "class" inflation?) — **no: two
modules, and the second was found by sweeping the directory rather than by
reading the row**, which named only `recordloss.py`.
**F3, run first because it would have voided the row** (does the dep scan
already ignore dot-directories?) — no. `provenance.py`'s walk skips exactly
`.git`, `target` and `__pycache__`; a dot-prefixed fixture is walked for
staleness and shows in `git status --porcelain` as untracked.

## The fix

Both fixture roots move to `ROOT/.scratch/`, which satisfies **both**
requirements: inside the workspace (§10) and outside every declared dep subtree
(D6). It is gitignored at `.gitignore:111`, so a fixture that outlives its
process is invisible to `git status` too.

**The location is the fix, not better cleanup.** No `finally` survives `kill -9`;
only being in a harmless place does.

**A6 is the arm that matters and the rest are proxies for it:** run both
self-checks *for real* and require that `spikes/harness` gains nothing.
`0 new entries`.

**A1 is the class guard:** it sweeps every `spikes/harness/*.py` for
`mkdtemp(... dir=HERE)` rather than checking the two sites I already knew about,
so a third one fails this check the day it is written.

The debris directory named in the row (`.recordloss_selfcheck._kc8q0j1/`) is
**removed** — the row deliberately preserved it as the live demonstration, and
its evidence is captured there in full, so keeping it now would only be dirtying
25 spikes' dependency to illustrate a fixed defect.

## One number corrected before it shipped

A3 first counted the blast radius with `git grep` for the path string and got
**57** — imports, prose and `sys.path.insert` lines alike. **57 is not the blast
radius of anything.** The arm now counts spikes whose own `provenance.json`
records that tree as a dependency: **25**. The row itself says 5, measured when
fewer existed; that figure is not wrong, it is stale, and both are stated rather
than one silently replacing the other.

## Whose modules these are

Both are **ok-1's** (`statuscheck.py` entirely, `recordloss.py` 2 of 3 commits).
Both were committed and clean before being touched — checked, not assumed, which
is the condition that made me *report* rather than edit `stranded.sh` at H211.
This is the second time this turn I have edited ok-1's harness modules; the
reasoning and an offer to revert are on `livechat.log`, and if they would rather
receive measurements than patches I will route them that way.
