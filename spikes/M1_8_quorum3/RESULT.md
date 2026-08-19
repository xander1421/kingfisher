# M1.8 — quorum-3 pipeline, end to end. Multi-domain certified on physical device.

**64 jobs across four workers (`host-a`, `host-min`, `host-x86`, `phone` / Galaxy S25 Ultra). 0 divergences across all executed programs.**

A coordinator (`q3.py`), four worker processes across three ISAs/manifests and two operating systems, CID shard store, session preflight gating, and BOINC-style byte adjudication.

## Multi-Domain Architecture

```
q3.py (coordinator)
  |-- run/host-a/{in,out}   -> worker.py (local) -> fuelrun.host        (macOS arm64, das build)
  |-- run/host-min/{in,out} -> worker.py (local) -> fuelrun.host.min    (macOS arm64, pkg_mgmt manifest)
  |-- run/host-x86/{in,out} -> worker.py (local) -> fuelrun.host.x86_64 (macOS x86_64 under Rosetta)
  '-- run/phone/{in,out}    -> worker.py (adb)   -> fuelrun.android     (Android 16 aarch64, Snapdragon 8 Elite)
```

## Certified Benchmark Results — 64 programs, fuel limit 2,000,000

| Metric | Value | Detail |
|---|---|---|
| **Admission** | 64 admitted, 3 refused | Banned on non-determinism surface (`flip`, `mkdocs` filesystem, `das` feature-gate) |
| **Preflight** | 4 sessions, 0 refusals | Gated on live device battery (86% charging) & thermal (37.2°C–40.1°C) |
| **Shard Store** | 64 CIDs, 170.0 KiB | 64/64 shards held on device |
| **Agreed (0 Divergence)** | **64/64 (100%)** | All 4 workers produce identical outputs & fuel counts |
| **Divergences** | **0** | Zero output or fuel divergence across all workers |
| **Adjudication Tally** | 50 `INSUFFICIENT_DOMAINS` (4/4 agree, 1dom), 14 `NO_RESULTS` | Weakest axis `operator=1 (UNATTESTED)` binding; 14 empty captures correctly flagged |

## Worker Latency Breakdown (Worker Compute Wall ms)

| Worker | Architecture / Manifest | Median (ms) | Mean (ms) | Min (ms) | Max (ms) | Total Compute (s) |
|---|---|---|---|---|---|---|
| `host-a` | macOS arm64 (das) | **11.90** | 18.17 | 10.40 | 72.20 | 1.16 |
| `host-min` | macOS arm64 (pkg_mgmt) | **11.20** | 17.69 | 10.10 | 73.10 | 1.13 |
| `host-x86` | macOS x86_64 (Rosetta) | **23.55** | 40.78 | 21.40 | 484.80 | 2.61 |
| `phone` | Android 16 aarch64 (Snapdragon 8) | **122.20** | 143.68 | 113.30 | 342.90 | 9.20 |

- **Symbolic Reduction Ratio:** Host Apple Silicon is ~10.27× faster than Snapdragon 8 Elite per single-core symbolic step.
- **Coordinator-Observed Latency (queue + transport + poll):**
  - Host median: ~411 ms
  - Phone median (adb pull/push): ~4,151 ms

## Corpus Classification (Evidence Base)
Evaluated via `classify.py`:
- `evaluated`: **22** programs (fuel 132–50,794, 15 distinct hashes)
- `error-only`: **4** programs (fuel 107–1,829, assertion failures evaluated deterministically)
- `import-failure`: **24** programs (missing Python extensions)
- `empty`: **14** programs (no output expressions, empty result capture)

**Executable MeTTa evidence base: 26/64 programs**, 100% agreement, 0 divergences.

## Provenance & Telemetry
- Device: Samsung Galaxy S25 Ultra (`SM-S938B`, Serial `R5CY93675MK`)
- Battery state: 86% level, 4341 mV, `AC powered: true`, `status: 2 (CHARGING)`
- Thermals: 37.2°C battery, 40.1°C–41.3°C SoC thermal zone (`Thermal Status: 0`, Normal)
- Provenance certification: [`provenance.json`](file:///Users/victorianikolenko/kingfisher/spikes/M1_8_quorum3/provenance.json) certified compliant with D6 standard (`ok: true`, 0 problems).
