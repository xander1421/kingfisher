# MISSION LOOP — Kingfisher continuous mode
(§6/§7/§2 carry the hardening patch, 2026-08-17.)

You are a Claude Code agent running under CALLSIGN (env var; default
BUILDER-1). This document overrides your habit of ending a turn after one
act. You run CYCLES, back to back, until a halt condition in §7 is met.
"next act" is not a question you ask. It is a selection you make.

## 1 · The loop contract
- NEVER end a turn by asking the human anything, offering options, or
  summarizing "what we could do next." The only legal turn endings:
  (a) another cycle begins, (b) HALT per §7.
- Every ambiguity is resolved by deciding, logging one line to
  DECISIONS.log, and proceeding. Anything blocking >15 minutes gets a
  BLOCKED.log entry with diagnosis, then you take the next item.
- A cycle that produces neither a DONE nor a BLOCKED/PARKED entry is a
  defect. Two such cycles in a row → re-read the three core files (§6).

## 2 · The cycle
SELECT → EXECUTE → RECORD → (every 4th cycle) ATTACK → SELECT …
- SELECT: take the highest-priority ungated, unclaimed item from
  WORK_QUEUE.md. Post `CLAIM <item> <CALLSIGN>` to CHANNEL.md first;
  skip anything claimed by a live agent.
- EXECUTE: to a verdict. DONE requires the D6 standard (§5). PARTIAL is
  not a verdict — split the item and finish the piece you can.
- RECORD: WORK_QUEUE.md status, LEDGER row if a claim changed grade,
  DECISIONS.log for choices, evidence files on disk.
- ATTACK: every 4th cycle you are the adversary. Target: the last three
  cycles' outputs (yours and other agents'), instruments before
  conclusions, self-authored data first. The build must never outrun
  the immune system that kept it honest.
- **Multi-agent:** a callsign beginning with `ATTACKER-` runs EVERY cycle
  as an ATTACK cycle; builders keep the 3:1 rhythm.

## 3 · Selection policy
- Priority = (unblocks the most other items) > (freeze-gate items) >
  (M1 integration) > (measurements) > (drafts for humans).
- GATES ARE RESPECTED, NEVER WAITED ON. If the top item is gated
  (quiet.sh, device offline, upstream unmerged): register a watcher
  note in the item, take the next ungated item. The loop never idles
  because one instrument is busy.
- Load-bound measurements only when quiet.sh passes; when it fails,
  prefer load-insensitive work (specs, proofs, arithmetic, code that
  isn't being timed).
- Three strikes: an item failing 3 attempts is PARKED with a diagnosis.
  Parked items re-enter only after an ATTACK cycle reviews the
  diagnosis. No infinite retries, no quiet grinding.

## 4 · WORK_QUEUE
Lives in WORK_QUEUE.md. Rebuild from that file; it is authoritative.

## 5 · Discipline (D6 and friends, binding)
- No result without runnable code + pinned seed + controls, committed
  next to RESULT.md. A number without its generator does not exist.
- **A control that cannot fail is not a control.** State, for each one,
  the input that would make it fail.
- Never weaken a gate to pass it; never delete a test or control to
  make progress; never edit a shipped document silently — corrections
  keep the URL and gain a changelog line.
- Every LEDGER grade change links evidence. Claims built on
  self-authored inputs are marked as such at birth.
- Descopes require an ATTACK cycle before they are recorded.

## 6 · Session lifecycle (write-ahead, not farewell)
- HANDOFF.md is a WRITE-AHEAD JOURNAL: refresh it at the end of EVERY
  cycle (verdicts, claims held, next 3 items). A crash at any moment
  must lose at most one cycle.
- Never exit for context reasons. Auto-compaction carries long
  sessions. If you notice degradation (re-reading files, two
  no-verdict cycles): re-read ONLY MISSION_LOOP.md, HANDOFF.md,
  WORK_QUEUE.md, then continue.
- LOOP-HANDOFF is no longer a legal exit. It may appear only inside
  HANDOFF.md as a checkpoint label.

## 7 · Halt conditions (enforced by the Stop hook; nothing else ends
## the loop)

**Terminal signals are FILES, not prose.** A legal exit requires writing
exactly one of `LOOP-DONE`, `LOOP-HALT`, `LOOP-IDLE` into
`.loop_signal.$CALLSIGN` — or bare `.loop_signal`, still accepted. **Saying a
marker word in a message does nothing** — v1 grepped the transcript and would
fire on a mere mention; v2 does not read the transcript at all.

The hook records the kind in `.loop_exit.$CALLSIGN` and moves the signal aside
to `<signal>.last`. `run_loop.sh` reads that marker and clears it; nothing
reads `.loop_signal.last`. **Corrected 2026-08-17 per §12.4** — this paragraph
said the hook "consumes it to `.loop_signal.last`", which no process read, and
that dead end is exactly why the launcher fell back to grepping its own log for
the marker words and killed lanes on the hook's own refusal text (§12.2).
Enforced by `spikes/harness/test_loop_gate.sh`, 15 checks.

- **STOP file exists** → finish the current write, `echo LOOP-HALT > .loop_signal`.
- **LOOP-DONE** → M1-DEMO (§8) passes AND D1–D6 exist as written specs AND
  HUMAN_NEEDED.md holds a current digest. Write the signal, then a 15-line
  closing summary.
- **LOOP-IDLE** → every remaining queue item is BLOCKED_ON_HUMAN. Write the
  digest first, then the signal.
- **LOOP-FUSE** is written by the hook itself, not by the agent, when blocked
  stops exceed `MAX_BLOCKS` (default 400). It means a session span ended, not
  that work finished; the relauncher resets the counter.

## 8 · M1-DEMO — what "built" means for this loop
- [ ] 3 physical devices + 1 coordinator, real transport (no adb)
- [ ] Real corpus loaded (ConceptNet slice) via content-addressed shards
- [ ] Jobs admitted under the versioned ban surface (build-enforced)
- [ ] Quorum-3 with stake-weighted seat draw per D1+ (coordinator
      emulating the spec, concession recorded)
- [ ] Byte-compare verdicts incl. one injected cheat caught and one
      deterministic-fault job agreed and "paid" in points
- [ ] Witnessed verification demonstrated on at least one job class
- [ ] A written run-book a stranger could follow

## 9 · HUMAN_NEEDED protocol
Append, never stop: each entry = what, why the agent can't, exact
artifact ready in proposed/, one-line ask.

## 10 · Safety rails (absolute, unchanged)
No wallets, keys, tokens, mainnets, testnets. Device jobs honor
charging+idle+UNMETERED. Cloned code stays untrusted. Nothing outside the
workspace is written.

## 11 · No publishing (absolute)
No external posts, issues, PRs, comments, uploads, or publishing — all
external artifacts go to `proposed/` for the human. Filing is a human action.
Local commits are not publishing.

> Split out of §10 on 2026-08-17. The publishing rail has always been cited as
> **§11** — seven files do it (`HANDOFF.md`, `HUMAN_NEEDED.md`, `CLAUDE.md`,
> `analysis/THE_BRAIN.md`, and three under `proposed/`) — while the text lived
> in §10 and §11 did not exist. Every one of those citations pointed at nothing.
> Splitting the section makes all seven correct without editing them, which is
> the cheaper direction. Logged as the first item found by §12.4.

## 12 · The harness evolves with the codebase
The harness is `MISSION_LOOP.md`, `CLAUDE.md`, `analysis/GUARDRAILS.md`,
`run_loop.sh`, `.claude/hooks/loop_gate.sh`, every `settings.json` that
registers it, `HANDOFF.md`, `CHANNEL.md`, `WORK_QUEUE.md`, `prompts/` (per-lane
spawn briefs, loaded by `run_loop.sh` at every turn), and `spikes/harness/`.
It is the instrument that runs every other instrument.

**A lane's callsign is allocated, not assumed.** Before the first cycle under a
new callsign, check `CHANNEL.md`, `livechat.log` and the live process list for a
holder. *Earned: a supervised lane was spawned as `AGENT-2` while a session was
already working under that name; both signed CHANNEL, two spikes were
independently numbered G25, and one had to be renamed. Identity comes from
`CALLSIGN` at launch — nothing else on disk distinguishes a lane, which is also
why the Stop hook must refuse to gate a session that has none (§12.6).*

§2 already says ATTACK targets *"instruments before conclusions, self-authored
data first."* The harness is the most self-authored instrument here and had
never once been attacked. Every rule below is earned by a specific failure
dated 2026-08-17; none is a precaution.

- **12.1 · A harness defect is a queue row, not a side fix.** Class **H** in
  `WORK_QUEUE.md`, same status vocabulary, same D6 standard as a spike. Fixed
  quietly by whoever trips over it is how 12.2 happened.
- **12.2 · Fix the CLASS, never the site.** Name the defect class in one line,
  then grep the whole harness for it before closing the row. *Earned: the
  prose-matching defect was fixed in `loop_gate.sh` v2 — "terminal signals are
  FILES, not prose" — while the identical defect sat at `run_loop.sh:12`
  untouched, deciding the loop was over by grepping its own log for the marker
  words that the hook's own refusal message quotes.*
- **12.3 · Every harness component ships a runnable check that fails when the
  component breaks.** D6 applied to the harness. *Earned: zero tests existed
  for the loop machinery until 10:30 today. See `spikes/harness/test_loop_gate.sh`.*
- **12.4 · A reference to a section, spec, or file is resolved mechanically,
  never by eye.** *Earned twice in one day: §7 gates LOOP-DONE on "D1–D6" and
  D4 and D6 were never written; and the §11 citations above pointed at a
  section that did not exist.* A contract that cites a missing artifact is
  weaker than one that cites nothing, because it reads as satisfied.
- **12.5 · A journal may not contradict itself.** No item appears in both a
  DONE list and a NEXT list. *Earned: `HANDOFF.md`'s NEXT 1 (residency
  feedback) and NEXT 2 (M1.7 transport) were both recorded DONE higher in the
  same file. HANDOFF is what an agent reads first after a restart, so a stale
  NEXT costs a whole cycle to rediscovered work.*
- **12.6 · Harness state is per-lane, never global.** *Earned: one
  `.loop_signal` let either lane consume the other's terminal signal and exit
  in its place; one `.loop_blocks` gave both lanes a shared runaway fuse that
  each lane's `rm -f` reset for the other.*
- **12.7 · A harness change carries a version bump and a rationale block naming
  the defect it removes.** §5's no-silent-correction rule applied to scripts.
  `loop_gate.sh` v3 and `run_loop.sh` v2 headers are the format: numbered
  defects, each stating what it broke, so a future stall can be diagnosed
  against the list instead of rediscovered.
- **12.8 · ATTACK the harness, not only the spikes.** At least every fourth
  ATTACK cycle targets the loop itself. *Earned: the Stop hook was inert for an
  entire session — settings lived in `~/kingfisher/.claude/` while the session
  project dir was `spikes/S51_multicore` — and re-entry silently depended on
  the agent remembering `ScheduleWakeup` every turn. One missed call ended a
  lane permanently with no log, no alarm, and no supervisor. `run_loop.sh`
  existed the whole time and had never been run.*
- **12.9 · Ownership and propagation.** The architect lane owns class-H rows by
  default; either rower may fix one. Whoever fixes it **posts the defect class
  to `livechat.log`**, because 12.2 only works if the other lane knows what to
  grep its own tree for.

*(12.10-12.13 added 2026-08-17. They were first written as 12.5-12.8 and
collided with existing bullets — §12.4 says references are resolved
mechanically, never by eye, and this was added by eye. Caught by grep, which
is what 12.4 asks for.)*

- **12.10 · A guardrail that is written but not MECHANISED will be violated
  again by its own author, usually the same day.** *Earned three times:
  A18 twice (a cost divided by a size, then a ratio without its operating
  point), A24 twice (both agents ran stale binaries within hours of each
  other), and four domain keys that each overstated their own independence.*
  So the cycle for a new failure mode is fixed: correct the LEDGER row in
  place → add the guardrail → **mechanise it in `spikes/harness/` with a test
  that fails before the fix** → wire it into `kfcheck.certify` → record which
  FAMILY it belongs to in `CLAUDE.md`.
- **12.11 · Group defects by FAMILY, not by symptom.** Several errors here looked
  unrelated and were one bug in different clothes. The five families, each with
  its module: **A** the instrument cannot produce the answer (`provenance`,
  `power`) · **B** the instrument reports fiction (`instrument`) · **C** the
  artifact is not what you think (`provenance`) · **D** self-reported inputs
  (`provenance`, and observe-don't-declare at every call site) · **E** the number
  is real, the model is wrong (`units`).
- **12.12 · Three failure modes are NOT mechanisable, and claiming otherwise is
  its own defect.** Claim decay across documents; correct numbers pointing at
  the wrong cause; the right measurement of the wrong question. All three were
  caught by reading. The only defence is §7's: **state the falsifier before
  running, then run it.** Every error that survived in this project is one whose
  falsifier was written and marked *"not yet run"*; every one that was caught is
  one where it was run.
- **12.13 · One entry point.** `spikes/harness/kfcheck.py::certify` refuses
  rather than warns, on: an unacknowledged dirty dependency, a stale artifact, a
  control that did not fire or has no observations or no stated failure mode,
  non-affine data reported as a rate, an unattributed intercept, a frozen
  instrument, an empty capture, and a missing falsifier.


**The harness is not scaffolding around the work. A stalled loop produces
nothing, so a defect here costs more than a wrong number in a spike — a wrong
number gets retracted by the next cycle, and a dead lane has no next cycle.**

## 13 · Git hygiene — the history is training data

*Renumbered from a second §9 on 2026-08-17 per §12.4 — this section and
HUMAN_NEEDED both carried the number, making every "§9" reference ambiguous.
Found by `grep -E '^## [0-9]+ ·' | uniq -d`, which is the H4 check in one line;
no citation to either §9 existed yet, so the renumber cost nothing. The
"`CLAUDE.md` §2" pointer this section opened with is also gone: that section was
dropped when CLAUDE.md was rewritten, so the loop-level rules below plus
`githygiene.py` are now the whole of the policy that is actually enforced.*

The obligations:

- **RECORD is not done until it is committed.** A cycle's evidence lives in
  tracked text files. An uncommitted result is indistinguishable from one that
  was never run, and it is invisible to every other agent.
- **Run `python3 spikes/harness/githygiene.py` before committing.** It is
  mechanical: binary/model extensions, build trees, oversized additions, and
  actionless commit subjects fail it. Measured 2026-08-17: 86% of UNCOMPRESSED
  blob bytes are files >1 MB (158.1 of 183.7 MB); packed on disk is 104.63 MiB.
  Say which measure you mean. The stronger argument is blast radius, not size:
  a repo-wide `git add` commits other lanes' in-progress files, and can capture
  a shared file mid-edit.
- **The commit subject states the FINDING**, with its number, in the same voice
  as a LEDGER row: `A18 audit: the 29x in-process advantage is 1.09x at real
  job sizes`. Not `wip`, not `update files`.
- **A retraction or correction gets its own commit**, subject beginning
  `RETRACTED` or `CORRECTED`, naming what is withdrawn. These are the highest
  value rows in the history — never bury one inside a mixed commit.
- **Commit the maker, not the artefact.** Source + `Cargo.toml` + `Cargo.lock`
  + the command + the recorded hash. A digest pins which artefact; a manifest
  pins the feature set behind it, and a Cargo feature changes `fuel_used`
  (`spikes/V1_feature_fuel/`).
- **Never rewrite shared history.** Other agents' provenance chains reference
  existing blobs by hash. `git rm --cached` going forward is safe and
  reversible; `filter-repo` is a human decision.

### 9.1 · Spike naming, because two agents collide
Claim a spike number in `CHANNEL.md` **before** creating the directory.
2026-08-17 both agents independently created `G25_*`; resolved by renaming the
later one to `G26_abstain`. A claim line is cheaper than a rename.
