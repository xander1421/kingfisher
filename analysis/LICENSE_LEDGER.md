# LICENSE LEDGER

Every repository cloned in this mission, its licence as read from the repository itself (not from GitHub's metadata guess), and what we are permitted to do with it.

Gate rules (mission §7):
- **Apache-2.0 / MIT / BSD** → PORT allowed, with attribution + a NOTICE entry.
- **MPL-2.0** → file-level copyleft; port isolated files only, keeping them MPL.
- **GPL / LGPL / AGPL** → never copy into our permissive tree. Study + clean-room reimplement from our own written spec, or (LGPL only) dynamic-link as an isolated component.
- **UNKNOWN** → all rights reserved. Read for ideas, copy nothing.

## The ledger

| repo | SPDX | evidence | verdict |
|---|---|---|---|
| trueagi-io/hyperon-experimental | **MIT** | `LICENSE`, © 2021 SingularityNET Foundation | **PORT** ✅ |
| Adam-Vandervorst/PathMap | **MIT** | `LICENSE`, © 2025 Adam Vandervorst; `license = "MIT"` in Cargo.toml | **PORT** ✅ |
| singnet/das | **Apache-2.0** | `LICENSE` + `NOTICE` | **PORT** ✅ |
| singnet/das-proto | **Apache-2.0** | `LICENSE` + `NOTICE` | **PORT** ✅ |
| singnet/das-toolbox | **Apache-2.0** | `LICENSE` + `NOTICE` | **PORT** ✅ |
| nunet/device-management-service | **Apache-2.0** | `LICENSE`, `copyright.txt`, per-file headers, a `lint-license` make target | **PORT** ✅ |
| akash-network/node | **Apache-2.0** | `LICENSE` | **PORT** ✅ |
| iExecBlockchainComputing/PoCo | **Apache-2.0** | `LICENSE`, © 2020-2023 iExec Blockchain Tech | **PORT** ✅ |
| opentensor/bittensor | **MIT** | `LICENSE`, © 2025 Opentensor Foundation / Yuma Rao | **PORT** ✅ |
| opentensor/subtensor | **Apache-2.0** | `LICENSE` | **PORT** ✅ |
| PrimeIntellect-ai/toploc | **MIT** | `LICENSE`, © 2024 Prime Intellect | **PORT** ✅ |
| PrimeIntellect-ai/prime-rl | **Apache-2.0** | `LICENSE` | **PORT** ✅ |
| PrimeIntellect-ai/OpenDiLoCo | **Apache-2.0** | `LICENSE` | **PORT** ✅ (unmaintained upstream) |
| gensyn-ai/rl-swarm | **MIT** | `LICENSE.TXT`, © 2025 Gensyn | **PORT** ✅ |
| **trueagi-io/MORK** | **UNKNOWN** | **no LICENSE/COPYING file; no `license` key in any of 12 Cargo.toml files; no licence statement in README** | **ALL RIGHTS RESERVED — read only, copy nothing** ⛔ |
| BOINC/boinc | **LGPL-3.0** (files say "LGPL 2.1 or later") | `COPYING.LESSER` + `COPYRIGHT`, © 2002-2019 University of California | **SPEC only** ⛔ |
| golemfactory/ya-client | **LGPL-3.0** | `LICENSE` | **SPEC only** ⛔ |
| golemfactory/ya-runtime-sdk | **GPL-3.0** | `LICENSE` | **SPEC only** ⛔ |
| golemfactory/ya-runtime-vm | **GPL-2.0** | `LICENSE` | **SPEC only** ⛔ |
| golemfactory/yagna (the monorepo) | — | **repository removed from GitHub (404)** | unavailable; see `BLOCKED.log` |

## Two entries that need emphasis

### MORK is UNKNOWN, and MORK is the most load-bearing elder
This was verified three ways: no licence file of any name in the tree, `grep -rin 'license' --include='*.toml' --include='*.md'` returns **zero hits**, and none of the twelve `Cargo.toml` files carries a `license` or `license-file` key. Its sibling dependency **PathMap is MIT**, which does *not* extend to MORK.

Consequences, applied throughout `GAP_MATRIX.md`:
- The exact engine, the fuel counter, the differential harness, the linalg crossover methodology, and the zipper/trie data structure are all classified **SPEC**, never PORT.
- `spikes/S3_mork_bench/RESULT.md` and `reports/REPORT_MORK.md` are written as *descriptions* of observed behaviour, detailed enough to reimplement from, precisely because the code cannot be copied.
- **Action for a human:** open an issue asking trueagi-io to add a licence. Everything else about MORK is ecosystem-friendly; this is almost certainly an oversight, and fixing it would change several rows of the gap matrix from SPEC to PORT.

### BOINC is LGPL and that is fine, because we want its policy not its code
LGPL would permit dynamically linking an unmodified BOINC library. We do not want to: the value is the Android suspend policy and the work-unit/redundancy schema, both of which are *designs*. `spikes/S6_scheduler/SCHEDULER_SPEC.md` and `reports/REPORT_BOINC.md` are deliberately written as clean-room specification source documents — behaviour, constants, and file citations, no copied code.

## Copies made during this mission
**None.** No file from any elder has been copied into `spikes/` or `out/`. Everything under `spikes/` was written from scratch. Three kinds of borrowing did occur and are declared:
1. **`spikes/S7_toploc_adapt/commit.py`** reimplements TOPLOC's Newton-divided-difference construction from the published algorithm and the `.pyi` interface. TOPLOC is **MIT**, so even a direct port would have been allowed; the file credits it in its docstring and diverges deliberately (prime-modulus check). A NOTICE entry is owed.
2. **`spikes/S4_hyperjob_schema/hyperjob_v0.proto`** deliberately mirrors NuNet's *vocabulary* (`version`, `allocations`, `redundancy`, `failure_recovery`) per mission §10.5. No NuNet code or schema file was copied; NuNet is Apache-2.0 and is credited in the file header.
3. **`spikes/S8_das_up/animals.metta`** is a copy of a sample data file from das-toolbox (**Apache-2.0**), used as query input for the spike and left in place with provenance noted here.

## NOTICE entries owed if any of this ships
```
This product includes software developed by:
  - SingularityNET Foundation — hyperon-experimental (MIT)
  - SingularityNET Foundation — DAS, das-proto, das-toolbox (Apache-2.0)
  - Adam Vandervorst — PathMap (MIT)
  - NuNet — Device Management Service (Apache-2.0)
  - Prime Intellect — TOPLOC (MIT), prime-rl / OpenDiLoCo (Apache-2.0)
  - iExec Blockchain Tech — PoCo (Apache-2.0)
  - Akash Network — node (Apache-2.0)
  - Opentensor Foundation — bittensor (MIT), subtensor (Apache-2.0)
  - Gensyn — rl-swarm (MIT)
```
BOINC, Golem and MORK are deliberately absent: nothing of theirs is included.
