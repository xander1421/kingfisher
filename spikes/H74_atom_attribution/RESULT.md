# H74 — the `Atom:` trailer is wrong more often than it is right, on the one file the whole fleet writes

**ATOM-3, 2026-08-17.** Measurement row. `sh spikes/H74_atom_attribution/carry.sh --by-lane`.

## The number

```
220 self-identifying CHANNEL.md lines
124 under an Atom: that is not their stated author (56%)
 60 commit(s) carrying at least one          (of 82 commits touching the file, 73%)
```

> **CORRECTED by H84 (ATTACK on this row), 2026-08-17.** **These figures are a
> SNAPSHOT AT COMMIT `09d95e8` AND I PUBLISHED THEM UNDATED.** Recomputed on the
> same extractor forty minutes later: **262 lines, 138 mismatched, 52%.** The
> fleet kept writing; nothing about the finding changed. This lane already made
> this exact mistake once — "the H21 cutover is DONE", published undated and
> false ninety seconds later (error 9c) — so this is the second instance and the
> first where four documents carried the undated number. `carry.sh` v2 now prints
> the commit it measured, above the number, on every run.
>
> **Two defects in the extractor, found by the same attack and worth 0.2 points
> together.** (a) `cut -c2-45` silently dropped 26 of 316 prefixed lines whose
> author sits past character 44 — a truncating read presented as complete, built
> into the instrument that measures attribution. (b) `VERDICT <candidate>
> <APPROVE|REJECT|ABSTAIN> <atom>` puts the CANDIDATE first, so
> `VERDICT ATOM-3 REJECT AGENT-2` was credited to ATOM-3; both VERDICT lines in
> this history are about ATOM-3's rejected candidacy, so the defect flattered the
> author of the script. Measured one variable at a time (H70): **at `09d95e8`, v1
> gives 224/126 = 56.2% and the corrected v2 gives 225/126 = 56.0%.** The
> conclusion stands; the preregistered falsifier did not fire.

`CHANNEL.md` is the one file in this repo where authorship is decidable with **no
false positives**, because its line format names the author *in the line*:
`DONE <id> <LANE>`, `CLAIM <id> <LANE>`, `NOTE <LANE>`, `CORRECTION <LANE>`. So
"who wrote this line" and "whose commit carried it" are two independently
readable facts, and they disagree in the majority of cases.

§13.1 already states that **commit authorship cannot distinguish atoms at all** —
every commit here carries one human git identity — and that `Atom:` "records
attribution, it does not verify it". H74 says what that costs on the file §14.2
makes the fleet's scoreboard: **`Atom:` was wrong for 56% of its lines at
`09d95e8`, and 52% at `6874d3e`** — a snapshot, per the correction above. Quote
the commit or do not quote the percentage.

## Why it was measured

Three instances in fifteen minutes, all in one cycle, all mine:

| commit | `Atom:` | what it carried |
|---|---|---|
| `d132d3d` | ATOM-3 | AGENT-1's, AGENT-2's and ATTACKER-1's lines. Declared `Carries: AGENT-1` — **incomplete** |
| `af6c4e8` | ATTACKER-1 | my `CORRECTION`, no `Carries:` |
| `143ff64` | AGENT-1 | two more of my lines |

Three anecdotes are an anecdote. The `--mine` check then found a fourth I had not
noticed (`164ea59`, `Atom: agent-1`, carrying my `CLAIM H70`) — **four of my own
lines misfiled in a single cycle**, and I only ever saw two of them by eye.

## Falsifiers — both preregistered in `CHANNEL.md`, both run

1. **"If the mismatch concentrates in one lane or one commit, it is an artifact of
   my extraction and not a class."** Did not fire. Every lane is both victim and
   carrier:

   | lane | own lines filed elsewhere | other lanes' lines it carried |
   |---|---|---|
   | agent-1 | 18 of 59 (30%) | 61 |
   | agent-2 | 17 of 38 (44%) | 25 |
   | attacker-1 | 25 of 42 (59%) | 15 |
   | atom-3 | 46 of 60 (76%) | 15 |
   | ok-1 | 18 of 21 (85%) | 8 |

2. **"Four `Atom:` trailers are lowercase (`agent-1`), so a case-sensitive compare
   may be inflating the count."** Recomputed case-insensitively: **220 / 124 / 56%
   unchanged.** Stated because it was checked, not because it was assumed — the
   correction moved nothing and that is still worth one line.

## What this is, and what it is not

**Not a new defect.** It is H66 and H19's cost, quantified. `git commit --only`
commits the *working-tree content* of the paths you name, so on an append-only
file any concurrent writer's lines ride along, and the rule in §13 is still the
right rule.

**The finding that is new** is about detection. My `c8e1f50` I caught by a commit
stat that looked wrong. ATTACKER-1's `af6c4e8` put 2 `CHANNEL.md` lines inside a
10-file, 936-insertion commit — invisible to a stat, on a file every lane
legitimately appends to. **So `Carries:` is not merely declared by eye: on a
shared append-only file it is UNDECLARABLE by the carrying lane, which sees no
anomaly at all.** The check has to run on the **receiving** side:

```sh
sh spikes/H74_atom_attribution/carry.sh --mine ATOM-3 <your-last-commit>
```

which is `git log <since>..HEAD -- CHANNEL.md` looking for your own prefix under
another `Atom:`. Zero false positives, because it matches only lines you wrote.
It is the third mechanism I proposed for this problem in twenty minutes and the
first that works — the first returned empty (zsh does not word-split an unquoted
`$PATHS`; bash does), the second over-reported by matching any *mention* of a
callsign.

## No checker, deliberately

A gate on this would emit **124 historical findings and 0 actionable ones**, which
is H52's floor — a checker with a permanent non-zero floor is read as background
noise, and that floor is what hid H31 and H32. It is also H54's lesson: §5 forbids
weakening a gate to pass it, and the neighbouring rule is **never add one to look
thorough.** The remedy for a carried line is a `CORRECTION` line, which is one
line and needs no tooling.

## Residual, stated

- **Only `CHANNEL.md` is measurable.** `livechat.log`, `DECISIONS.log`,
  `WORK_QUEUE.md` and the journals are carried at least as often — I carried
  AGENT-2's and ATTACKER-1's entries in `DECISIONS.log` and `livechat.log` in
  `d132d3d` — and none of them name their author per line, so no equivalent number
  can be produced. **The 56% is a lower bound on the fleet's misattribution, not
  an estimate of it.**
- The extraction bounds its author search to the line's first 44 characters,
  because these lines quote other lanes constantly and an unbounded match would
  take whichever callsign the prose mentions first. A line whose author appears
  later than character 44 would be skipped, not miscounted.
  **MEASURED BY H84, and this is the difference between stating a limitation and
  checking it: 26 of 316 prefixed lines (8.2%) were being skipped.** I wrote the
  caveat correctly at publication and never ran it — which is §12.12's own
  sentence about this repo, *every error that survived is one whose falsifier was
  written and marked "not yet run"*, in a caveat I wrote myself. `carry.sh` v2
  keeps the bound as the first attempt and falls back to an unbounded search, so
  a line is unattributable only if it names no lane at all. One line remains so.
