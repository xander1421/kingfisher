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
- **The licence question was already asked upstream, and answered.** In `trueagi-io/MORK` issue #2 ("License", closed 2025-05-21), Adam-Vandervorst — MORK's top contributor by 254 commits, and the copyright holder named in PathMap's MIT LICENSE — replied in full: *"Yes! It's now under MIT."* **The file was never committed.** At HEAD (`0653b50`) there is no LICENSE, no `license` key in any of the 10 manifests, and `gh api repos/trueagi-io/MORK --jq .license` returns `null`. The `server` branch (`2d6730b`) is the same.

**This shrinks the ask without moving the gate.** The action for a human is no longer "ask an org to make a licensing decision" but "reference issue #2 and ask for the file to be committed". Until that file exists at HEAD, **MORK stays UNKNOWN = all rights reserved**: a comment in a closed issue is a statement of intent, not a grant in the repository, and mission §7 is explicit. Every SPEC-not-PORT classification below stands, and "zero files copied" stands. Credit: found by AGENT-4, 2026-08-17.

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

## Wave 2 — added 2026-08-17

The original manifest sampled *analogous* systems and missed the *identical*
one. Ten repos added; **every one is permissive, none copyleft, none UNKNOWN.**
Licences read from the file on disk, per the gate — never from GitHub metadata,
which reported `NOASSERTION` for four of these.

| repo | HEAD | SPDX | evidence | verdict |
|---|---|---|---|---|
| Acurast/acurast-substrate | `b59f7d8` | **Unlicense** | `LICENSE`: *"free and unencumbered software released into the public domain"* | **PORT** ✅ *(public domain — no attribution obligation)* |
| Acurast/acurast-core | `26d5688` | **MIT** | `LICENSE.md`, verbatim MIT, © 2023 Acurast Association | **PORT** ✅ |
| Acurast/acurast-docs | `66e8a83` | **MIT** | `LICENSE.md`, © 2022 Acurast Association | **PORT** ✅ |
| Acurast/acurast-kotlin-sdk | `408429f` | **MIT** | `LICENSE` | **PORT** ✅ |
| PrimeIntellect-ai/prime | `433c505` | **MIT** | `LICENSE` | **PORT** ✅ |
| bacalhau-project/bacalhau | `29d1206` | **Apache-2.0** | `LICENSE` | **PORT** ✅ |
| n0-computer/iroh | `8455111` | **Apache-2.0 OR MIT** | dual: `LICENSE-APACHE` + `LICENSE-MIT` | **PORT** ✅ |
| hyperdimensional-computing/torchhd | `9d73e1b` | **MIT** | `LICENSE` | **PORT** ✅ |
| ggml-org/llama.cpp | `4df29be` | **MIT** | `LICENSE`; sparse-checkout `ggml/src/ggml-hexagon` | **PORT** ✅ |
| pytorch/executorch | `42ebbc3` | **BSD-3-Clause** | `LICENSE`, *"Neither the name Meta nor the names of its contributors…"* | **PORT** ✅ |

Checked and clean: no GPL or LGPL text anywhere in the sparse-checked-out
`executorch/backends/{qualcomm,samsung}` or `llama.cpp/ggml/src/ggml-hexagon`.

**Not cloned, and why** — `ipfs/kubo` and `GraphBLAS`/`LAGraph` skipped
(`DECISIONS.log` 01:14Z: iroh supersedes kubo for a phone-side store; MORK's
`linalg` already covers the semiring angle). `gensyn-ai/genrl` abandoned
(01:16Z: **no licence file** and last push 2025-11-12 — it would enter this
ledger as UNKNOWN and is stale).

**Still zero files copied from any elder, wave 1 or wave 2.**


---

## Round 2 additions — 2026-08-16

Ten repos the original manifest missed. **Every licence below was read from the
file content in the git object, not from a hosting API.**

| repo | licence | evidence | §7 class |
|---|---|---|---|
| **acurast-substrate** | **Unlicense (public domain)** | `LICENSE`, *"free and unencumbered software released into the public domain"*, closing with `unlicense.org` | **PORT**, attribution not even required |
| acurast-core | MIT | `LICENSE.md` — verbatim MIT body, no title line | PORT with attribution |
| acurast-kotlin-sdk | MIT | `LICENSE` | PORT with attribution |
| executorch | BSD-3-Clause | `LICENSE` + `pyproject.toml: license = {text = "BSD-3-Clause"}` | PORT with attribution |
| llama.cpp | MIT | `LICENSE` | PORT with attribution |
| prime | MIT | `LICENSE` | PORT with attribution |
| bacalhau | Apache-2.0 | `LICENSE` | PORT with attribution |
| iroh | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` | PORT, take either |
| torchhd | MIT | `LICENSE` | PORT with attribution |
| acurast-docs | n/a | prose | reference only |

**Zero copyleft, zero UNKNOWN in this round** — against round 1's two copyleft
elders holding the operational wisdom and one UNKNOWN blocking the fastest engine.

**Copies made during this mission: still None.** These are read, not vendored.

**Closed as a dead end:** `gensyn-ai/genrl` — the Verde implementation hunt in
`BLOCKED.log`. Unlicensed *and* stale (last push 2025-11-12). Under §7 an UNKNOWN
licence is all-rights-reserved; combined with staleness there is nothing to pursue.
