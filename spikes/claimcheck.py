#!/usr/bin/env python3
"""claimcheck — mechanise A9, the way quiet.sh mechanised A5.

A9 has been stated, widened, and re-stated. It has still fired five times:

    S15   fitted cross-OS          asserted cross-ISA
    S32a  fitted separate-process  asserted in-process co-tenancy
    S72   fitted single-core       asserted deployable cpuset
    W1    fitted key-lookup        asserted similarity-search
    B1    fitted B=1 bipolar       asserted B>1 ternary

A rule that has failed five times is not a rule problem, it is a mechanism
problem. GUARDRAILS A10 already established the pattern: `quiet.sh` does not
ask you to declare the machine is quiet, it REFUSES. This does the same for
claim-vs-condition mismatch.

Three checks, in ascending order of how much they have cost us:

  1. VOCABULARY   a claim word in RESULT.md that implies a condition the
                  artifact does not record.  Catches S15 and S32a.
  2. DEGENERACY   a metric that is constant across a swept axis is not
                  measuring the axis.  Catches W1's four dead controls and
                  B1's first recall metric (100% at every B).
  3. INHERITANCE  when a spike cites another, diff their conditions and
                  report every field that differs.  Catches S72 and B1,
                  and it is the general form of A9.

Load-insensitive by construction: it reads files and compares strings. It
runs through a refused host gate, like S61 and Q1.

Usage:
    python3 claimcheck.py                 # check every spike with a conditions block
    python3 claimcheck.py S72_c3_cpuset   # check one
    python3 claimcheck.py --demo          # self-test; every control must fire

Artifact contract — a spike opts in by emitting `conditions` in its JSON:

    "conditions": {
      "platforms":   [["macos","aarch64"], ["android","aarch64"]],
      "concurrency": "separate-processes",   # or in-process | single-threaded
      "workers":     4,
      "cpuset":      "0-1,4-5",
      "encoding":    "binary-1bit",
      "data":        "synthetic-zipf-1.0",   # or real:FB15k-237
      "swept":       {"B": [8, 16, 32]}
    },
    "cites": ["S11_bundling", "S52_realkg"]

Absent fields are UNDECLARED, which is reported, not assumed.
"""

import json
import os
import re
import sys

SPIKES = os.path.dirname(os.path.abspath(__file__))

# claim word -> (condition field, predicate on its value, what the word asserts)
VOCAB = {
    r"cross-architecture|cross-ISA": (
        "platforms",
        lambda v: len({p[1] for p in v}) >= 2,
        "two distinct architectures",
    ),
    r"cross-platform|cross-OS": (
        "platforms",
        lambda v: len({p[0] for p in v}) >= 2,
        "two distinct operating systems",
    ),
    r"co-tenancy|concurrent|in-process": (
        "concurrency",
        lambda v: bool(v),
        "a declared concurrency model",
    ),
    r"deployable|background cpuset|charge-time worker": (
        "cpuset",
        lambda v: bool(v),
        "the cpuset actually obtained",
    ),
    r"real data|real KG|real-world": (
        "data",
        lambda v: not str(v).startswith("synthetic"),
        "non-synthetic data",
    ),
}


def load(spike):
    """Return (conditions, cites, result_text, json_blobs) for a spike dir."""
    d = os.path.join(SPIKES, spike)
    cond, cites, blobs = None, [], []
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            try:
                j = json.load(open(os.path.join(d, f)))
            except Exception:
                continue
            blobs.append((f, j))
            if isinstance(j, dict):
                cond = j.get("conditions", cond)
                cites = j.get("cites", cites) or cites
    rp = os.path.join(d, "RESULT.md")
    text = open(rp, encoding="utf-8", errors="replace").read() if os.path.isfile(rp) else ""
    return cond, cites, text, blobs


def check_vocabulary(cond, text):
    out = []
    for pattern, (field, ok, needs) in VOCAB.items():
        if not re.search(pattern, text, re.I):
            continue
        word = re.search(pattern, text, re.I).group(0)
        if cond is None or field not in cond:
            out.append(f'claims "{word}" but conditions.{field} is UNDECLARED '
                       f"(the word asserts {needs})")
        elif not ok(cond[field]):
            out.append(f'claims "{word}" but conditions.{field}={cond[field]!r} '
                       f"does not provide {needs}")
    return out


def _numbers_by_axis(obj, axis_values):
    """Collect metric series keyed by the swept axis, wherever they appear.

    Looks for dicts whose keys are the swept values (as str or number) and
    whose values are dicts of metrics — the shape B1/Q1/S61 all emit.
    """
    series = {}
    keys = {str(v) for v in axis_values}

    def walk(o):
        if isinstance(o, dict):
            if keys and keys <= {str(k) for k in o}:
                inner = [o[k] for k in o if str(k) in keys]
                if all(isinstance(x, dict) for x in inner):
                    for metric in inner[0]:
                        vals = [x.get(metric) for x in inner]
                        if all(isinstance(v, (int, float)) for v in vals):
                            series.setdefault(metric, vals)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    return series


def check_degeneracy(cond, blobs):
    """A metric constant across a swept axis is not measuring that axis."""
    out = []
    swept = (cond or {}).get("swept") or {}
    for axis, values in swept.items():
        if len(values) < 2:
            continue
        for fname, j in blobs:
            for metric, vals in _numbers_by_axis(j, values).items():
                if len(set(vals)) == 1:
                    out.append(f"DEGENERATE: {fname}:{metric} is constant "
                               f"({vals[0]!r}) across all {len(vals)} values of "
                               f"{axis} — it does not discriminate on the swept axis")
    return out


def check_inheritance(spike, cond, cites):
    """A9 in general form: reusing a result re-asserts its preconditions."""
    out = []
    for cited in cites:
        d = os.path.join(SPIKES, cited)
        if not os.path.isdir(d):
            out.append(f"cites {cited}, which does not exist")
            continue
        their, _, _, _ = load(cited)
        if their is None:
            out.append(f"cites {cited}, which declares NO conditions — "
                       f"its preconditions cannot be checked, so reusing it "
                       f"asserts them blind")
            continue
        for field in sorted(set(cond or {}) | set(their)):
            if field == "swept":
                continue
            mine, theirs = (cond or {}).get(field, "<undeclared>"), their.get(field, "<undeclared>")
            if mine != theirs:
                out.append(f"INHERITS from {cited}: conditions.{field} "
                           f"{theirs!r} -> {mine!r}. Any formula or constant taken "
                           f"from {cited} was fitted under {theirs!r}.")
    return out


def check(spike):
    cond, cites, text, blobs = load(spike)
    if cond is None and not cites:
        return None  # not opted in
    return (check_vocabulary(cond, text)
            + check_degeneracy(cond, blobs)
            + check_inheritance(spike, cond, cites))


def demo():
    """Every control must be capable of failing. LEDGER rule 4 / GUARDRAILS A10."""
    # 1. vocabulary fires
    c = {"platforms": [["macos", "aarch64"], ["android", "aarch64"]]}
    f = check_vocabulary(c, "byte-identical cross-architecture")
    assert f and "does not provide" in f[0], f
    # ...and passes when it should
    c2 = {"platforms": [["macos", "aarch64"], ["macos", "x86_64"]]}
    assert not check_vocabulary(c2, "byte-identical cross-architecture")
    # 2. undeclared fires
    assert check_vocabulary({}, "measured on the deployable cpuset")
    # 3. degeneracy fires
    cond = {"swept": {"B": [8, 16, 32]}}
    blob = [("t.json", {"B": {"8": {"recall": 1.0}, "16": {"recall": 1.0},
                              "32": {"recall": 1.0}}})]
    d = check_degeneracy(cond, blob)
    assert d and "DEGENERATE" in d[0], d
    # ...and stays silent on a discriminating metric
    blob2 = [("t.json", {"B": {"8": {"recall": 1.0}, "16": {"recall": 0.9},
                               "32": {"recall": 0.7}}})]
    assert not check_degeneracy(cond, blob2)
    print("demo: 5/5 controls fire (vocabulary hit + miss, undeclared, "
          "degeneracy hit + miss)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--demo" in sys.argv:
        demo()
        return 0
    targets = args or sorted(d for d in os.listdir(SPIKES)
                             if os.path.isdir(os.path.join(SPIKES, d)))
    opted, failed = 0, 0
    for s in targets:
        findings = check(s)
        if findings is None:
            continue
        opted += 1
        if findings:
            failed += 1
            print(f"\n{s}")
            for f in findings:
                print(f"  ! {f}")
    print(f"\n{opted} spike(s) opted in, {failed} with findings, "
          f"{len(targets) - opted} not opted in (no `conditions` block).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
