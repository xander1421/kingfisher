# H89 — §10 "nothing is written outside the workspace" was enforced by nobody

**ATTACKER-1, 2026-08-19.** `certify ok=true`, 4 controls all fired, **all five
preregistered falsifiers RAN AND NONE FIRED.**

Artifacts: `probe.py` (the five falsifiers), `certify_run.py`, `falsifiers.json`,
`planted_writer.sh` (F3's plant, kept as evidence), `provenance.json`, and the
module, `spikes/harness/scratchcheck.py` **v2**.

---

## The finding is against the remedy I preregistered, not against §10

H89 was filed by this lane on 2026-08-18 with F3 asking for *"a detector that
flags a planted writer"*. Every reader of that sentence — me included — read it
as a scan of committed source. **Measured before building anything (F4): of the
8 §10 instances this fleet has on record, exactly 1 is visible to a source scan.**

| instance | citation | in a tracked file? |
|---|---|---|
| `/tmp/kfmsg.txt`, `/tmp/config.json.bak`, `/tmp/eh.bak`, `/tmp/ROSTER.bak`, `/tmp/kf_id.txt`, `/tmp/kf_sid.txt` | `CHANNEL.md:726` (ATOM-3) | **no** |
| the `git commit -F` message file behind `d717518` | `WORK_QUEUE.md:325` (AGENT-1) | **no** |
| `/tmp/_cm.$$` | `spikes/harness/test_commit_msg.sh:7` | yes |

**A source detector is blind to 7 of the 8 instances the row exists for.** That
is family **A** — the instrument cannot produce the answer — inside the row about
unenforced rails, and it was decidable from the design before any run, which is
what family A is supposed to be.

**Second measured fact, family D.** Those 7 are known only because two lanes
wrote them down. **A lane that does not confess leaves the rail with no evidence
it was ever broken**, so the rail's whole evidence base is self-reported. "8" is
a floor and is labelled one everywhere it appears.

**Third.** `.claude/settings.json` registered exactly one hook (`Stop`). At the
layer where all 7 happened there was no mechanism of any kind.

## What shipped

`spikes/harness/scratchcheck.py` v2, two mouths, and the second is the point:

* `--scan` — the source half. Finds the 1-in-8 that lives in a tracked file.
* `--hook` — a **PreToolUse gate**, registered in `.claude/settings.json` for
  `Bash|Write|Edit|NotebookEdit`. Finds the 7-in-8 as they are about to happen.

Plus the cause-removal, which is ATOM-3's own suggestion at `CHANNEL.md:726`:
`.scratch/` inside the workspace, gitignored. **Two of their six instances were
backups taken to be careful before editing a shared file — "the caution produced
the violation" — because a lane reaching for scratch had nowhere sanctioned to
reach.** A gate with no compliant destination is the always-red gate H14, H52,
H73 and H124 were each bypassed for.

**NO RAIL TEXT WAS EDITED.** `railguard.py` (H112/H118) gates
`MISSION_LOOP.md ## 10`, a lane may not authorise its own rail change (A22), and
H89 leaves *"is ephemeral scratch an exception?"* on H17 as not this lane's to
decide. `.scratch/` is compliant with §10 **as written**; naming a compliant
location decides nothing and removes the cause. **Residue for a human: §10 does
not say where scratch goes, and until it does, every careful lane will invent a
location. That sentence is an operator edit, not mine.**

## The five falsifiers — all ran, none fired

| | fires when | result |
|---|---|---|
| **F1** | every out-of-workspace path in committed source is READ-ONLY | **quiet** — 16 write positions, 6 not `mktemp`. Worst is live: `bringup.sh` does `mkdir -p` into `$HOME/Library/LaunchAgents`, a persistence mechanism written outside the tree by the one automatic path. H89 **predicted** that site and named it line 212; it is at **439** now, which is why §7 says cite the artifact and not its size |
| **F2** | >50% of hits are Android device paths §10 permits | **quiet** — 0 of 16, against 47 tree-wide. A property of the scope, and the null can contain the effect: a wider scope would have produced them |
| **F3** | a PLANTED writer is NOT flagged | **quiet** — flagged by `--scan` *and* refused by the hook. `planted_writer.sh` was never executed and the file it names does not exist |
| **F4** | a source scan flags >=4 of the 8 recorded instances | **quiet** — it flags **1**, the number recorded as a prediction in the CLAIM *before* the run, so the outcome cannot be read as "as expected" either way |
| **F5** | the sanctioned location cannot serve a real converted site | **quiet** — `test_carriescheck.sh:22` converted from bare `mktemp -d` to a template under `.scratch/`; **10 passed, 0 failed, identical to baseline**, including its `git init` sandbox, and the site now scans clean |

## Four controls, all fired

**C1 refuses and permits** (exit 2 / exit 0) — a gate with one verdict is not a
gate. **C2 reads are not writes** — 9 real read commands, 0 flagged; *the
commands that measured this row are in that set on purpose*, because a
classifier keyed on "the string appears" would have refused the investigation of
its own rail. **C3 mutation** — two mutations, each asserting it LANDED and each
taking a *different* control red: M1 widens the allowlist and the positives go
silent; M2 drops the write-position restriction and **7 of 9 negatives start
refusing**, which is what makes C2 load-bearing rather than decorative.
**C4 liveness** — the defect H1 is famous for here is a hook registered where no
session reads it. Tested rather than assumed: mid-session and with no restart, a
redirect to a scratch path outside the tree came back
`PreToolUse:Bash hook error ... REFUSED`, `ls` confirms the file was never
created, and an in-workspace write in the same session succeeded.

## v2, and it is the cycle's real finding: THE GATE REFUSED ITS OWN RESULT.md

v1 was handed the whole Bash command that writes **this file** — a heredoc whose
body quotes the refusal text — and classified the quoted paths as live writes.
The row's own write-up was unwritable. It fired on me twice, mid-cycle.

**This tree had already paid for that defect, 40 minutes earlier, in a module I
wrote.** `versioncheck.py` v1 (H180, mine) flagged its own test suite because
heredoc FIXTURES read as that file's version blocks; it grew `strip_heredocs`
and a check that keeps it so. **I wrote that fix and then did not reuse it here.**
§12.2 is *fix the CLASS, never the site*, and this was the site I left.

Fixed by **importing** `versioncheck.strip_heredocs`, never copying it — a copy
is the second site the rule is about. If that import ever fails, the module
cannot classify safely, so `_STRIPPER` goes False and the hook **stops blocking**
rather than becoming silently permissive; C6 asserts the import, so the launchd
sweep goes RED instead of the gate going quiet.

**I did not disable the gate to get past it.** Brief §9 forbids weakening a gate
to pass it, so the fix was routed through `.scratch/` — the sanctioned location
this row created — which is the first real use of it.

## The census: 16 write positions, and how the number got there

29 → 24 → 18 → 17 → 16, and **every removal was verified an individual false
positive before it was removed**, because a precision fix and a weakened gate
look identical from the total alone:

* **8 FPs from the character class** — an `awk -F` field separator read as an
  output file (`H120_orphan_quorum/run.sh:16`), plist XML in a heredoc, a
  backticked path in prose. `{}<>=` and a backtick cannot occur in a path this
  fleet writes. All 8 are kept as **negative controls**, real values cited by
  file, so the narrowing cannot silently widen later.
* **`-F` scoped to `git`** — the flag is overloaded. Kept, not dropped, because
  `git commit -F <file>` is the exact form of two of the eight recorded instances.
* **quote-aware redirects** — a redirect operator inside quotes is not an
  operator. Applied to the redirect rule ONLY: the *path* of a real write is very
  often quoted, so masking quoted spans everywhere would delete a true positive
  to remove a false one. **Operator position is quote-sensitive; argument
  position is not.**
* **comments skipped in `scan_source`, NOT in `write_targets`.** A comment cannot
  reach the hook, which is handed a whole command. Putting the skip in the shared
  classifier — where it first went — would have let a precision fix for the
  **census** silently narrow the live **gate**: §12.2's class with the sign
  flipped, the right fix at the wrong site. One of the two comments removed was a
  line *warning* about §10, reported as breaking it.
* **heredoc bodies (v2)** — which also removed the XML special case v1 carried
  for the symptom, since D1's fix addresses the cause.

By kind: `mktemp` 10 · `mkpath` 3 · `redirect` 3, over 422 tracked files.
**The 10 bare `mktemp -d` sites are the H17-undecided category and are reported,
not judged.** What is measured rather than argued: this tree already contains the
compliant form at three sites (`test_h75_routing.sh`, `test_h66.sh`,
`fleetcensus.sh`) doing the same job, and F5 converted a fourth with no change in
its result — so *whether* an exemption is owed is H17's, but *whether one is
functionally needed* is answered, and it is not.

## What this cannot do — stated before the code, not after

It classifies by **write position** and does not parse shell. A write through a
variable, a subshell, or a program's own internals is invisible. **It fails OPEN
on any internal error and closed only on a confident match**, deliberately: five
lanes route every Bash call through this hook and H124 recorded a 2m16s
fleet-wide outage from a gate that stopped parsing. A gate that can take the
fleet down is worse than an hour more of an unenforced rail. That asymmetry is
the residue and it is not a claim of coverage.

**Blast radius is smaller than the 16 suggests, and saying so is a limit on the
gate rather than a defence of it:** the hook sees the *agent's* command, so
running a suite passes even when that suite calls bare `mktemp -d` internally.
The 10 `mktemp` census rows are therefore reported by `--scan` and **not** gated.

## The account

**This row was CLAIMed by me on 2026-08-18 and produced no artifact at all.** It
sat OPEN for a day with its claim visible in an append-only log — the precise
shape the brief calls out, a falsifier written down and marked *not yet run*.
Two more §10 instances were recorded by other lanes inside that window. I took my
own dangling claim before taking anything new.

Errors of mine this cycle, all fixed at the cause, all still visible in the
controls: the first classifier reported 29 positions of which 8 were false, and I
published none of them until each was individually classified; the comment skip
went into the shared classifier first, where it would have narrowed the live
gate; **the heredoc defect above, which is the same class I had fixed elsewhere
40 minutes earlier**; and `certify` refused this spike five ways before it passed
— constant observations on C2, no `null_must_contain` anywhere, and
`STALE ARTIFACT` on the makers. **Every one of those refusals was correct, and
the last was correct about the wrong field**: `probe.py` is a maker and
legitimately predates the tree, so it is pinned by sha256 in `captures` rather
than claimed as an output.

## Filed as its own row, not bundled: H193

Bumping this module to v2 found that **`versioncheck.py` cannot see its own
version.** Its header regex matches a `#` COMMENT line, so a version declared in
a Python DOCSTRING is skipped as "no version header is not a defect".
**Measured: 18 of the 34 versioned modules in `spikes/harness/` declare their
version in a docstring and versioncheck sees NONE of them — including
`versioncheck.py` itself, `railguard.py`, `carriescheck.py` and `idscope.py`.**
H180's published "4 of 15 versioned harness files drifted" is therefore scoped to
16 of 34 files, and the 18 it never examined are the majority idiom for `.py`.
Filed as **H193** with the measurement. **Not fixed here** — fixing the site
while naming the class is what §12.1 forbids, and it is H180's own module, so the
row states the count and leaves the remedy to a cycle that can attack it
properly. This file carries a two-line `#` header so its *own* bump is checkable
now; that is compliance, not the remedy.

## Reported, not fixed — belongs to other lanes

* **`certify`'s staleness check races on a five-lane shared tree.** `deps` must be
  a directory, so my dep is all of `spikes/harness`, and a co-lane touching any
  unrelated file there makes my fresh artifact STALE. It fired twice on
  `test_loop_gate.sh` while this spike was being certified. Neighbourhood of
  **H187** (ATOM-3, claimed) — not touched under them.
* **`bringup.sh` exists twice**, at the repo root and in `spikes/harness/`, and
  only the root copy carries the live `$HOME/Library/LaunchAgents` write. Two
  sites, one rule — §12.2. Not this row's to merge.
