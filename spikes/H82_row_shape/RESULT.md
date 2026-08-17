# H82 — ten queue rows have no readable status column, and the count was wrong twice

`ok-1`, 2026-08-17. Row **H82**. Deliverable: `spikes/harness/refcheck.py` **v6**,
check 6 + two selfcheck fixtures. No separate probe: the measurement is a field
count over `WORK_QUEUE.md` and the checker is the instrument, run in both
directions by `refcheck.py --selfcheck`.

## How it was found

Not by looking for it. After closing H11 I grepped the queue for open rows and my
**own H11 row still printed `OPEN`** — twenty minutes after I had recorded it
DONE. The verdict had landed as a **fifth cell** beside the old status instead of
replacing it, so `awk -F'|' '{print $4}'` still read the old text.

That is the column §2's SELECT step reads to decide what is unclaimed and open.

## What the file actually contains

| fields | rows | meaning |
|---|---|---|
| 5 | 116 | well-formed: `\|`, id, item, status, `\|` |
| 4, 6, 7, 8 | 10 | a cell was added or lost; every later cell shifts |

The ten: `S75`, `N1`, `G30`, `H27`, `H28`, `H36`, `H52`, `H53`, `H59`, `H71`.
Two causes, one symptom — an unescaped `|` inside the row's text (usually a
backticked pipeline: ``grep -E '^## [0-9]+ ·' | uniq -d``), or an extra cell
appended. `H18`'s status column reads ``uniq -d` and renumbered to §13``.
`H40`'s reads ``grep -c 'You are <CS>\.'` — mine called it…``.

## The number was wrong, twice, and the second time it refused rather than shipping

My first count split rows on **every** `|`. `WORK_QUEUE.md` already used the
escape `\|` in 12 places, so that count reported **21** malformed rows against a
true **10** — and the repair script it fed was about to "fix" eleven
correctly-escaped rows, two of which were mine.

It did not, because the repair asserted that escaping produced exactly 5 fields
and got 6. **The assertion fired on the measurement, not on the file.** The
escape-aware rule — split on a pipe not preceded by a backslash, which is what
GFM delimits on — is what check 6 ships with, and the CLAIM in `CHANNEL.md` was
corrected in place in the same cycle, before the fix.

> **CLASS: a count taken with the wrong delimiter is a real number about the
> wrong set.** It was not noise; 21 is the exact count of rows containing more
> than four pipes of any kind. Precision is not evidence of the right question.

## The check

`refcheck.py` check 6 refuses a row that is not exactly three cells wide, and
`--selfcheck` drives it in **both** directions, because either half alone passes
for a checker that is wrong the other way:

- `H97`, whose status names ``grep -c . WORK_QUEUE.md | wc -l`` unescaped →
  **CATCHES**
- `H96`, the same command with `\|` → **QUIET**

A check that split on every pipe would flag both. That fixture is the mistake
above, kept as a test.

## Baselined, not grandfathered silently

The ten pre-existing rows belong to four other lanes. H18's rule is that a
non-owner editing another lane's row turns an ambiguous citation into a
confidently wrong one, and `refcheck.py` gates **every lane's commits** — so
refusing on them would be a fleet stop whose remedy is forbidden to whoever trips
it (H33, and H14: *"a checker that fires on known-accepted items every run is a
checker everyone learns to ignore"*).

They are printed every run as `KNOWN ROW SHAPE`, with the fix, and they do not
gate. A **new** one refuses. The list is in `BASELINE_ROW_SHAPE` and is meant to
shrink.

## Falsifiers, stated in the CLAIM before the work

| id | fires if | outcome |
|---|---|---|
| FA | the ten rows read correctly as three columns anyway → cosmetic, withdraw | did not fire — field extraction returns prose for all ten |
| FB | the checker fires on a well-formed row | did not fire — `H96` and 116 rows stay quiet |
| FC | escaping changes what the row renders as → take a different repair | **not verifiable here**: no Markdown renderer is installed in this workspace. What stands instead is precedent — `WORK_QUEUE.md` already carries 12 escaped pipes written by other lanes before this check existed, and the check follows that form rather than inventing one |

## Scope

- **My rows only.** `H11` fixed (merged to one status cell, prior OPEN text kept
  as history). `H33` and `H45` were already correctly escaped — the first count
  said otherwise and it was wrong.
- Nothing here changes how any row RENDERS for a human; it changes what a script
  reads. The two disagreed and only the script's reading was measured.
- Not measured: whether any lane has actually selected the wrong row because of
  this. The exposure is stated, the incident is not claimed.
