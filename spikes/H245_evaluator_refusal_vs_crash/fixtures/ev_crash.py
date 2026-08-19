#!/usr/bin/env python3
"""CRASHED: nothing on stdout, a traceback on stderr, non-zero exit.

`eval_determinism.py`'s live shape on a machine with no `adb`.
"""
import subprocess
subprocess.run(["kf-no-such-binary-h245"])
