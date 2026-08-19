#!/usr/bin/env python3
"""GitHub Next Autoloop Engine Driver for Operation Kingfisher.

Implements the metric-driven goal loop:
  1. Evaluate Baseline Metrics
  2. Inspect Queue & Mutation Targets
  3. Validate Safety Invariants (Hygiene, D6 Provenance, Retraction Bounds)
  4. Compare Candidate vs Baseline Scores
  5. Accept/Reject & Update External Memory (MEMORY.md)
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
CONFIG_FILE = os.path.join(REPO_ROOT, ".github", "autoloop", "config.json")
MEMORY_FILE = os.path.join(REPO_ROOT, ".github", "autoloop", "MEMORY.md")


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file not found at {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def run_evaluator(name, cmd, cwd=REPO_ROOT, timeout=120):
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        out = p.stdout.strip()
        if p.returncode != 0:
            return None, f"Exit {p.returncode}: {p.stderr.strip()}"
        # Parse JSON from evaluator output
        try:
            data = json.loads(out)
        except Exception:
            return None, f"Failed to parse JSON output: {out[:100]}"
        # An evaluator that FAILED still emits its metric keys, set to 0.0, next
        # to an "error" key. Checking only the exit code let that 0.0 be scored
        # as a real measurement: the first cold-start run reported
        # `filtered_mrr = 0.0 < min 0.25`, INVARIANT VIOLATION, REJECTED --
        # and wrote that verdict to MEMORY.md. Re-run once the artifacts existed:
        # 0.2648, above minimum, invariants pass. The metric was never bad; the
        # loop recorded a failure to measure AS a measurement of failure, which
        # is the difference between "we did not look" and "we looked and it is
        # broken". Treat a payload carrying `error` as an error regardless of
        # exit status.
        if isinstance(data, dict) and data.get("error"):
            return None, f"evaluator reported error: {data['error']}"
        return data, None
    except subprocess.TimeoutExpired:
        return None, f"Timeout after {timeout}s"
    except Exception as e:
        return None, str(e)


def evaluate_suite(config):
    print("=== [Autoloop] Running Evaluation Suite ===", file=sys.stderr)
    results = {}
    errors = []

    for name, spec in config.get("evaluators", {}).items():
        cmd = spec.get("command")
        timeout = spec.get("timeout_sec", 60)
        print(f"  -> Running evaluator '{name}': {cmd}", file=sys.stderr)
        data, err = run_evaluator(name, cmd, timeout=timeout)
        if err:
            print(f"     [ERROR] {err}", file=sys.stderr)
            errors.append((name, err))
        else:
            print(f"     [OK] {name} completed", file=sys.stderr)
            results.update(data)

    # Compute composite score
    metrics_spec = config.get("metrics", {})
    composite_score = 0.0
    total_weight = 0.0
    passed_invariants = True

    for m_name, m_spec in metrics_spec.items():
        val = results.get(m_name)
        weight = m_spec.get("weight", 1.0)
        target = m_spec.get("target", 1.0)
        min_acc = m_spec.get("min_acceptable")
        max_acc = m_spec.get("max_acceptable")
        direction = m_spec.get("direction", "maximize")

        if val is None:
            # SAY SO. This silently set invariants=False and printed nothing:
            # determinism_exact and cross_device_metta_fuel_match went missing
            # from the evaluator output and the run reported
            # `_invariants_passed: false` with no VIOLATION line anywhere, so
            # there was no way to tell "a gate failed" from "a gate never ran".
            # Those are opposite situations -- one is a real regression, the
            # other is a broken measurement -- and the loop treated them as the
            # same silent boolean.
            print(f"     [MISSING METRIC] {m_name} was not produced by any "
                  f"evaluator; invariants fail because it could not be checked, "
                  f"NOT because it regressed", file=sys.stderr)
            passed_invariants = False
            continue

        # Check invariant bounds
        if min_acc is not None and val < min_acc:
            print(f"     [INVARIANT VIOLATION] {m_name} = {val} < min {min_acc}", file=sys.stderr)
            passed_invariants = False
        if max_acc is not None and val > max_acc:
            print(f"     [INVARIANT VIOLATION] {m_name} = {val} > max {max_acc}", file=sys.stderr)
            passed_invariants = False

        # Enforce null baseline rule: candidate must strictly beat null baseline
        null_base = m_spec.get("null_baseline")
        if null_base is not None:
            if direction == "maximize" and val < null_base:
                print(f"     [NULL BASELINE VIOLATION] {m_name} = {val} < null_baseline {null_base}", file=sys.stderr)
                passed_invariants = False
            elif direction == "minimize" and val > null_base:
                print(f"     [NULL BASELINE VIOLATION] {m_name} = {val} > null_baseline {null_base}", file=sys.stderr)
                passed_invariants = False

        # Normalize score contribution
        if direction == "maximize":
            # If null baseline is set, normalize progress between [null_baseline, target]
            if null_base is not None and target > null_base:
                effective_val = max(0.0, val - null_base)
                norm_val = min(1.0, effective_val / (target - null_base))
            else:
                norm_val = min(1.0, val / target) if target > 0 else 1.0
        else:
            norm_val = min(1.0, target / max(1e-6, val))
        composite_score += norm_val * weight
        total_weight += weight

    norm_composite = round(composite_score / total_weight, 4) if total_weight > 0 else 0.0
    results["_composite_score"] = norm_composite
    results["_invariants_passed"] = passed_invariants

    # Check Pareto condition against stored baseline in MEMORY.md
    baseline_score = get_baseline_composite()
    pareto_passed = True
    if baseline_score is not None:
        if norm_composite < baseline_score:
            print(f"     [PARETO VIOLATION] Candidate composite {norm_composite:.4f} < baseline {baseline_score:.4f} (Pareto regression)", file=sys.stderr)
            pareto_passed = False
        else:
            print(f"     [PARETO PASS] Candidate composite {norm_composite:.4f} >= baseline {baseline_score:.4f}", file=sys.stderr)
    results["_pareto_passed"] = pareto_passed
    results["_baseline_score"] = baseline_score

    print(f"\n=== Composite Score: {norm_composite:.4f} (Invariants: {'PASS' if passed_invariants else 'FAIL'}, Pareto: {'PASS' if pareto_passed else 'FAIL'}) ===\n", file=sys.stderr)
    return results, errors


def get_baseline_composite():
    """Reads the highest ACCEPTED composite score recorded in MEMORY_FILE."""
    if not os.path.exists(MEMORY_FILE):
        return None
    best_score = None
    try:
        with open(MEMORY_FILE, "r") as f:
            for line in f:
                if "**ACCEPTED**" in line and "Composite score:" in line:
                    parts = line.split("Composite score:")
                    score_str = parts[1].strip().split()[0].rstrip("|").strip()
                    score = float(score_str)
                    if best_score is None or score > best_score:
                        best_score = score
    except Exception:
        pass
    return best_score


def record_memory(verdict, summary, delta_text):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    if not os.path.exists(MEMORY_FILE):
        return

    row = f"| {now} | Autoloop Driver | Full Suite | Automated Step | {delta_text} | **{verdict}** | {summary} |\n"
    content = open(MEMORY_FILE, "r").read()
    if "## 1. Iteration History Log" in content:
        parts = content.split("## 1. Iteration History Log")
        header_table = parts[1].split("\n\n")[0]
        # Append row
        updated_part = header_table + "\n" + row
        new_content = parts[0] + "## 1. Iteration History Log" + updated_part + "\n\n" + "\n\n".join(parts[1].split("\n\n")[1:])
        with open(MEMORY_FILE, "w") as f:
            f.write(new_content)


def main():
    parser = argparse.ArgumentParser(description="GitHub Next Autoloop Driver for Operation Kingfisher")
    parser.add_argument("--eval", action="store_true", help="Run evaluation suite and display metrics")
    parser.add_argument("--step", action="store_true", help="Execute one optimization loop step")
    parser.add_argument("--ci", action="store_true", help="Run in CI mode with strict exit code")
    args = parser.parse_args()

    config = load_config()
    results, errors = evaluate_suite(config)

    if args.eval:
        print(json.dumps(results, indent=2))
        return 0 if not errors else 1

    invariants = results.get("_invariants_passed", False)
    pareto = results.get("_pareto_passed", True)
    hygiene = results.get("hygiene_score", 0.0)

    if args.ci:
        if not invariants or hygiene < 1.0 or errors or not pareto:
            print("[CI FAIL] Invariants, hygiene, or Pareto condition failed.")
            return 1
        print("[CI PASS] All Autoloop invariants, targets, and Pareto condition satisfied.")
        return 0

    # Default step execution: candidate is KITCHEN-ELIGIBLE only if invariants pass, no errors, and Pareto condition satisfied
    is_eligible = bool(invariants and not errors and pareto)
    verdict = "KITCHEN_ELIGIBLE" if is_eligible else "KITCHEN_REJECTED"
    summary = f"Kitchen Composite score: {results.get('_composite_score')}"
    delta = f"MRR: {results.get('filtered_mrr')}, H@10: {results.get('hits_at_10')}"
    record_memory(verdict, summary, delta)
    print(f"[Autoloop Kitchen Complete] Candidate Status: {verdict} (NOTE: Autoloop evaluates kitchen Pareto; mission consensus is gated exclusively by independent-device digest match)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
