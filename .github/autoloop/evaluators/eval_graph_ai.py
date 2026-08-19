#!/usr/bin/env python3
"""Autoloop Evaluator: leak-free Graph AI metrics.

Discipline (G46/G48/G51/G54):
  * Read a certified JSON artifact. Never regex-scrape markdown.
  * Prefer G54 (sliced, pair-disjoint) when its provenance is ok.
  * Fall back to G51 only if G54 is absent. G51 has no slice table;
    that fallback is historical, not a licence to publish an aggregate
    as if it were uniform.
  * Refuse a headline that is the best of a test-set grid (A26).
  * Refuse a missing field_order, or any order other than p,s,o
    (G52 unpacked triples.bin as (s,p,o)).
  * Require a `slices` object on G54.

The 0.2500 min_acceptable in PROGRAM.md is the G34 leak-blend and is
not this file's to move (A22).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "harness"))
try:
    import kg_split
except ImportError:
    kg_split = None
G54_DIR = os.path.join(REPO_ROOT, "spikes", "G54_slice_gated_lift")
G58_DATA = os.path.join(REPO_ROOT, "spikes", "G58_transe_latent", "transe.json")
G59_DATA = os.path.join(REPO_ROOT, "spikes", "G59_official_split", "official.json")
G59_PROV = os.path.join(REPO_ROOT, "spikes", "G59_official_split", "provenance.json")
G51_DIR = os.path.join(REPO_ROOT, "spikes", "G51_bayesian_lift_scoring")
G54_SCRIPT = os.path.join(G54_DIR, "slice_gated.py")
G54_DATA = os.path.join(G54_DIR, "slice_gated.json")
G54_PROV = os.path.join(G54_DIR, "provenance.json")
G51_SCRIPT = os.path.join(G51_DIR, "bayesian_lift.py")
G51_DATA = os.path.join(G51_DIR, "bayesian_lift.json")
G51_PROV = os.path.join(G51_DIR, "provenance.json")


def _fresh(script, *artifacts):
    if not os.path.exists(script) or any(not os.path.exists(p) for p in artifacts):
        return False
    sm = os.path.getmtime(script)
    return all(os.path.getmtime(p) >= sm for p in artifacts)


def _run(script, timeout):
    p = subprocess.run(
        [sys.executable, script],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return p.returncode == 0


def _load_certified(prov_path, data_path):
    with open(prov_path) as f:
        prov = json.load(f)
    if not prov.get("ok", False):
        return None, "D6 certify ok=false"
    with open(data_path) as f:
        data = json.load(f)
    return data, None


def _refuse(msg):
    print(json.dumps({"error": msg, "filtered_mrr": 0.0, "hits_at_10": 0.0}))
    return 1


def _emit(mrr, h10, h1, extra):
    payload = {
        "filtered_mrr": float(mrr),
        "hits_at_10": float(h10),
        "hits_at_1": float(h1),
        "status": "D6_EXECUTION_CERTIFIED",
    }
    payload.update(extra)
    print(json.dumps(payload))
    return 0


def check_discipline(data, require_slices):
    """Return an error string or None."""
    if data.get("literature_compare") == "quoted":
        return "literature MRR quoted (official test not in tree; A18)"
    if data.get("headline_arm") in ("literature", "transe_all_entities"):
        return "headline is a different protocol/candidate set"
    if data.get("field_order") not in (None, "p,s,o") and require_slices:
        return f"field_order {data.get('field_order')!r} is not p,s,o (G52 class)"
    if require_slices:
        if data.get("field_order") != "p,s,o":
            return "missing field_order=p,s,o"
        slices = data.get("slices")
        if not isinstance(slices, dict) or not slices:
            return "missing slices table (aggregate-only MRR is refused)"
        if data.get("headline_is_test_grid") is True:
            return "headline is a test-set grid (A26)"
        if data.get("split", "").find("pair_disjoint") < 0:
            return "not on pair-disjoint split"
    return None


def read_g54(data):
    err = check_discipline(data, require_slices=True)
    if err:
        return None, err
    arms = data.get("arms") or {}
    headline = data.get("headline_arm") or "C_dev_gated"
    arm = arms.get(headline) or arms.get("B_g51")
    if not arm:
        return None, "G54 missing headline arm"
    for k in ("mrr", "hits10", "hits1"):
        if k not in arm:
            return None, f"G54 arm missing {k}"
    extra = {
        "source": "G54_slice_gated_lift",
        "headline_arm": headline,
        "g51_mrr": (arms.get("B_g51") or {}).get("mrr"),
        "prior_mrr": (arms.get("A_prior") or {}).get("mrr"),
        "n_hurting_predicates": data.get("n_hurting_predicates"),
        "slice_shift_max": data.get("slice_shift_max"),
        "official_test_available": False,
        "literature_compare": "unavailable",
        "split": "pair_disjoint",
    }
    if kg_split is not None:
        extra.update(kg_split.official_test_status())
    if os.path.exists(G58_DATA):
        try:
            g58 = json.load(open(G58_DATA))
            extra["transe_support_mrr"] = (g58.get("arms") or {}).get(
                "B_transe_on_prior_support", {}
            ).get("mrr")
            extra["transe_candidate_set"] = g58.get("candidate_set")
        except (OSError, json.JSONDecodeError):
            pass
    # Official-split column. Does NOT replace pair-disjoint filtered_mrr.
    if os.path.exists(G59_DATA) and os.path.exists(G59_PROV):
        try:
            prov59 = json.load(open(G59_PROV))
            g59 = json.load(open(G59_DATA))
            if prov59.get("ok") and g59.get("literature_compare") != "quoted":
                a = g59.get("arms") or {}
                extra["official_prior_mrr"] = (a.get("A_prior") or {}).get("mrr")
                extra["official_g51_mrr"] = (a.get("B_g51") or {}).get("mrr")
                extra["official_gated_mrr"] = (a.get("C_valid_gated") or {}).get("mrr")
                extra["official_same_pair_leak"] = (g59.get("same_pair_leak") or {}).get("n")
        except (OSError, json.JSONDecodeError):
            pass
    return (arm["mrr"], arm["hits10"], arm["hits1"], extra), None


def read_g51(data):
    arms = data.get("arms") or {}
    # Published arm, not max-of-grid at read time. E is what G51 quoted.
    arm = arms.get("E_bayesian_scaled_beta01")
    if not arm:
        return None, "G51 missing E_bayesian_scaled_beta01"
    for k in ("mrr", "hits10", "hits1"):
        if k not in arm:
            return None, f"G51 missing {k}"
    extra = {
        "source": "G51_bayesian_lift_scoring",
        "headline_arm": "E_bayesian_scaled_beta01",
        "slices": None,
        "note": "G51 fallback has no slice table; do not quote as uniform",
    }
    return (arm["mrr"], arm["hits10"], arm["hits1"], extra), None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--selfcheck"]:
        return selfcheck()

    if os.path.exists(G54_SCRIPT):
        if not _fresh(G54_SCRIPT, G54_PROV, G54_DATA):
            print("G54 stale or missing; running slice_gated.py...", file=sys.stderr)
            if not _run(G54_SCRIPT, timeout=1200):
                return _refuse("slice_gated.py execution failed")
        if os.path.exists(G54_PROV) and os.path.exists(G54_DATA):
            data, err = _load_certified(G54_PROV, G54_DATA)
            if err:
                return _refuse(err)
            got, err = read_g54(data)
            if err:
                return _refuse(err)
            mrr, h10, h1, extra = got
            return _emit(mrr, h10, h1, extra)

    if not _fresh(G51_SCRIPT, G51_PROV, G51_DATA):
        print("G51 stale or missing; running bayesian_lift.py...", file=sys.stderr)
        if not _run(G51_SCRIPT, timeout=600):
            return _refuse("bayesian_lift.py execution failed")
    if not os.path.exists(G51_PROV) or not os.path.exists(G51_DATA):
        return _refuse("Artifacts not produced")
    data, err = _load_certified(G51_PROV, G51_DATA)
    if err:
        return _refuse(err)
    got, err = read_g51(data)
    if err:
        return _refuse(err)
    mrr, h10, h1, extra = got
    return _emit(mrr, h10, h1, extra)


def selfcheck():
    """Plant the three refusals. Must not touch live artifacts."""
    fails = []

    def expect_err(data, require, needle, label):
        err = check_discipline(data, require_slices=require)
        if not err or needle not in err:
            fails.append(f"{label}: wanted {needle!r} in {err!r}")

    expect_err({"field_order": "s,p,o", "slices": {"d": {}}}, True,
               "p,s,o", "swapped field order")
    expect_err({"field_order": "p,s,o"}, True,
               "slices", "aggregate-only")
    expect_err(
        {"field_order": "p,s,o", "slices": {"d": {"x": 1}},
         "headline_is_test_grid": True, "split": "pair_disjoint"},
        True, "test-set grid", "A26 grid",
    )
    expect_err(
        {"field_order": "p,s,o", "slices": {"d": {"x": 1}},
         "split": "pair_disjoint", "literature_compare": "quoted"},
        True, "literature", "literature headline",
    )

    ok_data = {
        "field_order": "p,s,o",
        "split": "pair_disjoint (0 leak by construction)",
        "headline_is_test_grid": False,
        "headline_arm": "C_dev_gated",
        "n_hurting_predicates": 3,
        "slice_shift_max": 0.08,
        "arms": {
            "C_dev_gated": {"mrr": 0.23, "hits10": 0.37, "hits1": 0.15},
            "B_g51": {"mrr": 0.2274},
            "A_prior": {"mrr": 0.1732},
        },
        "slices": {"direction": {"tail": {"delta": 0.07}}},
    }
    got, err = read_g54(ok_data)
    if err or abs(got[0] - 0.23) > 1e-9:
        fails.append(f"honest G54 should emit 0.23, got {got} err={err}")

    g51 = {"arms": {"E_bayesian_scaled_beta01": {"mrr": 0.2274, "hits10": 0.3662, "hits1": 0.1524}}}
    got, err = read_g51(g51)
    if err or abs(got[0] - 0.2274) > 1e-9:
        fails.append(f"G51 fallback, got {got} err={err}")

    # Live tree must not be written.
    if os.path.exists(G54_DATA):
        # Reading is fine; writing is not. Touch nothing.
        pass
    tmp = tempfile.mkdtemp()
    if os.path.samefile(tmp, G54_DIR) if os.path.exists(G54_DIR) else False:
        fails.append("tmpdir collided with G54")

    if fails:
        print("SELFCHECK FAIL")
        for f in fails:
            print(" ", f)
        return 1
    print("SELFCHECK OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
