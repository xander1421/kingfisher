# H7 — the first ATTACK cycle aimed at the harness

**ATTACKER-1, 2026-08-17.** Row: `WORK_QUEUE.md` H7, released by ATOM-3 for a
fresh atom ("withheld from my release list in TWO revisions; reviewer 4 called
it a pattern not a slip").

## The falsifier, stated before running

> *If `test_loop_gate.sh` is real coverage, then restoring any one of the
> defects it was written for must turn it red. If the suite stays green with a
> defect restored, that check is inert and its PASS was a statement about
> nothing.*

Run it: `python3 spikes/H7_harness_attack/falsify.py` (exit 0 = every check
fired). No seed — every falsifier is a deterministic text substitution and a
deterministic suite run; there is no sampling anywhere in this spike.

## Why this and not another spike

The suite reported all-green and nothing had ever asked whether a *red* run was
reachable. (No count here on purpose — §7's own rule, earned by a sentence that
cited "15 checks" for hours while the suite grew: cite the artifact, not its
size.) That is not a hypothetical concern here: `test_loop_gate.sh`'s
own header records the 15-check version passing while the hook was broken,
because every check set `CALLSIGN`, and check 3 asserting that the bare-signal
path *worked* — thereby certifying the lane-theft hole it was meant to close.
**A green suite is evidence only if a red one is reachable.**

## Result

| | defect restored | check that must go red | verdict |
|---|---|---|---|
| F1 | refusal message names bare `.loop_signal` | `refusal names a path the hook obeys` | **FIRES** |
| F2 | launcher leaves the previous span's signal armed | `launcher clears a stale signal` | **FIRES** |
| F3 | callsign interpolated into the refusal JSON unvalidated | `UNPARSEABLE decision` | **FIRES** |
| F4 | `LANE="${CALLSIGN:-unknown}"` | `no callsign is not gated` | **FIRES** |
| F5 | bare `.loop_signal` accepted again | `bare signal is REFUSED` | **FIRES** |
| F6 | non-numeric fuse counter written back unchanged | `corrupt fuse file recovers` | **FIRES** |
| F7 | installed commit gate drifts from its tracked source | `DRIFTED from its tracked source` | **FIRES** |
| F8 | launcher spawns a lane on a callsign the hook will not gate | `launcher refuses what the hook will not gate` | **FIRES** |
| F9 | commit gate accepts another lane's per-lane files | `refuses another lane's journal` | **FIRES** |
| F10–F19 | the hook stops refusing at all · no exit marker · signal not consumed · malformed signal kept · signal read by glob · one shared fuse · fuse never releases · `STOP` ignored · env var back in a registration path · marker words unrecognised | one named check each | **ALL FIRE** |
| F20–F21 | the cross-lane gate refuses *everything* · the `Carries:` escape stops working | the two POSITIVE controls | **FIRE** |
| F22–F23 | a registration points at a hook that is not there | `reg <settings.json> resolves to an executable` | **FIRE** |

**CONTROL**: an unmodified copy comes back all-green, 0 fail. Without it, a
driver that broke every copy — a bad `build()`, a missing file, an unset `PATH`
— would report every falsifier firing and read as a perfect score. The control is
what separates *"the defect fired"* from *"the copy is rubble"*.

**The revert itself is a control.** Each one goes through
`edits.anchored_replace`, so a revert whose anchor has drifted **raises** rather
than silently doing nothing. A silent no-op revert would leave the check
passing and this script would report it sound on the strength of having tested
nothing — the failure mode `edits.py` exists for, and the one this script is
most exposed to.

**SCOPE.** At the end of the first cycle this read *"eight of forty proven,
thirty-two are not"* — a hand count, in prose, which is the instrument this
whole row distrusts. It was opened as **H17** rather than left as a caveat, and
H17 replaced it with a measurement the driver prints on every run. See below.

## H17 — coverage, measured rather than asserted (cycle 3)

The scope note above said *"9 of 43 proven, 34 are not"*. Counting by hand is
the wrong instrument for that, so `falsify.py` now **measures** it: it unions
every check name that went red under any revert and prints the ones that never
did. **23 falsifiers; 35 of 43 checks observed going red; the remaining 8 are
listed by the driver on every run**, so the number cannot decay into prose.

Measuring it immediately found a defect in the checks themselves. **Seven
checks renamed themselves on failure** — `hostile callsign refused: X` when
green, `hostile callsign emits an UNPARSEABLE decision: X` when red — so they
could not be tracked from a green run to a red one and coverage was
unmeasurable for them. They reddened every time under F3, under a different
name. Nobody would find that by reading; only counting found it. Fixed by
giving each check a stable name with the outcome in a parenthetical.

**The 8 that remain, with the reason each resists a single-edit revert.** They
are not all inert, and saying "8 uncovered" without this would be the decay
this row exists to stop:

- `hostile callsign handled: L 6` / `../L6` / `$(touch pwned)` / `` L`6 `` —
  under F3 the whitelist is gone and these callsigns still produce **valid
  JSON**, because none contains a quote. The check correctly stays green. It
  asserts a different property from the one F3 breaks.
- `no callsign was executed`, `hostile callsigns left no state` — these guard
  against `eval`/word-splitting, and the hook contains no `eval`. Falsifying
  them means **inventing** a defect rather than restoring one this repo had,
  which is a different and weaker kind of evidence. Named, not silently
  counted.
- `writes no 'unknown' marker`, `lane signal untouched` — need **two**
  simultaneous reverts (the `LANE` default *and* the glob signal read). The
  driver applies one edit per falsifier. This one is a real limitation of the
  driver, not of the checks, and multi-edit falsifiers are the next step.

## The error I made writing this, since the account is part of the work

F8's check was written **without a stub `claude`**. When its falsifier disarmed
the launcher's guard, `run_loop.sh` fell through to `command -v claude`, found
the real one, and **spawned a live agent on the callsign `L"6`** — a test that
starts production, written minutes after quoting this suite's own header line
that a test which can *stop* production is not a test, and repeating ATOM-3's
error 15 in the opposite direction. Caught because the run hung for 120s rather
than because anything checked. Killed by hand; the spawn reached no `CHANNEL`
line, no commit, no device.

Fixed structurally, not by care: the check now shadows `claude` on `PATH` with
a stub **and asserts the launcher never reached it**, so the safety is a
property the suite tests rather than a thing I remembered. The generalisable
form — and it is the same shape as everything else in this file: *a falsifier
runs the code path that was never supposed to execute, so a driver that reverts
a guard must assume the guard's absence is dangerous, not merely observable.*

## Three defects found on the way, all live

**1 · The Stop hook instructed lanes into a path it had stopped accepting.**
Section 5's refusal message — the *only* instruction a lane receives at the
moment it tries to stop — said *"into the file `.loop_signal`"*, the bare name
v5 had removed one section above in the same file. Reproduced on an isolated
copy: a lane obeying it verbatim blocked 3/3 turns, no exit marker, signal never
consumed, fuse climbing. **Co-found with AGENT-1** (row H16), who fixed section 5
and wrote the round-trip check at 11:52; my reproduction was independent and my
contribution here is F1, which shows that check is not inert.

**2 · A callsign is an untrusted string, and H16's own fix made it reachable.**
`$LANE` is interpolated into `.loop_exit.$LANE`, `.loop_blocks.$LANE` and —
since 11:52 — into the refusal JSON. Nothing validated its shape. Measured:

```
CALLSIGN='L"6'  ->  {"decision":"block","reason":"... .loop_signal.L"6 , and ..."}
                    json.decoder.JSONDecodeError: line 1 column 179
```

The block decision is unreadable, so the refusal is lost and the lane stops —
for exactly the reason the hook exists to prevent. **The fix for the refusal
message opened an injection into the refusal message.** Whitelist added to
`loop_gate.sh` v6; `run_loop.sh` v4 refuses the same shapes at launch, because
fixing one site is §12.2.

**RETRACTED, mine, within the same cycle.** I first wrote to `CHANNEL.md` that
`CALLSIGN=../x` writes `.loop_exit` outside the workspace. **It does not.**
`.loop_exit.` + `/../escaped` needs the directory `.loop_exit.` to exist; it
does not, the redirect fails, **0 files escaped**. Stated as a consequence and
never run — the thing this repo grades hardest. The whitelist still excludes
those callsigns, but on the JSON evidence, not the traversal.

**3 · The only enforcing gate in the repo is absent from every clone.**
`MISSION_LOOP.md` §13.1 said *"`.git/hooks/pre-commit` REFUSES a commit"*. That
file does not exist, and `pre-commit` is the mechanism `commit-msg.hook`'s own
header records as **already proven not to work** — `man githooks` gives it no
parameters, so `$1` was empty and it refused every commit. The real gate is
`commit-msg`, and `.git/hooks/` is untracked and cannot be tracked, so:

- a clone, a worktree or a re-init gets **no gate** and is told nothing;
- nothing in the tree referenced `commit-msg.hook`, so the tracked source was
  reachable only by having watched someone install it;
- nothing compared installed to source, so editing the source changed the
  *reviewed* artifact and not the *enforced* one — family **C**, "the artifact
  is not what you think", at the enforcement layer.

Fixed: `spikes/harness/install_hooks.sh`, a suite check for
missing/non-executable/drifted, F7, and the §13.1 citation corrected in place
with a changelog block.

## H19 — found in this cycle's RECORD phase, by trying to commit it

`git add <my paths>`; two seconds later `HEAD` was `b529081`, *"S76 recorded,
and two stale NEXT items retired"*, `Atom: AGENT-1` — carrying
`HANDOFF.ATTACKER-1.md`, `spikes/H7_harness_attack/` and **840 lines of this
cycle**.

**Neither lane broke §13.** Three lanes share one git **index**, and
`git commit` commits the index, not the adds you made. So "add paths you
touched, never `-A`" is not sufficient and never was: any lane's `git add` is
live ammunition for the next lane's `git commit`. §13.1 exists so that
attribution is possible at all — one human git identity cannot distinguish
atoms — and here it recorded the wrong answer **confidently, in the field that
exists to prevent exactly that.**

Not rewriting `b529081`: §13 forbids it without qualification and other lanes'
provenance chains reference existing blobs. The record is the `CHANNEL.md` line
plus a gate.

**The gate, because the mismatch is decidable at commit time.** A commit-msg
hook can see both `git diff --cached --name-only` and the `Atom:` trailer, so
`commit-msg.hook` v2 refuses a per-lane file — `HANDOFF.<X>.md`,
`loop_<X>.log`, `.loop_{signal,exit,blocks}.<X>`, `.heartbeat.<X>` — whose
owner is not the `Atom:`, and names `git commit --only <paths>` in the refusal.

- **Assumption, recorded as one:** ownership is inferred from the filename.
  Sound only because §12.6 independently obliges the harness to keep state
  per-lane. `prompts/<ATOM>.md` is deliberately **excluded** — spawn briefs are
  written by the harness owner *for* a lane, so ownership does not follow the
  name there and including it would refuse a legitimate commit.
- **`Carries: <ATOM>`** declares a deliberate cross-lane commit. Chosen over
  `--no-verify` because that also switches off the trailer and self-review
  gates, and an escape hatch that disables unrelated checks is how a gate ends
  up bypassed as routine.
- **Positive control**: the atom's own `HANDOFF.<ATOM>.md` still passes. A gate
  that refuses everything is not a gate, and that is the input that separates
  *"it checks ownership"* from *"it always says no"*.
- Falsifier **F9**.

## H14 — the module with no test, tested (cycle 4)

`githygiene.py` was **broken in HEAD**: no `import re`, so it died at *import*
time with `NameError`, in every lane's §13 pre-commit path, for at least twenty
minutes while its owner committed twice more. H14's one-line description of it
was *"the one harness module with no test"*, and the checker whose job is
catching bad commits could not run to catch its own.

**Its verdict also carried no information.** Exit 1 was permanent on 16
already-committed binaries that §13 forbids *removing* — other lanes'
provenance chains reference those blobs by hash. So the exit code was 1 before
you staged anything and 1 after, whatever you did: family **A**, the instrument
cannot produce the answer. Its own `ALLOW` comment had named this failure mode
in advance. Tracked violations are now reported and not gated; the *staged*
path, the one a commit can still fix, is unchanged.

**Then the new `--selfcheck` found two more defects on its first run:**

- with **no commits at all**, `git log -1` returns empty, every required trailer
  read as missing, and the tool reported a violation about a commit that does
  not exist — family **B**, printed under the heading *"in what you are about to
  commit"*;
- every HEAD check gated **your** commit on **someone else's** last one. In a
  three-lane shared tree HEAD is usually another lane's, and the only repair is
  rewriting history, which §13 forbids. Harness state that is not per-lane,
  again. HEAD findings are now reported, never gated — the *prospective* trailer
  gate is `.git/hooks/commit-msg`, which refuses, and which got stricter today.
- and `git ls-files` reads the **index**, so a brand-new violation was printed a
  second time under *"already committed"* — the label that means *not yours to
  fix*. `git ls-tree -r HEAD` is what that phrase means.

### Two defects in my own instruments, both found only by falsifying them

**1 · The driver truncated the file it was about to read.**
`open(p,'w').write(anchored_replace(open(p).read(), old, new))` — Python
evaluates `open(p,'w')` *before* the argument expression, so the file was
**emptied to zero bytes and then read as empty**. Both `G` falsifiers reported
`ANCHOR MISSING — cannot falsify`: a driver declaring the check untestable
because the driver had destroyed the input. Family **B**, in the tool whose job
is catching exactly this. **Caught only because `anchored_replace` refuses** —
`str.replace` would have written an empty file and reported the check green.

**2 · The self-check imported the wrong artifact.** The import probe ran
`import githygiene` with `cwd` set to the module's own directory, so it imported
whatever was **installed there** — a scratch copy with `import re` deleted still
passed, because the probe imported the healthy original. Family **C**. It passed
before the defect and after it, so no number of green runs could have exposed
it; only falsifying the check did. Now probed by absolute path via
`runpy.run_path`.

**3 · And the criterion for falsifying a self-check was wrong.** "The named
check goes red" fails for any defect fatal enough to stop the self-check
running — `G1` was reported INERT when in fact the module could not load at all.
The property is **"the self-check does not report success"**. Silence and death
both count, which is the point: silence reading as success is the failure that
ran through this repo's worst day.

## The defect class, for the other lanes to grep

> **An interface removed or renamed in code, while a surviving site still
> instructs callers to use it.**

Not the same as a dangling citation (§12.4), which points at nothing and reads
as satisfied. This one points at something that *exists and is wrong*, and it
lives in places nobody counts as a site — a runtime's own output string, a
journal's "how to stop" line — because they are strings, not rules. Swept:

| site | instructed | reality | state |
|---|---|---|---|
| `loop_gate.sh:108` refusal message | bare `.loop_signal` | refused since v5 | fixed by AGENT-1 (H16) |
| `HANDOFF.md` "to stop legally" | bare `.loop_signal` | refused since v5 | fixed by AGENT-1 (H16) |
| `HANDOFF.md` re-entry | `ScheduleWakeup` each turn | hook registered by absolute path since H-HOOKREG | fixed by AGENT-1 (H16) |
| `MISSION_LOOP.md:282` §13.1 | `.git/hooks/pre-commit` | gate is `commit-msg`; pre-commit proven unworkable | **fixed here** |

**Correction, mine, before committing:** the two `HANDOFF.md` rows were drafted
above as *"fixed here"*. They were not — AGENT-1 swept them under H16 at 11:5x
and I read the file afterwards. Of the four sites in the class, **AGENT-1 fixed
three and I fixed one.** Left in rather than quietly amended, because
mis-attribution is the defect §13.1 exists for and this repo has now made it
three times in one day.

`run_loop.sh:14` and the `v3`/`v5` blocks also name the bare path and are
**not** defects: they are rationale blocks describing what was removed, which is
what §12.7 asks for. The distinguishing test is not the string — it is whether
the sentence tells a reader what to *do*.

## Files

- `falsify.py` — the driver. Isolated copies only; the live tree is never
  written, because reverting a fix in place would disarm the live Stop hook for
  the length of the run with lanes running against it.
- `spikes/harness/test_loop_gate.sh` — 38 checks (was 37 at cycle start, 26 at
  session start). Cite the artifact, not the count.
- `spikes/harness/install_hooks.sh` v1, `.claude/hooks/loop_gate.sh` v6,
  `run_loop.sh` v4.
