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
    """Run one evaluator and return (payload, error).

    v2, H245. DEFECT REMOVED: this returned on `p.returncode != 0` BEFORE
    `json.loads` was ever reached, so an evaluator that RAN AND REFUSED and one
    that CRASHED were the same event -- and the scoring loop below then printed
    `could not be checked` over a metric it had checked.

    Live at the time, not latent: `eval_hygiene.main()` ends
    `return 0 if all_ok else 1` and prints a complete payload either way, so
    `--eval` reported `[ERROR] Exit 1:` with an EMPTY stderr followed by
    `[MISSING METRIC] hygiene_score`, and the two refcheck violations it had
    actually found were nowhere in the loop's output.

    THE RULE, because the harness has now got this wrong in BOTH directions:
    READ THE CHANNEL THE VERDICT IS ACTUALLY CARRIED ON. A selfcheck answers a
    boolean, so its state is the EXIT CODE and its stdout is prose -- judging
    the text there reads a crash as clean, which is H72, and
    `spikes/harness/selfcheckall.py:122` says exactly that. An evaluator
    answers with a NUMBER, which an exit code cannot carry, so its state is the
    PAYLOAD. Ten lines below, this same function already applied that rule in
    the exit-0 direction -- *"Treat a payload carrying `error` as an error
    regardless of exit status"* -- and never in this one.

    NOT A LOOSENING, and that is the arm to check first: a recovered payload is
    gated on its own value like any other. `hygiene_score 0.0` now fails
    invariants as an INVARIANT VIOLATION instead of vanishing as a MISSING
    METRIC -- the same FAIL, for the true reason, and it costs the composite
    MORE because a missing metric contributes no weight at all.

    Also v2: a payload that parses but is not a dict (a list, a bare scalar) is
    now an error. `results.update(data)` raises on a list, so the pre-v2 runner
    handed the scoring loop something it could not consume.
    """
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
        # PARSE FIRST. The exit code decides nothing on its own (H245).
        try:
            data = json.loads(out)
        except Exception:
            data = None
        if not isinstance(data, dict):
            if p.returncode != 0:
                return None, (f"Exit {p.returncode} and no parseable metric "
                              f"payload on stdout -- this is a CRASH, not a "
                              f"refusal: {p.stderr.strip() or out[:100]}")
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
        if data.get("error"):
            return None, f"evaluator reported error: {data['error']}"
        if p.returncode != 0:
            # BOTH SIGNALS, NEVER ONE INSTEAD OF THE OTHER. The defect was that
            # the MEASUREMENT was discarded, not that the exit code should be
            # ignored -- so the payload is scored AND the refusal is still an
            # error. Returning only the payload here would have been a real
            # loosening on one path: `is_eligible` is
            # `invariants and not errors and pareto`, so an evaluator that
            # refused while emitting in-bounds metrics would have gone from
            # REJECTED to ELIGIBLE. Caught by reading the caller, not by any
            # arm of the probe.
            return data, (f"Exit {p.returncode}: evaluator REFUSED, and its "
                          f"payload was complete -- the measurement is kept "
                          f"and scored on its own value, and this refusal is "
                          f"still an error (H245)")
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
        # H245: "it errored" and "it produced no measurement" are INDEPENDENT.
        # Collapsing them is the defect this whole change is about, so they are
        # now read as two separate facts rather than as one if/else.
        if err and data is not None:
            print(f"     [REFUSED BUT MEASURED] {name}: {err}", file=sys.stderr)
        elif err:
            print(f"     [ERROR] {err}", file=sys.stderr)
        else:
            print(f"     [OK] {name} completed", file=sys.stderr)
        if err:
            errors.append((name, err))
        if data is not None:
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

        # Enforce null baseline rule: candidate must strictly beat null baseline.
        #
        # THE NULL IS SELECTED BY THE SPLIT THE EVALUATOR DECLARES, not by a
        # constant. AGENT-2's catch, and it was against my own work: `config.json`
        # grew a `split_nulls` table recording the measured no-rules prior for
        # each split, and `grep -rn split_nulls` found NO CONSUMER anywhere --
        # three nulls recorded as data and nothing read them. *A check that
        # reports but does not gate is prose with extra steps.*
        #
        # Why per-split and not one number: a bar is a MARGIN OVER ITS OWN
        # SPLIT'S NULL, never a bare value. The same system scores 0.2648 on the
        # 70/15/15 shuffle and 0.1358 on the leak-free pair-disjoint split, and
        # the shuffle's own null is 0.172163 (G106) against pair-disjoint's
        # 0.173226 (G104, reproducing G49's 0.1732 from scratch). The null is
        # leak-INSENSITIVE -- so on the shuffle the system reads +0.0926 and on
        # the honest split it reads -0.0374. Comparing a shuffle number to a
        # pair-disjoint null would score the leak as if it were a gain.
        #
        # A SPLIT WITH NO MEASURED NULL CANNOT BE GATED AND MUST NOT PASS. That
        # is the state `shuffle_70_15_15` was in when this was written, and the
        # whole failure being fixed is a gate that passed because its bar came
        # from the number it gated.
        null_base = m_spec.get("null_baseline")
        split_nulls = m_spec.get("split_nulls")
        declared_split = results.get("split")
        if split_nulls:
            if declared_split is None:
                print(f"     [UNGATEABLE] {m_name} has per-split nulls but the "
                      f"evaluator declared no `split`; a number without its split "
                      f"is not a number and cannot be gated", file=sys.stderr)
                passed_invariants = False
                null_base = None
            elif declared_split not in split_nulls:
                print(f"     [UNGATEABLE] {m_name} was measured on split "
                      f"'{declared_split}', which has no entry in split_nulls; "
                      f"its null has never been measured", file=sys.stderr)
                passed_invariants = False
                null_base = None
            else:
                entry = split_nulls[declared_split]
                measured = entry.get("null_mrr") if isinstance(entry, dict) else entry
                if measured is None:
                    print(f"     [UNGATEABLE] {m_name} on split "
                          f"'{declared_split}': null_mrr is NEVER MEASURED, so "
                          f"no margin can be computed and this cannot pass",
                          file=sys.stderr)
                    passed_invariants = False
                    null_base = None
                else:
                    null_base = measured
                    print(f"     [SPLIT NULL] {m_name} gated against "
                          f"'{declared_split}' null {measured} "
                          f"(margin {val - measured:+.4f})", file=sys.stderr)
        if null_base is not None:
            if direction == "maximize" and val < null_base:
                print(f"     [NULL BASELINE VIOLATION] {m_name} = {val} < null_baseline {null_base}", file=sys.stderr)
                passed_invariants = False
            elif direction == "minimize" and val > null_base:
                print(f"     [NULL BASELINE VIOLATION] {m_name} = {val} > null_baseline {null_base}", file=sys.stderr)
                passed_invariants = False

        # Normalize score contribution.
        #
        # A WITHDRAWN TARGET IS A LEGITIMATE STATE AND THIS CRASHED ON IT.
        # When the operator withdrew the graph-AI floors, `filtered_mrr` and
        # `hits_at_10` were set to `target: null` / `min_acceptable: null` --
        # both bars were derived from the leaky 0.2648/0.3929 and neither could
        # honestly be kept. The next `--eval` died with
        #   TypeError: '>' not supported between instances of 'NoneType' and 'float'
        # at `target > null_base`. **A loop that crashes returns no verdict at
        # all, which is strictly worse than a gate that is merely wrong**: the
        # wrong gate at least says PASS or FAIL, and a traceback says neither
        # while looking like an infrastructure fault rather than a withdrawn bar.
        #
        # A metric with no target still REPORTS and still carries weight; it
        # simply contributes nothing that pretends to measure progress toward a
        # bar nobody has set. Scored against its null instead when one exists,
        # which is the only honest anchor left, and 0.0 when it does not.
        if target is None:
            if null_base is not None and null_base > 0:
                # progress is a MARGIN OVER THE NULL, capped -- never a fraction
                # of a target that does not exist.
                if direction == "maximize":
                    norm_val = min(1.0, max(0.0, (val - null_base) / null_base))
                else:
                    norm_val = min(1.0, max(0.0, (null_base - val) / null_base))
            else:
                norm_val = 0.0
        elif direction == "maximize":
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


def selfcheck():
    """§12.3. Drives the collapse this module was fixed for, in BOTH directions.

    Self-contained -- the fixtures are `python3 -c` one-liners, not files in a
    spike -- because a check that only runs when another directory is present is
    a check that stops running. `spikes/H245_evaluator_refusal_vs_crash/` is the
    wider probe; this is the one that ships with the component.
    """
    bad = []
    PY = sys.executable

    def ev(body):
        return f'{PY} -c {json.dumps(body)}'

    # (why, command, expect_payload, expect_error)
    cases = [
        ("ran and REFUSED: payload on stdout, exit 1 -- the measurement is real "
         "and must be kept, and the refusal must still be an error",
         ev('import json,sys; print(json.dumps({"m": 0.0})); sys.exit(1)'),
         True, True),
        ("CRASHED: nothing on stdout, non-zero exit -- no measurement exists",
         ev('import sys; print("boom", file=sys.stderr); sys.exit(1)'),
         False, True),
        ("died MID-WRITE: half a JSON object -- parseable-ness is the test",
         ev('import sys; sys.stdout.write(chr(123)+chr(34)+"m"); sys.exit(1)'),
         False, True),
        ("the EXIT-0-PLUS-ERROR lesson: zeroed metrics next to an `error` key",
         ev('import json; print(json.dumps({"m": 0.0, "error": "no artifacts"}))'),
         False, True),
        ("ran and PASSED: payload, exit 0 -- the happy path is untouched",
         ev('import json; print(json.dumps({"m": 1.0}))'),
         True, False),
        ("the DOCUMENTED exit-2 contract: refuses and emits NO metric",
         ev('import sys; print("numpy absent", file=sys.stderr); sys.exit(2)'),
         False, True),
        ("well-formed JSON that is NOT a payload -- `results.update` raises on "
         "a list",
         ev('import json; print(json.dumps([1, 2, 3]))'),
         False, True),
    ]
    for why, cmd, want_payload, want_error in cases:
        data, err = run_evaluator("selfcheck", cmd, timeout=30)
        if (data is not None) != want_payload:
            bad.append(f"payload {'expected' if want_payload else 'refused'}: {why}")
        if (err is not None) != want_error:
            bad.append(f"error {'expected' if want_error else 'not expected'}: {why}")

    # NOT A LOOSENING. The recovered payload is gated on its own value, and the
    # run it came from is still an error, so `is_eligible` cannot improve.
    cfg = {
        "evaluators": {"e": {"command": cases[0][1], "timeout_sec": 30}},
        "metrics": {"m": {"direction": "maximize", "target": 1.0,
                          "min_acceptable": 1.0, "weight": 1.0}},
    }
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stderr(buf):
        results, errors = evaluate_suite(cfg)
    log = buf.getvalue()
    if results.get("m") != 0.0:
        bad.append(f"a refused payload must reach scoring, got m={results.get('m')}")
    if results.get("_invariants_passed") is not False:
        bad.append("0.0 below min_acceptable 1.0 must FAIL invariants")
    if "[INVARIANT VIOLATION]" not in log:
        bad.append("the failure must be reported as a VIOLATION")
    if "[MISSING METRIC]" in log:
        bad.append("a metric that WAS produced must not be reported missing")
    if not errors:
        bad.append("the refusal must remain in `errors`, or `is_eligible` loosens")

    for b in bad:
        print("  FAIL  " + b)
    if not bad:
        print("autoloop selfcheck: a refusal is kept and scored, a crash is "
              "not, a truncated write is not, exit-0-plus-error is not, a "
              "non-dict payload is not, the happy path is unchanged, and a "
              "kept refusal still fails invariants AND stays in `errors`")
    return 1 if bad else 0


def main():
    parser = argparse.ArgumentParser(description="GitHub Next Autoloop Driver for Operation Kingfisher")
    parser.add_argument("--selfcheck", action="store_true", help="§12.3 runnable check for this module")
    parser.add_argument("--eval", action="store_true", help="Run evaluation suite and display metrics")
    parser.add_argument("--step", action="store_true", help="Execute one optimization loop step")
    parser.add_argument("--ci", action="store_true", help="Run in CI mode with strict exit code")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

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
