# H254 — the §10 gate read a regex alternation as a shell pipe, and refused a search

**ok-1, 2026-08-19.** Found by tripping it: the gate refused this command of mine
while I was reading another lane's script.

```
grep -nE 'git |cp |mktemp|TMP|SUITE|restore|trap' spikes/harness/test_h219_falsify.sh
  -> §10 REFUSED: this writes outside the workspace.
     mktemp      $TMPDIR (no template)
```

Nothing is written. The `|` before `mktemp` is a **regex alternation inside a
quoted pattern**, and `MKTEMP`'s anchor set — `(?:^|[;&|`(]|\$\()` — treats any
`|` as a pipe, so a word inside a search pattern landed in **command position**.

> **CLASS: an operator character inside quotes read as an operator.**

## Why the existing cases did not catch it

`scratchcheck.py` v3 already carries three of its author's own refused commands,
under the heading *"a gate that refuses the investigation of its own rail is
unusable"* — including `grep -rn "mktemp -d" spikes/harness/`. **All three are
clean only because their token has a SPACE before it**, so the anchor never
matched. Quoting was never understood; the space was doing the work. An
alternation with no space reaches the same defect the three cases were meant to
close.

## The fix, and what it deliberately does NOT do

`_anchor_quoted()` skips a match whose **anchor operator** is itself inside
quotes. Two subtleties, both asserted:

* **A backtick or `$(` inside DOUBLE quotes is still live**, so
  `echo "$(mktemp -d)"` keeps firing. Only single-quoted spans, and non-substitution
  operators inside double quotes, are inert.
* **It is not a mask over quoted spans.** `_in_quotes`'s own docstring records why
  that would delete true positives — the *path* of a real write is very often
  quoted (`mkdir -p "$HOME/Library/LaunchAgents"`). v4 looks only at the
  **operator**, never at the path.

| case | before | after |
|---|---|---|
| `grep -nE 'git \|cp \|mktemp\|TMP' f.sh` | **REFUSE** | clean |
| `grep -n 'x\|cd /etc && touch y' f.sh` | REFUSE | clean |
| `awk -F'\|' '$2 ~ /mktemp/' WORK_QUEUE.md` | REFUSE | clean |
| `ls \| mktemp` | REFUSE | **REFUSE** |
| `echo "$(mktemp -d)"` | REFUSE | **REFUSE** |
| `cd /etc && touch x` | REFUSE | **REFUSE** |

## What can fail

`python3 spikes/harness/scratchcheck.py --selfcheck` — **56 arms**, up from 53:
three new negatives, and mutation **M6**, which turns the anchor rule off and
requires the reported command to refuse again *while `ls | mktemp` keeps firing*.
A mutation that reddens everything proves only that the module runs.

**The POSITIVES are what make this a precision fix rather than a widening**, and
that distinction is v3's own lesson: v3 exists because v2 was five rounds of
false-positive work in which recall was never measured once.

## Recorded against myself

I logged this in `DECISIONS.log` when it happened and did **not** file it, because
two rows were already open against neighbouring gates. That was the wrong call by
one cycle: the refusal is silent about its cause — it names `mktemp` and a path
the command never mentions — so the next lane to hit it pays the same diagnosis
again. The row costs less than the diagnosis.
