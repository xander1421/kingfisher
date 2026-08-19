#!/usr/bin/env python3
"""S37 — WHICH `trie_witness` does each consumer actually load?

F2 said "no consumer changed verdict across the cutover" and that was TRUE and
partly VACUOUS: a consumer that never resolves to the live module cannot change
when the live module changes. This measures resolution per consumer instead of
assuming the import line means what it reads like.

Method: run each consumer in a SUBPROCESS with a sitecustomize-free shim that
imports the consumer's module and prints `trie_witness.__file__`. Consumers are
scripts, not libraries, so the shim replicates only their sys.path setup — which
is exactly the thing under test — and reads the answer out of `sys.modules`.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ROOT)
# REALPATH BOTH SIDES. The first version compared raw strings and reported
# `live 3` while five consumers were plainly resolving to the live file: their
# sys.path entries carry `..` segments, so the equal paths were unequal strings.
# A comparison that is wrong only for the passing case reads as a finding.
LIVE = os.path.realpath(os.path.join(ROOT, "spikes", "W2_witnessed_trie", "trie_witness.py"))

CONSUMERS = [
    "S20_verify_kinds/verify_kinds.py",
    "S23_consumer_sweep/probe.py",
    "S24_range_crossover/range_crossover.py",
    "S27_verify_floor/verify_floor.py",
    "S36_witnessed_job/witnessed_job.py",
    "S36_witnessed_job/attack.py",
    "S80_completeness_bytes/completeness.py",
    "S85_verify_vs_reexec/verify_vs_reexec.py",
    "W2_witnessed_trie/attack.py",
    "W6_incremental_witness/incremental_verifier.py",
    "W7_streaming_witness/streaming_verifier.py",
    "W9_bound_streaming_witness/bound_streaming_verifier.py",
]

SHIM = r'''
import runpy, sys, json, traceback
target = sys.argv[1]
err = None
try:
    # FULL RUN, not an early-stop trick. My first shim aborted at the first
    # import and reported UNRESOLVED for all 12, because it also swallowed the
    # reason with `except BaseException: pass` -- a clean-looking answer with the
    # diagnosis discarded, which is the family-B move this repo keeps paying for.
    # The exception is now REPORTED.
    runpy.run_path(target, run_name="__probe__")
except BaseException as e:
    err = f"{type(e).__name__}: {e}"
tw = sys.modules.get("trie_witness")
print("PROBE " + json.dumps({"file": getattr(tw, "__file__", None),
                             "has_v3": hasattr(tw, "path_prefix") if tw else None,
                             "error": err}))
'''


def main():
    out = {}
    for rel in CONSUMERS:
        d, f = os.path.split(rel)
        wd = os.path.join(ROOT, "spikes", d)
        p = subprocess.run([sys.executable, "-c", SHIM, f],
                           cwd=wd, capture_output=True, text=True)
        line = [l[6:] for l in p.stdout.splitlines() if l.startswith("PROBE ")]
        rec = json.loads(line[-1]) if line else {
            "file": None, "has_v3": None,
            "error": (p.stderr or "").strip()[-200:] or "no PROBE line"}
        rec["resolves_to_live"] = (os.path.realpath(rec["file"]) == LIVE) if rec["file"] else None
        out[rel] = rec

    n_live = sum(1 for v in out.values() if v["resolves_to_live"])
    n_pin = sum(1 for v in out.values() if v["file"] and not v["resolves_to_live"])
    n_none = sum(1 for v in out.values() if not v["file"])
    res = {"live_module": LIVE, "per_consumer": out,
           "n_live": n_live, "n_pinned_copy": n_pin, "n_unresolved": n_none}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "which_module.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    for k, v in out.items():
        where = "LIVE" if v["resolves_to_live"] else (
            os.path.relpath(os.path.realpath(v["file"]), ROOT) if v["file"] else "UNRESOLVED")
        print(f"  {k:<52} {where}")
    print(f"\nlive {n_live} | pinned copy {n_pin} | unresolved {n_none}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
