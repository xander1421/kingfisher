# HANDOFF — BUILDER-1, 2026-08-17

## Claims released
D1+, D5, D3 — all DONE. No live claims. `CHANNEL.md` is current.

## Cycles this session
1. **D1+** seat-draw spec → `specs/D1_seat_draw.md`
2. **D5** ban surface → `specs/D5_ban_surface.md`
3. **D3** economics → `specs/D3_economics.md`
4. **ATTACK** — broke two of the three above, both fixed in place:
   - D1+ R4 penalised any non-responding device. An honest charge-time device at
     duty 0.05 is offline **95%** of the time, so honest participation was
     net-negative. Replaced with two-phase offer/ack (Acurast
     `propose_matching`→`acknowledge_match`); penalty attaches to the ack.
   - D5 is only **2/5 enforceable today**: `das` and Python bindings are
     cfg-gated; `math.rs`, `fileio` and `random` have **zero** `cfg(feature`
     lines. `BAN_SURFACE_V1` is not shippable. → HUMAN_NEEDED #6.

## Also landed earlier this session
- **S71 (C2)**: per-device supply **2.83 jobs/s** 1-worker, **11.17** at 4,
  measured behind a green device gate. Replaces the INVALID 2.87 projection.
- **S72 (C3)**: packed popcount on the deployable cpuset. Exactness perfect
  (`f4e64fb7d70b9b0c`); throughput **15.2× short** vs my predicted 2.4× —
  wrong by 6.3×, and it argues **against** my own NPU descope.
- **W1**: witnessed re-execution. Witness ~4.2 KB flat in shard size (712× at
  3 MB). Kills S69's 1,500× traffic objection.
- **quiet.sh --device** added after finding every device measurement in the
  workspace had run ungated. Two false positives fixed in it.

## Gates
- host `quiet.sh`: **REFUSED** — 11 containers from another project. Not ours to stop.
- device `quiet.sh --device`: **OPEN**.

## Next 3 items
1. **W4** prefilter read set — now top of P1. The gating question above. Start
   by instrumenting `realkg.c` to count bundles scored per query; then ask
   whether any index makes it sublinear *without* changing the timings S52
   published on the linear version.
2. **D2** canonical result serialization per job class — last P0 freeze-gate
   item. Load-insensitive; links the hyperon nondeterminism drafts and must
   state Tier-A exclusions pending upstream.
3. **M1.8** quorum-3 pipeline as 3 host processes — the first M1 item that
   needs no second device and no open gate.

## Watcher notes — RESOLVED, and badly
- **The W1 attacker reported. W1 is INVALID.** `witness.py` modelled a
  clustered-index engine that does not exist: `S52/realkg.c:184` scores every
  bundle on every query, so the read set is **100% of the prefilter index**.
  Corrected witness **1.54–12.23 MB, not 4.4 KB**. Plus a unit error (12.8 MB is
  a B=8 index over 800k triples) and **four controls, none able to fail**.
- **W3 cancelled** — its premise is falsified by S52 on the identical corpus:
  measured 0.2 / 1.0 / 8.8% store checked against W1's 7.7 / 100 / 100%.
- **The consequence is the important part.** The S69/S70 *diagnosis* — eligibility
  coupled to residency — still stands. **The fix does not.** Residency coupling
  is not cut, the fleet-wide verification pool is not restored, and **C4's
  rare-shard attack is live again.**
- `L1` needs a second physical device for its cross-device half.

## The gating question now (W4, top of P1)
> **What is the read set of the HDC prefilter, and can it be made sublinear
> without invalidating S52's timings?**

The engine scores every bundle on every query. Nothing about verification
eligibility can be decided before this is measured — and note the trap: building
a clustered-index engine to make the read set small would invalidate S52's
timings, which were measured on the linear prefilter.

## Standing caution
Shard demand (`Δ`) is unmeasured **and unmeasurable from inside this
workspace** — S52's generator samples uniformly, an artefact. Per D3, no
coverage target, replication floor or Sybil cost may be given a number until a
real query stream exists. The buyer is the missing instrument.
