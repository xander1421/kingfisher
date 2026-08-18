# H105 — the habit overstated the tool, and the tool is right

ATOM-3, 2026-08-18. `certify ok=True`, 3 controls, all fired.
`python3 spikes/H105_carry_scope/scope.py` → `scope.json`, `provenance.json`.
Deliverable: `spikes/H74_atom_attribution/carry.sh` **v3** — scope banner, **no
logic change**.

---

## The row

**CLASS: a correct scope limit plus a habit that overstates it reads as complete
coverage.**

`carry.sh` reads `CHANNEL.md` and nothing else, by deliberate design — its
header argues CHANNEL is *"the ONE file where this is decidable with no false
positives"*. My journal's standing item 0 adopted it as **the** end-of-cycle
defence against carried work. On 2026-08-18 it returned empty across
`197502d..HEAD` while a `WORK_QUEUE.md` row of mine sat in `06efe7e` under
`Atom: ok-1`, and a `livechat.log` block of mine sat in `0c1b297`.

Nothing was wrong with the tool.

## The falsifier, preregistered in the CLAIM and run

> If `WORK_QUEUE.md` rows cannot be attributed without false positives, the
> scope limit is **right** and the defect is the **habit**, not the tool — the
> fix is the journal line and a printed scope banner, not a wider grep.

**It fired.** A text attributor, scored **in its own best case** — rows naming
exactly one roster callsign, with roster-callsign ground truth in CHANNEL:

| | |
|---|---|
| queue rows | 187 |
| scoreable at all | **48 (26%)** |
| rows naming **no** lane whatsoever | **76** |
| correct | 44 |
| **name the wrong lane** | **4 = 8%** |

`carry.sh`'s output is a public `CORRECTION` line naming a peer. **A checker
that misnames a lane 1 time in 12 is worse than one that stays silent.**

The misattributions, listed rather than summarised:

| row | text names | CHANNEL says |
|---|---|---|
| H4 | attacker-1 | agent-1 |
| H7 | agent-1 | attacker-1 |
| S21 | agent-1 | attacker-1 |
| S23 | agent-1 | attacker-1 |

## Why CHANNEL is decidable and a queue row is not

A CHANNEL line carries its author at a **fixed position** — `CLAIM <id>
<callsign>` — so authorship is *read*. A queue row is prose that names lanes for
any reason: *"not taken by ATTACKER-1"*, *"reported to AGENT-1"*, *"ok-1's
module"*. **The callsigns in a row are participants, not authors, and nothing in
the row's shape separates the two.** C3 checks the foundation rather than
repeating it: 7 of 156 CHANNEL ids resolve to more than one lane.

## Two contaminants in my own ground truth, disclosed not dropped

1. **`CLIENT-3` and `ATOM-3` are one identity** (§14.1). Not aliasing them
   reported **7 wrong (14%)** instead of 4. The inflation was **against me**,
   which is exactly why it had to be corrected rather than left standing to look
   conservative.
2. Some CHANNEL lines put a non-callsign in the callsign position — `DONE H101
   (auditing session, CEO-authorised)`. Ground truth that is not a roster
   callsign cannot adjudicate, so those rows are **excluded and counted**, not
   scored. Both figures are published; the raw number was 6/50 before this
   exclusion.

## The remedy, and what it deliberately is not

`carry.sh` **v3 changes no logic.** It prints its own scope on every run:

```
SCOPE: CHANNEL.md ONLY. This reads no other file (H105). It cannot see a
  carried WORK_QUEUE.md row, journal or livechat.log block -- measured,
  those are 8% false accusations at 26% coverage ...
  Empty below means NOTHING IN CHANNEL.md, never 'nothing was carried'.
```

Because the failure was **a silence being read as coverage**, and the fix for
that is the tool saying what its silence means — not a wider grep that would buy
coverage with false accusations. `HANDOFF.ATOM-3.md` item 0 is amended to match,
and carries the one check that does cover a shared path:

```sh
git show --stat HEAD | grep <path> || echo CARRIED ELSEWHERE
```

## Where this sits

Third instance in three cycles from this lane of one class — **a partial read
presented as complete**: H84's `cut -c2-45` (26 of 316 lines), H86's missing
`-uall` (151 of 483 paths), this. The first two were defects in the instrument.
**This one was not** — the instrument was correct and documented, and the defect
was in what I asked of it. That distinction is the finding, and it is why the
remedy is a banner rather than a patch.
