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

The suite reports `38 checks pass`. Nothing had ever asked whether a *red* run
was reachable. That is not a hypothetical concern here: `test_loop_gate.sh`'s
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

**CONTROL**: an unmodified copy comes back `40 pass, 0 fail`. Without it, a
driver that broke every copy — a bad `build()`, a missing file, an unset `PATH`
— would report all seven firing and read as a perfect score. The control is
what separates *"the defect fired"* from *"the copy is rubble"*.

**The revert itself is a control.** Each one goes through
`edits.anchored_replace`, so a revert whose anchor has drifted **raises** rather
than silently doing nothing. A silent no-op revert would leave the check
passing and this script would report it sound on the strength of having tested
nothing — the failure mode `edits.py` exists for, and the one this script is
most exposed to.

**SCOPE, stated because a number without it decays.** Eight of forty checks are
now proven non-inert. **Thirty-two are not.** F1–F8 are the newest checks plus
the defects that were *observed live* rather than reasoned about; the older
assertions about lane isolation, fuse separation and the STOP switch have no
falsifier yet. **"H7 DONE" does not mean the suite is verified** — opened as
H17 rather than left as a caveat in prose, because a caveat in prose is the
thing this row exists to distrust.

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
