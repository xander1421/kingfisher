# S6 — scheduler spec

**Verdict: GREEN.** Deliverable is `SCHEDULER_SPEC.md`: every rule in BOINC's Android suspend policy mapped to a WorkManager constraint or to explicit in-worker residue.

- 14 BOINC rules mapped: **6** become declarative `Constraints`, **6** survive as in-worker logic (charge floor at 90 % is far above `BatteryNotLow`; thermal; CPU share; disk quota; fuel limit; checkpointing), **2 are deleted** as artefacts of BOINC's architecture (GUI keepalive) or of floating-point non-determinism (`hr_class`).
- Constants extracted with file:line citations: `ANDROID_KEEPALIVE_TIMEOUT = 30 s`, `ANDROID_BATTERY_BACKOFF = 300 s`, `battery_charge_min_pct = 90`, `battery_max_temperature = 40 °C`, `max_ncpus_pct = 50`, `network_wifi_only = true`.
- One substantive improvement over BOINC identified: use `PowerManager.getCurrentThermalStatus()` (API 29+) instead of the battery thermistor, because NPU load throttles the SoC long before the battery hits 40 °C.
- One hard consequence surfaced for the rest of the design: a WorkManager worker has **no guaranteed runtime**, so `fuel_limit` is not only an anti-abuse bound — it is what makes a hyperjob interruptible and re-schedulable, and it constrains how big a job may be.
- iOS assessed and explicitly deferred: `BGProcessingTaskRequest` gives no completion guarantee; BOINC ships no iOS client for the same reason.

No code was written. The spike's question was "does BOINC's policy survive translation to a modern constrained-execution API, and what is left over" — it does, and the leftovers are enumerated.
