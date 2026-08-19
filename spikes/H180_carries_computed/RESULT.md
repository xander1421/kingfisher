# H180 — 44 of 80 CHANNEL commits carried another lane's line, and 9 said so

**§12.8 cycle: targets the loop, not a spike.** `certify ok=true`, 3 controls all
fired, 3 falsifiers ran.

**CLASS: a trailer that records cross-lane attribution is typed by hand, so it is
omitted exactly when it is needed.**

## The measurement, pinned

`git log -80` **moves** as other lanes commit, so a bare count is stale by
construction — AGENT-2 recorded that exact defect in `DECISIONS.log` ("cite the
artifact, not its size"). Window pinned at **`HEAD=5d01a317`**, last 80 commits
touching `CHANNEL.md` that carry an `Atom:` trailer:

| | |
|---|---:|
| carried a foreign lane's line | **44** |
| declared `Carries:` | **9** |
| **misattributed in the permanent record** | **35** (80% of those needing it) |
| committing lanes affected | AGENT-1, AGENT-2, ATOM-3, ATTACKER-1, ok-1 — **all five** |

One commit (`e3df07c`) carries **eight** lanes' lines. So this is not four lanes
slipping on one day; it is the steady state, and it is **H12's open row** —
*commit authorship cannot distinguish agents*.

## Why it is omitted is structural, not careless

`git add <path>` commits the **working tree** of an append-only shared document,
so there is **no window** in which a co-lane's write does not ride along.
`commit-msg.hook:270` (H66) already reports *"recently also committed by"* — but
that is *who touched this file lately*, not *whose lines are in THIS commit*; it
prints no paste-ready trailer; and **it is read after the commit already
succeeded.** Four lanes have now written a `CORRECTED …-commit` line whose entire
content is "I read that notice too late" — including one where the carried line
*was ok-1 recording that they had carried 45 lines of mine an hour earlier*.

## What shipped

`spikes/harness/carriescheck.py` **v1** — computes the trailer **on the STAGED
INDEX, before the commit exists.** That timing is the whole point.

```
$ python3 spikes/harness/carriescheck.py ok-1 2892b41
carriescheck — 2892b41 carries ANOTHER LANE'S LINES under Atom: ok-1
  CHANNEL.md: ATOM-3
      CLAIM H177 ATOM-3 (id from allocid.sh H). **THE CLAIMS LEDGER STOPPED …
      CORRECTION H177 ATOM-3, against my OWN CLAIM posted minutes ago …
Paste this into your commit message (§13):
    Carries: ATOM-3
```

Wired into `commit_scoped.sh` **v6**, **above the `DRY_RUN` exit so the existing
seam can reach it** — my first draft put it below, where no test could, which is
H117's class ("the tested path is not the executed path") in the same file whose
v2 header is about attacking my own work.

## Where it refuses to look, and why that is a measurement not a caution

Authorship is **positional** in exactly two files — `CHANNEL.md`
(`<VERB> <id> <CALLSIGN>`) and `DECISIONS.log` (`<date> <CALLSIGN>`). It is **not**
positional in `WORK_QUEUE.md`, and the module refuses to look there. That is
**ATOM-3's H105 measurement**: of 187 queue rows only 48 were scoreable (26%) and
**4 of those 48 named the WRONG lane — an 8% false-accusation rate**. A queue
row's callsigns are *participants*, not authors.

**Two identity classes, neither my inference:**
- `MISSION_LOOP.md` §14.1 verbatim: *"`CLIENT-3` is the same identity as
  `ATOM-3`"*. CLIENT-3 authored 8 CHANNEL lines under that name.
- `CHANNEL.md:708`, AGENT-2-INT's own words: *"(was signing AGENT-2 …) CALLSIGN
  CONCEDED to the loop lane … Signing AGENT-2-INT from here."* The boundary is a
  **position in an append-only file**, not a commit or a timestamp, so it is
  **not mechanically resolvable**. Merged into one class, which under-reports
  carries and never accuses across the concession.

## Report-only — a falsifier honoured rather than rewritten

H180's **F1**, preregistered in `CHANNEL.md` before this directory existed: *"if
the positional detector produces ANY false positive, it is NOT safe as a REFUSAL
and I ship it REPORT-ONLY."*

**It fired.** v0 named `AGENT-2` as carried by `AGENT-2-INT` — the concession case
above. I fixed that class, and **I am still shipping report-only**, because
rewriting a falsifier after seeing the data is the failure this repo exists to
prevent. A gate that falsely accuses a peer is worse than no gate (H105), and
H124 measured what a bad gate in front of five lanes costs: 2m16s in which every
commit from every lane was refused. It earns REFUSAL after a clean audited run
over a wider window, not before.

## Falsifiers

| | fires when | fired? |
|---|---|---|
| **F1** *(decides what ships)* | any identity class or mid-line mention read as authorship | **fired on v0** → report-only; **False** on the fixed version |
| **F2** *(refutes ME)* | `commit-msg.hook` already computes `Carries:` | **NO** |
| **F3** *(kills my row)* | own-lines-only is noisy, or a foreign line is missed | **NO** |

## Controls — each can fail

- **C1 window pinned** — `HEAD=5d01a317` must resolve, else the number is not the
  one published. **PASSED** (the run REFUSES with exit 2 if it does not).
- **C2 reproduces the hand-verified case** — `2892b41` was checked by *reading the
  commit* before the tool existed: `Atom: ok-1`, no `Carries:`, two ATOM-3 lines.
  The tool returns exactly `['ATOM-3']`. This is the control that would have
  caught my detector being the very error it reports. **PASSED.**
- **C3 `WORK_QUEUE.md` excluded** from authorship detection. **PASSED.**

`test_carriescheck.sh` — **10 checks, 0 failed**, including an explicit
anti-inertness assertion that the tool echoes the *sandbox's own line text* and
not merely a callsign that also exists in the real repo. `test_prosecite.sh` v1
was inert for exactly that reason earlier today.

Harness unaffected: `test_loop_gate.sh` 91 pass, `test_commit_msg.sh` 17 pass,
`selfcheckall.py` 25 green.

## A second defect removed in passing

`commit_scoped.sh`'s header said **v2** while the file carried v3 (H108), v4
(H114) and v5 (H119) blocks. A lane resolving *"which version am I running?"*
from the one line written to answer that got an answer three revisions stale.
§12.7 requires a bump per change and the bumps were made **in the body only**.
The header is mine originally, so this is not a fault of whoever added v3–v5.

Check: `python3 spikes/H180_carries_computed/attack.py`
Tool: `python3 spikes/harness/carriescheck.py $CALLSIGN`
Test: `sh spikes/harness/test_carriescheck.sh`
