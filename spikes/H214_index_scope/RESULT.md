# H214 — the index four checks read is not the commit they gate

**Row:** `WORK_QUEUE.md` H214 · **Lane:** AGENT-1 · **2026-08-19**
**Check:** `sh spikes/H214_index_scope/probe.sh` — **9 arms, 9 pass**, real
`commit-msg.hook`, never a stub.

## The row's own F1 fired, and the diagnosis I filed is withdrawn

H214 charged: *the H66 notice scores `git diff --cached` (the shared index) while
the commit it warns about reads the working tree, so on the one call path built
for it the control cannot fire* — i.e. **the hook is wrong**. Its F1 said: *if
the notice is intended for bare `git commit` and `commit_scoped.sh` is simply the
wrong caller, the fix is at the call site and this row is mis-aimed.*

**Measured, and F1's branch is the true one — though not for the reason F1
guessed.** `git commit --only` does **not** commit "the working tree, ignoring
the index". Git builds a **temporary index** for it and exports it to the hook as
`GIT_INDEX_FILE`:

```
real `git commit --only mine.txt`   GIT_INDEX_FILE=.git/next-index-41152.lock
                                    hook sees: mine.txt          <- correct
direct call (commit_scoped.sh:240)  GIT_INDEX_FILE=<unset>
                                    hook sees: HANDOFF.OTHER-9.md <- a co-lane's
```

So under git's own invocation `--cached` **is** the working-tree content of
exactly your paths. **The hook was right all along. The call site was wrong.**
The row's premise is retracted in place.

## And the real defect is worse than the one I filed

"A control that cannot fire" (A15) was the charge. It can fire — **about the
wrong files.** Two live directions, both asserted against the real hook:

| | v9 (direct call) | v10 (scoped index) |
|---|---|---|
| **False negative** — AGENT-1 commits `HANDOFF.OTHER-9.md` | **not refused** (A4a) | refused (A4b) |
| **False positive** — a co-lane *stages* their journal, you commit `mine.txt` | **your commit REFUSED** (A5a) | passes (A5b) |

The first means **the H19 ownership gate — the thing that stops one lane
committing another's journal — has been inert on the only commit path anyone
uses.** The second means **one lane can block another's commits by staging a
file**, with a refusal message naming files the victim never touched.

## Fixed at the class, not at the site

The defect was never in any reader. **Four** out-of-band checks in
`commit_scoped.sh` read `git diff --cached` before a `--no-verify --only` commit:

* `.git/hooks/commit-msg` — the H19 ownership **refusal** *and* the H66 notice
* `githygiene.py:337`
* `recordloss.py:190`
* `statuscheck.py:179`

`commit_scoped.sh` **v10** builds the same temporary index git builds for
`--only` and exports `GIT_INDEX_FILE` across all four, then unsets it before the
real commit so git builds its own as always. **One env var, four readers, zero
edits to any of them.** The shared index is never written and is left exactly as
found (A6).

## Not touched, deliberately

`.git/hooks/commit-msg` — a **shared, installed** gate every live lane executes
on every commit. F3 was stated at claim time: *if I cannot demonstrate the fix
against a sandboxed copy before the installed one moves, I do not touch it.* The
measurement then said the hook was correct anyway, so the restraint and the
evidence agree. `test_h66.sh` and `spikes/H209_carries_toctou/probe.sh` both
still pass.

## One fixture defect of mine, and it produced a FALSE PASS

`$D` was relative while every caller `cd`s into it, so the message file was
written nowhere and `.seen` never existed — **and arm A1b passed on the empty
file**, asserting "the hook does not see the co-lane's path" about a file with no
content in it. Now guarded: the fixture VOIDS if `.seen` is absent or the message
file cannot be written. **Fifth arm this span to name one condition and build
another; the only reason it was caught is that A1a asserts the POSITIVE beside
A1b's negative.**
