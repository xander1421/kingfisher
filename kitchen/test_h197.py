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

d = json.loads((SPIKE / "result.json").read_text())
ps = d["per_spike"]
assert d["n_spikes_with_unstable_hashes"] == 2, d["n_spikes_with_unstable_hashes"]
assert d["n_explained_by_hash_order"] == 2, d["n_explained_by_hash_order"]
assert ps["W7_streaming_witness"]["n_unstable_default"] == 10
assert ps["W9_bound_streaming_witness"]["n_unstable_default"] == 1
# every instability must vanish under PYTHONHASHSEED=0, or the diagnosis is wrong
for k, v in ps.items():
    if "error" in v:
        raise AssertionError(f"{k}: {v['error']}")
    assert v["n_unstable_hashseed0"] == 0, (k, v["n_unstable_hashseed0"])
# and at least one spike must be stable, or the probe distinguishes nothing
assert any(v["n_unstable_default"] == 0 for v in ps.values())
assert d["excluded_no_commitment_in_artifact"], "the exclusion record went missing"

print("test_h197: ok -- 2 of 5 spikes publish an unstable hash, "
      "all instability removed by PYTHONHASHSEED=0, 3 spikes stable")
