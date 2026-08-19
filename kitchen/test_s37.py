#!/usr/bin/env python3
"""S37's runnable check — RE-DERIVES the soundness property, does not re-assert it.

Re-runs cutover.py, which rebuilds S36's corpus and re-measures both verifiers.
If someone reverts the v3 COVER branch, F3's exhibit collapses and F1's replay
rejection drops from 37 to 0, and this goes red.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes" / "S37_completeness_cutover"

r = subprocess.run([sys.executable, str(SPIKE / "cutover.py")],
                   capture_output=True, text=True, cwd=str(ROOT))
assert r.returncode == 0, f"cutover.py exited {r.returncode}\n{r.stdout}\n{r.stderr}"
assert "certify ok=True" in r.stdout, r.stdout

d = json.loads((SPIKE / "result.json").read_text())
n = d["n_jobs"]
assert n == 37, n
assert d["post_cutover"] == {"honest_accepted": n, "replay_rejected": n}, d["post_cutover"]
assert d["pre_cutover"]["replay_accepted"] == n, "the pre-S37 hole no longer reproduces"
ex = d["exhibit"]
assert ex["pre_s37_accepts"] is True and ex["post_s37_accepts"] is False
assert ex["proof_is_unforged"] is True, "the exhibit is a tamper, not a replay"
assert ex["omitted"] == 382, ex["omitted"]
assert d["consumers"]["identical_across_cutover"] is True
# The vacuity is part of the result and is asserted so it cannot be forgotten.
assert d["consumers"]["resolve_pinned_copy"] == 5, d["consumers"]

print("test_s37: ok -- 37/37 honest accepted, 37/37 replay rejected, "
      "382-key omission exhibited, 12 consumers stable, 5 still on the pin")
