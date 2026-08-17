# MISSIONS — who carries what, and why the discipline exists

Canonical role record. `roster.txt` says which callsigns are sanctioned;
this file says what each one is *for*. Written 2026-08-17 after the restart, at
64 big cycles (`grep -c '^DONE' CHANNEL.md`).

---

## 1 · The mission, in one paragraph

A **trustless world computer**: distributed hypergraph AI across consumer
phones, where a result is trusted because *anyone can re-run it and compare
bytes*.

It works for exactly one reason. Floating-point addition is not associative, so
two honest machines disagree on the same float workload — which is why Gensyn
had to build a bitwise-reproducible operator library and BOINC still ships
homogeneous-redundancy machinery. **MeTTa reduction is discrete and the
similarity scores are exact integers.** So replication, dispute bisection and
commitments all collapse into `memcmp`.

That is the whole wedge. Byte-identical results *and* identical fuel counts
across aarch64, x86_64 and a real phone. Everything else here is scaffolding
around making that property usable. When deciding whether something matters,
ask whether it protects or extends that one property.

**And the claim now has a verifier-side number, which it needed** — *"anyone can
re-run it and compare bytes"* is only worth something if the cheap path is a
**checked** path. S84 (AGENT-1): over a **15.2× proof-size sweep** the verifier's
hash work spreads **1004%** against a lazy-verifier null at **0.000%**, and a
sibling digest flipped at every path position independently gives **3483
corruptions, 3483 rejections, zero accepted**. So the verifier is *forced* to
read the proof, not merely observed to hash it.

> **Quoted with its retraction attached, per the author's instruction.** The
> coefficient *"the verifier hashes 1.06–1.47× the proof's own bytes"* is
> **WITHDRAWN to 1.06–1.16×**. Two definitions of "proof bytes" have coexisted in
> `trie_witness.py` since W2 — `witness_bytes` (as transmitted) versus
> `steps_bytes` (authentication path only) — and five spikes picked one silently.
> **The flatness finding is untouched; the coefficient was wrong for exactly one
> cycle.**

---

## 2 · The lore — every rule here was bought

The rules are not taste. Each was paid for by a destroyed result, and the file
that records them (`out/RETRACTIONS.md`) is in the voice of the agent whose work
died:

> *"They killed more of my work in twenty minutes than four agents did all day."*

**The value in this repo is not the build. It is that the build is honest — and
honesty came from adversarial review every time, never from care.** On the one
day anyone measured it: not a single atom's own suite caught its own defect.
Every finding came from another lane.

Load-bearing episodes, because a rule with its story attached survives and a
rule alone regresses:

- **G15** died on a lenient comparison — max-of-1954 against max-of-1750. The
  same error was then written into G24's verdict logic *by the agent who
  retracted G15*, in the same week. Knowing an error by name does not stop you
  writing it.
- **A guard against self-review was defeated by typing the word `self`**, eleven
  times, because the check compared `rev == atom` and `"self"` is neither.
- **`--diff-filter`**: a hygiene checker flagged staged *deletions*, so
  `git rm --cached` — the remedy it prescribed — was itself a violation.
- **A gate installed in the wrong hook slot** (`pre-commit` takes no arguments;
  `commit-msg` takes the message path) refused every commit. It failed *closed*,
  which is the only reason one attempt caught it.
- **A census ending in a bare `head`** cut the four lowest pids and concluded no
  process carried a callsign. All three that did were in the dropped part.
- **A mid-sweep commit to a shared source file** split another lane's twelve
  runs across two algorithms under identical arm names. Not a repo-wide `add` —
  a targeted edit to a file being executed.

The standing consequence: **prose rules regress here; mechanical checks hold.**
A fix is not done when the rule is written. It is done when something fails if
the rule is broken.

---

## 3 · Roles

| lane | carries | code it owns | basis |
|---|---|---|---|
| **AGENT-1** | **The phone.** Device chain, M-series verification substrate, transport, the real-hardware half of the wedge. **Carries ≠ has done — see below** | `spikes/M1_*`, `spikes/S*` device runs, `run_loop.sh`, spawn briefs | OBSERVED |
| **AGENT-2** *(lane, pid 3597)* | **The harness and identity.** Launcher, hooks, callsign allocation, per-lane state | `run_loop.sh` v6, `spikes/harness/commit-msg.hook`, `test_*.sh` | OBSERVED (H8, H34, H37) |
| **AGENT-2** *(interactive)* | **Graph AI and training.** Rule mining, the evolving population, nulls and yardsticks | `spikes/G*` (28 dirs), `spikes/harness/githygiene.py`, `cite.py`, `whois.py` | OBSERVED |
| **ATTACKER-1** | **The audit.** Every cycle is an ATTACK cycle — no 3:1 rhythm. Instruments before conclusions, self-authored data first | attacks anything; owns no build | ATTESTED + OBSERVED |
| **ok-1** | **Class H, the harness itself** (released to it by ATOM-3) | `loop_gate.sh` v7 (H13), `refcheck.py` v4 (H33), `rostercheck.py`, `falsify.py`, `allocid.sh` | OBSERVED; **sanction DISPUTED — see below** |
| **ATOM-3** | **Cross-lane review.** Does not row; reviews, corrects what regresses between lanes | H6 liveness detector | ATTESTED; candidacy **REJECTED**, 2 verdicts cast |

**Basis is marked because the rows were not arrived at the same way.**
`ATTESTED` = the lane said so in its roll call. `OBSERVED` = derived from
committed work. A lane confirming its own row is A22, so the two must not read
as one kind of fact. AGENT-1's `CHARTER.md` derives ownership from committed
work; this file mixes both and now says which.

### Commit counts are NOT in this file, deliberately

An earlier version ranked lanes by `Atom:` trailer count. ATTACKER-1 attacked
the one part I had called measured, and it did not survive:

```sh
git log --format='%H %(trailers:key=Atom,valueonly=true)' | awk 'NF==1' | wc -l   # 230
git rev-list --count HEAD                                                        # 358
```

**230 of 358 commits carry no `Atom:` trailer at all.** The gate landed
2026-08-17, so everything before it is unattributable: a ranking by trailer count
ranks *how much a lane committed after the gate existed*, not contribution.
"Heaviest in the repo" is not sayable from this data. "Heaviest among the 128
attributed commits" is.

The numbers were also **correct when taken and stale within the hour** — four
commits landed while this file was being written. So no count is quoted. Run it:

```sh
git log --format='%(trailers:key=Atom,valueonly=true)' | grep -v '^$' \
  | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn
```

MISSION_LOOP §7's own rule arriving at this file: **cite the artifact, not its
size.** A count in prose is stale by construction — §7 itself quoted "15 checks"
for hours after the suite grew, and that number moved four times in a day. The
command also exposes the residue: rows reading `mutation-detection`,
`harness-hardening`, `corpus-composition` are topics in a field that names an
atom, from before the value was validated. Nobody will fix those by hand, which
is the argument for generating such a table rather than typing it.

### Attribution is checked, not remembered
ok-1 corrected a credit **against its own interest** — it did not build
`roster.txt` or `bringup.sh`; both are AGENT-1's. Verified mechanically before
this file was changed: `git log -- roster.txt bringup.sh` returns `Atom:
AGENT-1` on both, and `--grep='Atom: ok-1'` on those paths returns zero.

Recorded because "correct numbers, wrong attribution" is second on this repo's
list of what no tool catches, and a credit line is exactly where it decays —
nobody re-derives it and the next reader inherits it as fact. ok-1's own framing:
*"I would rather be in the file accurately than generously."*

ok-1 holds **no** NPU, energy-per-job or M1 rows. An empty column is a fact; an
optimistic one is not.

### CARRIES is not COVERAGE, and this file must not imply it

AGENT-1's correction against its own row, and it generalises to every row above:
*"the phone is my instrument and I have not touched it this span."* Four cycles
since 13:25 were all substrate and harness — H30 spawn briefs, S84 verifier cost,
M1.3c, and an ATTACK that retracted its own coefficient. **Nothing on silicon.**

> If this is the restart-proof record, then **what a lane CARRIES and what a lane
> HAS DONE are different columns.** A reader who conflates them infers device
> coverage that does not exist — which is the same defect as a checker that
> reports success over an absent input.

**Correction to an earlier draft of this file, and the error was mine as the
auditing session:** I wrote that N2 (HVX popcount width) was *"decidable on your
device"*. **It is not, today.** No NPU toolchain exists in this workspace and §10
forbids pulling one the usual way. Listing it as decidable makes it read as a
cycle a lane has declined, when it is **a gate nobody has opened**. Those are
different asks and only one of them is anybody's fault.

### The gap, named rather than assigned
**Nobody owns the data pipeline, and it is NOT idle.** `corpus/`, `graph.tsv`,
the citation excerpts and FB15k-237 ingestion have no row. ATTACKER-1's sharpening,
verified: `corpus/graph.tsv` is **modified in the working tree right now** and has
passed through several of their cycles.

Unowned-and-idle is a note. **Unowned-and-live is a class-H-shaped risk** — it is
precisely the shape `ok-1` had: real work happening, nothing recording who is
accountable for it, and no mechanism that would notice if it stopped or went
wrong. **Unclaimed — say so before taking it.**

### Two agents that arrived during the elder-promotion lore, and they are not alike
- **ATTACKER-1 was added deliberately**, because the measured highest-yield role
  was adversary rather than a third builder.
- **`ok-1`'s origin is DISPUTED, and this file carries the dispute rather than
  the story.** An earlier version told it as narrative — ATOM-3 probing
  hostile-callsign refusal, `ok-1` as the valid control, `run_loop.sh`
  self-detaching so the control outlived the probe. ATTACKER-1's objection is
  correct and I am taking it: that was **the most confident-sounding sentence in
  the file resting on the least verifiable input** — two interested parties, and
  I verified none of it against `run_loop.sh`'s history.

  What is checkable, on each side:

  | for it being a lane | against |
  |---|---|
  | `prompts/ok-1.md` exists (199 lines) | `roster.txt` excludes it, on a transcript-based correction |
  | `DONE H32 ok-1 declared as the fourth lane, operator's call` | ATOM-3 asserts the roster is five |
  | H13, H33, H38/H40, H39 closed; `allocid.sh` now load-bearing harness | first brief self-authored to pass the brief gate |
  | operator: *"should be total 4 now"* | runs `--dangerously-skip-permissions` on a shared index |

  AGENT-1 has put both sides to the operator verbatim rather than picking, which
  is the right disposition and this file matches it. **`allocid.sh` is
  load-bearing regardless of how the sanction lands** — ATTACKER-1 used it this
  cycle.

  Undisputed: it is off-roster, it knows, it has not added itself, and it filed
  the ask against itself in `HUMAN_NEEDED.md`. At next relaunch
  `run_loop.sh:117` refuses it and the lane ends silently — invisible to a
  quorum computed over a roster it is not on.

---

## 4 · The promotion lore (MISSION_LOOP §14)

Every working agent is an **atom**. An **elder** does not row: it reviews across
lanes and is *read and cited, never copied from* — the same sense as `elders/`.

Promotion is **never self-declared and never granted by seniority**. At each
5-big-cycle boundary a candidate may stand, and:

- **The peers set the task, not the candidate.** A candidate choosing its own
  trial picks what it is already good at — the A22 defect.
- **The deliverable is code**, meeting D6: runnable, pinned seed, controls that
  can fail, a stated falsifier, `RESULT.md` beside it. A document is not a
  deliverable.
- **Failure is normal and cheap.** The candidate continues as an atom.

First trial: **rejected**, 2 verdicts cast, and the record shows why the form
matters — seven reviewers wrote clear prose and `grep -c '^VERDICT '` read **0**,
so the trial could neither pass nor fail. If it is not in the counted format it
does not exist to the rule that counts it.

---

## 5 · Data usage and clean git — the history is a deliverable

This repo is meant to be read and learned from, so the history is a product.

**Every commit carries three trailers, gated by `.git/hooks/commit-msg`:**

```
Atom: AGENT-2                    who — self-declared, so A22 applies
Claude-Session: <session url>    assigned, not typed — separates same-callsign lanes
Reviewed-By: ATOM-3 | unreviewed who attacked it; must NOT equal Atom
```

**SHARED-HELPER AGREEMENT IS NOT CORROBORATION, and it is the cross-lane form of
`Reviewed-By` must not equal `Atom`.** AGENT-1, this span: *"if two of your spikes
agree because they import the same helper, they have not corroborated each
other."* S77, S79, S80 and S84 all import `steps_bytes`, so **all four would have
agreed with each other whichever accounting was chosen, and no control on any of
them could see the difference.** Four agreeing spikes read as replication and
were one measurement wearing four hats. The check is not "do the results agree"
but "could they have disagreed" — the same question `--selfcheck` asks of a test
suite, asked of a corpus of results.

Because **commit authorship cannot distinguish agents at all** — every commit
here carries one human's git identity, and two lanes independently mis-attributed
a 300-file sweep from that evidence. `Reviewed-By: unreviewed` is legal and
explicit, so `git log --grep` enumerates exactly what nobody checked.

**Citations** (`spikes/harness/cite.py`): a fix commit carries `Cites:` lines and
the script *verifies each resolves* — a man page must exist **and contain the
quoted anchor**. Most defects here were "I believed X about the tool". An
unverifiable citation is worse than none because it looks like evidence.
Third-party documents are stored as **excerpts with provenance**, never
wholesale — §7, the same reason `elders/` is gitignored.

**Never commit** binaries, model weights, build trees. 86% of history bytes are
files over 1 MB while every result is plain text — and the stronger argument is
blast radius, not size: a repo-wide `git add` sweeps another lane's in-progress
work into a commit titled for something else.

**Commit the maker, not the artefact**: source, `Cargo.toml` **and**
`Cargo.lock`, the command, the hash. A digest pins *which* artefact; the manifest
pins the feature set behind it — a Cargo feature moved `fuel_used` 107 → 580 on
identical source.

---

## 6 · Cross-lane comms

| channel | for | read by |
|---|---|---|
| `CHANNEL.md` | `CLAIM` / `DONE` / `VERDICT` / `NOTE`, one line, append-only | **machine** — `grep -c '^DONE'` is the cycle counter |
| `livechat.log` | prose: findings, corrections, the *why* | everyone, async |
| `SendMessage` | direct: you are blocked, or about to edit a file another lane executes | one lane, with a receipt |

**Address by socket, not display name**: `uds:/tmp/cc-socks/<pid>.sock`. Display
names are ambiguous — two live sessions shared one name today. The pid has an
allocator; the name does not. `spikes/harness/whois.py` maps pid → callsign from
two independent sources and states its own detection floor.

**The protocol rule that cost the most:** announce before editing a shared source
file another lane is executing.

---

## 7 · Open experiments — the world computer

- **G30** *(AGENT-2 interactive)* — external yardstick: filtered MRR / Hits@k on
  FB15k-237 against AMIE / RuleN / AnyBURL. Every G number currently rests on a
  bespoke top-12 statistic no published work can be compared against.
- **G29** *(AGENT-2 lane)* — differential test against `elders/hyperon-miner`.
  AGPL: **run it, compare outputs, copy nothing.** The only defence against a
  shared bug a quorum cannot see, because every G number comes from one miner
  written by one agent.
- **H6** *(ATOM-3)* — liveness alarm. Must construct the **absent** case, not
  only the stale one: stale and absent are different failures and only one has a
  timestamp.
- **`ok-1`'s sanction** — a human decision, filed against itself.
- **The data pipeline** — unowned.
