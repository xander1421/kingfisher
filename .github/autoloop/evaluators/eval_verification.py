#!/usr/bin/env python3
"""Autoloop Evaluator: Verification & Witness Metrics.

Under D6 discipline (H101/H107 fix):
  1. Verifies fresh provenance & incremental.json against incremental_verifier.py.
  2. If stale or missing, executes incremental_verifier.py directly.
  3. Validates kfcheck.certify ok=true.
  4. Extracts exact calculated values from incremental.json without default fallbacks.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
W6_DIR = os.path.join(REPO_ROOT, "spikes", "W6_incremental_witness")
SCRIPT_FILE = os.path.join(W6_DIR, "incremental_verifier.py")
DATA_FILE = os.path.join(W6_DIR, "incremental.json")
PROV_FILE = os.path.join(W6_DIR, "provenance.json")


def is_fresh():
    if not os.path.exists(PROV_FILE) or not os.path.exists(DATA_FILE) or not os.path.exists(SCRIPT_FILE):
        return False
    script_mtime = os.path.getmtime(SCRIPT_FILE)
    return (os.path.getmtime(PROV_FILE) >= script_mtime and os.path.getmtime(DATA_FILE) >= script_mtime)


def run_spike():
    p = subprocess.run(
        [sys.executable, SCRIPT_FILE],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    return p.returncode == 0


def main():
    if not is_fresh():
        print("Provenance stale or missing; running incremental_verifier.py...", file=sys.stderr)
        ok = run_spike()
        if not ok:
            print(json.dumps({"error": "incremental_verifier.py execution failed"}))
            return 1

    if not os.path.exists(PROV_FILE) or not os.path.exists(DATA_FILE):
        print(json.dumps({"error": "Artifacts not produced"}))
        return 1

    try:
        with open(PROV_FILE, "r") as f:
            prov = json.load(f)
        if not prov.get("ok", False):
            print(json.dumps({"error": "D6 certify ok=false"}))
            return 1

        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        records = data["corpus_benchmark"]["epoch_records"]
        last_rec = records[-1]
        cum_full = float(last_rec["cum_full_bw"])
        cum_wit = float(last_rec["cum_witness_bw"])
        bw_savings = round((1.0 - cum_wit / cum_full) * 100.0, 2)
        ram_bytes = int(last_rec["verifier_resident_bytes"])
        latencies = sorted([float(r["verifier_time_us"]) for r in records])
        median_lat_us = latencies[len(latencies) // 2]

        print(json.dumps({
            "witness_bandwidth_savings_pct": bw_savings,
            "verifier_ram_bytes": ram_bytes,
            "transition_us_median": median_lat_us,
            "status": "D6_EXECUTION_CERTIFIED",
        }))
        return 0
    except Exception as e:
        print(json.dumps({"error": f"Failed to parse verification artifacts: {e}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
