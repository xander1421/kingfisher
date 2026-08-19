#!/usr/bin/env python3
"""L1 — On-Device Neural Logits & Generation Byte-Level Determinism on Snapdragon 8 Elite.

Evaluates byte-identical determinism across discrete launches of Q4_0 quantized
LLM inference on Qualcomm Hexagon NPU (HTP0) / Adreno GPU / Oryon CPU.
"""

import os
import sys
import json
import subprocess
import hashlib
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
from provenance import Control, Falsifier
import kfcheck

HERE = os.path.dirname(os.path.abspath(__file__))


def run_on_device(cmd):
    p = subprocess.run(f"adb -s R5CY93675MK shell \"{cmd}\"", shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    print("==================================================================")
    print(" L1 — OFFLINE-AI NEURAL DETERMINISM ON SNAPDRAGON 8 ELITE        ")
    print("==================================================================")

    model = "SmolLM2-135M-Q4_0.gguf"
    prompt = "The capital of France is"
    ntok = 16
    reps = 4

    print(f"Target Model:  {model}")
    print(f"Prompt:        \"{prompt}\"")
    print(f"Tokens:        {ntok}")
    print(f"Repetitions:   {reps} discrete launches\n")

    cmd = f"sh /data/local/tmp/dev_run.sh {model} '{prompt}' {ntok} {reps}"
    rc, out, err = run_on_device(cmd)
    
    if rc != 0:
        print(f"ADB execution failed: {err}")
        return 1

    lines = [l.strip() for l in out.split("\n") if l.strip()]
    print(f"Raw Output Telemetry:")
    for l in lines:
        print(f"  {l}")

    hashes = [l.split()[0] for l in lines]
    lengths = [int(l.split()[1]) for l in lines]
    distinct_hashes = len(set(hashes))
    length_invariant = len(set(lengths)) == 1

    print(f"\n--- DETERMINISM EVALUATION ---")
    print(f"  Total Discrete Runs:     {len(hashes)}")
    print(f"  Distinct Hashes:         {distinct_hashes} (Required: 1)")
    print(f"  Token Length Invariance: {length_invariant} ({lengths[0]} bytes)")
    print(f"  Verdict:                 {'SELF-DETERMINISTIC (PASS)' if distinct_hashes == 1 else 'NON-DETERMINISTIC (FAIL)'}")

    final_results = {
        "device": "Samsung Galaxy S25 Ultra (SM-S938B / Snapdragon 8 Elite SM8750)",
        "model": model,
        "prompt": prompt,
        "ntok": ntok,
        "reps": reps,
        "hashes": hashes,
        "lengths": lengths,
        "distinct_hashes": distinct_hashes,
        "canonical_hash": hashes[0] if hashes else None,
        "verdict": "SELF-DETERMINISTIC" if distinct_hashes == 1 else "DIVERGENT"
    }

    with open(os.path.join(HERE, "result.json"), "w") as f:
        json.dump(final_results, f, indent=2)

    controls = [
        Control("C1_nonzero_generation_length", why="Inference produced non-empty generation", can_fail_because="early abort", null_must_contain="empty output"),
        Control("C2_fixed_extractor_pipeline", why="Prompt stripper tr/awk pipeline is deterministic", can_fail_because="unstable extraction", null_must_contain="pipeline drift"),
        Control("C3_bit_identical_invariance", why="Discrete launches yield distinct=1", can_fail_because="floating point drift", null_must_contain="hash divergence"),
    ]
    controls[0].observe(lengths[0] > 0, {"length": lengths[0]})
    controls[1].observe(length_invariant, {"lengths": lengths})
    controls[2].observe(distinct_hashes == 1, {"distinct": distinct_hashes, "hash": hashes[0]})

    falsifiers = [
        Falsifier("F1_cross_run_hash_divergence", refutes="that discrete launches produce divergent token streams", fires_when="distinct_hashes > 1", null_must_contain="hash divergence across runs"),
    ]
    falsifiers[0].observe(distinct_hashes > 1, {"distinct": distinct_hashes})

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(ROOT, "spikes", "S62_llm_backend_determinism")],
        artifacts=[os.path.join(HERE, "bench_l1.py"), os.path.join(HERE, "result.json")],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result", json.dumps(final_results, sort_keys=True))],
        falsifier="Discrete launches of Q4_0 on Hexagon NPU producing divergent token hashes",
        allow_dirty=True,
        note="L1: On-device neural logits & token stream byte-level determinism on Snapdragon 8 Elite.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    return 0 if (ok and distinct_hashes == 1) else 1


if __name__ == "__main__":
    sys.exit(main())
