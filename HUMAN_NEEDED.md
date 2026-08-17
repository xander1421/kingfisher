# HUMAN_NEEDED — work only a human can do
Append, never stop. Each entry: what · why the agent can't · artifact · ask.

## Standing
1. **File the hyperon PR (U1).** §10 forbids external posts. Artifact:
   `proposed/hyperon-nondeterminism/` — README (correctness framing, 40%
   wrong cardinality), 3 patches applying clean to `3f76dc4`, 319 tests pass,
   S57 corpus 0 rows differing. **Ask: open the issue + PR.**
2. **Post the MORK issue-#2 comment (U2).** Same rail. Artifact pending.
3. **File the DAS concurrency report.** Artifact:
   `proposed/das-concurrency/` — opens with a question ("was the async path
   meant to be restored?"), 1 patch, model-validated 50/50 vs 0/8.
   **Ask: open the issue.**
4. **A design partner's query stream.** Shard demand is the load-bearing
   unmeasured quantity and **cannot be measured from inside the workspace** —
   S52's generator samples uniformly over triples, an artefact. The buyer is
   now the missing instrument, not just the business risk.
5. **Two more Android devices** for M1-DEMO and for L1's cross-device half.

## Added by ATTACK cycle 4
6. **Upstream `cfg`-gate for the minimal build.** D5's ban surface is only 2/5
   enforceable today: `das` and the Python bindings can be dropped, but
   `math.rs`, `fileio` and `random` carry **zero** `cfg(feature` lines, so
   `sin-math`, `file-open!` and `flip` cannot be removed by build. One upstream
   change — `#[cfg(feature = "minimal")]` around those registrations — closes
   all three, and it is the same ask as M0.2 for `json.rs`.
   **Ask: raise it with the hyperon maintainers alongside U1.**
7. **Note on W1, for anyone briefed on it before today.** W1 was cited in
   conversation as killing S69's traffic objection and restoring the fleet-wide
   verification pool. It is now **INVALID**. If that claim reached anyone
   outside the workspace, it needs retracting: the witness is 1.54–12.23 MB, not
   4.4 KB, because the measured engine reads the whole prefilter index on every
   query.

- **hyperon: `libhyperonc.so` is built without a `SONAME`.** Any consumer linking
  the C API records the absolute host build path in `DT_NEEDED`; on Android the
  APK then fails `dlopen` with a `/Users/...` path. One-line fix upstream
  (`-Wl,-soname,libhyperonc.so` in the cdylib link args). Found in M1.1.
  Unfiled: publishing is disallowed by §11.

- **`hyperjob` needs a result kind for a panic, or panics declared unattributable
  in writing.** A panic is deterministic (both devices abort identically) but
  produces no envelope. `RESULT_FUEL_EXHAUSTED` is deterministic and payable;
  `RESULT_DEADLINE_EXCEEDED` is infrastructure and unpaid; a panic is neither.
  Silence means the first production panic is classified by whatever the code
  happens to do. M1.8c currently answers `AGREED_FAILURE` and refuses payment —
  a safe default, not a specification.
