# WORK_QUEUE — Kingfisher continuous mode
Status: OPEN | CLAIMED <agent> | DONE | BLOCKED | PARKED | GATED(<what>)
Seeded from MISSION_LOOP.md §4, 2026-08-17.

## P0 — freeze gate (written specs, <=2 pages, falsifiable)
| id | item | status |
|---|---|---|
| D1+ | seat-draw spec | **DONE** — `specs/D1_seat_draw.md`, 5 falsifiers, F5 live pending W3 |
| D2 | canonical result serialization | **DONE** — `specs/D2_canonical_result.md`; 3 classes, 4 upstream exclusions, 5 falsifiers, F5 (canonicalization hiding divergence) flagged as the danger direction |
| D3 | economics as FORMULAS | **DONE** — `specs/D3_economics.md`; no constant derived from Δ, feasibility bound only |
| D5 | ban-surface closure | **DONE** — `specs/D5_ban_surface.md`, v1 surface + 5 falsifiers; F3 unrun, cfg-gate aspirational |

## P1 — verification substrate
| Q1 | quorum simulator: fleet model × canonical envelope × majority adjudication | **DONE** — `spikes/Q1_quorum_sim/`, code+seed+2 firing controls. C4 quantified |
| id | item | status |
|---|---|---|
| W2 | witnessed re-exec on the trie substrate; non-membership via authenticated ordered structure; code+seed+controls | **DONE** — `spikes/W2_witnessed_trie/`. Membership + **non-membership** + **completeness** over a Merkle-committed radix-256 trie, with a verifier that returns False; 9 controls, all fire. Absence provable at **~2.0 KB** (deep miss; the 107 B random-miss figure is corpus arithmetic, `C_miss_depth` guards the substitution). Aligned `(p s ?o)` witness **0.05× shard**, auth path 1.5–2.4 KB **independent of answer size**; `(?p s o)` is exactly **1.00×** — never worth witnessing. Caught myself publishing an accidental cross-shard agreement (2541 vs 2474 B) whose halves moved in opposite directions. Does NOT rescue the prefilter (W4 stands); verifiable job class = trie-only queries |
| D4 | no recoverable subject — absent from `specs/`, never a queue row, in no DECISIONS entry. Evidence says numbering gap (D2 self-describes as "Last P0 freeze-gate item"; entry 81 lists D1+/D3/D6) | **BLOCKED_ON_HUMAN** — `proposed/D4_slot_candidates.md`, 4 rows + recommendation. Not agent-decidable: §7 makes it my own exit condition, so deciding it is A22 |
| D6 | discipline standard: no result without code+seed+controls | **DONE** — `specs/D6_discipline.md`. Enforcer named clause by clause (E1–E8 in `harness/provenance.py`), holes named (H1–H5), 5 falsifiers of which **2 KNOWN-FAILING at birth** (F1 vacuity, F5 number-not-in-artefact). F2 measured: 6 RESULT.md cite D6, **0** have a provenance.json; 4 of 89 spikes have one |
| — | **retro-fit owed**: Q1, S72, N1, W4, B1 cite D6 with no provenance record (W1 is INVALID already). Either record one or drop the citation | OPEN — consequence 2 of D6 |
| S73 | canonical **space** state at an epoch boundary; verifiable epoch deltas | **DONE** — `spikes/S73_epoch_commitment/`. 66 epochs over the real 67-program corpus chain and verify; a verifier **computes** `root_N+1` by folding `root_N` forward from the additions alone. **1,150 B per added atom batched / 1,770 B isolated** (12x space = 2.27x proof); epoch cost is **~1-2 recomputed nodes per added atom**, O(added) not O(space). XOR-of-hashes null gives the same O(k) delta and is **forged in one line** (`a^a=0`, declare an atom twice); its absence proof has no bytes to be made of (32 B vs the trie's 257 B). **Root commits to STATE, not history** — two epoch groupings reach the same root; history binding needs a `(root, delta)` chain, not built. 11 controls, all fire. Does NOT unblock bisection: interpreter state stays RED per S68 |
| W3 | ~~witness sizes under non-aligned access~~ | **CANCELLED** — premise falsified by S52 (0.2/1.0/8.8% measured vs W1's 7.7/100/100%). The 0.9× pathology is also an artefact: fixing the multiproof and the short final chunk gives exactly 1.000× |
| **W4** | **read set of the HDC prefilter: what is it, and can it be sublinear without invalidating S52's timings?** The engine scores every bundle on every query. **Verification eligibility cannot be decided before this.** Highest priority in P1 | **DONE** — `spikes/W4_prefilter_readset/`. Read set is 100% by construction (similarity search has no key order to skip). 78.59× amplification measured but it is oracle-fitting harness, outside S52's timed region. Witness 1.5–12.2 MB. Residency coupling NOT cut |

## P2 — M1 integration (the demo path)
| id | item | status |
|---|---|---|
| M1.1 | Android app skeleton (16 KB pages, pointer-tagging manifest, foreground dataSync budget) | **PARTIAL** — APK builds, installs, runs; `libhyperonc.so` 6.43 MiB loads in-process in 1.34 ms; **16 KB alignment verified 0x4000 on all LOAD segments** (S2 open item 3 closed). **Settles the preflight number at 98.47 us — 356x cheaper than M1.3's published 35.1 ms, 0.14% of a job.** **MeTTa now RUNS in-process**: `(+ 1 2)`->`3`, `(intersection-atom (A B C) (B C D))`->`(B C)`, 11.23 ms, **byte-identical to native `fuelrun` on the same device** (new axis: runtime host, not ISA). Found: `libhyperonc.so` has **no SONAME** (bakes the host build path into `DT_NEEDED`; fixed with `-Wl,-soname`). **WorkManager worker DONE**: runs MeTTa in-process (16.6 ms), refusal path proven. Found **SCHEDULER_SPEC 2 does not build** — rules 4+5 mutually exclusive (`Cannot set backoff criteria on an idle mode job`); spec corrected. **OPEN: process-per-job conflicts with WorkManager's process reuse** — largest open M1 issue. Blocker confirmed: `hyperonc` has no `[features]` block so the 4.00 MiB minimal build needs an upstream cfg-gate | 
| M1.3 | charge-time worker: WorkManager charging+idle+UNMETERED, checkpointed chunks | **PARTIAL** — in-worker preflight residue built and tested (24 assertions), session-gated dispatch wired into M1.8, refusal proven at session 0 and mid-run (32 dispatched, 32 completed, none lost). **CORRECTED**: the 35.1 ms was adb+dumpsys, i.e. the harness. Native sysfs read measures **8.4 us** — 4,180x cheaper — so per-job preflight IS viable and S6 marks it *Residue: yes*, i.e. required. Session gating in q3.py is a harness accommodation, not a design finding. True binder cost still unmeasured (needs M1.1). WorkManager/Kotlin half blocked on M1.1; `onStopped()` checkpointing blocked on the S68 state commitment. `spikes/M1_3_worker/` |
| M1.5 | shard store on iroh-blobs (BLAKE3 verified ranges — same proofs W1 uses) | **DONE, WITH A DEVIATION** — built as sha2-256 + sqlite LRU, stdlib only, not iroh-blobs/BLAKE3. Cold 173.5 KiB to device, warm **0 bytes**, phone median 109.0 -> 68.8 ms; 22 invariant assertions. `spikes/M1_5_shardstore/`. **The deviation needs revisiting:** the row justified BLAKE3 verified ranges as *"the same proofs W1 uses"* and W1 is INVALID, so that reason is dead — but `REPORT_Golem_clay_verification.md` supplies a NEW one. Requestor-side spot-checking audits a random RANGE, and verified ranges are exactly the primitive that lets a verifier check part of a blob without fetching all of it. Whole-blob sha2-256 cannot do that. Re-open if the Golem-style audit is adopted | 
| M1.7 | transport phone↔coordinator on iroh | **DONE** — phone dials out over HTTP, 66/66 byte-identical to host, loopback-only bind + `adb reverse` so no network surface. Miss control caught a fabricated-envelope bug (`curl -s` on 404). `spikes/M1_7_transport/` |
| M1.8 | quorum-3 pipeline end to end; first 1 phone + host as 3 processes | **DONE** — 66/67 unanimous, 3 processes / 2 OSes; the 1 refusal is `(flip)`, the corpus's own positive control. Not a trust-independent quorum (2 of 3 are the same binary on one host). `spikes/M1_8_quorum3/` |

## P3 — measurements
| N1 | ~~re-derive the ~50 µs prefilter cost~~ **DONE** — `spikes/N1_prefilter_cost/`, 23.9 µs at T=3, 8.7% of query. Amdahl rung restored |
| ~~N1-old~~ | superseded from a kernel profiled against the roof, 4 workers, background cpuset. The only rung that could still carry the NPU descope alone, and it inherits S18's artifact. **Device gate open** | OPEN — high |
| B1 | bundling compression vs recall, real KG | **DONE** — `spikes/B1_bundling_real/`. B=16 fits VTCM at p90 0.2%. Code shipped |
| id | item | status |
|---|---|---|
| C2 | per-device supply under gate | DONE — S71, 2.83/11.17 jobs/s |
| C3 | packed popcount on deployable cpuset | DONE — S72, 15.2× short, prediction wrong by 6.3× |
| L1 | oflineAI logits byte-compare, fixed extractor, 2 runs 1 device then 2 devices | OPEN — needs 2nd device for the second half |

## P5 — G-series (agent-2 lane)
| id | item | status |
|---|---|---|
| G24 | evolving rule population, six arms | **DONE** — `spikes/G24_population/`. Verdict NOT DOMINATED, precision 0.0355 flat, coverage +218%. **Three "why" statements corrected 2026-08-17 by G25; see its changelog** |
| G25 | explain `no_death +5059`: real tradeoff or rent calibration artefact? | **DONE** — `spikes/G25_carrying_capacity/`, 16 runs, 3 seeds on the 3 headline configs, 4 controls, `provenance.json ok=true`. **Both, and neither is about death.** G24's `no_death` arm contains **no selection at all** (nothing removed, `MAX_POP` unused, parents uniform, `imp` read only by death) so it never was "full minus carrying capacity". The missing 2×2 cell `no_death+no_abduct` gets **1514** correct at pop 531 vs `no_death`'s 6361 at 557 — at matched population with selection absent both sides, **abduction is worth 4847 and volume ~155**, so G24's "coverage rises with population size almost mechanically" is measured false. Keeping death and raising `WAGE_POOL` alone closes **51–85%** of the gap (3 seeds) at 2.6× fewer predictions and 2.5× the precision; +1753, disjoint ranges, exact permutation p=1/20=0.050 (the floor at n=3). **ECAN belongs as a precision mechanism, not as a coverage cost.** HOLE: selected-557 vs unselected-557 is unreachable — the dial saturates at pop ~239 (40× pool → 2.17× pop), so this rests on a trade, not a dominance |
| G26 | does `ROUNDS` reach a selected population of 557 where `WAGE_POOL` saturates? Closes G25's hole and gives the dominance test | OPEN — highest in this lane |
| G27 | differential-test the hand-rolled miner against `elders/hyperon-miner` on one corpus; the only defence against a shared bug quorum cannot see | OPEN |
| G28 | external yardstick: filtered MRR / Hits@1,3,10 on FB15k-237 against AMIE / RuleN / AnyBURL, replacing top-12 held-out confidence | OPEN |
| G29 | read `elders/hyperon-miner` surprisingness before writing another statistic — it subtracts the chance-structure baseline *inside* the measure, which would retire the 500-shuffle null and its 1/501 p-floor | OPEN |

## P4 — drafts for the human (proposed/ only, never post)
| id | item | status |
|---|---|---|
| U1 | hyperon nondeterminism PR text + minimal patches, final form | DONE — proposed/hyperon-nondeterminism/ |
| U2 | MORK issue-#2 comment, final form | OPEN |
| U3 | buyer one-pager: auditable on-device agents | OPEN |
| U4 | Deep Funding proposal refresh with current evidence grades | OPEN |

## Watchers
- host quiet.sh: REFUSED (11 containers, another project's). Recheck each cycle.
- device quiet.sh: OPEN.
- W1 attacker: live. W3 blocked on its verdict.
| M1.9 | QUIC transport | **EVALUATED, DEFERRED** — attacks the fixed cost, which is 27% and falling at deployable shard sizes (M1.5b: 63.2 ms + 37.9 MB/s); batching already gives **38x** in the regime where fixed cost dominates. Real wins are connection migration across WiFi/cellular and the TLS we entirely lack. Cost: Cronet adds several MB to a phone APK. **Adopt when** devices are seen changing network mid-job, or shards drop into the fixed-cost regime without pre-staging. `analysis/TRANSPORT_QUIC.md` |

## H — harness (added 2026-08-17 by CLIENT-3 per MISSION_LOOP §12.1)
The loop machinery is a first-class artifact under D6. It had no queue rows and
no tests while being the only thing between the fleet and a silent stall.
| id | item | status |
|---|---|---|
| H1 | Stop hook enforceable as written; per-lane signals; exit marker the launcher can read | **DONE** — `loop_gate.sh` v3, `spikes/harness/test_loop_gate.sh` 15 checks pass |
| H2 | launcher must not end a lane on prose; backoff; hang watchdog | **DONE** — `run_loop.sh` v2, 4 numbered defects in its header. **Live wrappers still run v1 (bash parsed at spawn); needs a STOP/relaunch cutover** |
| H3 | §11 publishing rail cited by 7 files never existed; §10 split so every citation resolves | **DONE** — MISSION_LOOP §11 |
| H4 | mechanical reference resolver: every §N / spec / file citation in the harness must resolve, per §12.4 | OPEN — the D1–D6 and §11 defects were both this class, found by eye |
| H5 | journal self-contradiction check: nothing in both a DONE list and a NEXT list, per §12.5 | OPEN — HANDOFF NEXT 1/2 were DONE above them |
| H6 | external liveness alarm — a lane dead for an hour is currently silent | OPEN — `launchd` KeepAlive per lane is the native form; `.heartbeat.$CALLSIGN` now exists to watch |
| H7 | first ATTACK cycle aimed at the harness rather than a spike, per §12.8 | OPEN |
