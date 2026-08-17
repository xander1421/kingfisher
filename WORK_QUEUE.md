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
| W2 | witnessed re-exec on the trie substrate; non-membership via authenticated ordered structure; code+seed+controls | OPEN |
| W3 | ~~witness sizes under non-aligned access~~ | **CANCELLED** — premise falsified by S52 (0.2/1.0/8.8% measured vs W1's 7.7/100/100%). The 0.9× pathology is also an artefact: fixing the multiproof and the short final chunk gives exactly 1.000× |
| **W4** | **read set of the HDC prefilter: what is it, and can it be sublinear without invalidating S52's timings?** The engine scores every bundle on every query. **Verification eligibility cannot be decided before this.** Highest priority in P1 | **DONE** — `spikes/W4_prefilter_readset/`. Read set is 100% by construction (similarity search has no key order to skip). 78.59× amplification measured but it is oracle-fitting harness, outside S52's timed region. Witness 1.5–12.2 MB. Residency coupling NOT cut |

## P2 — M1 integration (the demo path)
| id | item | status |
|---|---|---|
| M1.1 | Android app skeleton (16 KB pages, pointer-tagging manifest, foreground dataSync budget) | **PARTIAL** — APK builds, installs, runs; `libhyperonc.so` 6.43 MiB loads in-process in 1.34 ms; **16 KB alignment verified 0x4000 on all LOAD segments** (S2 open item 3 closed). **Settles the preflight number at 98.47 us — 356x cheaper than M1.3's published 35.1 ms, 0.14% of a job.** **MeTTa now RUNS in-process**: `(+ 1 2)`->`3`, `(intersection-atom (A B C) (B C D))`->`(B C)`, 11.23 ms, **byte-identical to native `fuelrun` on the same device** (new axis: runtime host, not ISA). Found: `libhyperonc.so` has **no SONAME** (bakes the host build path into `DT_NEEDED`; fixed with `-Wl,-soname`). **WorkManager worker DONE**: runs MeTTa in-process (16.6 ms), refusal path proven. Found **SCHEDULER_SPEC 2 does not build** — rules 4+5 mutually exclusive (`Cannot set backoff criteria on an idle mode job`); spec corrected. **OPEN: process-per-job conflicts with WorkManager's process reuse** — largest open M1 issue. Blocker confirmed: `hyperonc` has no `[features]` block so the 4.00 MiB minimal build needs an upstream cfg-gate | 
| M1.3 | charge-time worker: WorkManager charging+idle+UNMETERED, checkpointed chunks | **PARTIAL** — in-worker preflight residue built and tested (24 assertions), session-gated dispatch wired into M1.8, refusal proven at session 0 and mid-run (32 dispatched, 32 completed, none lost). **CORRECTED**: the 35.1 ms was adb+dumpsys, i.e. the harness. Native sysfs read measures **8.4 us** — 4,180x cheaper — so per-job preflight IS viable and S6 marks it *Residue: yes*, i.e. required. Session gating in q3.py is a harness accommodation, not a design finding. True binder cost still unmeasured (needs M1.1). WorkManager/Kotlin half blocked on M1.1; `onStopped()` checkpointing blocked on the S68 state commitment. `spikes/M1_3_worker/` |
| M1.5 | shard store on iroh-blobs (BLAKE3 verified ranges — same proofs W1 uses) | **DONE, WITH A DEVIATION** — built as sha2-256 + sqlite LRU, stdlib only, not iroh-blobs/BLAKE3. Cold 173.5 KiB to device, warm **0 bytes**, phone median 109.0 -> 68.8 ms; 22 invariant assertions. `spikes/M1_5_shardstore/`. **The deviation needs revisiting:** the row justified BLAKE3 verified ranges as *"the same proofs W1 uses"* and W1 is INVALID, so that reason is dead — but `REPORT_Golem_clay_verification.md` supplies a NEW one. Requestor-side spot-checking audits a random RANGE, and verified ranges are exactly the primitive that lets a verifier check part of a blob without fetching all of it. Whole-blob sha2-256 cannot do that. Re-open if the Golem-style audit is adopted | 
| M1.7 | transport phone↔coordinator on iroh | OPEN |
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
