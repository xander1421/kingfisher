#!/usr/bin/env python3
"""H166 - Does H164's phase-shuffle arm DISCRIMINATE rotation, or only destroy it?

ATTACK on H164's A2: "shuffling phase angles drops MRR to 0.0020 (99.4% collapse),
establishing 100% phase causality."

CLASS (A25, with A20's second clause): an ablation that removes more than it names
cannot measure the named part. Shuffling theta ~ U(-pi,pi) does not remove
*rotation*; it removes the ONLY per-relation parameter RotatE has, so the ablated
model cannot tell any of the 11 relations apart. Both "the relation embedding
matters" and "continuous complex rotation is the mechanism" predict collapse, so
the arm separates neither and 100% is not an attributable share.

The counter-arm KEEPS the parameter and removes only the named property:
theta quantised to the nearest of {0, pi}, i.e. r in {+1,-1}, an involution
(r*r = 1). It has the same shape, the same per-relation capacity and the same
number of free parameters -- it simply cannot rotate.

No code is retyped: G91's run.py and H164's attack.py are IMPORTED and their own
train / evaluate functions are called, so every arm is measured by the instrument
that produced the numbers under attack.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKES = HERE.parent
ROOT = SPIKES.parent

sys.path.insert(0, str(SPIKES / "harness"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


G91 = _load("g91_run", SPIKES / "G91_rotate_wn18rr" / "run.py")
H164 = _load("h164_attack", SPIKES / "H164_rotate_wn18rr_adversarial_audit" / "attack.py")

import numpy as np  # noqa: E402  (G91's re-exec has already guaranteed numpy)

import kfcheck  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

CORPUS_WN = ROOT / "corpus" / "wn18rr"

# Pins copied from the spikes under attack so C3 fails if either moved.
PIN_F001 = G91.PIN_F001
PIN_F002 = G91.PIN_F002

# H164's exact attack rng, so arm A2 is its arm and not a lookalike.
H164_ATTACK_SEED = 999
INVOLUTION_TOL = 1e-6


def quantise_to_involution(theta):
    """theta -> nearest of {0, pi} per (relation, dim).

    Keeps every per-relation parameter and every dimension; replaces continuous
    rotation with a sign involution. cos(theta) >= 0 -> 0, else pi.
    """
    return np.where(np.cos(theta) >= 0.0, 0.0, np.pi).astype(theta.dtype)


def involution_error(theta_q):
    """max ||r| - 1| and max |r*r - 1| for r = cos(theta_q) + i sin(theta_q).

    C2 exists because A25 applies to MY OWN arm: if r is not an involution then
    the arm is not the thing I named it after.
    """
    r_re = np.cos(theta_q)
    r_im = np.sin(theta_q)
    mod_err = float(np.max(np.abs(np.sqrt(r_re * r_re + r_im * r_im) - 1.0)))
    sq_re = r_re * r_re - r_im * r_im
    sq_im = 2.0 * r_re * r_im
    sq_err = float(np.max(np.abs(sq_re - 1.0) + np.abs(sq_im)))
    return mod_err, sq_err


def main() -> int:
    t0 = time.time()
    print("=== H166: does the phase-shuffle arm discriminate rotation? ===", flush=True)

    train_txt = G91.load_split_txt(CORPUS_WN / "train.txt")
    valid_txt = G91.load_split_txt(CORPUS_WN / "valid.txt")
    test_txt = G91.load_split_txt(CORPUS_WN / "test.txt")

    train, valid, test, npred, nent, r_map, e_map = G91.pack_ids(train_txt, valid_txt, test_txt)
    true_sp, true_po = G91.build_filtered_dict(train + valid + test)
    r_map_rev = {v: k for k, v in r_map.items()}

    E_re, E_im, theta, losses = G91.train_rotate_wn(
        train, nent, npred, epochs=G91.EPOCHS, lr=G91.LR,
        bsz=G91.BATCH_SIZE, reg=G91.REG, seed=G91.SEED)

    # ---- A0 honest, must reproduce G91's headline or nothing below is about G91
    mrr_a0, bd_a0, _ = H164.evaluate_per_relation(
        test, E_re, E_im, theta, true_sp, true_po, r_map_rev)
    print(f"A0 honest theta            MRR {mrr_a0:.4f}", flush=True)

    # ---- A1 involution: parameter KEPT, rotation REMOVED
    theta_q = quantise_to_involution(theta)
    mod_err, sq_err = involution_error(theta_q)
    mrr_a1, bd_a1, _ = H164.evaluate_per_relation(
        test, E_re, E_im, theta_q, true_sp, true_po, r_map_rev)
    print(f"A1 involution {{0,pi}}       MRR {mrr_a1:.4f}  "
          f"(|r|-1 {mod_err:.2e}, |r*r-1| {sq_err:.2e})", flush=True)

    # ---- A2 H164's own arm, reproduced bit-for-bit from its seed
    rng_attack = np.random.default_rng(H164_ATTACK_SEED)
    theta_shuf = rng_attack.uniform(-np.pi, np.pi, size=theta.shape).astype(np.float32)
    mrr_a2, _, _ = H164.evaluate_per_relation(
        test, E_re, E_im, theta_shuf, true_sp, true_po, r_map_rev)
    print(f"A2 shuffled (H164's arm)   MRR {mrr_a2:.4f}", flush=True)

    # ---- A3 THE DECISIVE ARM: H164's attack applied to a model that has NO
    # rotation to destroy. Same involution family, learned values discarded.
    rng_a3 = np.random.default_rng(H164_ATTACK_SEED)
    theta_q_shuf = np.where(
        rng_a3.uniform(0.0, 1.0, size=theta.shape) < 0.5, 0.0, np.pi).astype(np.float32)
    mrr_a3, _, _ = H164.evaluate_per_relation(
        test, E_re, E_im, theta_q_shuf, true_sp, true_po, r_map_rev)
    print(f"A3 shuffled involution     MRR {mrr_a3:.4f}", flush=True)

    drf = "_derivationally_related_form"
    drf_a0 = bd_a0[drf]["mrr"]
    drf_a1 = bd_a1[drf]["mrr"]
    print(f"\n{drf}: honest {drf_a0:.4f} -> involution {drf_a1:.4f}", flush=True)

    n_q = sum(v["queries"] for v in bd_a0.values())

    # ---------------- controls (each states the input that makes it fail) ----
    c1_ok = round(mrr_a0, 4) == 0.3546
    c2_ok = (mod_err < INVOLUTION_TOL) and (sq_err < INVOLUTION_TOL)
    c3_ok = (n_q == 6268) and (PIN_F001 == G91.PIN_F001) and (PIN_F002 == G91.PIN_F002)

    controls = [
        Control("C1_reproduces_G91",
                why="my re-run must reproduce G91's 0.3546 to 4 dp or nothing "
                    "downstream is about G91 at all",
                can_fail_because="seed, numpy version or protocol drift between "
                                 "G91's run and mine",
                null_must_contain="a headline MRR that is not 0.3546"),
        Control("C2_arm_is_an_involution",
                why="A25 applied to my OWN arm: if r is not an involution the arm "
                    "is not the thing I named it after",
                can_fail_because="a quantisation that leaves |r| != 1 or r*r != 1 "
                                 "beyond 1e-6",
                null_must_contain="modulus or square error above tolerance"),
        Control("C3_scope_and_pins",
                why="6,268 queries and F001/F002 pins unmoved",
                can_fail_because="a corrupted split or a pin edit",
                null_must_contain="wrong query count or moved pins"),
    ]
    controls[0].observe(c1_ok, {"mrr_a0": round(mrr_a0, 4), "g91_published": 0.3546})
    controls[1].observe(c2_ok, {"modulus_err": mod_err, "square_err": sq_err,
                                "tol": INVOLUTION_TOL})
    controls[2].observe(c3_ok, {"n_queries": n_q, "f001": PIN_F001, "f002": PIN_F002})

    # ---------------- falsifiers (each refutes ME, not H164) ----------------
    f1 = (mrr_a0 - mrr_a1) >= 0.05
    f2 = mrr_a3 >= 0.05
    f3 = drf_a1 < 0.50

    falsifiers = [
        Falsifier("F1_involution_loses",
                  refutes="my claim that continuous rotation is not what carries "
                          "G91's score",
                  fires_when="honest MRR - involution MRR >= 0.05",
                  null_must_contain="an involution arm that keeps the score"),
        Falsifier("F2_shuffle_discriminates",
                  refutes="my claim that H164's A2 cannot separate 'rotation is the "
                          "mechanism' from 'the relation parameter matters'",
                  fires_when="shuffling a rotation-free involution model leaves "
                             "MRR >= 0.05",
                  null_must_contain="a rotation-free model that survives shuffling"),
        Falsifier("F3_involution_loses_drf",
                  refutes="my account of _derivationally_related_form as an "
                          "involution-shaped relation",
                  fires_when="involution MRR on that relation < 0.50",
                  null_must_contain="that relation collapsing under involution"),
    ]
    falsifiers[0].observe(f1, {"honest": round(mrr_a0, 4), "involution": round(mrr_a1, 4),
                               "drop": round(mrr_a0 - mrr_a1, 4)})
    falsifiers[1].observe(f2, {"shuffled_involution_mrr": round(mrr_a3, 4),
                               "threshold": 0.05})
    falsifiers[2].observe(f3, {"drf_involution_mrr": drf_a1, "threshold": 0.50})

    res = {
        "spike": "H166",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "attacks": "H164 A2 phase-causality claim (not H164's arithmetic, not H165's leakage half)",
        "arms": {
            "A0_honest": {"mrr": round(mrr_a0, 4),
                          "theta": "learned, continuous"},
            "A1_involution": {"mrr": round(mrr_a1, 4),
                              "theta": "quantised to nearest of {0, pi}",
                              "rotation_removed": True,
                              "per_relation_parameter_kept": True},
            "A2_shuffled_h164": {"mrr": round(mrr_a2, 4),
                                 "theta": "U(-pi,pi), seed 999 (H164's arm)",
                                 "h164_published": 0.0020},
            "A3_shuffled_involution": {"mrr": round(mrr_a3, 4),
                                       "theta": "resampled from {0, pi}, seed 999",
                                       "rotation_removed": True},
        },
        "involution_check": {"modulus_err": mod_err, "square_err": sq_err,
                             "tol": INVOLUTION_TOL},
        "derivationally_related_form": {"honest_mrr": drf_a0, "involution_mrr": drf_a1},
        "breakdown_involution": bd_a1,
        "controls": {"C1_reproduces_G91": {"ok": c1_ok},
                     "C2_arm_is_an_involution": {"ok": c2_ok},
                     "C3_scope_and_pins": {"ok": c3_ok}},
        "falsifiers": {"F1_involution_loses": {"fired": f1},
                       "F2_shuffle_discriminates": {"fired": f2},
                       "F3_involution_loses_drf": {"fired": f3}},
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(CORPUS_WN),
              str(SPIKES / "G91_rotate_wn18rr"),
              str(SPIKES / "H164_rotate_wn18rr_adversarial_audit")],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="a rotation-free involution model that BOTH loses the score and "
                  "survives shuffling would refute this row entirely",
        allow_dirty=True,
        note="H166: H164's A2 arm removes the only per-relation parameter, so its "
             "collapse cannot attribute the score to rotation (A25/A20).",
    )
    print(f"\nD6 Provenance Certified: ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)

    print(f"=== H166 completed in {time.time()-t0:.2f}s ===", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
