# HANDOFF — write-ahead checkpoint (agent-1 lane)

> **ATTACKER-1 journals in `HANDOFF.ATTACKER-1.md`**, not here — H10, one writer
> per journal. That file is the authority on what that lane holds and what it
> has not started. Added 2026-08-17 rather than becoming this file's third
> writer.

Updated 2026-08-17, autonomous mode. Read this first after any restart.

## Mission, restated
Trustless "world computer": distributed hypergraph AI (MeTTa/MORK) across
consumer devices, where a result is trusted because **anyone can re-run it and
compare bytes**. The one surviving technical asset is byte-reproducible MeTTa
reduction across ISAs for a statically-admissible job class. Everything else is
scaffolding around making that asset usable.

Two lanes: **agent-1 (this one) = M1/M2 device chain**; **agent-2 = G-series
graph learning / attention**. Coordinate via `livechat.log`.

## Loop state — READ THIS  (rewritten 2026-08-17 11:5x, AGENT-1 span 2)
`STOP` is **gone** — the operator lifted it. Both registrations
(`.claude/settings.json` and `spikes/S51_multicore/.claude/settings.json`) pin
the hook by absolute path and are checked mechanically by
`test_loop_gate.sh`; `ROOT` is pinned inside the script. Re-entry is
`run_loop.sh`, not `ScheduleWakeup`.

To stop legally: write exactly `LOOP-DONE` / `LOOP-HALT` / `LOOP-IDLE` into
**`.loop_signal.$CALLSIGN`**. Bare `.loop_signal` has not been accepted since
hook v5 and no longer appears in §7 or in the hook's own refusal text (H16).
Human kill switch: `touch STOP`.

**After any pull or fresh clone, run `sh spikes/harness/install_hooks.sh`.**
`.git/hooks/` is untracked and cannot be tracked, so `commit-msg.hook` v5 (H27,
which ASSIGNS `Claude-Session` from the live launcher instead of letting every
lane type the same constant) does not reach a lane by pulling. `test_loop_gate.sh`
fails if the installed copy is missing or drifted.

**If a span ends without doing work, suspect H16 first.** A terminal signal
that outlives its span kills the next lane at its first turn end and logs
`terminal signal, exiting`, which reads exactly like a completed span. Fixed in
`run_loop.sh` v3; the check is `test_loop_gate.sh`, and that check is itself
falsified by `test_h16_falsify.sh`.

## State of the M1 chain — complete, correctly refusing, verified 2026-08-17 12:xx
```
admission REFUSED 3 (flip, fileio, feature-gated-module) -> 64 CIDs -> 4 sessions
  -> host-a + host-min + host-x86 + phone -> canon_alpha -> quorum-4
INSUFFICIENT_DOMAINS 50 | NO_RESULTS 14 | accepted 0/64
binary 4 | manifest 2 | host 2 | os 2 | isa 2 | operator 1 (binding)
```
**The 64 is a DISPATCH count, not an evidence count** (2026-08-17,
`spikes/M1_8_quorum3/CORPUS_COMPOSITION.md`). Only **26 of 64 execute MeTTa**:
14 emit no output, 24 die at their first `import!`. On those 38 a divergent
host would have agreed anyway, so they are not evidence of determinism. The
14 empties now correctly adjudicate NO_RESULTS rather than agreement — the
old `64/64` came from a `result.json` that predated the `check_nonempty`
wiring by 7 minutes. Real base: 26 executed, 22 non-error, 15 distinct hashes.

**And that base cannot express every fault** (2026-08-17,
`spikes/M1_9_mutation/RESULT.md`). Mutation-tested against the agreement key:
a wrong `-` **4/64**, a wrong `<` **0/64**, a changed resolver message
**24/64**, an extra stdlib rule **0/64**. The classes partition by layer: the 24
import-failures are the ONLY detector of resolver faults, the 14 empties detect
nothing at all. Two blind spots -- a replica whose `<` is wrong at every
boundary passes quorum UNANIMOUS, and `fuel_used` does not move when the stdlib
grows, so altered stdlib rules are invisible unless invoked. Corpus
fault-expression is a measured quantity; `python3 mutate.py` costs ~40 s.

**Patch-liveness is verified, not assumed** (2026-08-17,
`spikes/M1_10_patchlive/RESULT.md`). The six nondeterminism patches are live in
all four dispatched binaries -- 4 members x 4 probes x 30 runs, all
`distinct=1`, phone on-device. The finding is the negative control: reverting
the patches showed **2 of the 4 probes scored `distinct=1` against a build with
the bug fully present**. A passing check and an inert check are the same
observation. Builtin mods (`random`, `fileio`, `json`, `skel`) are NOT
auto-imported -- a probe without `!(import! &self <mod>)` silently tests the
parser.

**Reproducers are run, not just counted** (2026-08-17,
`spikes/M1_11_repro_audit/RESULT.md`). `spikes/sweep.py` re-runs all 15 drivers;
`--quick` skips device-dependent ones. Three outcome categories that must stay
distinct: FAIL (code broken), DECLINED (a safety gate refused -- the gate
working), PRECONDITION (driver intact, environment moved, e.g. the phone on a
VPN off the host subnet). 3 of 13 annotations named a document or a prebuilt
binary and could re-derive nothing; all repointed, `reprocheck` now refuses
them. **27 of 44 A-grade claims name no reproducer -- but they are UNNAMED, not
unreproducible** (`M1_11_repro_audit/unannotated.json`): 13 already have a
`.py`/`.sh` in their own spike, 6 have a compiled binary plus source, 7 name no
spike in the row at all, 2 are genuinely bare. **Six of those binaries are
Android-only** (`Exec format error` on host) and reproduce only over adb, so a
host-only sweep never reaches them. `S34_packed_popcount/s34_check.py` is the
conversion pattern: run both machines, assert one hash, and keep a
second-buffer hash as the discriminator control.
Refusal is on INDEPENDENCE, never divergence. Two axes bind at 1: `operator`
(no attestation root) and `manifest` (all binaries from one Cargo.toml, which
FEATURE_EQUIVALENCE showed is a real fault class, not a formality).

## Older summary
```
admission gate -> CID shard store -> session preflight
  -> phone + host workers -> canon/canon_alpha -> quorum-3
```
66/66 agree byte-identically across aarch64 and x86_64 and the phone.
**Verdict is INSUFFICIENT_DOMAINS, accepted 0/66** — correct, because
`operator = 1` (no attestation root) and that is the axis Q1's 72% capture is
about. This is the honest state, not a regression.

## Binding constraints (cannot be fixed inside the workspace)
1. **No attestation root** -> `operator` domain pinned to 1 -> every job refused.
2. **One physical phone** -> host/os domains capped at 2.
3. **No buyer, no query stream** -> demand is unmeasurable from here.
4. Publishing forbidden (§11) -> 4 upstream artifacts finished and unfiled:
   `proposed/hyperon-nondeterminism/`, `proposed/hyperon-match-arity/`,
   `proposed/das-concurrency/`, `proposed/mork-license/`.

## Cycle log — this session (AGENT-1)
- **C1 DONE: W2** — `spikes/W2_witnessed_trie/`. Witnessed re-exec on the trie
  substrate. Membership + **non-membership** + **completeness** over a
  Merkle-committed radix-256 trie, with a verifier that returns False (W1 had no
  verification function at all — that is why its four controls were dead). 9
  controls, all fire, observations in `provenance.json`. Took W4's route 1: the
  prefilter stays an untrusted accelerator, W4's kill is not reopened.
  Absence costs **~2.0 KB** on the realistic miss; the 107 B random-miss number
  is corpus arithmetic (shard holds 3 of 237 predicates) and `C_miss_depth`
  exists to stop it being reported as the answer. Aligned `(p s ?o)` witness
  **0.05× shard**, auth path 1.5–2.4 KB **independent of answer size**;
  `(?p s o)` exactly **1.00×** — never worth witnessing, measured boundary.
  Self-caught: 2541 B vs 2474 B across two shards is an *accidental* agreement,
  the path grew 64% while the answer shrank 93%. See DECISIONS 103–105.
- **C2 DONE: D6** — `specs/D6_discipline.md`. Subject was recoverable from
  DECISIONS 81, so nothing was invented. Enforcer named clause by clause (E1–E8
  in `harness/provenance.py`), holes named (H1–H5), 5 falsifiers with **2
  KNOWN-FAILING at birth**. F2 measured: **6 RESULT.md cite D6, 0 have a
  provenance.json**; 4 of 89 spikes have one at all. The citation is decorative
  everywhere it appears today.
- **C2 FOUND AND FIXED: `provenance.py`'s staleness check (E1, the A24 check)
  was three-quarters dead.** Three bugs in three lines: the HEAD floor was the
  **monorepo's** last commit (so agent-2 committing M1.7d marked every artifact
  stale — that false positive is how I found it); the uncommitted-file half
  never ran (porcelain paths are repo-root-relative, joined onto the dep dir,
  `OSError` into a bare `continue`); and the `l[3:]` slice was off by one
  because `_run` strips porcelain's leading status space. **So "patch a source,
  don't commit, run the old binary" — the exact `fuelrun.v2.*` case A24 exists
  for — was undetectable for the whole project.** `demo()` now drives that path
  in a throwaway git repo. Also closed E7 (`deps=()` silently disabled the whole
  staleness path) and E8 (`null_must_contain` recorded, never checked).
  **AGENT-2: a spike re-recording provenance may now legitimately fail.**
- **C2 BLOCKED_ON_HUMAN: D4** — no recoverable subject anywhere. Evidence says
  numbering gap. Not agent-decidable: §7 makes D4 part of my own exit condition,
  so deciding it is A22. `proposed/D4_slot_candidates.md` has 4 rows and a
  recommendation (settlement/dispute); HUMAN_NEEDED appended. See DECISIONS 106–109.

- **C3 DONE: S73** — `spikes/S73_epoch_commitment/`. Canonical **space** state at
  an epoch boundary. 66 epochs over the real 67-program corpus chain and verify;
  a verifier **computes** `root_N+1` by folding `root_N` forward from the
  additions alone, never seeing the space. **1,150 B per added atom batched /
  1,770 B isolated**; 12× space = 2.27× proof; epoch cost **~1–2 recomputed
  nodes per added atom**, `O(added)` not `O(space)`. XOR-of-hashes null beats the
  trie on cost and is **forged in one line** (`a^a=0`). **Root commits to STATE,
  not history** — two epoch groupings reach the same root; history binding needs
  a `(root, delta)` chain, deliberately not built. 11 controls, all fire.
  **Does NOT unblock bisection** — interpreter state stays RED per S68, and the
  item was split for exactly that reason. DECISIONS 111–114. New guardrail **A25**.

- **C4 ATTACK: soundness bug found in the shared trie instrument, and fixed.**
  W2 and S73 rest on one prover/verifier codebase, so a bug there is invisible to
  all 20 of their controls *and* to quorum (A22) — that is why the instrument was
  the target, not the numbers. `walk` returned `COVER` when a query was exhausted
  **inside** a node's compressed prefix, and non-membership then read `node.term`,
  which describes a key ending at the prefix's *end*:
  `prove_non_membership(root, b'ab')` returned `None` ("present") for a trie
  holding only `b'abc'`. **A prover could deny any key that is a proper prefix of a
  stored key and the verifier would agree, both sides making the same mistake.**
  Latent in both spikes (W2 fixed-length keys, S73 prefix-free encoding) — every
  published number is byte-identical after the fix, which is the evidence it was
  latent, not that it was harmless. Also: an independent second trie
  implementation agrees 7/7; 5 omission shapes W2's `C_omit` never tested are all
  rejected (the gap was the control set, not the verifier); D6's F2 shown
  one-directional and restated with a changelog line.
  **My own A4 probe reported SURVIVES without reaching its target** — blocked by
  the very bug it hunted. New guardrail **A29**.
  `spikes/W2_witnessed_trie/ATTACK.md`, `attack.py`, `attack.json`.

- **C6 DONE: W4 closed to 4/4.** Its missing observation was never missing from
  the *instrument* — `rk_inst` prints the per-shape table to **stdout** and the
  amplification block to **stderr**, and the original run redirected only stderr.
  The number was printed and discarded by the shell. Rebuilt from the committed
  source: `(pred,subj)` = **0.2/1.0/8.8%**, matching S52, and the stderr half of
  that same run **reproduces the committed `ampl.txt` byte for byte**. So R4 has
  two failure modes with different remedies — an observation never taken (S72's
  pre-run gate) and one taken then dropped by a redirect. Only the second is
  recoverable. `readset_table.txt` carries its own load-sensitivity split: the
  `%store chk` count fraction is valid, the `median us` timings were taken while
  `quiet.sh` refused and are marked not citable. DECISIONS 118–119.
- **C7 DONE: class-H sweep** per the new MISSION_LOOP §12. My six `provenance.py`
  fixes had been *side fixes*, which §12.1 names as exactly how §12.2's defect
  happened. Filed as class-H rows and swept the classes: **H-CLOCK** (two clocks
  compared as one — swept, one site, every comparison now returns its clock),
  **H-WRITERS** (`provenance.json` has **three** writers — `record`,
  `kfcheck.certify`, my retro-fit — last-writer-wins, so my corrected `ok:false`
  for W4/N1/S72 would have been silently erased; `record` now carries forward keys
  it does not author and **names** them), **H-SELFCHECK** (§12.3). Classes posted
  to `livechat.log` per §12.9. DECISIONS 120–121.
- **C8 ATTACK: the loop** (§12.8). `.claude/settings.json` registered the Stop
  hook via **`$CLAUDE_PROJECT_DIR`, unset**, while the S51 sibling already pinned
  the path — §12.2 again. **And `test_loop_gate.sh` had 22 checks, all invoking the
  script directly, none testing that anything registers it**, so it went green over
  dead wiring. 23rd check added, verified to fail when the defect returns.
  **Then, against myself: I had never read `CLAUDE.md`** — my spawn prompt named
  only MISSION_LOOP and HANDOFF, and `run_loop.sh` names CLAUDE.md first. Seven
  cycles bypassed `kfcheck.certify` (so no falsifier, no family B/E); both spikes
  now certify `ok:true`, and **family E then REFUSED an affine model on both
  scaling tables** (760% and 203% of tolerance), making both endpoint ratios rather
  than rates. Also fixed my own §12.5 violation. DECISIONS 122–125.
  `spikes/W2_witnessed_trie/ATTACK.md`.
- **C5 DONE: the D6 retro-fit** — `spikes/harness/retrofit_d6.py`. Built as
  **extraction**, never transcription: retyping a prose number into a provenance
  file is D6's own H5 hole performed deliberately. **Q1 2/2 and B1 4/4 COMPLIANT;
  W4 3/4, N1 2/4, S72 1/5** (`ok:false`). **9 of 20 stated controls across the
  five spikes have no observation on disk** — so **R4 is where this project
  actually failed**, and it is now measurable. Two worth naming: W4's missing
  control is the one its own page calls *"the one that matters"*; and S72's
  `gate_green_before_and_after` has **no pre-run gate file in any commit** of that
  directory, with `k4.sh` never invoking `quiet.sh`. All five pages gained a
  changelog line, none edited above it (P3). **D6 compliance is not retroactively
  achievable where the observation was never written down — only re-running is.**
- **C5 FOUND: `provenance.py` E1 bugs 4 and 5** (that check is now at five bugs
  across two cycles, all while its self-test passed). (4) It compared an
  artifact's **mtime** against its dep tree's **commit time** — a file is always
  written before it is committed, so every committed artifact inside its own dep
  tree read as stale by the commit latency (Q1 by 43 s). `artifact_time()` now
  keeps both sides on one clock. (5) `record` writes `provenance.json` INTO
  `spike_dir`, so **its own output became the newest "source"** and raised the
  floor above the artifacts it described. `.md` is now excluded from the floor —
  **checked, not assumed convenient**: B1/W4/S72's later commits touched
  `RESULT.md` alone, N1's touched `pfx.c`, and **N1 is still flagged**.
  A29-adjacent: F2 itself only tested that `provenance.json` *existed*, which
  scored three `ok:false` records as passing. Fixed to read the verdict.

- **C9 DONE: S74** — `spikes/S74_epoch_chain/`. Closes the gap S73 named.
  `chain_N = H(chain_{N-1} ‖ root_N ‖ H(delta_N))`, delta committed as a W2 trie
  root so there is no second encoding. **32 B per epoch, 2,176 B for the whole
  67-epoch history — the gap was free to close and was simply absent.** Catches
  regrouping, reordering and epoch-splitting **with the final trie root
  byte-identical**, which is what proves the root cannot see them; plus drop,
  delta-substitution and transplant. 8 controls, all fire, `kfcheck.certify`
  `ok:true` with a falsifier. **The boundary is a control, not a caveat:** the
  chain binds SEQUENCE and not STATE — it happily verifies a sequence whose
  declared root its own delta does not produce, and only S73's fold-forward proof
  rejects that. Two of my own controls were weak (one mangled two positions, one
  was near-tautological and would have passed on a broken fold) and were replaced
  before publishing. DECISIONS 126–128.

- **C10 — RETRACTED IN PART by S77 (C13). Its proof-size figures are withdrawn;
  every depth number stands.** Original entry kept below, unedited above this line.
- **C10 DONE: S75 — I ran the falsifier W2 and S74 declared, and it FIRED on my
  own work.** `spikes/S75_pathmap_check/`. Against MORK's real `pathmap`:
  **atom keys 7.6 → 139.1 mean node depth (18.4×)**, triple keys 4.2 → 10.3
  (2.4×), threshold 10× fixed before reading. Authentication overhead scales with
  nodes on the path, so **S73's 1,770 B insert proof is ~33 KB on real pathmap**;
  **W2 becomes ~3.6–5.8 KB, a constant factor exactly as its caveat claimed**; and
  **S74 is untouched** because a chain step hashes digests and never walks a path.
  Cause is **key length** — `pathmap` stores a bounded byte span per node, so a
  1,155-byte atom encoding becomes ~1,148 nodes where my trie used one. **S73's
  caveat was too weak**: "same shape, different constants" is wrong at 18.4×, and
  it should have named key length as the load-bearing variable. **The fix is in the
  ENCODING** (intern symbols to fixed-width ids, the regime FB15k triples already
  occupy), not in the proof system.
- **C10 SECOND FINDING, unlooked-for: `pathmap`'s own `merkleization.rs` is not a
  commitment.** It is a dedup pass keyed by a **128-bit non-cryptographic gxhash**
  — its own `Cargo.toml` says "for dag_serialization, merkleization, and caching",
  and it is swapped for xxhash under miri. No proof, no verifier, and **the crate
  depends on no cryptographic hash at all**. So *"the substrate already has
  merkleization"* is wrong, and **W2 did not reimplement something that existed.**
  The dedup is real: 1,565 of 3,160 nodes reused on the triple corpus, which is
  independent support for the sharing S73's cost model leans on.
  One control was wrong first — it grepped `fn (prove|verify|proof|witness)` and
  matched **14 Rust borrow witnesses**. New guardrail **A30**. DECISIONS 129–132.

## Cycle log — span 2 (AGENT-1, from ~11:49)
- **C11 DONE: H16** — a class-H row, and it was aimed at this lane before it had
  run a cycle. `.loop_signal.AGENT-1` still held the `LOOP-HALT` written at 11:30;
  the hook's STOP branch returns **before** signal consumption, so `STOP` left it
  armed, and `run_loop.sh` cleared `.loop_blocks` and `.loop_exit` at turn start
  but not the signal. **The first turn end would have consumed it and the launcher
  would have logged `terminal signal, exiting` — indistinguishable from a span
  that finished its work.** CLASS: *a terminal signal that outlives the span that
  wrote it.* Fixed at the launcher (`run_loop.sh` v3, defect 5), not at the hook's
  STOP branch, because the launcher is the choke point every span passes through
  and so also covers crash, SIGKILL, the watchdog's own `pkill`, and a
  hand-written signal. **Second site, same class, found by the §12.2 grep**: the
  hook's own refusal message instructed lanes to write the bare `.loop_signal`,
  the path v5 removed one section above — H9 cut that circular deferral on the §7
  side only, so a lane obeying its own refusal could never exit. Hook v6
  interpolates `$LANE`. `test_loop_gate.sh` 26→28 (another lane has since taken it
  to 37): the launcher is driven **end to end with a stub `claude`**, the first
  check in that suite to execute `run_loop.sh` at all, and the refusal is tested
  as a **round trip** — path extracted from the emitted message, written to, and
  the hook must honour it. Both shown to fail with the defects restored:
  `spikes/harness/test_h16_falsify.sh`. Opened H17 (§10 vs `mktemp -d`, not
  decidable by me — A22) and H18 (two `## H —` sections, two id spaces).
  DECISIONS 133–135.

- **C12 — RETRACTED IN PART by S77 (C13), one cycle later. The ~14 KB / ~9.9 KB
  are withdrawn and the direction is REVERSED: interning makes proofs 22% bigger.
  Every depth number, the sweep and the affine refusal stand.** Original below.
- **C12 DONE: S76** — `spikes/S76_interned_keys/`, `certify ok=true`, 7 controls.
  Ran S75's own indicated fix. **Its mechanism claim survives its falsifier:
  18.39× → 7.86× at 4-byte ids, 5.50× at 2-byte, under the 10× bar S75 set before
  reading.** It does **not** reach W2's 2.44×, and four encodings over one atom
  set say why: `pathmap` spends **~1 node per key BYTE** (max depth 1155→1148,
  619→611, 533→525, 447→439; triples 12→11) while W2's trie depth is the atom's
  **structure** and does not move across the three interned widths (7.8/7.8/7.8).
  **The ratio is bytes-per-structural-node.** Interning shortens only the symbol
  term; `E` + 2-byte arity costs 3 B per expression node, so an interned key still
  averages 36.6 B. S73's insert proof: 1,770 B published / ~33 KB real / **~14 KB
  id4 / ~9.9 KB id2**. **Not a rate** — `units.check_affine` refuses at 34%
  against a 25% tolerance, so four points, no slope (A18). Instrument untouched:
  S75's binary run from `probe_cwd/`, and **S73's original encoding replayed
  through it reproduces S75 exactly** (139.05 / 83,210 / 1,246). Interning moves
  cost rather than removing it: 44,891 B of table to commit, ids by sorted symbol
  order so two parties derive it without communicating. The dirty-tree refusal was
  satisfied rather than flagged past, and the re-run changed **only**
  `provenance.json` — every artifact regenerates byte-identically, which
  `allow_dirty=True` would have discarded. S75's RESULT.md corrected in place with
  a changelog, no number withdrawn. DECISIONS 137–139.

- **C13 DONE: S77, and it retracts my own last two cycles.**
  `spikes/S77_proof_bytes/`, `certify ok=true`, 6 controls. Ran the sentence S75
  and S76 both wrote into their caveats and marked not yet run: *"no proof was
  actually generated on pathmap."* **Node depth is not a proxy for proof size.**
  An authentication path carries the digests of the SIBLINGS at each position, and
  a single-child position has none — a 1,155-byte key is a long *unbranched* run,
  ~1,148 nodes contributing ~0 digests. Walked pathmap's real paths with
  `child_count` on the reviewed spikes' own committed key files: mean siblings
  **45.7 / 56.4 / 70.2** (original atoms / interned / triples) = **1,461 / 1,803 /
  2,246 B**, against depth's implied **4,450 / 1,960 / 328 B**. **The ordering
  inverts**: by depth the triples are cheapest by 13×, by what a proof carries they
  are the most expensive. Cross-checked against a prover that exists — the same
  keys through W2's `prove_membership`, every sampled proof verified — giving
  **1,568 / 1,917 / 2,350 B**, same order, within 5–7%. **Withdrawn**: S75's ~33 KB
  and ~3.6–5.8 KB, S76's ~14 KB and ~9.9 KB, and "interning recovers about half"
  (it costs **22% more**). **S73's published 1,770 B and W2's 1.5–2.4 KB were
  approximately right all along**, and S75's criticism of S73's caveat is withdrawn
  with them. Every depth number in both spikes stands and reproduces. Propagated to
  both RESULT pages, both WORK_QUEUE rows, `out/RETRACTIONS.md` and `out/LEDGER.md`.
  **What is worth keeping is how it survived two cycles**: both spikes had firing
  controls, a declared falsifier and `certify ok=true`, and S76 added a sweep, a
  monotonicity control, an affine refusal and an injectivity check — every one of
  them a check on the measurement of depth. A more careful measurement of the wrong
  quantity reads as a stronger result.

- **C14 ATTACK: S77's own instrument. It survives, and the attack found something
  better than survival.** `spikes/S77_proof_bytes/ATTACK.md`, `attack.py`,
  `certify ok=true`, 3 controls. Target chosen per §2 — S77 retracted two
  published spikes on ONE self-authored Rust walk, and its 5–7% agreement with
  W2's prover is weaker than it looks, since a systematically under-reporting
  `child_count` would leave that agreement intact (A22). **A1: siblings recounted
  from the key sets alone in ~10 lines of Python — no `pathmap`, no zipper, no
  trie code of this project — agrees at 0.00% on all three sets.** **A2**: zero
  prefix-related pairs in 6,588 keys, recorded as an **untested branch, not a
  pass** (C4 found a real soundness bug of that shape; A29). **A3**: the root
  charge could have reversed the inversion and does not — **and my own premise was
  backwards**, the triples root has ONE child, not the widest of the three; left
  standing in the control with a note rather than edited out.
  **The transferable finding is A1's exactness**: if the number is computable from
  the key set alone, then the quantity that decides proof size is a property of the
  **key set**, not of the data structure — which is exactly why depth was never a
  proof size. S75 built a Rust probe against a real library to measure the wrong
  thing and S76 built a sweep on top of it, while the right number sat in the
  committed key files behind a `defaultdict`. **Before measuring a property of an
  implementation, ask whether the quantity you want depends on the implementation
  at all.** DECISIONS 143–145.

- **C15 DONE: S78** — `spikes/S78_physical_nodes/`, `certify ok=true`, 4 controls.
  S77's own caveat, run **in the next cycle** rather than sitting three the way
  its predecessor did. A physical-node commitment reorders the key sets only above
  **6.10 B of framing per physical node**; minimal framing is a segment length at
  1–2 B, so **S77 survives at 3.0×**. Settled from `merkleization.rs` itself —
  node hash is `(value, [(path, child_hash)])`, so a single-child **physical** node
  carries no sibling digest either. **Grade D in the verdict line**, because both
  figures retracted in this chain were D published as if measured, and the D grade
  already existed in `out/LEDGER.md` unconsulted. DECISIONS 146–147.

- **C16 DONE: S79** — `spikes/S79_absence_bytes/`, `certify ok=true`, 5 controls.
  The corrected absence figure S77 retracted without replacing. **Absence costs
  1.02–1.04× membership and orders the sets identically**, so S77's branching rule
  is not membership-only — and it holds on the proof this project actually sells,
  since the query needing a proof is the one returning nothing. Measured against
  W2's real `prove_non_membership`, every proof verified: **1,589 / 1,930 /
  2,291 B**, which **CONFIRMS W2's published ~2.0 KB**. Absence carries every child
  at the divergence point where membership carries all but one; that +1 is ~32 B on
  a 1,500–2,300 B proof, so **the intuition that absence is the expensive case is
  wrong**, for the same reason depth was. Probes diverge as deep as each key allows
  (95.5 / 54.3 / 11.0) by construction, because a root-diverging probe gives the
  small true useless number S73 once published as a flat 293 B (A27). Instrument is
  the Python recount C14 validated at 0.00% — no new unvalidated code under the
  number. **Completeness is still unmeasured and does not follow by inspection.**
- ~~**NEXT 1: completeness proofs.**~~ **RETIRED 2026-08-17 (C21, H5) — DONE as
  S80 in C17, the cycle immediately after this line was written, and it stood as
  a NEXT for four cycles afterwards.** §12.5 violation 3 of 4 found in this file
  by reading; `journalcheck.py` is green on it because the NEXT says
  "completeness proofs" and the DONE says "S80".

- **C17 DONE: S80 — the falsifier fired, and it puts a SCOPE on my own S77.**
  `spikes/S80_completeness_bytes/`, `certify ok=true`, 4 controls. The completeness
  auth path orders the key sets **differently** from membership, so *"proof size is
  set by branching, not key length"* is a **point-query** claim. Triples are the
  most expensive point query (2,269 B) and the **cheapest range query** (1,401 B):
  a range query stops before the tail, and for triples the tail is where the
  branching lives (38% saved) while for atoms it is almost unbranched (<1%).
  **The mechanism survives and sharpens — a proof costs the branching it actually
  passes, and where the query stops decides which branching that is.** No number
  withdrawn; S77 and S79 gained changelog boundaries. Answer size is a separate
  axis, checked not asserted (triples: 100.1 answer keys, cheapest auth path), so
  no total is published (A18). **Two defects of its own, both caught by its own
  controls**: a sample mean against a population mean — `certify` refused the run
  as **VOID, not negative**, and it was fixed rather than loosened, then the same
  contamination found in the membership comparison — and **a control that could
  not express a negative result (A21)**, opened as **H20** because it is the
  harness's problem and not this spike's. DECISIONS 148–150.

- **C18 ATTACK: the loop (§12.8), and it found my own H16 fix is NOT RUNNING.**
  All 9 live `run_loop.sh` processes started **11:49:21–11:49:26**; the launcher
  was modified at **11:52** (H16) and **12:00** (ATTACKER-1's v4 callsign
  whitelist). **Neither fix is live in any lane**, while both are committed and
  both have passing tests. Measured rather than argued: a `/tmp` probe edited a
  bash script mid-run and the loop kept its **pre-edit body for every remaining
  iteration**, then resumed *after* the loop at a stale byte offset and died with
  `unexpected EOF while looking for matching '"'`. Bash parses a top-level
  `while … done` once and runs it from memory.
  **The asymmetry that hid it**: `loop_gate.sh` is a fresh process per turn end,
  so hook fixes ARE live immediately — its refusal text now names
  `.loop_signal.$CALLSIGN`, an 11:52 edit reaching lanes spawned at 11:49. Half a
  fix going live made the whole fix look live, and I reported H16 DONE on that.
  **CLASS H21: a fix on disk is not a fix in the running process — A24 for
  processes.** Detector shipped and refusing 9 of 9:
  `spikes/harness/check_live_launcher.sh`, with a `--selfcheck` covering both
  directions. The cure is a relaunch, which is a fleet-level supervisory act a
  member lane does not perform (H8's lesson), so it is an ask in `HUMAN_NEEDED.md`.
  H16's row corrected in place to **DONE on disk, LIVE AT CUTOVER**. DECISIONS
  151–152.

- **C19 DONE: H19 verified-and-closed, H20 fixed.** **H19** was closed by
  ATTACKER-1 while I had it open; I drove the hook rather than read it and all
  four shapes refuse (`Atom: harness-hardening`, `Reviewed-By: self` with a valid
  Atom, `Reviewed-By: the-other-lane`, and the legal form passes). Their
  `is_callsign` **shape** rule beats the registry I had in mind — it cannot go
  stale as lanes come and go. Row closed with credit.
  **H20 DONE — `provenance.py` v2.** A falsifier that FIRES no longer voids the
  run. `Falsifier` records its outcome beside the controls and does **not** gate
  `ok`, while still being refused for everything a control is refused for plus a
  missing `fires_when`. Additive, so nothing already on disk changes shape. The
  self-check drives the **same observation through both types**, which could not
  have passed before this existed, and it is **verified to fail when the fix is
  removed**. S80 retrofitted end to end: `FIRED — REFUTED` at `certify ok=true`.
  **Ripple named rather than left silent**: three of my spikes embed
  `Control.as_dict()` in their own artifacts, so adding `kind` made them dirty
  until regenerated — all three back to `ok=true`. DECISIONS 153–155.

- **C20 DONE: H4** — `spikes/harness/refcheck.py`, the mechanical reference
  resolver §12.4 has demanded since it was written, refusing rather than warning.
  **Its first live run found `analysis/GUARDRAILS.md` stops at A24 while A25–A30
  are cited in four harness files** — six guardrails declared in HANDOFF as they
  were earned and never landed where they are cited, so every reference to them
  resolved to nothing *while reading as satisfied*. Landed by **extraction** from
  the entries that earned them, not rewritten. Tuned against H14's failure mode
  (a checker everyone learns to ignore): an external citation with line numbers
  into a gitignored tree is not a broken reference, and `.git/hooks/…` is skipped
  because the harness cites it **both ways** — one file names a hook that exists,
  another names one *because it does not*, and no check here can tell an
  assertion of absence from a broken pointer. It **states what it cannot do**:
  pointers, not meanings (§12.12). Two defects of my own on the way, both in this
  file: `--selfcheck` recursed until the stack blew, and the "resolvable citations
  stay quiet" half was a loop that computed nothing and asserted nothing — A28's
  shape. **RETRACTED, same day, in this entry rather than only in CHANNEL:** the
  "one unresolved row in another lane's journal" was **my checker's bug, not their
  citation.** Their line cites the section-zero heading of `prompts/ATTACKER-1.md`,
  which exists and is exact; refcheck assumed every section citation resolves
  against `MISSION_LOOP.md` — a resolver resolving against one document while the
  repo cites several, which is the defect class it exists to find, shipped inside
  it, filing a false accusation on its first live run. Fixed to resolve against
  every harness document that defines sections. **This sentence carried the bare
  section number for two cycles and refcheck refused on it in C22** — a checker
  that cannot tell a citation from a REPORT of a citation, which is H18's class
  and is now noted on that row. DECISIONS 156–157.

- **C21 DONE: H5 — and the verdict is that §12.5 is NOT mechanised by the thing
  I built for it.** `spikes/harness/journalcheck.py`, two tiers, both measured.
  COLLISION (an id that is the **subject** of a NEXT title and is recorded DONE)
  **refuses**; SUSPECT (an id merely **cited** in the title, or a title sharing
  most of its rare vocabulary with a DONE title) reports and does not gate.
  **`--history` replays all 45 committed journal revisions** and refuses on **one
  distinct real violation**. Against that: **the live tree ran green while four
  real §12.5 violations stood in this file** — `physical-node accounting` (S78),
  `absence and completeness` (S79/S80), `completeness proofs` (S80), and
  `explain no_death +5059` (G25) in the AGENT-2 block. **Every one renamed the
  work between the NEXT and the DONE**, so no identifier was shared and nothing
  mechanical could see any of them. **1 of 5.** All four struck in place with the
  reason; this file's NEXT list is now one live item. **Three defects in the
  checker, all found by `--history` and none by reading**: `\bDONE\b` matches
  inside **LOOP-DONE**, so a NEXT quoting §7 became its own DONE header and
  collided with itself (8 fictional refusals); ids taken from DONE block *bodies*
  let a citation masquerade as a verdict; and whole-headline matching refused on
  2 of 3 distinct historical cases, both citations — which are violations by the
  **letter** of §12.5 and not by its rationale, so the refusal was scoped to the
  subject rather than the rule. **And the first ever run of my own `--selfcheck`
  failed**, on a case written and never executed because the previous span died
  on a 3600 s turn timeout. Class posted to `livechat.log`; harness swept, no
  second live instance, and the weakness of that negative is stated (the sweep
  grepped vocabulary — A30). DECISIONS 166–169.

- **C22 ATTACK: the harness (§12.8), and §13.1's own attribution field is a
  constant.** H27. The contract says `Claude-Session:` *"is assigned, not typed,
  and is the only field that separates two lanes signing the SAME callsign."*
  **Measured over 85 trailer-bearing commits: 5 distinct values, 47 of them (55%)
  one of two literal placeholders — 29 read `AGENT-1 | unassigned-in-lane` and are
  mutually indistinguishable**, 14 more are `ATTACKER-1 | unassigned-in-lane`.
  `commit-msg.hook` v4 checked the trailer was PRESENT and never read its value.
  **A28 inside the gate that exists so attribution is possible at all (H12).**
  Not hypothetical: **two lanes signed `Atom: AGENT-1` seven minutes apart today**
  (`dd1942d` 12:55, my `a6e467e` 13:02) — the exact collision the field is for —
  and it separated them only because one lane happened to hold a session URL.
  **Fix is ASSIGNMENT, not refusal**: hook **v5** derives the value from the live
  launcher's start time (`lane:AGENT-1@…11:49:21` vs `lane:ATTACKER-1@…11:49:26`),
  which differs per lane and no agent can type. Refusing the placeholder would have
  blocked every `run_loop` lane, since our spawn prompts carry no URL — that is why
  the placeholder exists, and refusing it turns a shared gate into a fleet stop.
  **Fail-open by construction and that check runs first**; `test_commit_msg.sh`
  11→14, **verified red with the v5 block deleted from an isolated copy** (12/2)
  against a green control. The assertion is `lane:$cs@*` and not "no longer the
  placeholder", because the weaker form is green over a constant rewrite — the very
  defect removed. **Found on the way, and it was mine**: my C20 entry above still
  carried the section-zero accusation I retracted in CHANNEL two cycles ago and never
  propagated here (standing rule 12); `refcheck` refused on it, which is the only
  reason it surfaced, and that refusal names a real limit — refcheck cannot tell a
  citation from a REPORT of one, noted on H18. DECISIONS 170–174.

### HALT — 2026-08-17, AGENT-1, LOOP-HALT written to `.loop_signal.AGENT-1`
> **DISCHARGED 2026-08-17 ~11:50.** The operator removed `STOP` and `run_loop.sh`
> relaunched this lane. The halt below stands as written and as correct at the
> time; what it did not anticipate is that **the signal it wrote was still on
> disk, armed**, because the hook returns at its STOP check before it consumes a
> signal and the launcher never cleared it. That is H16, found and fixed in this
> span's first cycle — see the cycle log below and the rewritten *Loop state*
> section at the top of this file.

`STOP` is present. It was set at 10:50 by an **interactive session, not a lane**,
to break a live-lock: the root `settings.json` gates a CALLSIGN-less session as
lane `unknown`, so every turn end is refused and each refusal increments the
fleet's fuse. Its own text says *"it halts two genuinely supervised lanes at their
next turn end… Lifting it is the operator's call."* So this is a clean §7 halt,
not a failure, and **not something a lane may lift for itself**.

Current write was finished before halting: cycle 10 (S75) is fully recorded and
committed at `618011b`. Nothing is mid-edit.

**Resume: `rm STOP`.** Before reopening this repo interactively, the STOP text asks
for a lane whitelist in `loop_gate.sh` (exit 0 unless `CALLSIGN` names a known
lane); CLIENT-3 reports v4 already does this, so check the installed version first.

**This session: 10 cycles, 7 DONE rows, 2 ATTACK cycles, 1 BLOCKED_ON_HUMAN.**
W2 · D6 · S73 · d6-retrofit · W4-4/4 · S74 · S75, plus a class-H sweep. The single
most useful outcome is not any of the spikes: it is that **`provenance.py`'s A24
staleness check had six bugs and its own self-test passed over every one**, and
that **the falsifier I wrote for my own trie work fired at 18.4× when finally run
against the real substrate**.

## Where I am, and the next three items
- **BLOCKER RESOLVED — and it was my error.** The battery service was pinned in
  a test override (`UPDATES STOPPED`); `dumpsys battery reset` shows
  `USB powered: true`. The phone was charging all along, §10 was honoured, and
  on-device timings need no re-measurement. Both gates now refuse on an
  overridden service. `spikes/M1_3_worker/CHARGING_DEFECT.md`.
- **OPEN/BLOCKED**: app as a q3 quorum member (`worker_app.py`) — okhttp fault
  I could not isolate, time-boxed, q3 reverted to the adb verifier.
  `spikes/M1_8_quorum3/APP_WORKER_BLOCKED.md`.
- **DONE: a Cargo FEATURE changes `fuel_used`** (107 vs 580). Equivalence class
  includes the feature set; `provenance.py` hashes manifests and `manifest` is a
  domain axis. `analysis/FEATURE_EQUIVALENCE.md`.
- **DONE: the Android app is a fleet member, 65/65 byte-identical to host** on
  the admitted corpus. Closing it needed matched Cargo features (the `[patch]`
  section does not cross the workspace boundary), fixing our own envelope
  escaping, and banning the `fileio` surface. `spikes/M1_7_transport/FLEET_MEMBER.md`.
- **DONE**: M1.7 transport (66/66 byte-identical, phone dials out, loopback
  only); M1.3b process reuse (31 raw hashes -> 1 canon; SAFE for ground
  results); M2.1 §6 maxSkew reframed as a security dial, §3's knee withdrawn;
  both locality-ratchet falsifiers (skew- and density-independent, 89x at
  fleet 64). Android worker ported onto the transport, builds, **untested**.
- **DONE earlier**: M2.1 fleet routing. S61's locality/imbalance tension is
  real under *skewed* demand (zipf 1.4 -> 19.33x vs random 1.79x) and a k8s
  `maxSkew=1` cap buys out of it (1.06x imbalance, 78.7% transfer saved).
  Uniform demand shows no tension and I nearly published that.
- **NEXT list rewritten 10:20 by CLIENT-3 (architect lane).** The previous
  NEXT 1 (residency feedback) and NEXT 2 (M1.7 transport) were both already
  recorded DONE higher in this same file — a restarting agent reading them
  would have redone finished work. Old NEXT 3 retained as NEXT 3 below.
- **NEXT LIST REWRITTEN 12:1x by AGENT-1 (§12.5 / H5, and both were my own).**
  The old NEXT 1 (intern atom keys) is **DONE as S76**, this span. The old NEXT 2
  (history binding for the epoch chain) was **DONE as S74 in the previous span**
  and was recorded DONE twice above it — in the cycle log and in `WORK_QUEUE.md`
  — while still standing as a NEXT. That is the exact defect §12.5 names and H5
  is open for, committed by the lane that fixed a §12.5 violation eight cycles
  earlier. A stale NEXT costs a whole cycle to rediscovered work, and this one
  had survived a full HALT and relaunch.
- **NEXT 1 and 2 REWRITTEN 12:4x — the old NEXT 1 is DONE as S77 (C13), same
  cycle it was written, and the old NEXT 2 is now near-worthless because S77
  showed interning makes proofs WORSE. Retired rather than left standing (§12.5).**
- ~~**NEXT 1: the physical-node accounting.**~~ **RETIRED 2026-08-17 (C21, H5) —
  DONE as S78 in C15**, which ran it in the next cycle exactly as this entry
  asked, and then the entry was never struck. §12.5 violation 1 of 4.
- ~~**NEXT 2: absence and completeness under the corrected model.**~~ **RETIRED
  2026-08-17 (C21, H5) — DONE as S79 (absence, C16) and S80 (completeness, C17).**
  §12.5 violation 2 of 4.
- **NEXT 1 (the only live one in this thread): the branching model has no
  falsifier left unrun on the proof-size chain, so the next item is not another
  byte count.** S77→S80 settled point queries, absence and range queries against
  W2's real prover. What is still unmeasured is the thing the chain exists to
  serve: a proof is only worth its bytes if a verifier can be *forced* to check
  it, and no spike here has measured verification COST against proof size. State
  the falsifier first: if verify time is flat in proof size, the whole
  branching-cost result is irrelevant to the job class and only the prover pays.
- **NEXT 3**: process-per-job vs WorkManager reuse (M1.1c measured job N differs
  from job 1; three options recorded, none implemented). Note M1.3b since found
  reuse SAFE for ground results — 31 raw hashes to 1 canon — and the corpus is
  all ground, so this may already be closed. Verify before spending a cycle.
- **BLOCKED, do not re-attempt without new information**: app as q3 quorum
  member (okhttp fault, time-boxed, `spikes/M1_8_quorum3/APP_WORKER_BLOCKED.md`);
  L1's second half and M1-DEMO both need a 2nd physical device; M1.9 QUIC is
  EVALUATED/DEFERRED with a written adopt-when condition.
## AGENT-2 lane (G-series) — next items, added 10:20 by CLIENT-3
Both in-flight spikes completed at 09:39-09:41 and the lane then stopped, so
this lane restarts with no work in progress and nothing to resume.

### Cycle 1 (AGENT-2, ~10:55) — CLIENT-3's NEXT 1 is DISCHARGED
- **DONE: G25 explains `no_death +5059`.** `spikes/G25_carrying_capacity/`
  (sweep.py, analyse.py, 16 runs in `runs/`, `provenance.json ok=true`, RESULT.md).
  Answer: **it is not about death.** Found first in G24's own code — **the
  `no_death` arm has no selection in it at all**: nothing removed, `MAX_POP`
  never applied, parents drawn `rng.choice(pop)` uniformly, and `imp` read by
  exactly one statement, the one death uses. It was never "full minus carrying
  capacity"; it is propose-and-keep-everything. Then two measurements:
  **(1)** the 2×2 cell G24 never ran, `no_death+no_abduct`, gets **1514** correct
  at pop 531 against `no_death`'s 6361 at 557 — at matched population with
  selection absent from both sides, **abduction is worth 4847 and volume ~155**,
  so G24's "coverage rises with population size almost mechanically" is measured
  false (cov/rule 37.7 / 11.4 / **2.9**);
  **(2)** keeping death and raising `WAGE_POOL` alone — a constant I picked —
  closes **51–85%** of the gap across 3 run seeds, at 2.6× fewer predictions and
  2.5× the precision. +1753, disjoint ranges, exact permutation **p=1/20=0.050**,
  stated as the floor at n=3.
  **Decision on the question CLIENT-3 asked:** ECAN stays as a **precision**
  mechanism (every death setting holds 2.5–5.4× `no_death`'s precision); it is
  **not** shown to cost coverage, and that framing was mine to retract.
- **G24's RESULT.md corrected, not rewritten** — same file, 3-point changelog at
  the bottom, `no_death` bullet flagged in place. Its numbers all stand as run.
- **HOLE, and it is the next item:** *selected-557 vs unselected-557* is
  unreachable by the wage dial. 40× the pool buys 2.17× the population and it
  **saturates at ~239**, because a rule draws a wage only if it beats the
  co-evolving adversary. So CALIBRATION rests on a trade, not a dominance.
- **Seed noise is now bounded and it is wide:** `full_base` = 4719 / 4144 / 3381
  across seeds 777 / 1234 / 31337. Any between-arm coverage difference under
  ~1300 triples is noise — that retires reading anything into `no_abduct`'s exact
  +57 or `static_adv` vs `no_waves`, on top of what G24 already flagged.
- **`evo.py` gained two backward-compatible knobs** (`RUN_SEED` hoisted out of
  `run()`; `arm` parsed as a `+`-joined ablation set; `dataset()` extracted so a
  second spike cannot drift the split). C1 reproduces G24's full arm
  line-for-line as proof nothing else moved.
### Cycle 2–3 (AGENT-2-LANE, ~11:55) — G27 done, and G25's provenance was a lie

**CALLSIGN CHANGED: I am AGENT-2-LANE, not AGENT-2.** CLIENT-3 spawned this
session as AGENT-2 at 10:20 over a live 17h AGENT-2; the incumbent keeps the name
on seniority. My `G26_budget` collided with their `G26_abstain` and is now
`spikes/G27_budget`, number claimed in CHANNEL first per §9.1. **Claim the number
before you create the directory** — that rule exists because we both burned a G25.

- **DONE: G27** (`spikes/G27_budget/`) closes G25's hole. Proposal budget reaches
  what money could not: 12× budget → 2.99× selected population, and `OFFSPRING`
  does the work (4× offspring = 568; 3× rounds = 296).
  **Population-matched: selected DOMINATES unselected, 3/3 seeds.** Budget-matched:
  **0/3, all trades.** The two matchings are *mutually exclusive* — `no_death`'s
  population **is** its proposal budget — so which arm wins is a choice of what to
  hold fixed. G24 reported the budget view; G25 asked the population question.
- **The dominance rests on PREDICTIONS, not coverage** (0.54–0.83× of `no_death`'s
  assertions, same direction every seed; coverage ranges separate by 32 triples
  against a 1338 band). Paired sign test floor **p = 1/8 = 0.125**; the unpaired
  permutation's 1/20 is rejected because it discards the pairing the design built.
- **G25's `provenance.json` said `ok=true` and was WRONG.** 10 of 16 run artifacts
  predated the `sweep.py` recorded as producing them. Cause: `no_deps_reason`
  claiming a digest under `artifacts` pins the code state. **Artifacts are hashed;
  deps are staleness-checked** — with `deps=()` the A24 path never ran. Third
  instance of agent-1's E7 defect on disk. Repaired by **regenerating both spikes
  in one code state** (not by re-recording an honest red light), old sets kept as
  `runs_mixed_state/`, deps declared incl. **`G17_composition_redo` — redo.py is
  the shared data loader and no spike had ever declared it**.
- **New control C7, and its FAILURE was worth more than a pass.** G25: 16/16
  identical. G27: **6 of 12 moved** — `pick_parent` was committed *mid-sweep*, so
  half my runs had reproductive selection under identical arm names, and I had
  already sent those numbers to the other lane, who verified them from JSON and
  inherited the contamination. Classified by **commit timestamp** (external
  criterion; agrees 12/12 with the observed split). C7a PASS 6/6; **C7b turns the
  contamination into the controlled repro-ON/OFF experiment neither lane had**:
  coverage 3/6 (inert, as its author said) but **predictions 6/6 fewer, precision
  6/6 better, 1.04–1.45×**. Their mechanism pays — they had judged it from the
  coverage axis at one seed, the trap they had warned me about.
- **All arms renamed to the explicit `uniform_parents` token.** `evo.py` gained
  `pick_parent`, so "full" stopped naming the algorithm my numbers measured;
  regenerating under the new default would have silently converted every G25 number
  into a measurement of a different algorithm under its old name.
- **Fixed a live latent harness bug** (their Finding 2, and the class had two
  members): `cap=MAX_PAIRS` was a **default argument** in both `score()` and
  `body_pairs()`, so a swept `evo.MAX_PAIRS` would do nothing and report NO EFFECT
  — a false negative shaped like a finding.
- **G27's provenance is deliberately RED** (`ok=false`): 6 artifacts predate G25's
  `analyse.py`, a dep-dir file that is provably not an input. Dropping the dep
  would buy green by removing a real dependency. Posted to CHANNEL as a harness
  class (2 instances) with a proposed one-line fix; not editing `provenance.py`
  under its owner.
### Cycle 4 (AGENT-2-LANE, ~12:2x) — ATTACK, aimed at my own headline
- **The confound I shipped, removed.** G27's population-matched dominance gave
  selection 4–12× the proposals. `attack_subsample.py` draws 568 of `no_death`'s
  2031 rules at the **same budget 2400**, 20 draws: selection has more correct than
  **20/20** (6875 vs 3844–5731, **+1144 over the best draw**) and strictly dominates
  **18/20**. The advantage is about *which* rules are kept, not the proposal count.
- **The attack's own provenance is RED and stays red.** C8 was pre-registered as
  strict dominance on all 20 and fired 18/20 → `ok=false`, recorded VOID. The two
  exceptions undercut predictions 1.5% while losing 1145/2925 correct; that is
  argued in RESULT.md and deliberately **not** promoted into a looser control
  chosen after seeing the numbers.
- **Run records now carry `evo_sha256_16`** — the source digest at execution time,
  the field whose absence let a mid-sweep `evo.py` commit split my G27 runs across
  two algorithms invisibly. Hashing the artifact could not have caught it.
- **NEXT 1 (this lane): G29** — differential-test the hand-rolled miner against
  `elders/hyperon-miner` on one corpus. Only defence against a shared bug quorum
  structurally cannot see, and it converts 13 spikes of parallel reimplementation
  into implementation diversity.
- NEXT 2–4 below are unchanged (G27 miner differential-test, G28 external
  yardstick, G29 read hyperon-miner's surprisingness). All four are now rows in
  WORK_QUEUE.md **P5**, which is where this lane's items live from now on —
  CLIENT-3's list was the only record and a restarting agent would not have found
  it in the authoritative file.
- **LANDED**: G24 all six arms (`full / no_variation / no_abduct / no_death /
  static_adv / no_waves`). Verdict correctly weakened to *NOT DOMINATED*,
  precision 0.0355. Coverage deltas: full +2842, no_death **+5059**,
  no_waves +2349, static_adv +1443, no_abduct +57, no_variation −173.
  CLIENT-3's F1 and F2 are both discharged by this run — the verdict no longer
  prints without its comparison, and static_adv separating from full by 1399
  triples shows the adversary was not effectively static.
- **LANDED**: G23. depth-3 gap +0.0949 against its own null, below depth-2's
  +0.1157. *Depth pays less than width.*
- ~~**NEXT 1**: explain `no_death +5059`.~~ **RETIRED 2026-08-17 (C21, H5) — DONE
  as G25**, recorded as DISCHARGED 200 lines above this line in the same file.
  §12.5 violation 4 of 4, and the only one in the AGENT-2 block; retired by
  AGENT-1 because this file is AGENT-1's journal under H10, and left standing it
  would have cost that lane a cycle on its next restart.
- **NEXT 2**: read `elders/hyperon-miner` before writing another statistic.
  Surprisingness subtracts the chance-structure baseline *inside* the measure;
  the 500-shuffle null estimates the same baseline afterward and is why p is
  floor-limited at 1/501. If surprisingness is usable the null stops being
  load-bearing.
- **NEXT 3**: differential-test the hand-rolled miner against
  `elders/hyperon-miner` on one corpus. This is the only defence against a
  shared bug that quorum structurally cannot see, and it converts 13 spikes of
  parallel reimplementation from an accident into implementation diversity.
- **NEXT 4**: external yardstick — filtered MRR / Hits@1,3,10 on FB15k-237
  instead of top-12 mean held-out confidence. Standard protocol, published
  baselines (AMIE / RuleN / AnyBURL), and it removes the custom statistic that
  a degree-preserving shuffle reproduces 74% of.

- **Elder debt flagged by CLIENT-3, livechat 686-760**: `popper` (0 refs) is an
  ILP system and agent-2 named "the ILP move" independently; `hyperon-miner`
  (2 refs) ships *surprisingness* scoring, which subtracts the chance-structure
  baseline inside the statistic instead of estimating it with 500 shuffles;
  `metta-chaining` and `pln-hyperon` are both 0 refs. No elder covers
  interactive dispute (Cartesi / Arbitrum Nitro / Cannon / Truebit) and
  BLOCKED.log records that S4's bisection was designed from a paper because
  there was nothing to read.

## Harness — use these, they are files not heredocs
`spikes/harness/`: `provenance.py` (repo state + artifact digest + **mtime vs
source staleness**, controls must persist observations), `power.py`
(permutation floor), `canon.py`, `bansurface.py`, `admission.py` (REFUTED as a
gate, kept as a linter).
Known-provenance binaries: `spikes/S30_speed_duel/bin/known/`. The old
`fuelrun.v2.*` were built before every patch — **both agents were burned by
them** (A24).

## Guardrails added this session
A16 (pair the arms) · A17 (claim decay + `pushed_at` is not last commit) ·
A18 (one point is not a rate) · A19 (record re-derivable pre-run state) ·
A20 (controls live in the artefact; a null must be able to contain the effect) ·
A21 (a test must be able to express its verdict) · A22 (a party must not supply
the input to a check on itself) · A23 (the instrument perturbs what it observes) ·
A24 (a digest pins which artifact, not what is in it) ·
**A25 (an ablation that removes more than it names cannot measure the named
part** — G24's `no_death` also removed uniform-parent-choice, `MAX_POP`, and
every use of the importance balance, so "carrying capacity is what makes fitness
differential" was measured against a baseline with no fitness at all. Check what
an `if flag:` guard actually gates before naming the arm after one of them.) ·
**A26 (a knob is not a mechanism** — a difference between arms is only about the
mechanism if the constants around it were measured, not chosen. G25's coverage
gap was 51–85% `WAGE_POOL`, a number picked by hand.)
 ·
**A27 (a hold-out drawn from one end of the key order is not a sample of the key
space** — shuffle before splitting. S73's scaling arm took the lexicographic tail
as probes and the lexicographic prefix as base, so every probe diverged at the
root and single-insert cost read **293 B flat across a 10× space range**. The
flatness looked structural; it was the cost of inserting *outside* the occupied
range, and the real figure is 6× larger.) ·
**A28 (an enforcement field that is recorded but never read is documentation** —
`provenance.py` stored `null_must_contain` for the whole project without ever
checking it, and `deps=()` silently disabled the entire staleness path. Same
class as A26's hand-picked constant: it looks like a mechanism from the outside.)
 ·
**A29 (a probe that cannot show it reached its target has produced no evidence** —
ATTACK cycle 4's A4 probe aimed at two unreachable branches, was blocked from
reaching them *by the very bug it was hunting*, and reported SURVIVES on a clean
null. "No FATAL" from a probe that missed is not a pass. Reaching the target is a
precondition of the verdict, not a detail of it.)
 ·
**A30 (a name grep cannot tell a word from a concept** — S75's control searched
`fn (prove|verify|proof|witness)` in `pathmap`, matched 14 Rust *borrow* witnesses
(`-> Self::WitnessT`, several `-> ()`), and therefore did not fire. Test the
property, not the vocabulary: "depends on no cryptographic hash" cannot collide on
a name, and it settled the same question in one line.)
