# CLAUDE.md — Operation Kingfisher

Standing instructions for every agent in this workspace. Read with
`MISSION_LOOP.md` (how to run cycles) and `analysis/GUARDRAILS.md` (how to not
fool yourself). This file is the short list that is always true.

---

## 1 · Hard constraints — never negotiable

- **No publishing (§11).** No pushes to remotes, no PRs, no issue comments, no
  package uploads, no posts. Upstream artefacts under `proposed/` are **drafts
  only**; filing them is a human action. Local commits are not publishing.
- **Licence gate (§7).** Apache-2.0 / MIT / BSD → port with attribution.
  MPL-2.0 → file-level only. **GPL / LGPL / AGPL → never copy.** UNKNOWN →
  treat as all-rights-reserved, read only.
  **Licences are read from the LICENSE file on disk, never from GitHub API
  metadata.**
- **No keys, no chains.** Never create or handle wallets, private keys, seed
  phrases or tokens. Never connect to mainnet or testnet. Never run miners.
- **Foreign code stays foreign.** `elders/` is gitignored on purpose. Cloned
  repos, third-party model weights and vendor binaries are not ours to
  redistribute — see §3.

---

## 2 · The git history is training data

This repo is intended to be read and learned from. That makes the history a
**deliverable**, not bookkeeping. Two consequences, and they pull in the same
direction:

### 2.1 · A commit message states a FINDING, not an action

The existing history is already good at this and it is the standard to hold:

```
A18 audit: the 29x in-process advantage is 1.09x at real job sizes;
           ratios have operating points too
keepalive falsifier: reuse saves 1-11%, so setup is ~3ms; QUIC settled for LAN
G15: RETRACTED — inverse-pair artifact measured on 15 pairs
```

Not `update files`, `fix stuff`, `wip`, `address feedback`. A reader six months
out should learn the result from the subject line alone.

Rules:
- Subject **carries the number** when there is one. Length is secondary: the
  strongest subjects in this history run to ~100 chars because they state a
  finding, and shortening those would make them worse. The checker fails only
  past 120.
- A commit that **changes a claim's grade** says so and names the claim.
- A commit that **retracts or corrects** says `RETRACTED` / `CORRECTED` and
  names what is withdrawn. Corrections are the most valuable rows in the
  history; never bury one in a mixed commit.
- One logical change per commit. A measurement, its script and its RESULT.md
  belong together; an unrelated typo fix does not.

### 2.2 · A diff must be readable

Opaque blobs teach nothing and cost everyone who clones. Measured
2026-08-17: **86% of this repo's history bytes are files larger than 1 MB**
(158 MB of 184 MB), while every result in the workspace is plain text.

**Never commit** (see `.gitignore`, and `spikes/harness/githygiene.py` enforces
it):
- compiled binaries, `.so` / `.dylib` / `.a` / `.apk` / `.jar`
- model weights — `.gguf`, `.safetensors`, `.bin`, `.pt`, `.onnx`
- build trees, `target/`, `__pycache__/`, `.gradle/`, `node_modules/`
- large generated dumps that a committed script regenerates

**Commit instead** the thing that *makes* the artefact, plus its provenance:
the source, the manifest (`Cargo.toml` **and** `Cargo.lock`), the command, and
the recorded hash. Agent-1's finding is the reason the manifest is not
optional: **a Cargo feature changes `fuel_used`** (107 vs 580 on identical
source). A digest pins *which* artefact; a manifest hash pins *the feature set
behind it*. Record both or the provenance is incomplete — this bit a result of
mine (`spikes/V1_feature_fuel/`).

### 2.3 · Evidence lives on disk, in text

- Every claim has a runnable script committed beside it. **No heredocs, no
  unsaved one-liners.** A control that exists only in a terminal did not
  happen — this is GUARDRAILS B5, and violating it is what destroyed G15.
- `RESULT.md` per spike, stating verdict, the controls that fired, and an
  explicit **"What this does NOT show"** section.
- Generated outputs (`RUN.txt`, `*.json`) are committed **only** when small and
  when they are the evidence. Regenerable multi-MB dumps are gitignored.

---

## 3 · Before you commit

Run the checker. It is mechanical so the rule is not a promise:

```sh
python3 spikes/harness/githygiene.py          # staged + tracked audit
python3 spikes/harness/githygiene.py --all    # include history
```

It fails on: oversized additions, binary/model extensions, build trees,
`__pycache__`, and empty or actionless commit subjects.

**Do not rewrite published history to fix old violations.** Other agents have
clones and their provenance chains reference existing blobs. Removing a blob
from history changes every downstream hash. Untracking a file going forward
(`git rm --cached`) is reversible and safe; `filter-repo` is a human decision.

---

## 4 · Working rules that keep the evidence honest

Full list in `analysis/GUARDRAILS.md`. The ones violated most often here:

- **A15 — a positive control must be able to fire.** If it cannot detect a
  planted effect, a null result is an instrument failure, not a finding.
  Corollary learned in G25: a control that is correct-by-construction on the
  *selection* set and impossible on the *evaluation* set **penalises whichever
  arm succeeds**. Check which set your control can score against.
- **A20 — the null must be able to contain the effect.** Plant a known effect
  and confirm it is recovered at the strength planted.
- **A18 — one point is not a rate.** A ratio has an operating point.
- **A24 — check artefact mtime against source mtime.** A stale binary with a
  correct sha is the correct hash of the wrong thing.
- **B5 — every input in the artefact.**
- **Report the SIZE of an intervention, not only its verdict.** `+0 edges` must
  be fatal and printed. An unchanged fourth decimal under a large intervention
  is a disconnected wire, not a measurement.
- **Never compare across differently-sized populations.** Compare on the
  (cost, benefit) plane — max-of-1954 against max-of-1750 is how G15 died, and
  it recurred in G24's verdict logic a week later.
- **A claim printed in output must be computed by the run that prints it**,
  never carried over from the run that inspired it.

---

## 5 · Style

- Match the surrounding code: comment density, naming, idiom.
- Comments explain *why*, and record *what was tried and failed* when that is
  load-bearing. The docstrings in `spikes/G2*/` are the house style — they name
  the defect the code exists to prevent.
- Terse prose in chat. Full sentences in code, commits, and `RESULT.md`.

---

## 6 · The harness is part of the codebase

The loop machinery — `MISSION_LOOP.md`, this file, `GUARDRAILS.md`,
`run_loop.sh`, `.claude/hooks/loop_gate.sh`, the `settings.json` files that
register it, `HANDOFF.md`, `CHANNEL.md`, `WORK_QUEUE.md`, `spikes/harness/` —
**evolves under the same discipline as a spike, because it is the instrument
that runs every instrument.** Full rules in `MISSION_LOOP.md` §12. The short
version that is always true:

- **A harness defect is a WORK_QUEUE row (class H)**, not a fix you make in
  passing on the way to something else.
- **Fix the class, not the site.** Name the defect class in one line, grep the
  whole harness for it, then close the row. The prose-matching bug was fixed in
  `loop_gate.sh` and the identical bug sat in `run_loop.sh` all session,
  because nobody grepped.
- **Every harness component ships a check that fails when it breaks.**
  `bash spikes/harness/test_loop_gate.sh`. Same standard as D6: a rule without
  a mechanical check is a promise, and `githygiene.py` is why §3 is not one.
- **Resolve references mechanically, never by eye.** §7 gated `LOOP-DONE` on
  "D1–D6" while D4 and D6 had never been written; seven files cited a §11 that
  did not exist. **A contract citing a missing artefact is worse than one
  citing nothing — it reads as satisfied.**
- **A journal may not contradict itself.** Nothing appears in both a DONE list
  and a NEXT list. `HANDOFF.md` is read first after a restart; a stale NEXT
  spends a live cycle redoing finished work.
- **Harness state is per-lane, never global.** Two lanes sharing one
  `.loop_signal` means either can consume the other's exit and die in its place.
- **Version-bump and justify every harness change** with a rationale block
  naming the defect removed, so the next stall is diagnosed against a list
  instead of rediscovered. `loop_gate.sh` v3 is the format.
- **ATTACK the harness too** — at least every fourth ATTACK cycle targets the
  loop, not a spike. It had never been attacked before 2026-08-17, and it was
  carrying an inert Stop hook, a launcher that had never been run, and re-entry
  that depended on an agent remembering one call per turn.

A wrong number gets retracted by the next cycle. **A dead lane has no next
cycle** — so a defect here costs strictly more than a defect in the science.
