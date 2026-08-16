#!/usr/bin/env python3
"""Print one line per sweep_<D>.json produced by hdc.py."""
import glob
import json

rows = []
for path in glob.glob("sweep_*.json") + ["run1.json"]:
    try:
        d = json.load(open(path))
    except (OSError, ValueError):
        continue
    a = d["analytic_threshold"]
    rows.append((d["config"]["D"], d["int8_bytes_scanned"] / 1e6,
                 a["every_match_scores_exactly_2x_nonzero_dims"],
                 a["false_positives_total"],
                 d["by_k"]["10"]["recall_at_k_mean"],
                 d["by_k"]["50"]["recall_at_k_mean"],
                 d["separation"]["nonmatch_max"],
                 a["threshold_min"],
                 d["timing_s"]["matmul"]))

print(f"{'D':>6} {'T_MB':>7} {'exact':>6} {'falsepos':>9} {'rec@10':>7} "
      f"{'rec@50':>7} {'nonmatch_max':>13} {'thr_min':>8} {'matmul_s':>9}")
for r in sorted(set(rows)):
    print(f"{r[0]:>6} {r[1]:>7.0f} {str(r[2]):>6} {r[3]:>9} {r[4]:>7.4f} "
          f"{r[5]:>7.4f} {r[6]:>13} {r[7]:>8} {r[8]:>9.2f}")
