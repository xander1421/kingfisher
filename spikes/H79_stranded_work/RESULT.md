# H79 — an uncommitted edit has no owner, so correct behaviour by every lane produces a deadlock

**ATOM-3, 2026-08-17.** `sh spikes/harness/stranded.sh`

## CLASS

**An uncommitted edit has no owner and the harness has no mechanism to find one,
so a file that gates other lanes can sit indefinitely with every lane *correctly*
deferring to a lane that may not exist.**

Every rule involved is right. §13, H19 and H66 all say do not touch another
lane's in-flight work — H19 was earned by a lane's `git add` being consumed by
another's `git commit`, H66 by my own `c8e1f50` carrying 78 lines of ok-1's. The
deadlock is what those correct rules produce when nobody can tell *in-flight*
from *abandoned*.

## The instance that provoked it

`spikes/W2_witnessed_trie/trie_witness.py`:

- 145 lines modified, all three verify functions wrapped in `try/except`
- **untouched for 115 minutes**, and imported by five spikes
- `certify` refuses on it as a dirty dependency, which gates **W5-epoch-bisect**
  (mine) and **AGENT-1's own S20 run**
- AGENT-1 posted *"please commit it"* to `livechat.log` at ~16:5x, addressed to
  whoever made the edit. **Nobody answered, and nobody could answer
  authoritatively** — H74 measured that git cannot attribute an uncommitted edit
  at all.

## The one comparison that decides it

`git status` cannot separate in-flight from stranded. This can:

> **Is the file's owner-by-history still committing, while this file is not?**

A lane mid-edit has committed nothing since it started. A lane that moved on has
committed repeatedly.

| verdict | rule | what to do |
|---|---|---|
| `IN-FLIGHT` | owner's newest commit is **older** than the file's mtime | leave it, say nothing |
| `STRANDED` | owner has committed **since** the file was last touched | no live editor — ask, in `livechat.log` |
| `NO-OWNER` | last commit has no `Atom:`, or one not on `roster.txt` | nothing to infer from — must be asked |

A tie is `IN-FLIGHT`. The benefit of the doubt goes to the lane, because the cost
of wrongly calling a live edit stranded is another lane touching it.

**`owner-by-history` is not the author of the edit and this script never says it
is.** It is the last atom to *commit* that path. Per H74 the author of an
uncommitted change is not recoverable, which is exactly why this reports evidence
for an ask and refuses to name a culprit.

## Falsifier — preregistered in `CHANNEL.md`, then run

> *If the aged files belong to lanes that have NOT committed since last touching
> them, they are simply mid-turn — "stranded" is the wrong word, the remedy is
> patience rather than policy, and this row is withdrawn.*

**It did not fire.** Of 339 uncommitted files: **261 STRANDED, 70 NO-OWNER, 8
IN-FLIGHT** — and every one of the 8 in-flight is under two minutes old. The
`owner-by-history` of every aged group has committed repeatedly since; AGENT-1's
newest commit is 17:21 against a `trie_witness.py` last touched at ~15:35.

Grouped by directory — the actionable unit, because `git commit --only <dir>` is
one act — **14 stranded groups**, oldest first:

```
STRANDED  270m   2 files  AGENT-1     spikes/G32_isurp_baseline
STRANDED  200m   1 file   AGENT-1     spikes/S77_proof_bytes
STRANDED  115m   2 files  AGENT-1     spikes/W2_witnessed_trie      <- gates W5 and S20
STRANDED   94m   1 file   AGENT-1     spikes/M1_7_transport
STRANDED   93m   2 files  AGENT-1     spikes/M1_8_quorum3           <- gates M1.13 (§8 item)
STRANDED   76m  64/63/63/58 files     spikes/M1_8_quorum3/run/*/out
STRANDED   75m   1 file   ok-1        spikes/harness
STRANDED    4m   1 file   ATTACKER-1  spikes/harness
```

## What the number is NOT

- **"STRANDED 261" is not 261 problems.** ~248 of them are generated `.env` job
  outputs under one spike's `run/` tree. v1 of this script printed one line per
  file and led with `STRANDED 261`, which is H52's floor in a new coat — a count
  dominated by one directory reads as a fleet in crisis. Grouped, it is 14 lines.
- **STRANDED does not mean "should be committed".** It means the file has no live
  editor. Some of it may be deliberately-uncommitted generated output; the split
  is 273 modified-tracked against 67 untracked, and this script does not judge
  which of those *ought* to land. That is the owner's call, which is the whole
  point of reporting rather than acting.
- **It is not an accusation.** `owner-by-history` is the last committer of the
  path, not the author of the edit sitting on it.

## Not done, deliberately

**I did not commit any other lane's file**, and the script tells you not to.
§13, H19, H66, and my own error 10 this span — `c8e1f50` carried 78 lines of
ok-1's work under my `Atom:` and I used `--only` exactly as §13 prescribes.

**I committed my own first.** `spikes/W5_epoch_bisect/provenance.json` was 43
minutes stranded with `owner-by-history=ATOM-3` when this script first ran.
Publishing a list of other lanes' stranded work while carrying one of my own is
the A22 shape. Committed as `b622fa0` before this row was written; the scan now
returns zero rows naming ATOM-3.

## Controls — `--selfcheck`, six, each able to fail

- all three verdicts fire, and all three **differ** (a collapsed classifier would
  satisfy any single-branch assertion)
- **a tie favours the editing lane** — the falsifier for the classifier itself:
  if `STRANDED` were the default rather than the result of the comparison, this
  goes red
- **a non-roster `Atom:` is refused.** v1's live defect: it reported
  `owner-by-history=corpus-composition` — a *task name* in trailers predating the
  gate that now refuses a non-callsign `Atom:` (H10) — and classified those files
  `IN-FLIGHT`, i.e. *"a lane is editing this, leave it alone"*, for an owner that
  is not a lane and can never commit again. **Wrong in the dangerous direction.**
- `mtime` works on this platform. `stat -f %m` is BSD, `stat -c %Y` is GNU; an
  empty mtime would make every file `NO-OWNER` and the scan meaningless **while
  still exiting 0**.

## Reproduce

```sh
sh spikes/harness/stranded.sh --selfcheck
sh spikes/harness/stranded.sh
```
