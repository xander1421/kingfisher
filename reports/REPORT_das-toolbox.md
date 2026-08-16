# REPORT: das-toolbox (das-cli)

## 1. Identity
- URL: https://github.com/singnet/das-toolbox
- Commit: `a1e193bbfd8a8a1467870dc22913c8f550676b58` (2026-08-13)
- License: **Apache-2.0** (+ `NOTICE`). Gate: **PORT allowed with attribution.**

## 2. Shape
272 Python, 71 JSX + 45 JS (`das-dashboard`, a web configurator), 23 `.bats` (shell test suite), 11 shell. Four products in one repo: `das-cli/`, `das-dashboard/`, `das-runner-manager/`, `gatekeeper/`. Build: `setup.py` → pip, plus `make build` producing a **`.deb`**; `dist/` holds packaged artefacts.

## 3. Entry point
`das-cli` (click-based). Every command can be executed **on a remote host over SSH** (`--remote --host --user --key-file/--password`), which is how a fleet of shard hosts is meant to be operated.

Command groups: `atomdb-broker`, `attention-broker`, `command-router`, `config`, `context-broker`, `database`, `database-adapter`, `evolution-agent`, `example`, `inference-agent`, `jupyter-notebook`, `link-creation-agent`, `logs`, `metta`, `python-library`, `query-agent`, `release-notes`, `system`, `update-version`.

Each service group follows the same five-file shape (`*_cli.py`, `*_module.py`, `*_docs.py`, `__init__.py`, + settings), and each is a thin lifecycle wrapper — `start` / `stop` / `restart` — over a Docker container with `--network host`.

## 4. What it actually does
- **Config**: an interactive wizard writing `~/.das/config.json`; the schema and defaults live in `das-cli/src/common/config/core.py`. Ports are all in the 400xx range (redis 40020, mongo 40021, attention 40001, query 40002, link-creation 40003, inference 40004, evolution 40005, context 40006, atomdb 40007, command-router 40008, jupyter 40019), each agent additionally reserving a 1000-port range for per-query bus sockets (42000-42999, 43000-43999, …).
- **`database start`**: runs redis + mongodb containers.
- **`metta load <path>`**: syntax-checks and bulk-loads `.metta` into the Atomspace via the `trueagi/das-1.0.0-metta-parser` loader image. A `morkdb` loader image (`trueagi/das-mork-loader-1.1.0`) is configured alongside it.
- **`<agent> start`**: runs `trueagi/das:<version>` with `busnode --service=<name> --endpoint=... --ports-range=... --config=~/.das/config.json`.

## 5. Verified working (S8)
Used it to stand up a complete local Atomspace on this machine and run a query end to end — redis, mongodb, attention broker, query agent, `animals.metta` loaded, `(Similarity "human" $S)` returning monkey/chimp/ent. Full transcript in `spikes/S8_das_up/RESULT.md`.

Two defects found in the process, both worth reporting upstream:
1. **`das-cli config set` cannot produce a valid config.** It never prompts for `agents.command_router.http_api`, but `das-cli database start` then refuses to run without it (`[ValueError] ... Missing entry: 'agents.command_router.http_api'`). The defaults exist in `core.py:163-175`; only the prompt is missing.
2. **Docker socket discovery is hardcoded to the default.** The Python docker SDK goes to `/var/run/docker.sock` regardless of the active docker *context*, so on macOS with colima (or any non-Docker-Desktop setup) every command fails with `ConnectionRefusedError(61)` until `DOCKER_HOST` is set by hand.

## 6. Verdict for the mission
Not a source of algorithms — a source of *operational shape*. Three things are worth copying for our desktop shard-host agent: the **single JSON config with a versioned schema and a validation gate**, the **uniform `start`/`stop`/`restart`/`logs` lifecycle per service**, and **`--remote` over SSH as a first-class flag** so one operator can run many hosts. The `.deb` + systemd packaging is the same desktop-daemon assumption NuNet makes, and the same one that does not survive contact with Android.
