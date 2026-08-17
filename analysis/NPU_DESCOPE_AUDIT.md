# NPU descope — audit, 2026-08-17. The ladder no longer holds it up.

I descoped the NPU on a "ladder" argument stated as independent of throughput.
Three measurements and one verification later, most of the ladder is gone. This
records that rather than defending the decision.

## The ladder, rung by rung

| rung | status now |
|---|---|
| **No QNN redistribution licence question** | **GONE — verified.** `~/alex/oflineAI` contains **zero** QNN/QAIRT files. The APK ships `libggml-htp-v73/75/79/81.so` — ggml's own HTP skels, MIT, built from source. Vendor libs are **declared** via `uses-native-library` (`libcdsprpc.so`, `libadsprpc.so`, `libOpenCL.so`) — device-resident, loaded from the system, **not redistributed**. Redistribution was the entire objection |
| **No vendor SDK / no delegate integration** | **Largely gone.** `ggml-hexagon` *is* the delegate and it is MIT. oflineAI has already built the skels and shipped them — the integration cost I cited as unpaid is paid |
| **The prefilter is only ~50 µs, so Amdahl caps the win** | **Compromised.** The workspace's own note: this figure *"inherits S18's overhead artifact and should be re-derived from a kernel that has been profiled against the roof."* It is also single-core, like S72's 15.2× was |
| Quantisation scale pinning | **Stands.** S12's 46% silent recall loss and S31's recall 0/8 are measured. A real hazard — but an engineering hazard with a known rule (S31: scale ≥ 2·nnz(Q)/126), not a blocker |
| Cross-vendor requantisation unmeasured | **Stands** — but it is an *unknown*, not an objection |
| No HVX popcount kernel exists | **Stands** — a cost, not an argument |

## And the evidence has moved the other way three times

| finding | effect |
|---|---|
| **S72b** — kernel is bandwidth-bound at 4 workers, 5.7× short of the roof (per-instance 329 → 220 GOP/s) | bandwidth bounds are what on-chip memory fixes |
| **B1** — B=16 puts an 800k shard at **6.41 MB**, inside 8 MB VTCM, at p90 0.2% store checked | the residency premise, previously unmeasured, **holds** |
| **oflineAI** — 700 t/s prefill on HTP0 v79, this exact silicon, shipping | the NPU is not hypothetical here; it is running |

## Honest verdict
**The descope is no longer supported by the argument that justified it.** What
remains is one measured hazard with a known mitigation (scale pinning), one
unknown (cross-vendor requantisation), and one unpaid cost (no HVX kernel). None
of those is the reason I gave.

The correct disposition is **not** "revive the NPU" — that would be the same
reflex in the other direction, and A12 warns that a removal justified by a
measured replacement is safe while one justified by an assumed replacement is
not. It is: **the descope is now a resource-allocation decision, not a technical
conclusion, and it should be labelled as one.**

## What would settle it, in priority order
1. **Re-derive the ~50 µs** from a kernel profiled against the roof, at 4
   workers, on the background cpuset. The Amdahl argument is the only rung that
   could still carry the decision alone, and it is currently inherited from an
   artifact. Device-side, gate is open.
2. **Cross-vendor requantisation bit-exactness** — the one genuine unknown, and
   the thing that decides whether NPU results are Tier-A verifiable at all.
3. An HVX popcount kernel, which is the cost, and should not be paid before 1
   and 2.

## Process note
This audit exists because a human pointed out that the QNN licence rung was
already dead — solved by oflineAI's move to open packages — and I had gone on
citing it. **A ladder argument is only as good as its most recently checked
rung**, and I had not re-checked any of them since writing it.
