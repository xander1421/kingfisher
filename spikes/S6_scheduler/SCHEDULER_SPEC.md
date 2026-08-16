# S6 — Charge-time scheduler spec (BOINC policy → Android WorkManager)

**Verdict: GREEN** (design spike; no code, by design — the deliverable is the mapping).

Source of truth for the left column: `elders/boinc/client/cs_prefs.cpp` `CLIENT_STATE::check_suspend_processing()`, `elders/boinc/client/client_state.h:704-709`, `elders/boinc/lib/prefs.cpp:200-240`, `elders/boinc/android/BOINC/app/src/main/java/edu/berkeley/boinc/client/DeviceStatus.kt`.
**Licence note: BOINC is LGPL-3.0. Nothing below is copied code. This is a written spec derived from observed behaviour, to be implemented clean-room** (see `analysis/LICENSE_LEDGER.md`).

## 0. The structural difference, first

BOINC on Android is a **long-lived native process** babysat by a Kotlin service that feeds it battery telemetry every ≤30 s; if the telemetry stops, the client kills itself (`ANDROID_KEEPALIVE_TIMEOUT`). That architecture is a fight against the platform, and it is why BOINC needs a foreground service, an exemption from battery optimisation, and its own hysteresis logic.

Our device agent should **not** be a daemon. It should be a `CoroutineWorker` that WorkManager starts when the constraints are already satisfied and stops when they stop being satisfied. The OS then owns the policy that BOINC hand-rolls, and every BOINC rule below either (a) becomes a declarative constraint, or (b) survives as in-worker logic because WorkManager has no equivalent.

## 1. Rule-by-rule mapping

| # | BOINC rule (file:symbol) | Android mechanism | Notes / residue |
|---|---|---|---|
| 1 | `!run_on_batteries && host_is_running_on_batteries()` → `SUSPEND_REASON_BATTERIES` | `Constraints.setRequiresCharging(true)` | Exact match. WorkManager stops the worker on unplug and reschedules; no polling. |
| 2 | Charge floor: `battery_charge_pct < battery_charge_min_pct` (default **90**) | `setRequiresBatteryNotLow(true)` **+ in-worker check** | `BatteryNotLow` only fires at the system low-battery threshold (~15 %), *far* below BOINC's 90 %. Read `BatteryManager.EXTRA_LEVEL/EXTRA_SCALE` in `doWork()` and `Result.retry()` below the configured floor. **Residue: yes.** |
| 3 | Thermal: `battery_temperature_celsius > 40` or `BATTERY_STATE_OVERHEATED` | `PowerManager.getCurrentThermalStatus()` + `addThermalStatusListener` (API 29+) | Prefer the OS thermal status (`THERMAL_STATUS_MODERATE` and above ⇒ stop) over a raw battery-temperature threshold — it accounts for SoC and skin temperature, which a 2013-era battery thermistor rule does not. Fall back to `EXTRA_TEMPERATURE > 40 °C` below API 29. **Residue: yes.** |
| 4 | Thermal/charge backoff `ANDROID_BATTERY_BACKOFF = 300 s` before resuming | `Result.retry()` + `setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, MINUTES)` | WorkManager's exponential backoff starting at 5 min reproduces the hysteresis and improves on it (BOINC's own comment calls the fixed 300 s *"crude hysteresis"*). |
| 5 | `!run_if_user_active && user_active`; `suspendWhenScreenOn` | `setRequiresDeviceIdle(true)` | Idle in WorkManager means screen off **and** the device has been idle a while — stricter than BOINC's "screen off". Combined with (1) this is the literal "phones compute at charge time" of the mission. |
| 6 | `network_wifi_only` (Android default **true**) | `setRequiredNetworkType(NetworkType.UNMETERED)` | Exact match, and `UNMETERED` correctly handles metered-Wi-Fi, which BOINC's wifi check does not. |
| 7 | `max_ncpus_pct` (Android default **50 %**) | in-worker: `Runtime.availableProcessors()/2`, sized thread pool | No WorkManager equivalent. On big.LITTLE, prefer *count* over *affinity*: Android gives no reliable core pinning. **Residue: yes.** |
| 8 | `rsc_disk_bound`, `allowed_disk_usage()` | `setRequiresStorageNotLow(true)` + own quota against `Context.getFilesDir()` | Shard cache must self-evict; see (12). **Residue: yes.** |
| 9 | `cpu_times.suspended(now)` — time-of-day window | `PeriodicWorkRequest` window, or an in-worker clock check | Rarely wanted; keep as an optional user preference. |
| 10 | `rsc_fpops_bound` → abort task that overruns | in-worker fuel limit: bounded `interpret_step` count | Our version is *better than* a FLOP bound: it is exact and reproducible (see `reports/REPORT_hyperon-experimental.md` §C API). This is the `fuel_limit` of the hyperjob tuple. **Residue: yes — and it is the core of the design, not an afterthought.** |
| 11 | `delay_bound` → `report_deadline` per result | `setInitialDelay` / the job's own deadline field; worker must checkpoint | WorkManager can stop a worker at any moment; every job needs a resumable checkpoint or a "fits in one window" size bound. **Residue: yes.** |
| 12 | Project disk share, `file_deleter` | LRU over the content-addressed shard cache, keyed by CID | Content addressing makes eviction safe: anything evicted is re-fetchable and identical. |
| 13 | GUI keepalive (30 s) or the client exits | **deleted** | Pure consequence of BOINC's two-process design. We have one process; the constraint system is the supervisor. |
| 14 | `hr_class` homogeneous redundancy | **deleted** | Only needed for float reproducibility. MeTTa reduction is discrete and deterministic — any two devices are comparable. See `reports/REPORT_BOINC.md` §4.1. |

## 2. The resulting constraint set

```kotlin
val constraints = Constraints.Builder()
    .setRequiresCharging(true)            // rule 1
    .setRequiresDeviceIdle(true)          // rule 5
    .setRequiredNetworkType(NetworkType.UNMETERED)   // rule 6
    .setRequiresBatteryNotLow(true)       // rule 2, coarse half
    .setRequiresStorageNotLow(true)       // rule 8, coarse half
    .build()

val work = OneTimeWorkRequestBuilder<HyperjobWorker>()
    .setConstraints(constraints)
    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, TimeUnit.MINUTES)  // rule 4
    .setInputData(workDataOf("job_cid" to cid))
    .build()
```

In-worker preflight, in order, each returning `Result.retry()`:
1. thermal status ≥ `THERMAL_STATUS_MODERATE` (rule 3)
2. battery level < configured floor, default 90 % (rule 2)
3. free cache space below the shard the job needs (rule 8)
Then run with `min(1, availableProcessors()/2)` threads (rule 7), a hard `fuel_limit` on interpreter steps (rule 10), and a checkpoint written at every fuel-checkpoint interval (rule 11).

## 3. What Android gives us that BOINC never had
- **`ThermalStatus` is a system-wide, vendor-calibrated signal.** BOINC infers heat from one battery thermistor. Under sustained NPU load the SoC throttles long before the battery reaches 40 °C, so a battery-temperature rule would let us run hot and slow; the thermal API tells us to stop.
- **Constraints are enforced by the OS, not polled.** No keepalive, no 300 s timer, no wakelock, no battery-optimisation exemption prompt — which is also the difference between an app users keep and one they uninstall.
- **`WorkManager` survives reboot and process death** without a foreground-service notification.

## 4. What Android takes away — the honest list
- **No guaranteed runtime.** A worker can be stopped at any moment (`onStopped()`), so a job must either fit comfortably inside one charge window or checkpoint. This is the single biggest design constraint on the hyperjob's `fuel_limit`: fuel is not just an anti-abuse bound, it is the unit that makes jobs *interruptible and re-schedulable*.
- **No background network server.** A phone can never be dialled. All coordination is phone-initiated pull, which rules out the DAS/NuNet assumption of a reachable peer (see `reports/REPORT_NuNet_DMS.md` blocker #9).
- **`setRequiresDeviceIdle(true)` can starve** on a phone that is never idle-while-charging (bedside charging is the good case; a phone charging in a car is not). Ship a preference to relax idle to "screen off", accepting the user-experience risk BOINC accepted with `suspendWhenScreenOn`.
- **Doze deferral** means "charge-time" in practice is a nightly batch, not a continuous stream. Job sizing and market latency expectations must assume a *once-a-day, multi-hour* window per device, not a live worker pool.

## 5. iOS, for completeness
There is no iOS equivalent of this table. `BGProcessingTaskRequest` (`requiresExternalPower = true`, `requiresNetworkConnectivity = true`) is the closest primitive, but the OS grants runtime opportunistically, gives no completion guarantee, and enforces a hard expiration handler. BOINC has no iOS client for exactly this reason. Treat iOS as: **Rung-2 NPU pre-filter jobs only, small, best-effort, never on the critical path** — or not at all in the first two milestones. Tracked in `out/RISKS.md`.
