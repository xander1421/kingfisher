# ELDERS, ROUND 2 — the identical project, and the NPU answer

Ten repos cloned that the original manifest missed. Every licence read from the
file on disk, not from an API. The pattern worth naming first:

**The original manifest sampled systems that were *analogous* to ours (BOINC,
Golem, Akash — volunteer computing, compute marketplaces) and missed the one that
is *identical*.** Acurast is this project's thesis, in production, on 260,000+
phones. It should have been elder #1, not #21.

## Licence gate — §7 classification

| repo | licence | verified how | class |
|---|---|---|---|
| **acurast-substrate** | **Unlicense** (public domain) | `LICENSE`, text runs to `unlicense.org` | **PORT**, no attribution even required |
| acurast-core | MIT | `LICENSE.md`, verbatim MIT body, untitled | PORT |
| acurast-kotlin-sdk | MIT | `LICENSE` | PORT |
| executorch | BSD-3-Clause | `LICENSE` + `pyproject.toml: license = {text = "BSD-3-Clause"}` | PORT |
| llama.cpp | MIT | `LICENSE` | PORT |
| prime | MIT | `LICENSE` | PORT |
| bacalhau | Apache-2.0 | `LICENSE` | PORT |
| iroh | Apache-2.0 / MIT dual | `LICENSE-APACHE`, `LICENSE-MIT` | PORT |
| torchhd | MIT | `LICENSE` | PORT |
| acurast-docs | — | prose, not code | reference |

**Zero copyleft, zero UNKNOWN.** The original 21 gave us two copyleft elders
holding the operational wisdom (BOINC, Golem) and one UNKNOWN blocking the fastest
engine (MORK). This round has no such friction, and `acurast-substrate` is the most
permissive result the gate can return.

---

## 1. GAP row 6 is falsified. The NPU was never the biggest unknown.

`GAP_MATRIX` row 6 reads *"**Nothing in any elder targets a phone NPU.**"* and
rates it **BUILD / M**, *"the single biggest unknown in the plan."*

`pytorch/executorch`, BSD-3, pushed today, `backends/qualcomm/serialization/qc_schema.py:62,93`:

```python
SM8750 = 69  # v79
...
QcomChipset.SM8750: SocInfo(QcomChipset.SM8750, HtpInfo(HtpArch.V79, 8)),
```

That is **our exact SoC** — the Galaxy S25 Ultra's SM8750 — with its HTP
architecture (v79) and VTCM size declared. The backend links
`libQnnHtp.so`, `libQnnHtpV*`, `libQnnSystem` directly (101 references to
`QNN_SDK_ROOT`), **bypassing NNAPI entirely** — which is precisely the route S31
concluded was the only one available after finding NNAPI exposes no accelerator on
this chip. S31 got the diagnosis right and then we filed the cure under BUILD.

**It also independently confirms our hardest NPU constraint.**
`qc_schema.py:36` declares `vtcm_size_in_mb: int = 0`, so `HtpInfo(HtpArch.V79, 8)`
means **VTCM = 8 MB on SM8750**. `LEDGER` lists *"VTCM is 8 MB vs a 12.8 MB packed
store — it does not fit"* under NEVER MEASURED. It is no longer a datasheet
reading; it is a constant in a vendor-tracking production repo.

> Row 6 becomes **PORT / S-to-M**, not BUILD / M. The remaining unknown is narrow
> and specific: whether HVX gives us a wide popcount, and whether an 8 MB VTCM can
> hold a bundled store. Both are answerable against real code now.

Also available and unexamined: `backends/samsung` (this device's other vendor path),
plus `ggml-org/llama.cpp` `ggml/src/ggml-hexagon` (MIT, 124k stars), `alibaba/MNN`,
`Tencent/ncnn`.

---

## 2. Acurast: the thesis, shipped, and a different answer to verification

`acurast-substrate/pallets/` — public domain:

```
acurast  marketplace  compute  processor-manager  candidate-preselection
rewards-treasury  hyperdrive  hyperdrive-ibc  hyperdrive-token
token-claim  token-conversion
```

### 2a. Their verification does not need determinism, and that reframes our pitch
Acurast runs jobs inside the phone's **TEE with hardware key attestation** — the
silicon signs a statement that the hardware is genuine and the loaded code was not
modified — plus staked compute. **No replication.** So the question this workspace
calls its biggest risk — who pays for the second run — they answered by not having
a second run, and it works for *any* workload, not only deterministic ones.

Our mission's central bet is *"deterministic symbolic reduction makes verification
nearly free."* **Acurast made verification nearly free without determinism.** So
"verification is nearly free" is no longer a differentiator and must stop being
used as one.

What genuinely survives, and it is a real distinction:

> **Their trust model requires trusting Qualcomm, Google and Samsung silicon plus
> the attestation chain. Ours requires trusting nothing — a byte comparison anyone
> can re-run.** S57 just measured that across two ISAs, three platforms and 560,847
> interpreter steps.

That is now the *whole* distinction, and `out/PROPOSAL_DRAFT.md` should say exactly
that instead of the cost argument.

### 2b. Their matcher already answers the gap we called novel
`pallets/marketplace/src/match_checker.rs` — the complete constraint set of a
production matcher, 25 named failure modes. Each is encoded failure history.
Counted by frequency of check:

| constraint | ×  | do we have it? |
|---|---|---|
| `CalculationOverflow` | 21 | no — every arithmetic op is checked; ours are not |
| `ScheduleOverlapInMatch` | 4 | **no — `hyperjob` has no schedule at all** |
| `DuplicateSourceInMatch` | 2 | **no — see below** |
| `ProcessorVersionMismatch` | 2 | no — binary version pinned per match |
| `ProcessorMinMetricsNotMet` | 2 | no — minimum device capability floor |
| `Overdue`/`UnderdueMatch` | 3 | no — a match must land inside a window, not early either |
| `NetworkRequestQuotaExceededInMatch` | 1 | no — per-job network quota |
| `IncorrectSourceCountInMatch` | 2 | partial — replication count enforced on-chain |
| `InsufficientReputationInMatch` | 1 | no |
| `Unverified`/`SourceNotAllowed`/`ConsumerNotAllowed` | 6 | no — allow/deny both directions |

**`DuplicateSourceInMatch` is the one that stings.** `GAP_MATRIX` §46 names our one
genuinely novel gap as *"commit/reveal with a worker-bound seal — without it,
replication across untrusted devices can be gamed by echoing another device's
hash."* S49 built that seal and shipped it broken.

Acurast prevents the echo attack with a storage-map check at match time
(`match_checker.rs:157-163`): the map is keyed `(source, job_id)`, and a device
already holding an assignment for that job cannot take a second slot —
`Some(_) => Err(DuplicateSourceInMatch)`. **No cryptography.** Combined with
BOINC's *majority of a quorum* (`GUARDRAILS.md` C5), that is two independent
production answers to the problem we classified as novel and then got wrong.

The seal is still worth having — it defends against collusion between *distinct*
devices, which a duplicate check cannot see. But it is a second line of defence,
not the primary mechanism, and it was never the novel part.

### 2c. Liquid matching is wedge #2, in production
`propose_matching` / `propose_execution_matching` (`lib.rs:542,651`) with an
off-chain Matcher pairing Deployments to Processors. `GAP_MATRIX` row 4 rates the
locality-aware matcher **BUILD**. Read this pallet before writing more of M3.

---

## 3. Two more entrants, and a threat to the settlement design

- **Destra Edge** — a third funded phone-inference network.
- **VeriLLM** (arXiv 2509.24257) claims verifiers validate decentralised inference
  at **~1% of inference cost**. S7 measured our verification at roughly full
  re-execution (85 ms recompute against a 0.7 ms check), and `FINAL_REPORT` calls
  that the project's biggest risk. Someone published a 1% answer. Read it before
  designing settlement.

So the phone-fleet space has **at least three funded entrants** and the original
recon found none of them.

## 4. Gaps our own docs opened and never closed

| repo | licence | note |
|---|---|---|
| `PrimeIntellect-ai/prime` | MIT | M0.5, named in `BLOCKED.log`, never cloned. `shardcast` lives here. **Now cloned.** |
| `gensyn-ai/genrl` | **none** | the Verde hunt from `BLOCKED.log`. Unlicensed and stale (2025-11-12) — **dead end, close the item** |
| `torchhd`, GraphBLAS/LAGraph, `ipfs/kubo` | MIT / Apache-2.0+BSD / dual | tier 2, never cloned |
| `bacalhau` | Apache-2.0 | compute-over-data: schedule jobs where the data already is — wedge #2's premise, in production Go |
| `iroh` | Apache-2.0/MIT | content-addressed transport; better M1.5/M1.7 fit than kubo — Rust, built for direct connections |
| `risc0`, `sp1` | Apache-2.0 | zkVMs — relevant *because* verification economics is the open question |
| `differential-dataflow`, `souffle`, `kuzu` | MIT / UPL-1.0 / MIT | MORK alternatives while its licence is unresolved |

## What to do with this

1. **Rewrite `GAP_MATRIX` row 6** — PORT, not BUILD; name the two narrow unknowns.
2. **Rewrite the differentiator in `PROPOSAL_DRAFT`** — trustlessness, not cost.
3. **Add the missing matcher constraints to `hyperjob`** — schedule, version pin,
   capability floor, match window, network quota, duplicate-source. Per
   `GUARDRAILS.md`, any field a production schema has and we lack must be
   *justified*, not deferred.
4. **Demote the seal** from novel-primary to defence-in-depth, and fix the ledger
   text that calls it the one thing the mission's capability list missed.
5. **Read `pallets/marketplace` and `pallets/compute` before more M3.**
