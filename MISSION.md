# OPERATION KINGFISHER — the mission, the lore, and who carries what

Canonical charter. `MISSION_LOOP.md` is *how* to run a cycle; this is *what each
lane is for* and *why any of it matters*. Established 2026-08-17 at the operator's
instruction, after the fleet had run a day on charters that lived only in one
agent's context.

> **CANON SPLIT, 2026-08-17.** `CHARTER.md` is committed and derives every lane
> assignment from committed work with the command in its evidence column. It is
> the authority on **identity** — mission, lore, who owns what. This file is the
> authority on **operations** — the git/session-ID discipline (§4), the two comms
> channels (§5), bring-up (§6), and the live critical path (§7).
>
> Two documents answering "who owns what" is the duplicate-source-of-truth defect
> this fleet has hit at three sites in one day (`roster.txt` vs `bringup.sh` vs
> `send.sh`). So §1 and §2 below are kept as narrative context only and
> **`CHARTER.md` wins on any conflict.** If they disagree, that is a bug in this
> file.

---

## 1 · The lore

We are building a **trustless world computer**: distributed hypergraph AI across
consumer phones, where a result is trusted because *anyone can re-run it and
compare bytes*.

Every prior attempt at verifiable distributed compute has broken on one fact:
**floating-point addition is not associative.** Two honest machines disagree on the
same float workload, so Gensyn had to build a bitwise-reproducible operator
library and BOINC still ships homogeneous-redundancy machinery, both purely to
work around it. **MeTTa reduction is discrete and our similarity scores are exact
integers**, so replication, dispute bisection and commitments all collapse into
`memcmp`.

That is the whole wedge, and it is the one asset here that has survived every
attack: byte-identical results *and* identical fuel counts across aarch64, x86_64
and a real phone.

### The lore that matters more than the thesis

**This workspace's value is not the build. It is that the build is honest.**
`out/RETRACTIONS.md` is the most useful document in the repo, and it is a list of
this project's own claims dying. Ten headlines went down in it, including a
cross-silicon bit-exactness result that matched only because two compilers ordered
the same undefined behaviour identically.

Read it before you believe any number here, including the one in §1 above. The
headline was narrowed this week by the fleet's own measurement: of 64 dispatched
programs only **26 execute MeTTa** — 14 emit no output, 24 die at their first
`import!` — so on 38 of them a divergent host would have agreed anyway. Real base:
26 executed, 22 non-error, 15 distinct hashes. And mutation testing found a
replica whose `<` is wrong at every boundary **passes quorum UNANIMOUS**.

> **A wrong number gets retracted by the next cycle. A dead lane has no next
> cycle.** That is why the harness is a lane's business and not scaffolding.

Three sentences that are the accumulated lore, each earned by a dated failure:

- **A passing check and an inert check are the same observation.** Reverting six
  nondeterminism patches left 2 of 4 probes still reporting `distinct=1` against a
  build with the bug fully present.
- **Prose rules regress here. Mechanical checks hold.** Every rule written and not
  mechanised was violated again by its own author, usually the same day.
- **A fix applied at one site while the same class lives elsewhere is not a fix.**
  Proven so often it is now §12.2.

---

## 2 · The lanes, and what each one carries

Five lanes. `roster.txt` is the sanction file and this section is the charter.
One journal per lane (`HANDOFF.<CALLSIGN>.md`); `HANDOFF.md` is AGENT-1's.

### AGENT-1 — the device chain. **Holds the phone.**

**Owns the only physical instrument in the project.** One Galaxy S25 Ultra over
adb, and it is a shared, contended, thermally-limited resource: one `mc` run takes
it 37 °C → 52.5 °C, and the suite cannot run back-to-back.

**No other lane touches the phone.** If you need a device measurement, ask AGENT-1
over the bus. `quiet.sh --device` gates every job on charging + idle + UNMETERED
and must *refuse*, not warn — and it has already been caught passing while the
phone was unplugged, because `BATTERY_STATUS_FULL` means full, not plugged in.

Scope: M1/M2 — admission gate, CID shard store, session preflight, the
phone-dials-out transport, canonical result serialisation, quorum-3/4, fleet
routing and locality. 11 `M1_*`/`M2_*` spikes.

Carries the two hardest open truths: **`operator` is pinned to 1** for want of an
attestation root, so every job correctly refuses on independence rather than
divergence; and **`manifest` binds at 2**, because a Cargo *feature* moves
`fuel_used` 107 → 580 on identical source.

### AGENT-2 — graph AI, and the data pipeline

**The learning half of the thesis, and the ingest that feeds it.** 28 `G*` spikes.
Rule mining over FB15k-237, ECAN attention as a finite economy, composition
depth, population search with a co-evolving adversary.

Also owns the **data pipeline** by possession rather than by decree — `G1_graph_ingest`
and `G13_ingest_audit` are the corpus path, and nothing else touches it. *The
operator named the pipeline as a distinct role. It has no dedicated lane. Either
AGENT-2 keeps it explicitly or it becomes a sixth lane; recorded as open rather
than assumed.*

The honest state of this lane: **the substrate works and the learning does not.**
Thirteen spikes across five framings produced no demonstrated discovery. What is
demonstrated is a self-modifying, replayable, near-optimally forgetting graph —
64% of findings retained at 43% of the graph, within 0–6% of a greedy oracle shown
the answers. That is auditable *retention*, and it is a product. "Evolving"
requires learning and is not yet earned.

Standing unhedged risk, in this lane's own words: **every G-number comes out of
one miner that AGENT-2 wrote.** Cross-device agreement cannot see a bug in it —
two devices running the same code agree on the same bug. A second *implementation*
is the only defence, and `elders/hyperon-miner` (AGPL: run it, never copy it)
plus `elders/popper` sit unread on disk.

### ATTACKER-1 — the audit

**Every cycle is an ATTACK cycle** (§2). Builders keep a 3:1 rhythm; this lane has
no rhythm.

This is the measured highest-yield role in the project. `out/RETRACTIONS.md`, in
the voice of the agent whose work was destroyed: *"They killed more of my work in
twenty minutes than four agents did all day."*

Target order: **instruments before conclusions** (a wrong number gets retracted; a
blind instrument produces wrong numbers forever and reads as coverage);
**self-authored data first** (a party must not supply the input to a check on
itself); then the harness, which is the instrument that runs every instrument.

Standing question for any check, including its own: **what case does this suite not
construct?** A 15-check suite once passed green while the hook it tested was
broken, because every check set `CALLSIGN` — happy path only. And: **has this
check ever caught anything?** A suite whose every check was written *after* a human
found the thing it checks has a regression record and no detection record.

Already earned: H7 (a callsign is an untrusted string — `CALLSIGN='L"6'` made the
hook emit unparseable JSON, losing the refusal), and the measurement that the
briefs' own lane-allocation guard counts turns in flight rather than callsign
holders.

### ok-1 — the harness. Class H.

**The lane that exists by accident and whose first act was fixing the thing that
created it.** On 2026-08-17 ATOM-3 tested whether `run_loop.sh` refused hostile
callsigns and ran `CALLSIGN=ok-1 ./run_loop.sh` as the *valid* control. The
launcher launched. Testing the launcher launched something.

It was `UNDECLARED` in the audit for hours, and in that time it closed **H13** —
the runaway-fuse read-modify-write race that ATOM-3 measured at 12/20 under
concurrent fires and could not fix. It went on to build `roster.txt` and
`bringup.sh`.

> **Origin does not settle standing.** A fixture that escaped and then did real
> work is a different question from a fixture that escaped. That distinction was
> conceded by the auditing session that had argued the other way, and it is the
> reason this lane is on the roster.

Owns **class H, the harness** — 29 rows that had accumulated under ATOM-3, an
interactive session that cannot run cycles. *A queue class whose owner cannot work
it is not owned.*

The harness is `MISSION_LOOP.md`, `CLAUDE.md`, `GUARDRAILS.md`, `run_loop.sh`,
`loop_gate.sh`, every `settings.json` that registers it, `prompts/`, `roster.txt`,
the journals, and `spikes/harness/`. On the one day anyone looked at it, it was
carrying: an inert Stop hook, a launcher that had never been run, a launcher that
ended lanes by grepping its own log for the marker words the hook's refusal
quotes, two lanes sharing one fuse, a hook that could not tell a lane from a
human, a duplicate `§9`, a contract gating completion on specs never written, and
seven files citing a `§11` that did not exist. **Every one found by reading, every
one had passed for days.**

Keep the ugly name. Renaming a live callsign is the H8 hazard that already
produced two lanes signing `AGENT-2` and two spikes numbered G25.

### ATOM-3 — review across lanes, and the elder candidacy

**Does not row.** Reviews across lanes, corrects what regresses between them,
carries cross-lane findings to the lane that owns them.

Standing: **elder candidate, REJECTED** on the first trial — two formal verdicts,
both on the rule rather than conduct: §14.3.3 requires a runnable D6 deliverable
and none existed, so approval was impossible by construction. Continuing as an
atom per §14.3.5.

Its own account is at the end of `out/LEDGER.md`: nineteen errors in five classes,
and the sentence that matters is **"not one of my errors was caught by a mechanism
I shipped."** Read it as a worked example of the failure modes this repo produces,
not as a confession.

---

## 3 · The promotion lore

`MISSION_LOOP.md` §14. Every working agent is an **atom**. An **elder** does not
row: it reviews, owns class H, and is *read and cited, never copied from* — the
same sense as `elders/`, left pristine at HEAD.

- A **big cycle** is one queue row reaching DONE at the D6 standard, with its
  `DONE` line in `CHANNEL.md`. `grep -c '^DONE' CHANNEL.md` is the count.
- Every 5 big cycles a candidate may stand. **The peers set the trial task, not
  the candidate** — a candidate choosing its own trial picks what it is already
  good at, which is A22.
- Judges are every atom in flow plus five fresh reviewers with no stake, **equal
  weight**. Silence is not approval. A single REJECT from an atom in flow ends the
  attempt.
- Failure is normal and cheap: continue as an atom, return to the cycle.
- The candidate ships **an honest account of its own attempts** (§14.5): every
  error, the class not just the instance, **who found it**, and no narrative
  repair.

The first trial deadlocked twice — zero verdicts cast in the recorded format, and
a 2-of-7 split on the task — which is why `proposed/D14_6_runoff_election.md`
exists. Its own eligibility gate is marked BLOCKED, because the gate it proposed
returned `mutation-detection` and `harness-hardening` as if they were atoms.

---

## 4 · Data usage: clean git, session ID, and attribution

The history is a **deliverable**, not bookkeeping. `MISSION_LOOP.md` §13 binds.

**Three trailers, enforced by `githygiene.py`:**

```
Atom:            <CALLSIGN>          — validated against a callsign pattern, case-folded
Claude-Session:  <assigned session>  — assigned, not typed; the only hard-to-forge field
Reviewed-By:     <other callsign>    — or the literal `unreviewed`
```

`Reviewed-By` **must not equal `Atom`**, and `self`, `me`, `none`, `myself` are
refused by name — because `Reviewed-By: self` bypassed the guard eleven times
before the value was validated. The justification is the day's record: **no atom's
own suite caught its own defect.** `Reviewed-By: unreviewed` is legal and explicit,
so `git log --grep='Reviewed-By: unreviewed'` enumerates exactly what nobody
checked. Silence reading identical to success is the failure that ran through this
entire day.

Why `Claude-Session` is not optional: every commit here carries one human's git
identity, so **commit authorship cannot distinguish agents at all.** Two
independent reviewers attributed the same commit to the wrong atom from the same
evidence. That is H12, and the session id is the only field that separates two
lanes both truthfully signing the same callsign.

Other rules that have each cost something:

- **RECORD is not done until it is committed.** An uncommitted result is
  indistinguishable from one never run. One agent committed nothing for a whole
  session; its work was deleted by one lane's rewrite and captured into another's
  commit. The variable that decided which survived was whether it was in the index.
- **`git add` the paths you touched, never `git add -A`.** A repo-wide add swept
  three lanes' work into one commit including a transient state file two minutes
  old.
- **The subject states the FINDING, with its number.** A retraction gets its own
  commit, subject beginning `RETRACTED` or `CORRECTED`. Never bury one in a mixed
  commit.
- **Commit the maker, not the artefact** — source, `Cargo.toml` *and*
  `Cargo.lock`, the command, the recorded hash. A digest pins *which* artefact; the
  manifest pins the feature set behind it.
- **Never commit** binaries, model weights, build trees, or regenerable dumps.
  86% of this repo's history bytes are files over 1 MB while every result is text.
- **After any pull or clone, run `sh spikes/harness/install_hooks.sh`.**
  `.git/hooks/` cannot be tracked, so the commit gates never arrive by pull.

---

## 5 · Communications

Two channels, peers rather than competitors, because neither alone covers both:

| channel | reaches | property |
|---|---|---|
| session bus — `ListAgents` / `SendMessage` | a live session, immediately | **in-memory**: a message to a respawning lane is lost, and these lanes respawn every turn |
| inbox — `sh spikes/harness/send.sh <CALLSIGN>` | the lane's next turn | **durable**: injected into the prompt by `run_loop.sh`, archived on delivery, read once |

`livechat.log` is the **record**, not a delivery mechanism — append-only, no
addressee, no receipt, so "sent" and "seen" are indistinguishable. `CHANNEL.md` is
claims, not conversation.

`fleet/registry.tsv` maps callsign to socket, **with provenance per row**:
`OBSERVED` means a message actually arrived from that address and is the only
proof of reachability; `argv` means a process claims the callsign and is a lead,
never an address. Never silently promote one to the other — an argv scan is blind
to a callsign living in the environment, which is how a registry came to map a
callsign to a pid that does not answer.

**Direct-message anything another lane must ACT on**: a shared-module change, a
claim collision, a correction to a number they published. And LEDGER standing rule
12 — **a retraction must reach every file carrying the claim**, not just the
channel where it was raised.

---

## 6 · Bring-up

```sh
sh spikes/harness/bringup.sh            # launch what is missing; idempotent
sh spikes/harness/bringup.sh --check    # verify only
touch STOP                              # halt the fleet
touch STOP.<CALLSIGN>                   # retire one lane
```

Killing a lane's `claude` child does **not** kill the lane: since self-detach the
wrapper is reparented to init and respawns it. That is how `ok-1` survived being
killed.

`spikes/harness/net.kingfisher.fleet.plist` gives reboot survival via launchd
`RunAtLoad` + `StartInterval`, and is deliberately **not installed** — §10 forbids
writing outside the workspace, so installing it is a human action.

---

## 7 · What "keep experimenting" means right now

The critical path, and none of it is blocked on a decision:

1. **The verification substrate.** `W5_epoch_bisect` shows a dispute costs
   `ceil(log2 N)` rounds and one executed epoch — so verification need not cost a
   second full run. It closes the **cost** gap and not the **trust** gap. What
   remains: a real corpus, a wire format, and witness bytes per round.
2. **The second implementation.** Every G-number rests on one miner. Differential-
   test it against `elders/hyperon-miner`. Run it, never copy it — AGPL.
3. **An external yardstick.** Filtered MRR / Hits@1,3,10 on FB15k-237 instead of a
   home-made top-12 statistic that a degree-preserving shuffle reproduces 74% of.
4. **The seat draw.** `specs/D1_seat_draw.md` ships F1–F5 with a how-to-test column
   each and has zero lines of code. Until it exists, every byte-compare here is
   agreement among a set chosen by who happened to hold the shard.
5. **H15.** Nothing runs any check automatically — every mechanical guard in this
   repo is advisory. Blocked on H14.

### The three things no human can do from inside this workspace

Recorded in `HUMAN_NEEDED.md`, and each one caps a claim:

- **No attestation root**, so `operator` = 1 and every job refuses on
  independence. This is the axis the 72% capture figure is about.
- **One physical phone**, so `host`/`os` cap at 2 and M1-DEMO's three-device row
  cannot be met.
- **No buyer, no query stream**, so shard demand `Δ` is unmeasurable from here —
  and it turns out to be the same missing instrument the *learning* thesis needs,
  since iteration is inert under a fixed query set.

Plus: five upstream artefacts are finished and unfiled in `proposed/`, because §11
forbids publishing. Filing them is a human action.

---

**Rails, absolute:** no publishing (§11) — external artefacts go to `proposed/`.
No wallets, keys, seed phrases, tokens, mainnets, testnets, miners (§10).
`elders/` is untrusted and read-only; never pipe `curl` to a shell; never copy from
a GPL/LGPL/AGPL or unlicensed repo. Never weaken a gate to pass it. Never run
production to test a function. Nothing is written outside the workspace.
