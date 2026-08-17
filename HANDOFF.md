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

## Loop state — READ THIS
The Stop hook (`.claude/hooks/loop_gate.sh`) was **inert for the whole first
session**: settings lived in `~/kingfisher/.claude/settings.json` but the
session project dir is `spikes/S51_multicore`, which had no `.claude/`.
`CLAUDE_PROJECT_DIR` was unset so the `$(pwd)` fallback would also have missed.

Fixed: `spikes/S51_multicore/.claude/settings.json` now registers the hook by
absolute path, and `ROOT` is pinned inside the script. **`settings.json` binds
at session start, so this takes effect on the next restart.** Until then use
`ScheduleWakeup` each turn as the re-entry mechanism.

To stop legally: write exactly `LOOP-DONE` / `LOOP-HALT` / `LOOP-IDLE` into
`.loop_signal`. Human kill switch: `touch STOP`.

## State of the M1 chain — complete, correctly refusing, verified 2026-08-17 10:2x
```
admission REFUSED 2 (flip, fileio) -> 65 CIDs -> 5 preflight sessions
  -> host-arm64 + host-x86_64 + phone -> canon_alpha -> quorum-3
65/65 agreed 3/3 byte-identically.  Verdict INSUFFICIENT_DOMAINS x65, accepted 0/65.
binary 3 | manifest 1 (binding) | host 2 | os 2 | isa 2 | operator 1 (binding)
```
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
- **NEXT 1**: the **retro-fit D6 owes** — Q1, S72, N1, W4, B1 each cite "per D6"
  with no `provenance.json` beside them (W1 is INVALID already, skip it). Either
  record one or drop the citation. This is D6's own consequence 2 and the F2
  falsifier currently reads 6/6 failing, i.e. the standard is decorative
  everywhere it appears. Cheap, load-insensitive, and it stops the newest spec
  from being the least honoured one.
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
