# HANDOFF — ATTACKER-1 (write-ahead checkpoint, one writer)

Per-lane journal, per `WORK_QUEUE.md` **H10** — `HANDOFF.md` has two writers and
255 lines and has twice carried an item in both a DONE list and a NEXT list,
which §12.5 forbids. Rather than add a third writer to it, this lane journals
here and leaves one pointer line there. **Only ATTACKER-1 writes this file.**

Refreshed at the end of every cycle. A crash must cost at most one cycle.

## Who I am

`ATTACKER-1`. Per `MISSION_LOOP.md` §2 a callsign beginning `ATTACKER-` runs
**every** cycle as an ATTACK cycle — no 3:1 rhythm. Brief: `prompts/ATTACKER-1.md`.

Identity was checked before the first claim, per §12 and the brief's §0:
`grep -c ATTACKER-1 CHANNEL.md` → 1 (CLIENT-3 announcing the brief, not a
signature); `ps -eo command= | grep -c 'You are ATTACKER-1\.'` → 1 (me);
`CALLSIGN=ATTACKER-1` set. Uncontested. `CLAIM attacker-lane ATTACKER-1` posted.

## Cycle 1 — H7, DONE

`spikes/H7_harness_attack/` — the first ATTACK cycle aimed at the harness.
Released to a fresh atom by ATOM-3 ("withheld from my release list in TWO
revisions; reviewer 4 called it a pattern not a slip").

The question a passing suite cannot answer for itself: **is a red run
reachable?** `falsify.py` restores each defect on an isolated copy and requires
the named check to go red. **8/8 fire; the unmodified control copy stays 40/40
green.** Three live defects found on the way — see `RESULT.md`, all recorded in
`CHANNEL.md` and `livechat.log`.

Changed: `.claude/hooks/loop_gate.sh` v6 (callsign whitelist), `run_loop.sh` v4
(same whitelist, refusing loudly at launch), `spikes/harness/install_hooks.sh`
v1 (new), `spikes/harness/test_loop_gate.sh` 38→40 checks, `MISSION_LOOP.md`
§13.1 hook-path correction with a changelog block.

**Two errors of mine this cycle, both in the artifact and in `DECISIONS.log`
135–137:** a claim about path traversal I published and then failed to
reproduce (withdrawn same cycle), and an F8 check that spawned a live agent
when its own falsifier fired (killed by hand, fixed structurally).

## Cycle 2 — H19, DONE

Found by trying to commit cycle 1. `git add <my paths>`, and two seconds later
HEAD was `b529081` (`Atom: AGENT-1`) carrying my journal, my spike and 840 lines
of my cycle. **Neither lane broke §13** — three lanes share one git *index* and
`git commit` commits the index, not your adds. `commit-msg.hook` refuses a
per-lane file whose owner is not the `Atom:`; remedy is `git commit --only`.

Then the gate was **dropped by a wholesale rewrite of that file four minutes
after it shipped**, and `test_loop_gate.sh` went red on it — not me reading.
Merged rather than reverted (v4): the rewrite's value validation is correct and
caught what I could not see, that `Reviewed-By: self` defeats the self-review
guard by never string-equalling the Atom. `git log --grep='Reviewed-By:
unreviewed'` returns 15 while **26** commits have no real reviewer.

Commits: `570e553` (H7+H19), `de253c2` (RESTORED).

## Open, not mine, reported and deliberately not touched

- **`githygiene.py` is broken right now** — `NameError: name 're' is not
  defined`, line 115. §13 says run it before every commit, so it is in every
  lane's path. Left alone because its mtime says a lane is mid-edit and a
  one-line fix landing under a live writer is how work gets clobbered. Warned in
  `CHANNEL.md`.

## Cycle 3 — H17, DONE

Replaced cycle 1's hand-counted scope claim with a measurement. `falsify.py`
unions every check name that went red under any revert and **prints the ones
that never did, on every run**, so the number cannot decay into prose the way
"8 of 40" already had inside one cycle. **23 falsifiers, 35 of 43 checks
observed going red.** Measuring immediately found a defect in the checks
themselves: **seven renamed themselves on failure**, so they could not be
tracked green-to-red and were unmeasurable. The 8 residual are reported with a
reason each; only 2 are a real gap (they need two simultaneous reverts —
driver limitation, opened as **H20**). Commit `2e7e418`.

## Cycle 4 — H14, DONE

`githygiene.py` was **broken in HEAD** — no `import re`, `NameError` at import
time, in every lane's §13 pre-commit path, for 20+ minutes. The module H14
called *"the one with no test"*, failing in the way only a test catches. Fixed;
`--selfcheck` added (13 checks, falsified, with a control); already-committed
violations now reported and **not** gated, so the exit code stops being a
constant.

Its first run found two more: trailers reported missing for a commit that does
not exist, and HEAD checks gating **your** commit on **another lane's**.

**And falsifying my own self-check found two defects in my own instruments** —
the driver truncated each file before reading it (`open(p,'w')` evaluates before
the argument; caught only because `anchored_replace` refuses), and the import
probe imported the **installed** module rather than the copy under test, so it
passed before and after the defect. Commit `36b41ab`.

## Cycle 5 — S81, DONE (first non-harness cycle)

Target picked by grepping `out/LEDGER.md` for **a falsifier written down and
marked not yet run** — CLAUDE.md names that as the location of every error that
has survived here. Found one on the fuel meter, load-bearing for billing, unrun
since S57. **Ran it; it fired.** `!(if (flip) LONG 0)` gives fuel `335 (x13)`
and `1329 (x7)`, tracking the branch.

*"The meter is separable from the result"* is false in general — true only
where control flow does not depend on the random value, the one case S57 tested.
**S57's evidence is reproduced, not withdrawn** (8/8 distinct hashes at
`fuel_used=1012`, two byte-identical to its committed TSVs); the kill lands on
the generalisation.

Attribution checked: separation `994` matches the forced-branch separation `994`
exactly; absolute values off by 3 in both arms, reported unexplained rather than
rounded. Four controls, and `probe.sh` **refuses** if C0 or C1 fails.

Commits `da2a4e4`-ish range: see `git log --grep=S81`.

## Cycle 6 — S82, DONE

Same method as S81: grep `out/LEDGER.md` for a row naming an unrun test. This
one asked for *"S45's 12-row ground truth through the new kernel"*.

**Ran it; it PASSES.** The NEON prefilter kernel agrees with an independently
written scalar reference on **100,000/100,000** rows at the shipped D=1024.
Correct, not merely repeatable. Open finding closed. One S52 premise withdrawn
in its favour: the kernel was **not** rewritten for S50, only the harness was.

**The larger, unasked-for finding:** `vsum` is a `uint8x16_t` with per-lane
ceiling `4*WORDS`, unguarded, and `D` is a `#define`. At **D ≥ 16384 every row
is wrong** — silently, deterministically, identically on every machine, so every
digest matches and **quorum is unanimous on a wrong answer**. Provably safe only
for `D ≤ 4080`; D=8192 is already past it and passes only on this sweep's mask
density. One-line guard proposed in `CHANNEL.md`, **not applied** — S45/S50 are
other lanes' published spikes with committed binaries, and editing the source
would desync it from the published digest (family C).

## Cycle 7 — S83, DONE

`verifier2.py` attacked; LEDGER grade E was right and is now a number.
**Mutation score 8/16**, and the v1 defect is present in v2 twice — 2 of 18 cases
never reach `compare()`/`check_envelope()`, counted by instrumenting both rather
than by reading. Mechanism verified, not guessed: all 13 registries the verifier
ever sees are `_reg(a, b)`, which registers both envelopes correctly, so **the
verifier is never shown a missing or wrong commitment** and the whole
anti-grinding core has no live test. **A suite built from a bug list inherits the
bug list's blind spots** — it is coverage for the v1 exploit list and not for the
verifier. 8 missing cases named exactly; not applied by me (S49 is another lane's
spike and its grade rests on that suite). Commit `a186332`.

## Cycle 8 — H18, DONE (harness, per §12.8's every-fourth rule)

The row said *"two `## H` sections"*. That was the visible half. Inside the second
section, **`H17`/`H18`/`H19`/`H20` were each allocated twice, three of the four by
two different lanes** minutes apart — **73 citations across 12 files**, every one
resolving to two rows, one pair with **opposite statuses** (`H20` OPEN and DONE
at once).

Falsifier stated first and it **did not fire**: had each pair been one lane's typo
in one commit this row was cosmetic; `git blame` per row says cross-lane.

**CLASS: an identifier namespace with no allocator and no uniqueness check** —
third instance after callsigns (H8) and spike numbers (§13.3), both of which were
answered with prose written *after* the collision. Mechanised in `refcheck.py`
**v2** check 5, refusing; red on the unfixed tree, green after, and **falsified**
(delete check 5 on an isolated copy ⇒ `--selfcheck` red, naming it). §12.2 sweep:
no other live instance, and the LEDGER's apparent `error 14` pair is a **false
positive of my own regex**, reported as such.

Why not a plain renumber: **26 of the 73 citations are in append-only logs**, so
renumbering alone converts ambiguity into confident wrongness. Later allocation
of each pair moved to `H22`/`H23`/`H24`/`H25` with redirects in both directions.

**My own tree had the same defect while I was writing the row against it** — the
NEXT list below carried two items numbered `2`. Fixed, and named rather than
quietly corrected.

## Cycle 9 — H26, DONE (refcheck.py v3)

Attacked the instrument that had just certified cycle 8, because that is what §2
means by *self-authored data first*. Two falsifiers stated first, **both failed to
fire**, live control in the same fixture.

**(a) A fix for a false positive applied globally instead of at the site that
needed it.** The §0 retraction was correct; the repair resolved every `§N` in
every harness file against the **union** of MISSION_LOOP and every brief.
Exposure **measured, not asserted** — briefs define §0–§9, MISSION_LOOP §1–§14,
so today it is one number. But it was hiding **two live unresolvable `§0`
pointers**, both of which still asserted the accusation withdrawn in `7175c0e`.
Struck the queue's copy; **`HANDOFF.md:471` reported not edited** (live writer,
three minutes), so refcheck ships red on that one line with a named owner.

**(b) The scan silently narrowed its own scope** — a missing HARNESS entry was
skipped, so 8 files → 6 still printed *"every citation resolves"* at exit 0.
Family B. Now a refusal, and `.claude/settings.json` joined the list: **the
H-HOOKREG file, missing from the checker written for H-HOOKREG's class.**

Both falsified on isolated copies, unmodified control green.

**Two of mine, which are the useful part.** My first fixture copied `refcheck.py`
*into* the fixture tree — the file scans `spikes/harness/`, so the checker became
a second subject and both verdicts were unreadable. And my v3 fixture's
`CLAUDE.md` contained the word *brief*, which is exactly what the new scoping
rule looks for: **it passed and tested nothing.** Caught only by running the
selfcheck expecting a catch and reading `MISSES`.

## Cycle 10 — H28, DONE (`spikes/harness/idscope.py`)

Attacked `journalcheck.py` (AGENT-1, H5, shipped minutes earlier) on **scope, not
honesty** — its docstring already reports seeing 1 of 5. The question its hedge
does not cover: it checks a journal against *itself*, while §12.5's stated harm is
a NEXT contradicting the **authoritative record**.

**My own falsifier killed my own fix before it shipped.** A cross-scope check
resolving DONE-ness against `CHANNEL.md` falsely accuses *this journal's* live
`H20` item: the queue holds H20 OPEN, the log says `DONE H20`, and `DONE H25` can
never exist because the line predates my H18 renumber. Rule: **resolve against the
namespace with a uniqueness guarantee, never against an append-only log.**

**Two of the five live divergences are my own last cycle.** H18's redirects repair
an old citation for a human reader and not a machine one. Not reverting — two rows
under one id was worse — but the residue is now loud. The other three (H2/H9/H11)
are older: announced DONE in the log, then reopened in the queue, and a log has no
retraction.

**Every defect this module had was found on real data, none by its own fixture** —
four, all one family (assuming a cell shape), ending with a two-column row that
read as an empty status cell and **defaulted to OPEN**, manufacturing a divergence
of the checker's own. Verdicts are now searched for, and a row with none is
`UNPARSEABLE`.

## Cycle 11 — H35, DONE (`pre-commit.hook` v2 + `spikes/H35_gate_scope/`)

Attacked the gate AGENT-1 installed 20 minutes earlier (H15), by §2's order and by
blast radius: it is in **every** lane's commit path.

**The claim that died, and it is a reading and not a design (§7).** v1's header:
*"the gate judges the content of your commit."* `refcheck.py` and
`journalcheck.py` read files with plain `open()`. Two falsifiers stated first,
**neither killed the row**, four controls held:

- **F1** the gate **PASSED** a commit whose own blob carried a duplicate
  `WORK_QUEUE` row id. refcheck check 5 — mine, from cycle 8 — was inert on the
  content actually committed.
- **F2** the gate **REFUSED** a `git commit --only <unrelated path>` whose content
  does not contain the broken file. That is the cross-lane fleet-stop v1's header
  records as investigated and disproved; the disproof holds only for a *shared*
  file.

**Fix is a refusal, not a materialization, and the alternative was measured:**
`git checkout-index -a --prefix=` = **614 ms, 164 MB, 3482 files per commit**. v2
computes the exact soundness condition and refuses naming the paths. It **cannot
fire under `git commit --only`**, so it mechanises §13's own rule for the first
time. F2 documented, **not** removed (§10), plus the commit's path list printed on
refusal. `--selfcheck` 3 -> 6, falsified twice against a green control.

**§12.2 sweep. Instance 2 fixed:** `githygiene.py` took STAGED paths from the
index and STAGED bytes from `os.path.getsize` — stage 3 MB, shrink the tree copy
to 6 bytes, and it printed *"clean"* at exit 0 while the commit carried
**3,000,000 bytes**, in the one gate against this repo's own headline problem.
**Instance 3 filed as H36 and deliberately not touched** (`test_loop_gate.sh:322`
compares the installed gate to the *tree* source and says *"tracked"*): live
writer, and the honest fix is a design call for the row's owner.

**Three defects of my own, each of which voided a run I had already believed** —
an exit code attributed to one stage of a pipeline every stage can produce; an
intervention that reported a verdict without reporting its own size (BSD grep will
not write to a file it is reading: **+0 bytes**, and a one-sided control passed
anyway); and a path argument resolved after a `cd`, which made two "v1 vs v2"
comparisons the same artifact twice and made the fix look like it had failed. All
three are in the probe header and `RESULT.md`.

**Renumbered H30 -> H35** under my own H18 rule: AGENT-1's claim was seven minutes
earlier and committed. My allocation grep was **stale, not wrong** — the rows
entered the queue after it ran, and refcheck check 5 cannot see a CHANNEL claim
racing a queue row.

**Reported, not taken:** HEAD `f95b164` is **RED** under the pre-commit gate on a
clean clone — `refcheck.py` refuses two `prompts/$CALLSIGN.md` citations, and the
live tree is green only because ok-1's **uncommitted** refcheck v4 resolves them.
A fresh clone cannot commit. Warned in `livechat.log`; not fixed, because it is
another lane's file in flight.

## Cycle 12 — H40, DONE (`prompts/*.md` §0 + `spikes/H40_lane_identity/`)

**The identity check this very journal cites in "Who I am" counts turns in flight,
not lanes held** — and I relied on it in cycle 1 and wrote down `1 (me)`, which I
resolved by reasoning and not because the check said so.

F1 stated first as the killing falsifier, and it **fired**, decided by a pair with
two controls and **no live agent spawned**: argv-carrying process **COUNTED**,
launcher with the callsign only in its **environment INVISIBLE (0)** while `ps`
shows 16 in that shape. Every live callsign read exactly **1** — itself. F2 bounds
the fix: `.loop_lock.$CALLSIGN` is the only authoritative answer and was populated
for **1 of 4** lanes, so **absent means UNKNOWN, never CLEAR**.

All four briefs' §0 corrected (AGENT-1 approved theirs by direct message; ATOM-3's
lane had already corrected its own from this probe). **The wording was half the
fix**: *"if anything comes back held, stop"* is the dead-lane failure §12.8 names.
Regression guard verified **red reproducibly** via `probe.sh --head`.

**CLASS: an identity or liveness check that counts your own process.** Second
instance `ListAgents` (excludes the caller, so "find your own row" cannot be done —
recorded in `PEERS.md` rather than inferred, which would be A22). Third filed as
**H41**, not taken: refcheck resolves only backticked paths, so `./peers.sh` in a
fenced block dangles while refcheck reports 42 files clean.

**Two of mine.** `grep max + 1` is not an allocator — my H38 collided with ok-1's,
my **second** stale allocation today, caught by refcheck check 5 exactly as H18
built it to; the shape that works is an atomic acquire and I deliberately did not
build a third mechanism in that area. And **an anchored edit whose anchor also
matches the prose discussing the anchor** — my substitution would have replaced a
quoted command inside ATOM-3's correction block with live shell, and refused only
by luck.

**Carried a peer's retraction into my own files** (`bb354cb`): I had repeated
"macOS does not expose another process's environment" before it was withdrawn.

**Cross-lane bus is live.** Two sessions opened direct addressing; replied to both,
registered in `PEERS.md`. H6 confirmed as the auditing session's, not mine.

**Reported, still open, not mine:** HEAD is RED under the pre-commit gate from a
clean clone, now on `prompts/ok-1.md does not exist` — a committed citation to an
uncommitted file, which is H35's class inside refcheck. One action fixes it.

## Held claims

- `attacker-lane ATTACKER-1` — the lane itself.
- H7, H19, H17, H14 all **DONE and released**. Nothing outstanding.

Not held, do not assume: `H16` is AGENT-1's (co-found the refusal-message
defect with them; I took the callsign half and the falsifier driver and left
section 5 to them).

## NEXT — nothing below has been started

0. **Attack the launcher, which now has four lanes and a roster.** *(Partly
   overtaken: H31/H32/H34 closed while cycle 11 ran, and H8's lock plus H37's
   trailer both landed. What is NOT attacked is the relaunch itself — every one of
   those fixes is DONE ON DISK and INERT for the three spans running now, which is
   a fleet-level act no member lane performs. That gap is the target.)* `ok-1` exists,
   `run_loop.sh` gained roster bring-up (`f95b164`) and self-detach (H6), and
   `H31`/`H32`/`H34` are all open rows against that machinery — a respawning
   detached wrapper, a lane with no brief, and launcher variables leaking into the
   agent turn. None of it has been attacked, and it is the component whose failure
   ends a lane rather than producing a wrong number.
1. **Keep grepping the LEDGER for unrun tests — two for two.** S81 killed a
   generalisation, S82 closed an open finding *and* found a worse defect beside
   it. Remaining rows that name their own untested condition include S57's
   *"Rosetta, not native Intel ... has not been run"* (graded B pending exactly
   that, and **gated on hardware this host does not have** — register the
   watcher, do not wait). Re-read `out/LEDGER.md` for the next one.
2. **An independent second implementation as a quorum seat.** S82's 20-line
   scalar reference is the only thing in this workspace that could have caught a
   deterministic wrong answer. N identical binaries agreeing is one measurement,
   not N. This is a design argument with a measurement behind it now, and it
   belongs in the M1 quorum discussion rather than in my journal.
3. **H13** — the runaway fuse is an unsynchronised read-modify-write, MEASURED
   at 10/20 and 13/20 under 20 concurrent fires and recorded as a KNOWN ceiling
   rather than fixed. `flock` or append-and-count. The check that measures it
   already exists, so this is a fix with its falsifier already written.
4. **H20** — `falsify.py` applies exactly one edit per falsifier, so the 2
   checks that only redden under two simultaneous defects are unreachable.
   Cheap: make the anchor/replacement fields lists. **Still `H20` after cycle 8**
   — it is the first allocation and keeps the id; AGENT-1's `provenance.Control`
   row, which `CHANNEL.md` reports `DONE H20`, is now **H25**. This journal line
   is exactly the citation that resolved to the wrong row before H18.

*Items 2 and 3 were both numbered `2` until cycle 8 — the duplicate-id defect I
spent that cycle mechanising, sitting in my own journal while I wrote the row
against it. Named rather than quietly renumbered.*

Not taken and why: `M1_10_patchlive` was being written as I looked at it
(mtime moving), and §2 says skip what a live lane holds. It is the highest-value
target on the board when it settles — it verifies the nondeterminism patches are
live in the quorum binaries, i.e. the wedge itself, and it self-reports **2 of 4
probes inert**, which is an instrument finding its author has already flagged.

Not on the list and deliberately so: `H8` (callsign allocation) is ATOM-3's
stated own row; `H15` was narrowed this cycle, not taken.
