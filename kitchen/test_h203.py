#!/usr/bin/env python3
"""H203's runnable check — re-runs the fix's own verification.

F1 is the assertion that matters and it is stronger than the test that found the
bug: two DIFFERENT hash seeds must agree, not one seed twice.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes" / "H203_stream_order_determinism"

# The fix itself, asserted at the source so a revert is caught without a run.
for rel in ("spikes/W7_streaming_witness/streaming_verifier.py",
            "spikes/W9_bound_streaming_witness/bound_streaming_verifier.py"):
    src = (ROOT / rel).read_text()
    assert "rnd.choice(list(live_set))" not in src, f"{rel}: H203 reverted"
    assert src.count("rnd.choice(sorted(live_set))") == 2, rel

r = subprocess.run([sys.executable, str(SPIKE / "probe.py")],
                   capture_output=True, text=True, cwd=str(ROOT))
assert r.returncode == 0, f"probe.py exited {r.returncode}\n{r.stdout}\n{r.stderr}"
assert "certify ok=True" in r.stdout, r.stdout

d = json.loads((SPIKE / "result.json").read_text())
assert d["n_hashes_differing_across_hashseeds"] == 0, d["per_spike"]
# NON-VACUITY: hashes must have been found and must have moved vs HEAD, or the
# zero above is the absence of a measurement rather than the presence of a fix.
assert sum(v["n_hashes"] for v in d["per_spike"].values()) > 20
assert d["n_hashes_moved_vs_HEAD"] > 0, "the edit never reached the code path"
w = d["w9_falsifier_wallclock_term"]
assert w["median_latency_us_now"] < 400.0, (
    "W9's median latency is near its 500us falsifier threshold again -- the "
    "load-vs-fix attribution in H203's RESULT.md is no longer licensed")

print(f"test_h203: ok -- 0 hashes differ across PYTHONHASHSEED 1 vs 2, "
      f"{d['n_hashes_moved_vs_HEAD']} moved vs HEAD, W9 latency headroom "
      f"{w['headroom_ratio']}x")
