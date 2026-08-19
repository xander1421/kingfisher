#!/usr/bin/env python3
"""H197 — does Python's string-hash randomisation reach a published commitment?

Found while running S37's F2 consumer sweep. W7 declares `SEED = 20260817`,
records `'seed': SEED` in its result, and still prints a different
`final_chain_head` on every run.

METHOD, and the two-run design is the whole point: each spike is run TWICE in
the default environment and TWICE under `PYTHONHASHSEED=0`, and every 64-hex
value in its result artifact is compared. A single run tells you nothing; a
comparison against the COMMITTED value would confound "unstable" with "drifted
since it was committed", which are different defects.

  F1  if the PYTHONHASHSEED=0 pair also diverges, the cause is not hash order
      (a clock, a set over floats, filesystem order) and the diagnosis is wrong.
  F2  if W7 is the only spike that varies, this is a spike defect, not a class.
  F3  if every varying hash is an internal benchmark field nothing quotes, the
      blast radius is zero and this is a note, not a finding.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))

import kfcheck                                                     # noqa: E402
from provenance import Control, Falsifier                          # noqa: E402

HEX64 = re.compile(r"^[0-9a-f]{64}$")

# The verification substrate: the spikes whose artifacts ARE commitments.
TARGETS = [
    ("W7_streaming_witness", "streaming_verifier.py", "streaming.json"),
    ("W9_bound_streaming_witness", "bound_streaming_verifier.py", "bound_streaming.json"),
    ("W6_incremental_witness", "incremental_verifier.py", "incremental.json"),
    ("W2_witnessed_trie", "trie_witness.py", "witness.json"),
    ("S85_verify_vs_reexec", "verify_vs_reexec.py", "crossover.json"),
]

# EXCLUDED, EACH WITH THE MEASURED REASON, because a silent exclusion reads as
# coverage (H186). C2 REFUSED THE FIRST TARGET LIST -- `certify ok=False,
# CONTROL C2_hashes_were_found DID NOT FIRE -- run is VOID` -- and it was right:
# I had named `W2/attack.json`, which carries `{seed, findings}` and NOT ONE
# 64-hex value, so the probe would have reported it perfectly stable while
# measuring nothing. That is the exact failure C2 was written for, firing on its
# author. The control is unchanged; the target list was wrong.
#
#   W2_witnessed_trie/attack.json      0 hashes  -> use trie_witness.py -> witness.json (1 hash)
#   S80_completeness_bytes/…json       0 hashes  -> publishes BYTE COUNTS, no digest
#   S27_verify_floor/…json             0 hashes  -> same
#   S24_range_crossover/…json          0 hashes  -> same
#
# A spike whose artifact carries no commitment is OUT OF THIS PROBE'S SCOPE, and
# that is a different statement from "stable". It is recorded, not dropped.
NO_COMMITMENT_IN_ARTIFACT = {
    "S80_completeness_bytes/completeness.json": 0,
    "S27_verify_floor/verify_floor.json": 0,
    "S24_range_crossover/range_crossover.json": 0,
    "W2_witnessed_trie/attack.json": 0,
}


def hashes(obj, path=""):
    """Every 64-hex value in the artifact, keyed by its JSON path."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from hashes(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from hashes(v, f"{path}[{i}]")
    elif isinstance(obj, str) and HEX64.match(obj):
        yield path, obj


def run_once(d, script, artifact, hashseed=None):
    env = dict(os.environ)
    if hashseed is not None:
        env["PYTHONHASHSEED"] = str(hashseed)
    wd = os.path.join(ROOT, "spikes", d)
    p = subprocess.run([sys.executable, script], cwd=wd, env=env,
                       capture_output=True, text=True)
    ap = os.path.join(wd, artifact)
    if p.returncode != 0 or not os.path.exists(ap):
        return None, (p.stderr or p.stdout)[-200:]
    return dict(hashes(json.load(open(ap)))), None


def main() -> int:
    rows = {}
    for d, script, artifact in TARGETS:
        a, ea = run_once(d, script, artifact)
        b, eb = run_once(d, script, artifact)
        c, ec = run_once(d, script, artifact, hashseed=0)
        e, ee = run_once(d, script, artifact, hashseed=0)
        if a is None or b is None or c is None or e is None:
            rows[d] = {"error": ea or eb or ec or ee}
            continue
        keys = sorted(set(a) | set(b))
        unstable = sorted(k for k in keys if a.get(k) != b.get(k))
        unstable_pinned = sorted(k for k in sorted(set(c) | set(e))
                                 if c.get(k) != e.get(k))
        rows[d] = {"n_hashes": len(keys),
                   "unstable_default": unstable,
                   "n_unstable_default": len(unstable),
                   "unstable_hashseed0": unstable_pinned,
                   "n_unstable_hashseed0": len(unstable_pinned),
                   "explained_by_hash_order":
                       bool(unstable) and not unstable_pinned}

    ok_rows = {k: v for k, v in rows.items() if "error" not in v}
    varying = {k: v for k, v in ok_rows.items() if v["n_unstable_default"]}
    explained = {k: v for k, v in varying.items() if v["explained_by_hash_order"]}

    res = {"spike": "H197", "targets": len(TARGETS), "ran": len(ok_rows),
           "excluded_no_commitment_in_artifact": NO_COMMITMENT_IN_ARTIFACT,
           "n_spikes_with_unstable_hashes": len(varying),
           "n_explained_by_hash_order": len(explained),
           "per_spike": rows}
    out = os.path.join(HERE, "result.json")
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2)

    for k, v in rows.items():
        if "error" in v:
            print(f"  {k:<32} ERROR {v['error'][:60]}")
        else:
            print(f"  {k:<32} hashes={v['n_hashes']:<3} "
                  f"unstable={v['n_unstable_default']:<3} "
                  f"unstable@HASHSEED=0={v['n_unstable_hashseed0']:<3} "
                  f"{'HASH-ORDER' if v['explained_by_hash_order'] else ''}")
    print(f"\n{len(varying)} of {len(ok_rows)} spike(s) publish an unstable hash; "
          f"{len(explained)} explained by string-hash order")

    c1 = Control("C1_probe_sees_stability", why="at least one measured spike must "
                 "come out STABLE, or the probe is calling everything unstable",
                 can_fail_because="a probe comparing timestamps as hashes would "
                 "report every spike unstable and distinguish nothing",
                 null_must_contain="every spike reported unstable")
    c1.observe(len(varying) < len(ok_rows),
               {"ran": len(ok_rows), "unstable": len(varying),
                "stable": len(ok_rows) - len(varying)})

    c2 = Control("C2_hashes_were_found", why="a probe that found no 64-hex values "
                 "would report perfect stability",
                 can_fail_because="a wrong artifact filename yields an empty hash "
                 "set and a vacuous green",
                 null_must_contain="a spike with n_hashes = 0")
    c2.observe(all(v.get("n_hashes", 0) > 0 for v in ok_rows.values()),
               {k: v.get("n_hashes") for k, v in ok_rows.items()})

    f1 = Falsifier("F1_not_hash_order",
                   refutes="that string-hash randomisation is the cause",
                   fires_when="a PYTHONHASHSEED=0 pair also diverges",
                   null_must_contain="an unstable hash that survives PYTHONHASHSEED=0")
    f1.observe(any(v.get("n_unstable_hashseed0") for v in ok_rows.values()),
               {k: v.get("n_unstable_hashseed0") for k, v in ok_rows.items()})

    f2 = Falsifier("F2_only_one_spike",
                   refutes="that this is a CLASS rather than one spike's defect",
                   fires_when="exactly one measured spike publishes an unstable hash",
                   null_must_contain="a single varying spike")
    f2.observe(len(varying) == 1, {"varying": sorted(varying), "ran": len(ok_rows)})

    ok, problems = kfcheck.certify(
        HERE, deps=[os.path.join(ROOT, "spikes", "W7_streaming_witness")],
        artifacts=[out], controls=[c1, c2], falsifiers=[f1, f2],
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="PYTHONHASHSEED=0 does not stabilise the hashes, or only one "
                  "spike varies",
        allow_dirty=True,
        note="H197: string-hash randomisation reaching a published commitment.")
    for k in (c1, c2, f1, f2):
        print(f"  {k.name}: fired={k.fired}")
    print(f"\ncertify ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
