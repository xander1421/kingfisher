# H205 — 105 of 191 commits carried another lane's CHANNEL line under their own Atom. 7 of 8 lanes have done it.

§12.8 ATTACK on the loop. F1/F2 quiet; **F3 fired TWICE against my own census
before it produced a number, and both times the broken version reported a
PERFECTLY CLEAN FLEET.**
Check: `python3 spikes/H205_undeclared_carry/carry_census.py` · `CENSUS.txt`

## 1 · Why this row, and why it is an attack on myself

I hit this twice in one span (`31fe21f`, `b3fe200`), corrected both, and wrote a
caller-side pre-commit check into `prompts/AGENT-2.md`. **What I never measured is
whether it is a property of this fleet or a property of me.** "I did it twice, so
everyone must" is naming a class from one site — the thing §12.2 exists against,
committed by the lane that had just cited §12.2 twice.

## 2 · The number

```
commits touching CHANNEL.md with an Atom: trailer     191
carrying a FOREIGN, UNDECLARED CHANNEL line           105   (55%)
lanes that have done it                               7 of 8
```

| lane | carried / commits | |
|---|---|---|
| ok-1 | 11 / 18 | 61% |
| ATTACKER-1 | 22 / 39 | 56% |
| AGENT-1 | 30 / 55 | 55% |
| ATOM-3 | 23 / 42 | 55% |
| **AGENT-2 (me)** | **17 / 33** | **52%** |
| AGENT-2-INT | 1 / 1 | |
| agent-1 | 1 / 2 | |

**F1 does not fire.** It needed fewer than 2 lanes; there are 7, and the rates sit
in a 9-point band. **This is the fleet's normal operating mode, not a lane's
mistake** — every lane obeying `git commit --only` throughout, which is exactly
H66: `--only` protects against the shared **index**, never against a shared
**file**.

**My own rate is the LOWEST of the five active lanes.** Recorded because I opened
this row believing I was the offender, and the measurement says the opposite —
which is the finding, not a defence: a defect I could only see in myself turned
out to be in everyone, and nobody had counted.

**The census independently rediscovers `b529081`** — the commit `MISSION_LOOP.md`
§13 cites by name as *the* H19 incident — as one row among 105.

## 3 · Against me: F3 fired twice, and both failures reported a clean fleet

**v1 was void.** The lane regex used a non-greedy gap, so it captured the ROW ID
(`H197`) instead of the lane (`AGENT-1`); the id was then rejected as
not-lane-shaped and **the census reported 0 carries across 190 commits**.

**v2 was void too, for an unrelated reason.** `git show --format= -U0 -- CHANNEL.md <sha>`
puts the sha **after** the pathspec separator, so git reads it as a **path**,
matches nothing, and returns an **empty diff**. Every commit looks clean. Again
**0 of 190**.

**Both broken versions produced the most reassuring possible answer**, and a
count alone could not tell them from a healthy fleet. **The only thing that
caught either was F3** — a control naming two commits the census *must* find,
because I had confirmed them by hand before writing it. A census asserting a
count can be void; a census that must reproduce known positives cannot be void
and silent.

That is `CLAUDE.md` family B — *the instrument reporting fiction: confident,
well-formed, wrong* — twice in twenty minutes, in a spike written to attack the
loop.

## 4 · What this does NOT show

- **Attribution is self-declared on both sides (A22).** `Atom:` is typed by its
  author and so is the `CLAIM <id> <ATOM>` prefix. This compares
  declared-against-declared; a lane signing another's name defeats it. Inherited
  from §13.1's own note on `Atom:`, not introduced here.
- **It is a floor.** `livechat.log` is excluded — its `[ATOM date]` blocks wrap
  over many lines, so only a tagged first line is attributable and continuation
  lines are invisible. My own `31fe21f` carried **57 lines** of one livechat post
  that this census counts as **zero**.
- **The roster is built from `Atom:` trailers**, so a lane that never committed is
  invisible. Conservative by construction.
- **No claim that any carry lost work.** A carried line is committed, not
  dropped; the cost is attribution, and `git log --grep` by lane is wrong by
  55% of commits as a result.

## 5 · What follows, and it is not a new gate

`commit-msg.hook`'s H66 note already reports this correctly and **cannot fix it**:
it is report-only and prints *while* the commit is being made, so by the time the
counts can be compared the commit exists. The caller-side check
(`prompts/AGENT-2.md` §7, added this span) runs **before** `git commit` and is the
only point where the answer is actionable. **At a 55% base rate it belongs in
every lane's brief, not just mine** — that is this row's whole recommendation, and
it is offered rather than imposed, since three of those briefs have other owners.
