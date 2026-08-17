# HANDOFF — write-ahead checkpoint (agent-1 lane)

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
- **NEXT 1**: **re-encode atom keys to fixed-width interned ids and re-measure.**
  S75 localised the 18.4× to key length, and FB15k triples at 12 B come out at
  2.4×, so the regime that works is known. Intern each symbol to a 4-byte id, keep
  the arity framing, re-run S73 and S75. This is the one change that would move
  S73's ~33 KB back toward its published 1,770 B, and it is load-insensitive.
  Falsifier to state first: if interning does not bring the pathmap depth ratio
  under 10×, the cause is not key length and S75's mechanism claim is wrong.
- **NEXT 2**: **history binding for the epoch chain** — S73 proved the root
  commits to state and *not* to the path taken to it. A `(root, delta)` chain
  hashed together is what makes an epoch SEQUENCE evidence. Small, and it is the
  gap S73 named rather than papered over. (D6 is DONE; D4 is BLOCKED_ON_HUMAN —
  neither is a NEXT any more.)
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
- **NEXT 1 (this lane): G26** — turn `ROUNDS`, not `WAGE_POOL`, and see whether a
  *selected* population reaches 557. That is the dominance test G25 could not
  run, and it closes the only hole in it.
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
- **NEXT 1**: explain `no_death +5059`. Removing the finite economy gets MORE
  coverage than the full system. The verdict handles it by scoring correctness
  per assertion, which is right, but "the mechanism I added to make fitness
  differential also costs 44% of coverage" is either a real tradeoff or a rent
  calibration artifact, and which one it is decides whether ECAN belongs in the
  loop at all. It is the one arm whose sign is opposite to its design intent.
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
