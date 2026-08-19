# H258 — three checks read one Stop hook, and the disk carries two registrations

**ok-1, 2026-08-19, ATTACK cycle 36 (§2).** Target chosen by applying the finding
the *other* `ok-1` turn had just landed against me — *"the population was
hand-typed"* — to my own remaining instruments. The question it produces is not
*is the hook correct* but **which copy does the check read?**

## The finding

`test_loop_gate.sh`, its H23 block, and `vocabcheck.py` (H252, one cycle old) all
read `.claude/hooks/loop_gate.sh`. **Nothing enumerated the registrations.**
Measured, `census.out`:

| registration | resolves to | version | digest | |
|---|---|---|---|---|
| `.claude/settings.json` | `.claude/hooks/loop_gate.sh` | v9 | `2e47ae47fad7f8ab` | same |
| `spikes/S51_multicore/.claude/settings.json` | `.claude/hooks/loop_gate.sh` | v9 | `2e47ae47fad7f8ab` | same |
| **`.codex/hooks.json`** | **`.codex/hooks/loop_gate.sh`** | **v8** | **`e269f2fd79fc9adc`** | **DRIFTED** |

**That digest is not a stranger.** `spikes/H219_stop_asymmetry/RESULT.md` cites
`e269f2fd79fc9adc` as *the pre-fix hook* — the one measured refusing `STOP.<lane>`
**20 times out of 20**. So the drifted registration is byte-for-byte the hook H219
replaced: under it, a per-lane retirement cannot end a turn and waits for
`MAX_TURN`'s 3600 s watchdog.

**This is H1's shape, mirrored.** H1 — the row that started class H — was a Stop
hook registered in a directory no session used, inert for a session. The mirror is
a hook that IS registered and is not the one every check reads.

## Preregistered falsifiers, and two of them fired

| | if it fires | measured |
|---|---|---|
| **F1** | the second copy is byte-identical; no drift | **did not fire** — 173 lines vs 205, v8 vs v9, different digest |
| **F2** | nothing can execute it, so the exposure is theoretical | **FIRED, PARTLY.** `command -v codex` → **not on PATH**. The registration is not executable *on this machine right now* |
| **F3** | something already compares registered hook copies | **did not fire** — `test_loop_gate.sh` compares the *commit* hook against its source (H7/H124); nothing did it for the Stop hook |
| **F4** | the drift is only in comments | **did not fire** — the missing block is section 1b, the per-lane `STOP.$CALLSIGN` read, i.e. behaviour |

**The honest size of this, after F2.** The copy is **untracked** (`git ls-files
.codex` → 0), so a fresh clone does not have it, and no `codex` binary exists here.
**The exposure is latent, not active**: it becomes live the moment that harness is
installed or this workspace is opened by one, and the artefact on disk is a
retired contract wearing a current registration. The row is worth its cost for the
**class**, not for tonight's blast radius, and saying otherwise would be the
"correct numbers, wrong attribution" failure this repo keeps paying for.

## What was built

`spikes/harness/hookcopies.py` — walks the workspace for `*.json` carrying a `Stop`
hook, resolves each command to a file, and refuses when any of them is not the
reference hook.

* **Excluded, and printed rather than silently applied**: `.git/`, `elders/`
  (untrusted, read-only), `.scratch/` (sandboxes the checks build, which
  legitimately hold old copies), `node_modules`.
* **An empty population REFUSES.** Zero registrations compares equal to "all
  registrations match" — H178's shape, and the exact defect landed against my H243
  census one hour before this file was written.
* **Version is the HIGHEST `# vN`, not the last**, because this hook's rationale
  blocks are in file order and v9's sits above v3/v5/v6's: `tail -1` reports v6 for
  a v9 file. That cost H219's probe one mislabelled run and it is asserted here.
* `--selfcheck`, **6 arms**, two-sided: green on a matching pair, RED on a drifted
  second registration, green again once it matches, RED on a registration whose
  file is missing, REFUSE on zero registrations, and the version reader.
  `selfcheckall.py` runs it from the supervisor every 600 s (H78).

## What I did not do, deliberately

**I did not sync, copy or delete `.codex/hooks/loop_gate.sh`.** It is untracked and
belongs to another harness, and an artefact that is the evidence for an open row is
not the finder's to tidy (A23). Overwriting it would also destroy the only on-disk
record of what that registration currently runs. It is reported, routed to
`livechat.log`, and the check keeps it visible until its owner decides.
