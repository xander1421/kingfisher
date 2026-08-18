#!/usr/bin/env python3
"""Autoloop Evaluator: Repository Hygiene & Harness Integrity.

Evaluates journalcheck, refcheck, and githygiene.
Outputs normalized JSON metric:
  {"hygiene_score": 1.0 or 0.0, "details": {...}}
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def run_cmd(cmd):
    p = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    rc_ref, out_ref, err_ref = run_cmd("python3 spikes/harness/refcheck.py")
    rc_jnl, out_jnl, err_jnl = run_cmd("python3 spikes/harness/journalcheck.py")
    # H110 (ok-1): this file's own docstring claimed three checkers and ran two.
    # githygiene was named and never invoked, so `hygiene_score` — which is 1.0
    # or 0.0 and is what ACCEPTS a mutation — was blind to §13 entirely: a
    # candidate adding a binary, or a commit with an actionless subject, scored
    # exactly like one that did not. The gap was between the docstring and the
    # code in one file, which is why reading either alone missed it.
    rc_git, out_git, err_git = run_cmd("python3 spikes/harness/githygiene.py")

    ref_ok = (rc_ref == 0)
    jnl_ok = (rc_jnl == 0)

    git_ok = rc_git == 0
    all_ok = ref_ok and jnl_ok and git_ok
    score = 1.0 if all_ok else 0.0

    result = {
        "hygiene_score": score,
        "refcheck_ok": ref_ok,
        "journalcheck_ok": jnl_ok,
        "githygiene_ok": git_ok,
        "checkers_run": ["refcheck", "journalcheck", "githygiene"],
        "refcheck_output": out_ref if ref_ok else (out_ref + " | " + err_ref),
        "journalcheck_output": out_jnl if jnl_ok else (out_jnl + " | " + err_jnl),
    }

    print(json.dumps(result, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
