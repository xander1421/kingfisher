#!/usr/bin/env python3
"""H197's runnable check — RE-DERIVES instability, does not re-assert a number.

Re-runs probe.py, which runs each spike four times. If someone sorts the
offending set in W7 or W9, `n_unstable_default` drops and this goes RED — which
is correct: the row's measurement no longer describes the tree and the fix wants
a before/after record.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes" / "H197_hashseed_commitment"

r = subprocess.run([sys.executable, str(SPIKE / "probe.py")],
                   capture_output=True, text=True, cwd=str(ROOT))
assert r.returncode == 0, f"probe.py exited {r.returncode}\n{r.stdout}\n{r.stderr}"
assert "certify ok=True" in r.stdout, r.stdout

# UPDATED 2026-08-19 BY H203, WHICH FIXED WHAT H197 MEASURED. NOT RELAXED.
#
# This file asserted `n_unstable_default == 10` and `== 1`. H203 replaced
# `rnd.choice(list(live_set))` with `sorted(live_set)` at four sites, so both are
# now 0 and those assertions HAD to go red. That polarity was designed and stated
# in H197's docstring -- "a red means the row's measurement no longer describes
# the tree and somebody must read the row again" -- and it is the only thing that
# would have made anyone re-read it. The pre-fix measurement is preserved in
# spikes/H197_hashseed_commitment/RESULT.md as the historical record.
#
# WHAT THIS CHECK NOW DEFENDS is stronger than what it defended before: ZERO
# unstable hashes anywhere, so a regression that reintroduces set-iteration order
# into any of these five artifacts turns it red.
d = json.loads((SPIKE / "result.json").read_text())
ps = d["per_spike"]
assert d["n_spikes_with_unstable_hashes"] == 0, (
    "a spike publishes a hash that changes between two runs -- H203 regressed: "
    f"{[k for k, v in ps.items() if v.get('n_unstable_default')]}")
for k, v in ps.items():
    if "error" in v:
        raise AssertionError(f"{k}: {v['error']}")
    assert v["n_unstable_default"] == 0, (k, v["unstable_default"])
    assert v["n_unstable_hashseed0"] == 0, (k, v["n_unstable_hashseed0"])
# NON-VACUITY: a probe that found no hashes would satisfy every line above.
assert sum(v["n_hashes"] for v in ps.values()) > 100, "the probe found no hashes"
assert d["excluded_no_commitment_in_artifact"], "the exclusion record went missing"

print("test_h197: ok -- 0 of 5 spikes publish an unstable hash "
      f"({sum(v['n_hashes'] for v in ps.values())} hashes compared); "
      "pre-fix state is H197's RESULT.md, fix is H203")
