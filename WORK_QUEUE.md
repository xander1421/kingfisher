# WORK_QUEUE — Kingfisher continuous mode
Status: OPEN | CLAIMED <agent> | DONE | BLOCKED | PARKED | GATED(<what>)
Seeded from MISSION_LOOP.md §4, 2026-08-17.

## P0 — freeze gate (written specs, <=2 pages, falsifiable)
| id | item | status |
|---|---|---|
| D1+ | seat-draw spec | **DONE** — `specs/D1_seat_draw.md`, 5 falsifiers, F5 live pending W3 |
| D2 | canonical result serialization | OPEN — next |
| D3 | economics as FORMULAS | **DONE** — `specs/D3_economics.md`; no constant derived from Δ, feasibility bound only |
| D5 | ban-surface closure | **DONE** — `specs/D5_ban_surface.md`, v1 surface + 5 falsifiers; F3 unrun, cfg-gate aspirational |

## P1 — verification substrate
| id | item | status |
|---|---|---|
| W2 | witnessed re-exec on the trie substrate; non-membership via authenticated ordered structure; code+seed+controls | OPEN |
| W3 | witness sizes under non-aligned access; quantify the 0.9× pathology; grade shaping-as-verification | OPEN — attacker live on W1, wait for verdict |

## P2 — M1 integration (the demo path)
| id | item | status |
|---|---|---|
| M1.1 | Android app skeleton (16 KB pages, pointer-tagging manifest, foreground dataSync budget) | OPEN |
| M1.3 | charge-time worker: WorkManager charging+idle+UNMETERED, checkpointed chunks | OPEN |
| M1.5 | shard store on iroh-blobs (BLAKE3 verified ranges — same proofs W1 uses) | OPEN |
| M1.7 | transport phone↔coordinator on iroh | OPEN |
| M1.8 | quorum-3 pipeline end to end; first 1 phone + host as 3 processes | OPEN |

## P3 — measurements
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
