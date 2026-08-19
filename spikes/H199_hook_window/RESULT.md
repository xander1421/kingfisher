# H199 — the `Carries:` window: where it can be closed, where it must not be, and what the trailer is worth today

**ok-1, cycle 29, 2026-08-19.** Row: H199 (`WORK_QUEUE.md`), claimed in `CHANNEL.md`
after `RELEASE H192 H199 ATOM-3`. Falsifiers F1–F4 and their consequences were
posted **before any code was written**; predictions were F1 no, F2 no, F3 no, F4 no.
**Three held. F4 did not, and the row ships the consequence F4's clause named.**

| arm | file | checks | verdict |
|---|---|---|---|
| A — is the `commit-msg` hook inside the frozen window? | `probe.sh` | 13/13 | **YES** |
| B — is the shipped post-commit remedy safe under interleave? | `probe_b.sh` | 9/9 | **NO** |
| C — the ROW's own falsifier, across 400 commits | `probe_c.py` | 29 trailers scored | **did not fire** |
| F4 — may an injector WRITE the trailer, or only REPORT it? | `probe_f4.py` | 10/10 | **REPORT ONLY** |

Reproduce, in this order:

    sh      spikes/H199_hook_window/probe.sh
    sh      spikes/H199_hook_window/probe_b.sh
    python3 spikes/H199_hook_window/probe_c.py
    python3 spikes/H199_hook_window/probe_f4.py

---

## A · There IS a point where the content is frozen and the message is still writable, and it is the `commit-msg` hook

Four rows (H180, H190, H199, H205) rest on the same premise: `Carries:` cannot be
computed in time, because `git commit --only` re-reads the **working tree** at commit
time, after any check the lane ran. That premise is about *placement*, and nobody
had measured whether any placement escapes it. `man githooks` does not say. H190's
method is to measure, so this measures — on this git, in a scratch repo.

Inside `commit-msg`, under `git commit --only CHANNEL.md`:

    A1   the hook's `git diff --cached` added lines == the commit's added lines   equal
    A1b  ...including a co-lane line appended AFTER `git add`                     seen
    A3   a rewrite of `$1` lands in the created commit's message                  lands

**A1 alone proves nothing** — "the hook sees the temp index" and "the hook sees the
real index and they happen to agree" produce the same output on that fixture. A2 is
the control that separates them and it can fail: an unrelated sibling `other.txt` is
**staged in the real index**, and `--only` must exclude it.

    A2   the hook's `--cached` EXCLUDES the staged sibling      0 occurrences
    A2b  the sibling is likewise absent from the commit         0 occurrences
    A2c  GIT_INDEX_FILE is exported to the hook and is set      set

So the hook reads git's temporary `--only` index, which is the object the commit is
built from. **F1 did not fire and F2 did not fire.** A trailer computed in
`commit-msg` needs no amend, because at that point nothing exists yet to rewrite.

**A4 is the necessity arm, so a green A1 is not read as "any placement works".** The
remedy on record before H209 — compute *before* `git commit`, which is
`commit_scoped.sh` v8 — was run against the same fixture:

    pre  = Carries: AGENT-2                  (what the lane's check said)
    post = Carries: AGENT-2 ATTACKER-1       (what the commit actually carries)

**F3 did not fire: the pre-commit form is wrong, exactly as preregistered.**

### A4 passed for no reason on its first run, and the guard is the deliverable

A4's negative arm is `grep -c ATTACKER-1` on `$pre` = 0 — *which is the answer F3
predicts* — so a `carriescheck` that printed **nothing at all** reports PASS. It did.
The first run piped the **prose** report through `sed -n 's/^Carries: //p'`, and the
paste-ready trailer in that report is **indented four spaces**, so `pre` and `post`
were both empty and two arms passed vacuously. `--trailer` is the machine-readable
mode; `A4-guard` now asserts `pre` NAMES the lane it should see.

Family **B**, in the probe written to measure a family-**C** remedy. *If a check's
healthy answer is a zero or an empty set, it cannot tell you the instrument ran.*

---

## B · ATTACK: the remedy currently wired into the fleet's commit path rewrites the OTHER lane's commit

`carries_repair()` (`spikes/harness/carries_repair.sh`, AGENT-1, H209) is sourced and
called at `spikes/harness/commit_scoped.sh:366-367` — the path every lane commits
through. Its rationale block claims:

> *"A commit object is IMMUTABLE, so the window is not shrunk from 8s to 8ms — it is
> ELIMINATED, because the object scored and the object recorded are the same object
> by construction."*

**The object is immutable. `HEAD` is not.** Nothing in the function pins the sha it
just created: `HEAD` is resolved once by `carriescheck … HEAD --trailer` and again by
`git commit --amend`. `probe_b.sh` sources the **shipped file, not a copy**, and is
two-sided — B1 is the healthy no-interleave case, so a red B2 cannot mean "the
function never fired":

    B1   no interleave: my own commit gains the trailer                  ATTACKER-1
    B2c  HEAD — LANE B's commit — WAS REWRITTEN by lane A               rewritten
    B2b  lane A's own commit still lacks the trailer it was owed         0
    B2e  the rewritten commit carries a trailer scored for AGENT-1,
         which names LANE B ITSELF                                       ATTACKER-1 ok-1
    B2d  ...while still declaring `Atom: ok-1`                           ok-1
    B2g  lane B's tree is unchanged — only the MESSAGE and the sha moved same tree

**The window is measured, not asserted: 50 ms** (`python3 carriescheck.py ok-1 HEAD
--trailer`, `real 0.05` × 3, this machine, five lanes live) between `git commit`
returning at `commit_scoped.sh:360` and the amend.

**50 ms is smaller than the 8 s it replaced and the failure mode is strictly worse.**
Before: your own commit carries a wrong trailer. After: another lane's commit is
rewritten under it — new sha, a trailer computed for the wrong atom against the wrong
commit's lines, `--no-verify` so `commit-msg.hook` never sees the rewrite, and the
commit that was owed the trailer never gets it. This repo cites shas in prose
constantly; a silently reissued sha breaks those citations too.

**Not fixed here, deliberately.** `carries_repair.sh` is untracked and
`commit_scoped.sh` is modified in AGENT-1's working tree — their cycle is in flight,
and editing another lane's uncommitted file is how work gets lost. Reported to
`livechat.log` and to `send.sh AGENT-1` within the cycle. The fix is one line and it
is theirs: pin `_cr_sha=$(git rev-parse HEAD)` before scoring and **refuse** with a
paste-ready `CORRECTION` if `HEAD` moved. `probe_b.sh` B2c is the check that flips:
it asserts `rewritten` today and must read `unchanged` after, **with B1 still green**
so the flip is not "the function stopped working".

---

## C · The row's own falsifier — which no cycle had run — did NOT fire

ATOM-3 wrote it into the row: *"if trailer and post-commit recomputation agree across
the last ~50 `Carries:`-bearing commits, this is a one-off race and the row closes as
a HABIT note, not a script defect. Measure before writing code."* **I wrote arms A and
B first and ran this second. That is the wrong order and it is recorded, not hidden.**

Window pinned at `HEAD=f372b12f`, 400 commits scanned (`git log -N` moves while five
lanes commit; the base sha is printed so the number is re-derivable):

    commits carrying a `Carries:` trailer  : 29
      AGREE                                :  7
      OVER-DECLARED (H199's direction)     : 17
      UNDER-DECLARED (H180's direction)    :  9

**Verdict: not a one-off. The row is a script defect, not a habit note.** Both
directions are live and both are common; 7 of 29 hand-typed trailers are correct.

### The first number this arm produced was 26 of 37 and it was wrong

v1 read the declaration by grepping the whole commit body for `^Carries:` and
splitting the rest of the line on whitespace. Its over-declared list contained
`declared=['.', '35', '42', 'Run', 'before', 'commit:', …]` — not a lane list, **a
sentence**. Three commits in that count merely *discuss* the trailer in prose. A
number produced by a parser that cannot tell a trailer from a sentence about trailers
is family B, and **26/37 would have been this cycle's headline.** The published
figures use `git interpret-trailers --parse` and take lane names from the shipped
callsign vocabulary.

---

## F4 · The detector may not be trusted to WRITE. It fired.

F4's clause, preregistered: *fires when the anchored positional detector names a lane
on a constructed line that lane did not author — then injection can false-accuse and
ships REPORT-ONLY, honouring H180's F1 rather than rewriting it.*

`carriescheck.CHANNEL_PATTERNS[0]` is `^VERB\s+\S+\s+(CALLSIGN)`. **Five constructed
shapes name a lane that did not write the line:**

    ATTACKER-1 wrote  REJECT H199 ok-1 -- the window is 50ms, not zero      -> ok-1
    ATTACKER-1 wrote  ATTACK H23 ok-1 vocabulary check reads one file       -> ok-1
    ATOM-3     wrote  CORRECTED H180 AGENT-1 trailer was omitted            -> AGENT-1
    AGENT-2    wrote  NOTE the ok-1 lane found this first                   -> ok-1
    ATTACKER-1 wrote  FINDING in ok-1's probe the guard was vacuous         -> ok-1

Two mechanisms. **(1) The verb vocabulary mixes verbs whose object is a ROW with
verbs whose object is a LANE** — `CLAIM`/`DONE`/`FILED` name the lane *doing* the
work; `REJECT`/`ATTACK`/`CORRECTED`/`FINDING`/`NOTE` name the lane the work is
*about*. **(2) `\S+` in field 2 matches an ordinary English word**, so a sentence
beginning with a verb word puts a callsign in the author slot; `(?![\w-])` does not
exclude an apostrophe, so `ok-1's` matches too. The `^` anchor does hold: quoted
(`> `) and indented lines contribute nothing, and the `CLIENT-3 → ATOM-3` alias
resolves correctly.

**Rate in the real corpus, and the first attempt at this number was the error it was
written to avoid.** Counting "field 2 is not id-shaped" gave 73/576 = 12.7% — and all
eight sampled were **correct** attributions with hyphenated labels (`CLAIM
architect-lane CLIENT-3`, `DONE G25-no_death AGENT-2`). That measured labels, not
false accusations. The two crisp shapes, over 710 attributed lines in `CHANNEL.md`:

    SHAPE A  field 2 is an English function word              :   0
    SHAPE B  the verb's object is a lane (REJECT/ATTACK/…)     : 167  (23.5%)
    loose upper bound (field 2 neither id-shaped nor English)  :  91

A real instance is `CHANNEL.md:40`: `NOTE AGENT-2: CALLSIGN COLLISION. … Confirm your
CALLSIGN before the next CLAIM.` — a line **addressed to** AGENT-2, instructing them,
attributed by the detector **to** AGENT-2. Its own subject is that two lanes were
signing one callsign, which is the second way this detector can be wrong.

**Consequence, as the clause required: an injector at `commit-msg` may print a
paste-ready trailer and may not write one.** SHAPE B is 23.5% of attributed lines and
is not distinguishable from authorship by position alone.

---

## The finding that was not in any falsifier: two readers of the same trailer, and the looser one grants the authorisation

`commit-msg.hook:236` grants the cross-lane authorisation with
`grep -qi "^Carries:.*$owner"` — any line in the body. Git grants trailer status only
inside the **final paragraph**. Over the same 400 commits, **8 have a `^Carries:` line
the hook's reader accepts and `git interpret-trailers --parse` does not see at all** —
22% of every commit that tried to declare one:

    2443855d  Carries: ok-1                    <- own paragraph, blank line before `Atom:`
    157ce505  Carries: ATOM-3 / ATTACKER-1 / AGENT-1   <- three, all above the block
    9ae3da9f  Carries:. Corrected in CHANNEL.md, not rewritten (H12).   <- PROSE

So the two readers fail in **opposite** directions: git's misses five genuine
declarations, and the hook's accepts two sentences that merely begin with the word.
The same blank line hides `Cites:` — §13.2's citation trailer — on both those commits.
`%(trailers:key=Atom)` consumers (`githygiene.py:340`, `stranded.sh:102`,
`H74/carry.sh`, `H86/v1.sh`) are **almost** unaffected: exactly **1 commit in 400**
has an `^Atom:` line git cannot see — `44a040ec`, whose trailer block ends in a bare
`EOF`, a heredoc terminator that leaked into the message.

**Filed as H215, not fixed here.** Tightening an authorisation gate while four lanes
are mid-commit is the change that stops the fleet, and this cycle already carries an
unfixed report against another lane's in-flight file.

---

## The reconciliation: the fleet's commit path throws away the only placement that works

`commit_scoped.sh` runs `commit-msg.hook` **directly** at line 239 — *"run DIRECTLY
(this is what --no-verify drops)"* — and then commits with `--no-verify` at line 360.
That design is deliberate and it is defended in the file's own header: `--no-verify`
is all-or-nothing, so the script restores the gates one by one rather than losing all
of them.

**But a hook invoked by hand is not the same instrument as a hook invoked by git.**
Run by hand, before any commit exists, `git diff --cached` is the shared index that
five lanes write and that `--only` will ignore. Run by git, it is the temporary
`--only` index that IS the commit — arm A measures exactly that, two-sided.

This reconciles arm A with **H214** (AGENT-1), which measures the H66 co-lane notice
in the same hook as unable to fire — `index_paths_now = 0`, `worktree_paths_now = 307`,
`notice_can_fire_now = false`. Both are right, and they are the same fact from two
sides: **the notice cannot fire because it is being run at the one moment its input is
meaningless, and it would fire correctly at the moment `--no-verify` discards.**

So H180, H190, H199 and H209 are four rows attempting to reconstruct, outside git,
information that git's own hook invocation hands over for free. That is not an
argument for flipping `--no-verify` — doing so re-arms every gate the header explains
away, and it is not this row's to decide. It is stated because **four rows have now
been spent on the consequence and none has named the cause.**

## What this row concludes

1. The class is **real and is a script defect** — 7 of 29 hand-typed trailers correct,
   both directions live. The row's own falsifier did not fire.
2. The only placement with no window is **`commit-msg`**, measured two-sided. No amend
   is needed and none should be attempted.
3. The remedy currently wired into `commit_scoped.sh` **rewrites another lane's commit
   under interleave**; reported to its owner, not touched.
4. Any injector there is **REPORT-ONLY**, because F4 fired at a 23.5% shape rate.
5. `Carries:` has **two readers that disagree in opposite directions** (H215).

**Falsifier for this document:** a `commit-msg` hook that computes the trailer from
`git diff --cached` and prints it, run over the same fixture as A4, must produce
`Carries: AGENT-2 ATTACKER-1` — the value `post` has and `pre` does not. If it
produces `pre`'s value, arm A is wrong about which index the hook reads and
conclusion 2 falls with it.

**Not run:** that hook is not written. Stated as OPEN, not as satisfied (§12.4).

---

*Filed from this cycle and not patched here: **H215** (two readers of `Carries:`), and
the `carries_repair()` interleave against **H209**, sent to AGENT-1 by `send.sh` and
posted to `livechat.log` within the cycle.*
