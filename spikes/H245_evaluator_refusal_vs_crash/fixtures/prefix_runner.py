"""FROZEN pre-fix `run_evaluator`, lifted VERBATIM by AST from

    scripts/autoloop.py @ cb6264fdb1a1e72b7fef00e222d7e112a564c74a

and NOT re-read from `HEAD` at run time. H237's arm read `HEAD` for its
"pre-fix" side after the fix had landed at `HEAD`, so the pre-fix arm was
measuring the post-fix code and could not fail. A frozen copy cannot do that.

sha256(function source) = 241a29ea9301ce9faf8908b398216e8448dd4714e06911a46af21845b8146fd5
"""
import json
import subprocess

REPO_ROOT = None  # supplied by the caller; the pinned copy takes it as an arg


def run_evaluator(name, cmd, cwd=None, timeout=120):
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
