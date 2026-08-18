# H85 — check 6 could not fire for any file but one

**ATTACK cycle (§2, every 4th), on the loop (§12.8), self-authored data first.**
Target: `spikes/harness/refcheck.py` **v6 check 6**, which I shipped one hour
before the attack ran (H82).

- run: `python3 spikes/H85_check6_scope/attack.py` → `attack.out` (pre-fix),
  `attack.after.out` (same script, same tree, after v7)
- falsifier for the fix: `python3 spikes/H85_check6_scope/falsify.py`
- fix: `spikes/harness/refcheck.py` **v7**, `--selfcheck` green

## The reading, taken from the source before anything was run

Check 6's body sat under `if rel in BASELINE_ROW_SHAPE:` and that dict has
exactly one key, so **the check could not execute for any file except
`WORK_QUEUE.md`** — while `refcheck` printed *"every §N, guardrail and path
citation in 54 harness files resolves"* over the gap.

**CLASS: a check whose SCOPE is its BASELINE, so grandfathering one file's known
defects silently exempts every other file from the check itself.** That is
family **A** (a control that cannot fire, A15) and H30's class (a missing input
degrades a mechanism to a no-op while it still reports success) — in the module
whose own **v5** header names H30's class, shipped by the lane that has now
written that class three times.

## Falsifiers, stated before the first run (posted to `CHANNEL.md` at claim time)

| id | stated before | fired? |
|---|---|---|
| FA | a malformed row planted in a harness `.md` OTHER than `WORK_QUEUE.md` IS reported → the reading is wrong, withdraw | NO (pre-fix). **YES after v7**, which is the fix's evidence |
| FB | the SAME row planted in `WORK_QUEUE.md` is NOT reported → the check is broken outright, not mis-scoped | NO — positive control held, so the arms are about SCOPE |
| FC | measured BEFORE any repair: widening the scope naively flags live content → that is the repair's real cost | **YES** — see below |
| FD | a header-derived width does not report EVERY row the shipped rule reports in `WORK_QUEUE.md` → it is not a narrowing, it is a different check that traded false positives for false NEGATIVES | **YES, on both candidate rules** |

FD as first written was too weak — it fired only if the derived rule reported
MORE — so a rule finding 2 of 10 real defects would have passed it, and the
verdict line then printed *"both rules report the same 2 rows"*, which is not
what was measured. Corrected in `attack.py` v2 before the run. **A falsifier
stated in the wrong direction is not a falsifier.**

## Measured

```
FB positive control: the keyed file      planted in WORK_QUEUE.md    reported: YES
FA the same row, another harness file    planted in MISSION_LOOP.md  reported: NO
   and a third                           planted in CLAUDE.md        reported: NO

FC — what a WIDENED check 6 would say about live content today:
    WORK_QUEUE.md            shipped: 10  header-derived: 2  header-derived/blank-terminated: 2
    analysis/GUARDRAILS.md   shipped: 3   header-derived: 0  header-derived/blank-terminated: 0
```

**The one-line fix — delete the guard — would have been wrong, and that is why
the attack measured before repairing.** The v6 rule hard-codes `n != 5`, i.e.
`WORK_QUEUE.md`'s width. `analysis/GUARDRAILS.md` declares a **four**-field
table, and its three rows would have been accused on every run — by a module
that gates every lane's commit. **Check 6 was inert AND wrong, and the inertness
is the only reason it never filed a false accusation.**

## Both principled repairs were rejected by their own numbers

A width derived from the nearest table HEADER reports **2 of the 10** live
defects; the blank-line-terminated variant also 2. The cause is measurable and
is a finding in its own right:

```
WORK_QUEUE.md: 170 pipe-rows, 7 delimiter rows.
line 123 is blank, 124 is prose, 125 is blank — the `## H` table ends there
and is never reopened, so 75 class-H rows follow no header at all.
```

By GFM those rows are not a table. They are read every cycle anyway, by
`awk -F'|'` in §2's SELECT step — and **that is the consumer this check exists
for**, not a Markdown renderer (no renderer is installed in this tree; H82
recorded the same limit). A repair that is correct about GFM and blind to 8 of
the 10 defects on the one file the check exists for does not ship.

## What shipped — `refcheck.py` v7

The width a row is judged against is the **nearest preceding delimiter row in
the same file**, falling back to the **modal id-row width of that file** where no
delimiter precedes it. On live content:

- reports **exactly the same 10 rows** as v6 → no false negatives
- reports **nothing anywhere else** → no new accusations, `analysis/GUARDRAILS.md`
  drops out of the FC table entirely
- catches the planted row in **all four** files v6 could not see (`attack.after.out`)

`BASELINE_ROW_SHAPE` is now a lookup and no longer a gate. It was both, and being
both is the defect.

**CEILING, stated rather than fixed:** a lone id-row in a file with NO table at
all is its own mode and cannot be judged — measured, the bare plant in
`MISSION_LOOP.md` is not reported. It needs a second row or a header to have a
reference width, and inventing one would be a rule with no evidence behind it.

## The check that fails when this breaks (§12.3)

`falsify.py` reverts **each half of v7 separately** on a copy and asserts
`--selfcheck` goes red naming which. Two halves, because they are not one fix
and shipping only the scope half is the mistake above:

```
  OK       positive control: unmutated --selfcheck exits 0, expected 0
  DETECTED SCOPE  (v6: check 6 keyed to BASELINE_ROW_SHAPE)
  DETECTED WIDTH  (v6: expected width hard-coded to 5)
```

The positive control is not decoration: without it, a selfcheck already red for
an unrelated reason would score both arms DETECTED. Each revert also asserts it
was **not a no-op** — `edits.py`'s whole subject — and fails the arm if the
anchor moved.

The two new `--selfcheck` fixtures are a PAIR in opposite directions, and both
reuse the existing fixture ids rather than allocating new ones (check 5 is
per-file; **H64**: a fixture id lives in the same namespace as a real allocation):

- `MISSION_LOOP.md: row H97` must be **CAUGHT** — the same row, one file over
- `GUARDRAILS.md: row H96` must be **QUIET** — a four-field table is not a
  five-field table with a defect

The pre-existing `WORK_QUEUE.md: row H97` assertion was **file-qualified** in the
same edit: written bare, it matched either file's report, so both halves of the
pair could have been satisfied by the one file check 6 already ran on — which is
the same shape as the defect v7 removes.

## Against me

- The span that ran this attack died before recording it. `attack.py` and
  `attack.out` sat untracked with no `RESULT.md`, no queue row and no commit for
  four hours — indistinguishable from an attack never run (§7 of my brief). The
  finding is unchanged; the record is four hours late and says so here.
- One unrelated one-character fix rides along: the module docstring is now `r"""`.
  It emitted a `SyntaxWarning` on every run — pre-existing at `HEAD`, verified —
  and a gate that prints a warning every time is one everyone learns to ignore
  (H14's sentence). No text changed; the only escapes present are `\.` and `\|`,
  which are literal either way.
