# REPORT: BOINC

## 1. Identity
- URL: https://github.com/BOINC/boinc
- Commit: `19689c30c82e9e29cef6e60d55f6089a62848ac2` (2026-08-16 — same day as this recon)
- License: **LGPL-3.0** (`COPYING.LESSER`, GPL-3 text also present as `COPYING`). Per-file headers say "LGPL v2.1 or, at your option, any later version" — © 2002-2019 University of California.
- Gate: **copyleft — never copy code into our permissive tree.** LGPL permits *dynamic linking* of an unmodified library, but BOINC's value here is scheduler *policy* and *schema*, not a linkable library. **Everything BOINC-derived in the gap matrix is SPEC: study, write our own spec, clean-room implement.** This report is written to be that spec's source document.

## 2. Shape
- 587 `.cpp` + 421 `.h` = **309,586 LOC** of C/C++, plus 344 PHP (project server web), **194 Kotlin** (the Android client), 269 XML, 114 shell.
- Build: autotools (`configure.ac`, `Makefile.am`) for the client/server; Gradle for `android/BOINC`; per-arch NDK scripts `android/build_boinc_arm64.sh` etc.
- Twenty-plus years of accumulated `checkin_notes_2002 … 2012` — a useful archaeology, not a liability.

| dir | role |
|---|---|
| `client/` | the compute client: `client_state.{h,cpp}`, `cs_prefs.cpp` (**the suspend policy**), `app_control.cpp`, `cpu_sched.cpp` |
| `sched/` | server side: `validator.cpp`, `validate_util2.cpp`, `credit.cpp`, `sample_bitwise_validator.cpp`, `script_validator.cpp` |
| `db/` | `boinc_db_types.h` (**the WORKUNIT / RESULT schema**), `schema.sql` |
| `lib/` | `prefs.{h,cpp}` (the preference vocabulary + defaults), `common_defs.h` |
| `android/` | Gradle app (`android/BOINC`), NDK build scripts, `Android_Verification_Matrix.md` |
| `api/`, `apps/`, `tools/`, `html/` | app-side API, samples, project tooling, PHP web |

## 3. Entry points
- Client: `CLIENT_STATE` in `client/client_state.cpp`; the policy question `CLIENT_STATE::check_suspend_processing()` at `client/cs_prefs.cpp:218` is called every poll and returns a `SUSPEND_REASON_*`.
- Android: the C++ client runs as a **separate native process** supervised by a Kotlin `Monitor` service (`android/BOINC/app/src/main/java/edu/berkeley/boinc/client/Monitor.kt`) that speaks GUI RPC to it over a socket; `DeviceStatus.kt` pushes battery/screen/wifi state in.
- Server: `sched/validator.cpp` main loop → `check_set()` per work unit.

## 4. Extraction targets

### 4.1 Work unit + result schema (`db/boinc_db_types.h:466` and `:623`)
**WORKUNIT** — the fields that matter to us:
- Work description: `xml_doc` (BLOB, the job spec), `appid`, `name`, `batch`, `result_template_file`, `keywords`, `size_class`, `app_version_num`.
- **Resource bounds, all as declared upper bounds**: `rsc_fpops_est` (estimate, used to predict runtime), **`rsc_fpops_bound`** (hard upper bound; exceeding it aborts the task), `rsc_memory_bound`, `rsc_disk_bound`, `rsc_bandwidth_bound`.
- **Redundancy control**: `min_quorum`, `target_nresults` (≥ min_quorum, over-issued to absorb loss), `max_error_results`, `max_total_results`, **`max_success_results`** ("if #success results exceeds this without consensus, i.e. WU seems nondeterministic, mark WU_ERROR_TOO_MANY_SUCCESS_RESULTS").
- Consensus outcome: `need_validate`, `canonical_resultid`, `canonical_credit`.
- **`hr_class`** — homogeneous redundancy: send replicas only to *numerically similar* hosts, because floating-point differs across CPU/compiler/library. Also `app_version_id` + `homogeneous_app_version`.
- Deadlines: `delay_bound` (→ each result's `report_deadline`), `transition_time`.

**RESULT**: `workunitid`, `hostid`, `userid`, `server_state`, `outcome`, `client_state`, `validate_state`, `report_deadline`, `sent_time`, `received_time`, `cpu_time`, `elapsed_time`, `flops_estimate`, `exit_status`, `claimed_credit`, `granted_credit`, **`xml_doc_out` — "MD5s of output files"**, `stderr_out`.

**Direct read for the hyperjob tuple.** `rsc_fpops_bound` is `fuel_limit` under another name — and BOINC needed it for exactly our reason: to bound an untrusted computation and kill it deterministically. `xml_doc_out` carrying output MD5s is `result_hash`. `min_quorum`/`target_nresults` is `replication_policy`. **`hr_class` is the field we get to delete**: it exists only because floating-point isn't reproducible across hosts. MeTTa reduction is discrete and deterministic, so we can replicate across *any* two devices — a strictly stronger position than BOINC ever had, and the reason our verification is cheaper than theirs.

### 4.2 Redundancy / quorum + credit
- `sched/validate_util2.cpp`: given the results of a WU, `init_result()` each; once the number of good results ≥ `wu.min_quorum`, look for a canonical result — **"a set of at least `min_quorum/2+1` results that are equivalent according to `check_pair()`"**. Majority of the quorum, not of everything received.
- `check_pair()` is project-supplied. `sched/sample_bitwise_validator.cpp` is the strictest instance: MD5 every output file (`md5_file()`), compare the vectors, byte-equality or nothing. There is also `sample_substr_validator`, `script_validator` (shell out), and fuzzy numeric comparison for float apps.
- Credit (`sched/credit.cpp`): `fpops_to_credit(fpops) = fpops * COBBLESTONE_SCALE`, with `COBBLESTONE_SCALE = 200/86400e9` (`lib/common_defs.h:63`) — i.e. **200 credits per day of sustained 1 GFLOPS**. Claimed credit is `cpu_time × device flops`; granted credit is the WU's canonical credit, so *all* correct replicas get the same amount regardless of who was slower. `credit.h` keeps `pfc_samples` (peak-FLOPS-count history) per host/app-version to normalise dishonest or wildly-varying hardware claims.
- Lesson we should copy: **pay the canonical amount, not the claimed amount.** It removes the incentive to lie about hardware or to run slowly.

### 4.3 The Android client's charging / idle / thermal policy — **file paths and constants**
All in `client/cs_prefs.cpp`, function `CLIENT_STATE::check_suspend_processing()`:

Non-Android checks first (`cs_prefs.cpp:218-277`), in order: benchmarks running → `start_delay` → OS-requested suspend → run mode NEVER → `!run_on_batteries && host_is_running_on_batteries()` → `!run_if_user_active && user_active` → `cpu_times.suspended(now)` (time-of-day window) → `suspend_if_no_recent_input` (idle-time ceiling) → exclusive app running → non-BOINC CPU usage above limit, with a **2×`MEMORY_USAGE_PERIOD` hysteresis** before resuming.

Then, `#ifdef ANDROID` (`cs_prefs.cpp:278-324`):
1. **GUI keepalive**: if no RPC from the Kotlin GUI within `ANDROID_KEEPALIVE_TIMEOUT = 30` s (`client/client_state.h:704`), the client **exits** — battery data is only trustworthy while the supervisor is alive.
2. **Thermal**: `battery_state == BATTERY_STATE_OVERHEATED` **or** `battery_temperature_celsius > global_prefs.battery_max_temperature` → suspend and set `battery_heat_resume_time = now + ANDROID_BATTERY_BACKOFF` (`= 300` s, `client_state.h:708`). Comment in-source: *"crude hysteresis"*.
3. **Charge floor**: `battery_charge_pct < global_prefs.battery_charge_min_pct` → suspend, `battery_charge_resume_time = now + 300` s.
4. Both backoffs are re-checked as separate `SUSPEND_REASON_BATTERY_*_WAIT` states, so a recovered device still waits out the 5 minutes.

Android defaults (`lib/prefs.cpp:208-239`):
| pref | Android default |
|---|---|
| `battery_charge_min_pct` | **90** |
| `battery_max_temperature` | **40 °C** |
| `max_ncpus_pct` | **50** (desktop: 0 = all) |
| `network_wifi_only` | **true** (desktop: false) |
| `cpu_usage_limit` | 100 |
| `niu_max_ncpus_pct` / `niu_cpu_usage_limit` | 100 / 100 (when not in use) |

Signal acquisition is on the Kotlin side (`client/DeviceStatus.kt`): `ACTION_BATTERY_CHANGED` sticky broadcast → `EXTRA_LEVEL`/`EXTRA_SCALE` (charge %), `EXTRA_TEMPERATURE`, `EXTRA_PLUGGED` (AC / USB / WIRELESS, each separately preference-gated: `powerSourceAc`, `powerSourceUsb`, `powerSourceWireless`), plus `screenOn` and wifi from `ConnectivityManager`. There is a `suspendWhenScreenOn` preference and a `stationaryDeviceMode` for permanently-plugged devices.

Mapped to modern Android WorkManager constraints in `spikes/S6_scheduler/SCHEDULER_SPEC.md`.

## 5. Verdict for the mission
The schema and the policy are twenty years of hard-won operational truth and they map onto our design almost field for field — but the licence means we take the *design*, never the code. The most valuable single insight is negative: half of BOINC's verification machinery (`hr_class`, homogeneous app versions, fuzzy comparators) exists to work around floating-point non-reproducibility. Our workload does not have that problem, so we get BOINC's redundancy guarantees at a fraction of BOINC's complexity.
