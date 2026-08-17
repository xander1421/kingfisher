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
1. **D2** canonical result serialization per job class — last P0 freeze-gate
   item. Load-insensitive; links the hyperon nondeterminism drafts and must
   state Tier-A exclusions pending upstream.
2. **W3** witness sizes under non-aligned access — quantify W1's 0.9×
   pathology, grade the shaping-as-verification claim. **Was blocked on the W1
   attacker; check `CHANNEL.md` and the task notification for its verdict
   before starting, and fold its findings in.**
3. **M1.8** quorum-3 pipeline as 3 host processes — the first M1 item that
   needs no second device and no open gate.

## Watcher notes
- An adversary was launched against **W1** and had not reported when this
  session wrapped. Its verdict must be folded into W1 *and* W3 before either is
  built on. W1 is currently load-bearing (it revived the fleet-wide
  verification pool and gave wedge #2 its second justification) and was
  self-verified — the same pattern that killed S69/S70.
- `L1` needs a second physical device for its cross-device half.

## Standing caution
Shard demand (`Δ`) is unmeasured **and unmeasurable from inside this
workspace** — S52's generator samples uniformly, an artefact. Per D3, no
coverage target, replication floor or Sybil cost may be given a number until a
real query stream exists. The buyer is the missing instrument.
