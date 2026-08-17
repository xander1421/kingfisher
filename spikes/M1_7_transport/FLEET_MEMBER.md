# M1.1 + M1.7 — the Android app is a fleet member, not an adb puppet

**10/10 jobs pulled over the dial-out transport and evaluated in-process.
9/10 byte-identical to host; the one difference is a runtime-configuration
difference, and finding it bounds what every earlier cross-check proved.**

```
installed app-debug.apk sha256 ccc7a9e6d5f3
envelopes 10/10 in 56.5 s
server: polls 11 · jobs_out 10 · shard_bytes 12,220 · results 10 · misses 0
KFWORKER: FLEET RUN: 10 jobs in 5724.1 ms, exited on idle
KFWORKER: PREFLIGHT REFUSED: battery:100%<101% -> retry with backoff
```

The chain, with nothing pushed by adb except the APK and the loopback tunnel:

```
WorkManager constraints -> per-job preflight -> HTTP long-poll -> shard by CID
  -> MeTTa in-process via JNI -> POST envelope
```

The refusal control still fires alongside the working path, so the run
demonstrates both that the worker executes and that it can decline.

## The 1/10 difference is configuration, not nondeterminism
`integration_tests__das__test.metta` does `!(import! &self das)`.

```
host fuelrun : (Error (import! ModuleSpace(GroundingSpace-top) das) Failed to resolve …
app via JNI  : () | () | (Error (das-service-status! …) ServiceN…
```

The app got **further** — it resolved the module and failed later, at the
service call. The two runtimes are not built the same way:

| | constructor | working dir |
|---|---|---|
| `fuelrun` | `Metta::new(None)` | process default |
| app (`kfjni.c`) | `metta_new_with_stdlib_loader(NULL, &space, env)` | `env_builder_set_working_dir(filesDir)` — required, because the `directories` crate resolves XDG paths that are unwritable on Android |

Different constructor and different working directory means **different module
resolution**, so a program that imports a module is comparing two environments,
not two executions.

## What this bounds
Earlier runs compared `fuelrun.android` against `fuelrun.host` — the *same*
runtime configuration on two platforms, which is the determinism claim. This run
compares **app-JNI against fuelrun**, which differ in construction, so 9/10 is
the right answer and 10/10 would have been the suspicious one.

It is a concrete instance of the LEDGER's standing warning that the equivalence
class includes the runtime environment. **A device agent and a verifier must be
built the same way, or module-touching programs will disagree without either
being wrong.** Neither the ban surface nor the quorum catches this: both
runtimes are internally deterministic and they simply answer different
questions.

Action: the admissible job class already excludes network services; `import!` of
a module whose resolution depends on the working directory belongs on the same
list. Not yet enforced.

## Also fixed here
`run_app.py` did not install the APK, so the first attempt ran the pre-port
build and timed out at 240 s looking like a transport bug. It now installs and
prints the sha256 of what it installed. **A24 again: the artifact tested was not
the artifact built**, and the digest is printed so the next person can tell.
