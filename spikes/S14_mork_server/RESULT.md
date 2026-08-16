# S14 — the recon read the wrong MORK branch

**Verdict: YELLOW, and it corrects three conclusions in the original deliverables.**
`elders/MORK` is a depth-1 clone of `main`. The branch that carries the HTTP
server, the Python client, the docs and the benchmarks is `server`, which is
**305 commits ahead of and 265 commits behind main** and has a materially
different tree. Two of the three portability blockers the workspace recorded do
not exist there. The licence problem does.

Prompted by the upstream README and wiki. Clone: `mork-server/` (depth 1,
blobless, branch `server`, HEAD `2d6730b`).

## The two trees are not the same project

| | `main` (what the recon read) | `server` (what upstream documents) |
|---|---|---|
| HEAD | `0653b50` | `2d6730b` |
| `server/` (HTTP server) | absent | **present** |
| `python/` (client + 11 examples) | absent | **present** |
| `docs/` (`mm2.md`, `roadmap.md`) | absent | **present** |
| `benchmarks/`, `notes/` | absent | **present** |
| `linalg/` (the crossover benches) | **present** | absent |
| `differential/` (the verification harness) | **present** | absent |
| `expr/`, `interning/` | **present** | absent |
| LICENSE | **none** | **none** |

`reports/REPORT_MORK.md` and `analysis/GAP_MATRIX.md` row 7 describe `main`.
Every upstream-facing document — README, wiki, "where to start" — describes
`server`. Neither branch is the whole project.

## Three corrections

### 1. The process boundary already exists — it does not need building
`out/PORT_PLAN.md` M1.6 and `DECISIONS.log` entry 17 settle on running "MORK
desktop-only behind a process boundary". That boundary ships: `mork-server` is an
HTTP server with a Python client (`ManagedMORK.connect(...)`), sub-space scoping
via `work_at` (upstream calls them *lenses*), and `import`/`upload` /
`export`/`download` for bulk and small transfers. Whatever is written to talk to
MORK should be written against that API, not invented.

### 2. `/dev/shm` is a `main`-only blocker
`BLOCKED.log` entry 4 and `S3_mork_bench/RESULT.md` record
`kernel/src/space.rs:35` hardcoding `ACT_PATH = "/dev/shm/"`, calling it a
**high**-severity blocker that "breaks on Android *and* macOS". On the `server`
branch:

```
grep -rn "ACT_PATH" --include="*.rs" .   → no matches
```

`/dev/shm` survives only in commented-out lines of `kernel/src/main.rs`. The
blocker should be re-tested against `server` before it is carried into any
planning document, and the M0.6 issue should name the branch.

### 3. Canonical serialisation exists — GAP row 9 is partly wrong
`analysis/GAP_MATRIX.md` row 9 says "No elder has a content-addressed *Atomspace
shard* … Needs: canonical serialisation, a CID, a manifest, and an LRU cache on
device", classified **SPEC / M**. The serialisation half exists:

```
kernel/src/space.rs:
  restore_symbols(path)        restore_from_dag(path)
  restore_tree(path)           restore_paths(path) -> pathmap::paths_serialization::DeserializationStats
```

plus a `.paths` wire format with `paths_import` in the client, and the wiki's
account of writing a space to disk and paging it back in on demand:

> "if the space is too large to fit in memory, the loading from disk will allow
> access to occur as needed … the act files are very compact … a convenient way
> to share files when bandwidth is in short supply"

That is most of a shard format, including the offline-capable phone-side cache
`out/STATE_OF_THE_UNION.md` Layer 1 lists as missing. What is genuinely absent is
**content addressing** — a hash, a CID, a manifest. Row 9 should be re-scoped
from "build a shard format" to "put a CID and a manifest on an existing one",
which is smaller.

## What did not change

- **Still no licence, on either branch.** `git ls-tree` finds no LICENSE or
  COPYING on `server` any more than on `main`. M0.1 remains the highest-leverage
  single action in the workspace, and there is now a named contact for it: the
  wiki is maintained by charlie.derr@singularitynet.io, and the README says
  "please contact us".
- **Still nightly, still undeclared.** `server` has no `rust-toolchain.toml` and
  `Cargo.toml` is `edition = "2024"`, so `BLOCKED.log`'s nightly finding stands.

## Also worth noting from upstream docs, not in any report
- Hard limits: **max expression size 64, max symbol size 64, max variable
  mentions 64**. These are constraints on the hyperjob program and on any shard
  serialisation, and appear nowhere in `spikes/S4_hyperjob_schema/`.
- `transform` is the single primitive — "all queries are just special cases of
  transform" — taking a `($pattern, $template)` pair. That maps directly onto the
  hyperjob body and is a better shape for it than an opaque program blob.
- Branch `wasm_sink_all_dense_nodes` exists. A WASM target is a second portability
  route to the device that no report considers.
- Repo scale: 61 stars, 60 forks, 9 contributors, 27 open PRs, 4 open issues.
  Small and active; an upstream contribution would be visible.

## Not done here
Nothing was built. This is a tree inspection: no `cargo build`, no server started,
no `.paths` round-trip measured. Verifying that `server` builds on stable, that
ACT persistence works off `/dev/shm`, and that a `.paths` file round-trips a space
byte-identically are the three follow-ups, and all three are cheap.
