#!/usr/bin/env python3
"""H168 side-finding — H164's A3 "unit modulus" control cannot fail.

H164 audits G91's RotatE and reports A3 `passed: true`, max_modulus_error
1.19e-07, which read in its DONE line as an attack the model survived. The
quantity it computes (`attack.py:183`) is:

    modulus = np.cos(theta) ** 2 + np.sin(theta) ** 2

That is the Pythagorean identity. It is 1.0 for EVERY theta, so it is a property
of `np.cos`/`np.sin`, not of the trained model, and 1.19e-07 is float32 epsilon
rather than a measurement. Family A: a control that cannot contain the effect.

Run this file: `python3 a3_cannot_fail.py`. Exit 0 = the control was shown
inert (i.e. this finding holds); exit 1 = some input made it fire, and the
finding is withdrawn.
"""
import sys

import numpy as np

GATE = 1e-5   # H164 attack.py:185  audit_modulus_ok = (max_mod_err < 1e-5)


def h164_a3(theta):
    """H164's A3, verbatim."""
    modulus = np.cos(theta) ** 2 + np.sin(theta) ** 2
    return float(np.max(np.abs(modulus - 1.0)))


def main() -> int:
    rng = np.random.default_rng(0)
    cases = {
        "trained-like uniform(-pi,pi) f32": rng.uniform(-np.pi, np.pi, (11, 64)).astype(np.float32),
        "ALL ZEROS (never trained at all)": np.zeros((11, 64), np.float32),
        "diverged huge 1e8": np.full((11, 64), 1e8, np.float32),
        "diverged huge 1e30": np.full((11, 64), 1e30, np.float32),
        "tiny 1e-30": np.full((11, 64), 1e-30, np.float32),
        "float64 instead of float32": rng.uniform(-np.pi, np.pi, (11, 64)),
        "adversarial 1e7 random f32": (rng.uniform(-1, 1, (11, 64)) * 1e7).astype(np.float32),
    }
    print(f"H164 A3 gate: max|cos^2(theta)+sin^2(theta) - 1| < {GATE}\n")
    print(f"{'theta handed to the control':<36}{'max err':>12}   verdict")
    fired = []
    for name, th in cases.items():
        e = h164_a3(th)
        ok = e < GATE
        print(f"{name:<36}{e:>12.3e}   {'passes' if ok else 'FIRES'}")
        if not ok:
            fired.append(name)

    nan = np.full((11, 64), np.nan, np.float32)
    e = h164_a3(nan)
    print(f"\nNaN theta: max err = {e}; `{e} < {GATE}` is {e < GATE}")
    print("  -> the control DOES flip on NaN, but a NaN embedding is a dead model,")
    print("     not a violated unit modulus. The stated fault is still unreachable.")

    print("\nVERDICT: an untrained all-zeros model and a diverged 1e30 model BOTH pass.")
    print("A3 measures np.cos/np.sin, not G91. It is zero evidence about the model.")
    if fired:
        print(f"\nWITHDRAWN — these inputs made it fire: {fired}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
