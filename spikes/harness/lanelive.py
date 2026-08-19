#!/usr/bin/env python3
"""`launcher_alive(pid)` — the python half of lanelive.sh. ok-1, H243, 2026-08-19.

A pid is not an identity. `os.kill(pid, 0)` and `ps -p <pid>` both answer "is some
process alive with this number", and this fleet burns ~1300 pids/minute through a
99999-pid space -- about 75 minutes to wrap. `registry.py` and `whois.py` both
reported a lock holder as live on that basis; `run_loop.sh` refuses to, in a
comment that says why, and was the only reader that did.

Check: `python3 spikes/harness/lanelive.py` runs the self-check below. It asserts
the FALSE cases only -- this interpreter is not a launcher, a wild pid is not
alive, a non-numeric string is not a pid. The TRUE case needs a process that looks
like a launcher to `ps`, which is a fixture, and it is driven in
`spikes/H243_lock_liveness/probe.sh` rather than faked here.
"""
import os
import subprocess


def launcher_alive(pid) -> bool:
    """True iff `pid` is a live process whose command names run_loop.sh."""
    try:
        pid = int(str(pid).strip())
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    out = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                         capture_output=True, text=True)
    return "run_loop.sh" in out.stdout


def demo():
    assert launcher_alive(os.getpid()) is False, "this interpreter is not a launcher"
    assert launcher_alive(999999) is False, "a pid past the wrap is not alive"
    assert launcher_alive("not-a-pid") is False
    assert launcher_alive("") is False
    assert launcher_alive(None) is False
    assert launcher_alive(0) is False
    print("lanelive: 6 self-checks pass (FALSE cases; the TRUE case is a fixture "
          "in spikes/H243_lock_liveness/probe.sh)")


# `--selfcheck` because that is the interface `selfcheckall.py` runs from the
# supervisor every 600 s (H78). A check that only runs when a human types its
# path is prose with an interpreter attached.
if __name__ == "__main__":
    demo()
