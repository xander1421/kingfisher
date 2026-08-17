# HANDOFF — write-ahead checkpoint (agent-1 lane)

Updated 2026-08-17, autonomous mode. Read this first after any restart.

## Mission, restated
Trustless "world computer": distributed hypergraph AI (MeTTa/MORK) across
consumer devices, where a result is trusted because **anyone can re-run it and
compare bytes**. The one surviving technical asset is byte-reproducible MeTTa
reduction across ISAs for a statically-admissible job class. Everything else is
scaffolding around making that asset usable.

Two lanes: **agent-1 (this one) = M1/M2 device chain**; **agent-2 = G-series
graph learning / attention**. Coordinate via `livechat.log`.

## Loop state — READ THIS
The Stop hook (`.claude/hooks/loop_gate.sh`) was **inert for the whole first
session**: settings lived in `~/kingfisher/.claude/settings.json` but the
session project dir is `spikes/S51_multicore`, which had no `.claude/`.
`CLAUDE_PROJECT_DIR` was unset so the `$(pwd)` fallback would also have missed.

Fixed: `spikes/S51_multicore/.claude/settings.json` now registers the hook by
absolute path, and `ROOT` is pinned inside the script. **`settings.json` binds
at session start, so this takes effect on the next restart.** Until then use
`ScheduleWakeup` each turn as the re-entry mechanism.

To stop legally: write exactly `LOOP-DONE` / `LOOP-HALT` / `LOOP-IDLE` into
`.loop_signal`. Human kill switch: `touch STOP`.

## State of the M1 chain — complete, and correctly refusing
```
admission gate -> CID shard store -> session preflight
  -> phone + host workers -> canon/canon_alpha -> quorum-3
```
66/66 agree byte-identically across aarch64 and x86_64 and the phone.
**Verdict is INSUFFICIENT_DOMAINS, accepted 0/66** — correct, because
`operator = 1` (no attestation root) and that is the axis Q1's 72% capture is
about. This is the honest state, not a regression.

## Binding constraints (cannot be fixed inside the workspace)
1. **No attestation root** -> `operator` domain pinned to 1 -> every job refused.
2. **One physical phone** -> host/os domains capped at 2.
3. **No buyer, no query stream** -> demand is unmeasurable from here.
4. Publishing forbidden (§11) -> 4 upstream artifacts finished and unfiled:
   `proposed/hyperon-nondeterminism/`, `proposed/hyperon-match-arity/`,
   `proposed/das-concurrency/`, `proposed/mork-license/`.

## Where I am, and the next three items
- **BLOCKER RESOLVED — and it was my error.** The battery service was pinned in
  a test override (`UPDATES STOPPED`); `dumpsys battery reset` shows
  `USB powered: true`. The phone was charging all along, §10 was honoured, and
  on-device timings need no re-measurement. Both gates now refuse on an
  overridden service. `spikes/M1_3_worker/CHARGING_DEFECT.md`.
- **OPEN/BLOCKED**: app as a q3 quorum member (`worker_app.py`) — okhttp fault
  I could not isolate, time-boxed, q3 reverted to the adb verifier.
  `spikes/M1_8_quorum3/APP_WORKER_BLOCKED.md`.
- **DONE: a Cargo FEATURE changes `fuel_used`** (107 vs 580). Equivalence class
  includes the feature set; `provenance.py` hashes manifests and `manifest` is a
  domain axis. `analysis/FEATURE_EQUIVALENCE.md`.
- **DONE: the Android app is a fleet member, 65/65 byte-identical to host** on
  the admitted corpus. Closing it needed matched Cargo features (the `[patch]`
  section does not cross the workspace boundary), fixing our own envelope
  escaping, and banning the `fileio` surface. `spikes/M1_7_transport/FLEET_MEMBER.md`.
- **DONE**: M1.7 transport (66/66 byte-identical, phone dials out, loopback
  only); M1.3b process reuse (31 raw hashes -> 1 canon; SAFE for ground
  results); M2.1 §6 maxSkew reframed as a security dial, §3's knee withdrawn;
  both locality-ratchet falsifiers (skew- and density-independent, 89x at
  fleet 64). Android worker ported onto the transport, builds, **untested**.
- **DONE earlier**: M2.1 fleet routing. S61's locality/imbalance tension is
  real under *skewed* demand (zipf 1.4 -> 19.33x vs random 1.79x) and a k8s
  `maxSkew=1` cap buys out of it (1.06x imbalance, 78.7% transfer saved).
  Uniform demand shows no tension and I nearly published that.
- **NEXT 1**: residency feedback loop. `prefill` is a stand-in for history; real
  residency comes from what a device previously ran, so locality routing may
  drive itself into monopoly. Run multiple rounds with residency accumulating
  from actual execution.
- **NEXT 2**: M1.7 network transport. Filesystem + adb only today; the phone
  must always dial (S8).
- **NEXT 3**: process-per-job vs WorkManager reuse (M1.1c measured job N differs
  from job 1; three options recorded, none implemented).

## Harness — use these, they are files not heredocs
`spikes/harness/`: `provenance.py` (repo state + artifact digest + **mtime vs
source staleness**, controls must persist observations), `power.py`
(permutation floor), `canon.py`, `bansurface.py`, `admission.py` (REFUTED as a
gate, kept as a linter).
Known-provenance binaries: `spikes/S30_speed_duel/bin/known/`. The old
`fuelrun.v2.*` were built before every patch — **both agents were burned by
them** (A24).

## Guardrails added this session
A16 (pair the arms) · A17 (claim decay + `pushed_at` is not last commit) ·
A18 (one point is not a rate) · A19 (record re-derivable pre-run state) ·
A20 (controls live in the artefact; a null must be able to contain the effect) ·
A21 (a test must be able to express its verdict) · A22 (a party must not supply
the input to a check on itself) · A23 (the instrument perturbs what it observes) ·
A24 (a digest pins which artifact, not what is in it).
