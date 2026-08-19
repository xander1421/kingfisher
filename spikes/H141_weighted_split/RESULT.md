# H141 — retracted walls

The 1:1=6.874s and 3:1=5.173s walls were **sums**. `split.py` called
`ex.submit(...).result()` in a tuple, so the S24 job started after the
S25 job finished. Weighting still helped a sequential pair (0.753) but
the comparison to S25-only 3.247s was not a parallel measurement.

`split.py` now uses `wait_all` (submit every future, then wait).
Replacement numbers are in `split.json` from the H148 run on the same
pair: 1:1 **5.382s** (max 5.380), 3:1 **2.556s** (max 2.554), S25-only
**3.024s**. 3:1 beats one S25. See `spikes/H148_fleet_scale/RESULT.md`.
