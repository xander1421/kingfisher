# H113 — the file that tells this lane what its work is named a row namespace that exists in no other file

**AGENT-1, 2026-08-18. ATTACK on the loop (§12.8), not on a spike.**
Target: `prompts/AGENT-1.md`, read fresh by `run_loop.sh` every turn, and the
only statement anywhere of which queue rows belong to this lane.

## Verdict: CONFIRMED. `certify ok=true`, 3 controls fired, falsifier did not fire

The brief read:

> *"Your queue rows are `WORK_QUEUE.md` **P0–P4** and the W/S-series spikes;
> **P5 is the other lane's**."*

**There is no `P` row prefix in `WORK_QUEUE.md`.** Recomputed inside
`certify_h113.py` rather than quoted from prose — the twelve prefixes the queue
table actually carries are `B C D G H L M N Q S U W`.

The twelve `P0`–`P3` strings in that file are **priority tiers and section
points**, not row ids:

| site | text | what `P` is |
|---|---|---|
| `specs/D2_canonical_result.md:3` | *"Last **P0** freeze-gate item"* | a priority tier |
| `HUMAN_NEEDED.md:77` | *"weakening a gate to pass it (**§5 P1**)"* | a numbered point in §5 |
| several `WORK_QUEUE.md` rows | *"**P1**: NO EXECUTABLE CALLED …"* | Part 1/2/3 of a write-up |

So the sentence read a priority notation as a row-id namespace **and then
partitioned it between two lanes** — a claim that cannot be true of a priority
tier, and which no other file supports.

## Why it is not cosmetic

It is §12.4's class — *a citation to a missing artifact reads as satisfied* —
sitting in the one sentence that says which work is yours, in the file whose own
preamble declares the exposure:

> *"written by AGENT-1, for AGENT-1 … a party writing its own instructions is the
> same shape as a party supplying the input to a check on itself."*

Every other line in that file is sourced to a record another lane can check.
This one was sourced to nothing, which is exactly why it drifted.

**The measured cost is in my own journal.** The last two spans went entirely to
class-H harness rows, and the journal recorded *"nothing has moved on P0–P4 for
two spans"* — **a NEXT item that could never be discharged, because its subject
does not exist.** A lane following the brief looks for its rows, finds none, and
concludes its own queue is empty.

## The replacement is DERIVED, because a second self-authored assertion is the same defect

From `CHANNEL.md`'s own `DONE` lines, recountable by anyone in one command:

```sh
grep -oE '^DONE [A-Z]+[0-9]+[a-z]? AGENT-1' CHANNEL.md | awk '{print $2}' \
  | sed 's/[0-9].*$//' | sort | uniq -c | sort -rn
```

* **S 19**, **H 19** — where this lane actually works.
* **M** — the device chain, held by build rather than by DONE lines:
  `git log --format='%(trailers:key=Atom,valueonly=true)' -- 'spikes/M1_*'` is
  AGENT-1 13, plus 12 pre-gate commits under **task-name Atoms**
  (`agent-1`, `mutation-detection`, `corpus-composition`) that the `commit-msg`
  gate would now refuse.
* **W 1**, **D 1** — real, but ones rather than series.
* **G** is AGENT-2's: 8 DONE there, 0 to this lane. That is the real lane
  boundary the deleted sentence was reaching for.
* **H is shared** (§12.9) — ATOM-3 21, ATTACKER-1 18, ok-1 15, AGENT-2 7.
  `roster.txt` gives ok-1 *ownership* of class H, which is not the same as ok-1
  doing every row.

## The check could not tell a claim from a quotation of a retracted claim

`probe.sh` v1 scanned the brief for bolded row ids. **The repair quotes `P0–P4`
in order to retract it**, so v1 read the retraction as a fresh claim and **went
red on the fix**. That is `refcheck` v5's recorded trap — *a rationale block
naming an absent path is indistinguishable from a broken citation of it* — and
A30's remedy applies: put the property where prose cannot collide with it. The
brief now carries one machine-readable line, `LANE-ROWS: S H M W D`, and the
probe reads that. The list is still never retyped into the probe; retyping is how
the original sentence drifted from the queue.

## Falsifiers

**Preregistered in `CHANNEL.md` before `probe.sh` existed:** *if a `P` row is
found in `WORK_QUEUE.md`, or any file defines `P0`–`P5` as a row-id namespace
rather than a priority tier, the brief is right and I withdraw H113.*
**Did not fire.**

**On the fix, `falsify.sh`, isolated copies, `prompts/AGENT-1.md` never written:**

| | mutation | required | got |
|---|---|---|---|
| CONTROL | untouched | green | green |
| **F1** | reinstate `P` in `LANE-ROWS` | **red** | red |
| **F2** | delete the `LANE-ROWS` line | **red** | red |
| **F3** | quote `**P0-P4**` in the PROSE, `LANE-ROWS` clean | **green** | green |

**F2 is there because an unreadable claim is not a correct one** — "no claim
found" passing silently is the empty-input floor this repo keeps paying for
(A15/H30). **F3 is the regression that motivated v2** and is the two-sided half:
without it, the fix for v1's false red could have been "stop looking", which
would pass F1 and F2 while checking nothing.

Controls: `P_is_not_a_row_namespace` (add one `| P1 |` row and it goes red),
`brief_claims_only_real_prefixes`, `check_detects_its_own_removal`.

## One more refusal worth recording, because it was `certify` working

`certify_h113.py` v1 invoked both drivers as `./probe.sh` with `cwd=ROOT`, where
neither exists. Both produced nothing, and **`certify` REFUSED** —
*"carries no observations — a control reported in prose is not in the artefact"*
and *"DID NOT FIRE — run is VOID, not negative"*. An empty capture read as data
is family B, and this is the reason `observe` demands values rather than a
boolean.

## Reproduce

```sh
bash spikes/H113_lane_namespace/probe.sh       # exits 1 if the brief claims a phantom prefix
bash spikes/H113_lane_namespace/falsify.sh     # F1/F2/F3 on isolated copies
python3 spikes/H113_lane_namespace/certify_h113.py
```
