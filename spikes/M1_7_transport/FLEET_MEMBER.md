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

---

# Closing the gap: 65/65 on the admitted corpus

The 9/10 became 61/65 at full scale. Three distinct causes, **two of them ours**.

## 1. The agent and verifier were built with different Cargo features
`libhyperonc` takes workspace defaults `["pkg_mgmt", "das"]`. `fuelrun` declared
`default-features = false, features = ["pkg_mgmt"]`. So `import! das` resolved in
the agent and not in the verifier — the app got *further* and looked wrong.

Building the verifier with `das` failed:
```
expected `hyperon_atom::Atom`, found a different `hyperon_atom::Atom`
```
`metta-bus-client` is a **git** dependency (`singnet/das` tag 1.0.2) that pulls
`hyperon-atom` from the registry while the workspace uses a path dep. The
hyperon workspace root carries a `[patch.'https://github.com/trueagi-io/...']`
section reconciling them — and **a crate outside the workspace does not inherit
it**. That is precisely why the agent (built inside) had `das` and the verifier
(built outside) silently did not.

Fixed by copying the patch section into `fuelrun/Cargo.toml`. Both binaries
rebuilt with matching features; `bin/known/` digests updated.

## 2. Our transport corrupted the payload it carried
The envelope was built by string concatenation with
`.replace("\"", "'")` to avoid breaking the JSON. That silently rewrote **every
double quote in every result**:

```
host: (Error (change-state! &ReplPrompt "> ") ...
dev : (Error (change-state! &ReplPrompt '> ') ...
```

Three of the four remaining mismatches were this. The earlier 10/10 passed
because those ten programs happened to contain no quotes.

**A transport that mangles the payload is worse than one that drops it** — a
drop is visible, a mangle looks like a divergence and sends you hunting the
engine. Replaced with real JSON escaping.

## 3. One genuine environment dependency, now banned at admission
`mkdocs.metta` calls `(file-open! "./docs/generated/corelib.md" ...)`. A
**relative path** resolves against the runner's working directory, which is
`filesDir` on the app and the shell cwd on the host.

This is not nondeterminism: each runtime is internally deterministic and both
report their own filesystem honestly. **Quorum cannot detect it** — every
replica would answer correctly about a different filesystem.

Added the whole `fileio.rs` surface to `bansurface.py`, enumerated from its
`register_function` calls: `file-open!`, `file-read-exact!`,
`file-read-to-string!`, `file-write!`, `file-seek!`, `file-get-size!`.

```
corpus 67: ADMIT 65  REJECT 2
  REJECT mkdocs.metta                       ['filesystem']
  REJECT python__sandbox__test_gnd_conv.metta  ['flip']
```

The first version of that regex used `\b` after the trailing `!` and **never
matched** — `!` and the following space are both non-word characters, so there
is no boundary. Caught by the assertion written alongside it.

## Result
```
envelopes 65/65 in 56.4 s · 66 polls · 174,804 shard bytes · 0 misses
ADMITTED CORPUS, app-in-process vs host: 65/65
```

## What the sequence shows
Four "divergences" between an agent and its verifier: **one was a build-config
difference, three were our own tooling, and one was a real environment
dependency that replication is structurally blind to.** Zero were engine
nondeterminism.

That ratio is the lesson. Before attributing a cross-platform difference to the
thing being measured, the build configuration, the transport encoding and the
environment have to be eliminated — and each of those is easier to get wrong
than the engine is.
