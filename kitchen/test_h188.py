#!/usr/bin/env python3
"""H188's runnable check — RE-DERIVES, it does not re-assert.

H187's class is that a kitchen check reading a committed `result.json` and
re-asserting the numbers in it stays green over exactly the rot it should
catch. So this check RE-RUNS `attack.py`, which re-imports S91's live `run.py`.

POLARITY, stated deliberately: if S91 is ever FIXED -- if its worker starts
reading its `agent`, or its pin is really compared -- F1 or F3 fires and this
check goes RED. That is correct and is the point. A red here means H188's
finding no longer describes the tree and somebody must read the row again, not
that S91 is broken.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes" / "H188_seats_are_one_computation"

r = subprocess.run([sys.executable, str(SPIKE / "attack.py")],
                   capture_output=True, text=True, cwd=str(ROOT))
assert r.returncode == 0, f"attack.py exited {r.returncode}\n{r.stdout}\n{r.stderr}"
assert "certify ok=True" in r.stdout, r.stdout

res = json.loads((SPIKE / "result.json").read_text())
for name, c in res["controls"].items():
    assert c["fired"] is True, f"control {name} did not fire"
for name, f in res["falsifiers"].items():
    assert f["fired"] is False, f"falsifier {name} FIRED -- re-read H188/RESULT.md"

f = res["findings"]
assert f["arm0"]["matches_committed"] is True, "arm0 no longer reproduces S91"
assert f["armA"]["seat_reads"] == 0 and f["armA"]["tripwire_live"] is True
assert f["armB"]["max_distinct_digests_per_job_across_5_seats"] == 1
assert f["armB"]["s91_distinct_digests"] == f["armB"]["s91_corpus_jobs"]
assert f["armB"]["real_chain_distinct_hashes"] < f["armB"]["real_chain_jobs"]
assert f["armC"]["identical_to_baseline"] is True, "wrong pin now changes the verdict"
assert f["armD"]["fictional_F3_fired"] is False
assert f["armD"]["collapsed_F3_fired"] is True, "axis audit no longer responds"
assert f["armE"]["real_chain_operator_strings"] == ["operator:self"]

print("test_h188: ok -- 3 controls fired, 3 falsifiers did not, 7 arm assertions")
