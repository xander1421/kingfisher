#!/usr/bin/env python3
"""H203 — the repair H197 left open: `rnd.choice(list(set_of_bytes))`.

H197 measured that W7 and W9 publish hashes that change every run and that
`PYTHONHASHSEED=0` stabilises them. It did NOT locate or fix the cause: a change
that moves a published chain head needs its own before/after record (§12.1).

CAUSE, four sites: `W7/streaming_verifier.py:337,343` and
`W9/bound_streaming_verifier.py:610,615` did `rnd.choice(list(live_set))`.
`live_set` is a set of BYTES; CPython randomises bytes/str hashing per process.
**The RNG is perfectly seeded; the sequence it indexes into is not.** That is why
recording `'seed': SEED` in the artifact meant nothing.

FALSIFIERS, PREREGISTERED IN CHANNEL.md:
  F1  STRONGER THAN THE TEST THAT FOUND THE BUG. H197 proved stability by running
      PYTHONHASHSEED=0 twice, which only shows a fixed hash seed gives a fixed
      answer. After the fix, PYTHONHASHSEED=1 and PYTHONHASHSEED=2 must produce
      IDENTICAL hashes. If not, the fix is not a fix.
  F2  the fix must not be a new experiment. Sorting changes WHICH keys the stream
      touches, so the chain head WILL move -- but if honest_all_passed, the
      mutation-rejection count or the record count changes, the fix altered the
      benchmark and not just its ordering.
  F3  if hashes still vary after sorting, the four-line diagnosis is incomplete
      and there is a second source.
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
TARGETS = [
    ("W7_streaming_witness", "streaming_verifier.py", "streaming.json"),
    ("W9_bound_streaming_witness", "bound_streaming_verifier.py", "bound_streaming.json"),
]
# WHAT MUST NOT MOVE: the fix reorders the stream, so hashes AND byte counts are
# expected to change -- different keys have different lengths. What the benchmark
# CONCLUDES must not.
#
# DERIVED, NOT TYPED, and that is a correction. My first list was hand-written
# (`honest_all_passed`, `mutations_rejected`, ...) and matched NOTHING in W9's
# artifact, so C2 refused the run as VOID -- the same failure H197's C2 caught an
# hour earlier, from the same cause: a name list typed from memory. **Every
# BOOLEAN field is a verdict by construction and cannot be mis-typed**, so the
# verdict half is now collected structurally. `total_events` is named explicitly
# because it is an int and it is the one count that must not move.
#
# DELIBERATE SCOPE: byte counts and per-record sizes are NOT invariants here.
# Sorting changes which keys the stream touches, so `cum_witness_bytes` and
# friends legitimately move; asserting on them would make F2 fire on the fix
# working. Stated rather than left implicit.
NAMED_INT_INVARIANTS = ("total_events",)


def hashes(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from hashes(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from hashes(v, f"{path}[{i}]")
    elif isinstance(o, str) and HEX64.match(o):
        yield path, o


def invariants(o, path=""):
    """Every boolean verdict, plus the named int counts. See NAMED_INT_INVARIANTS."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, bool) or (k in NAMED_INT_INVARIANTS
                                       and isinstance(v, int)):
                yield f"{path}/{k}", v
            yield from invariants(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from invariants(v, f"{path}[{i}]")


def run(d, script, artifact, hashseed):
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(hashseed)
    wd = os.path.join(ROOT, "spikes", d)
    p = subprocess.run([sys.executable, script], cwd=wd, env=env,
                       capture_output=True, text=True)
    ap = os.path.join(wd, artifact)
    if p.returncode != 0 or not os.path.exists(ap):
        return None, None, (p.stderr or p.stdout)[-200:]
    doc = json.load(open(ap))
    return dict(hashes(doc)), dict(invariants(doc)), None


def committed(d, artifact):
    p = f"spikes/{d}/{artifact}"
    blob = subprocess.run(["git", "show", "HEAD:" + p], cwd=ROOT,
                          capture_output=True, text=True).stdout
    doc = json.loads(blob)
    return dict(hashes(doc)), dict(invariants(doc))


def main() -> int:
    rows = {}
    for d, script, artifact in TARGETS:
        # F1: two DIFFERENT hash seeds, not the same one twice.
        h1, i1, e1 = run(d, script, artifact, 1)
        h2, i2, e2 = run(d, script, artifact, 2)
        if h1 is None or h2 is None:
            rows[d] = {"error": e1 or e2}
            continue
        keys = sorted(set(h1) | set(h2))
        differ = sorted(k for k in keys if h1.get(k) != h2.get(k))
        ch, ci = committed(d, artifact)
        moved = sorted(k for k in sorted(set(h1) | set(ch)) if h1.get(k) != ch.get(k))
        inv_changed = sorted(k for k in sorted(set(i1) | set(ci)) if i1.get(k) != ci.get(k))
        rows[d] = {"n_hashes": len(keys),
                   "differ_across_hashseeds": differ,
                   "n_differ": len(differ),
                   "n_hashes_moved_vs_HEAD": len(moved),
                   "invariants_checked": sorted(i1),
                   "invariants_changed_vs_HEAD": inv_changed,
                   "invariant_values": i1}

    ok_rows = {k: v for k, v in rows.items() if "error" not in v}
    n_differ = sum(v["n_differ"] for v in ok_rows.values())
    n_inv = sum(len(v["invariants_changed_vs_HEAD"]) for v in ok_rows.values())
    n_moved = sum(v["n_hashes_moved_vs_HEAD"] for v in ok_rows.values())

    # W9's falsifier is a DISJUNCTION containing a WALL-CLOCK term
    # (`median_latency_us > 500.0`). That is the term that moved, and it is why
    # F2 fires. Recorded as a measurement so the reading is checkable rather
    # than argued -- see RESULT.md for the A/B that separates load from the fix.
    w9 = json.load(open(os.path.join(
        ROOT, "spikes", "W9_bound_streaming_witness", "bound_streaming.json")))
    median_us = w9["sqlite_shardstore_stream"]["median_latency_us"]

    res = {"spike": "H203", "per_spike": rows,
           "w9_falsifier_wallclock_term": {
               "median_latency_us_now": median_us, "threshold_us": 500.0,
               "headroom_ratio": round(500.0 / median_us, 2),
               "committed_at_HEAD_us": 508.71},
           "n_hashes_differing_across_hashseeds": n_differ,
           "n_invariants_changed_vs_HEAD": n_inv,
           "n_hashes_moved_vs_HEAD": n_moved}
    out = os.path.join(HERE, "result.json")
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2)

    for k, v in rows.items():
        if "error" in v:
            print(f"  {k:<32} ERROR {v['error'][:70]}")
        else:
            print(f"  {k:<32} hashes={v['n_hashes']:<4} "
                  f"differ@seed1-vs-2={v['n_differ']:<3} "
                  f"moved_vs_HEAD={v['n_hashes_moved_vs_HEAD']:<3} "
                  f"invariants_changed={len(v['invariants_changed_vs_HEAD'])}")
    print(f"\n{n_differ} hash(es) still vary across hash seeds; "
          f"{n_moved} moved vs HEAD (EXPECTED); {n_inv} invariant(s) changed")

    c1 = Control("C1_hashes_moved_vs_HEAD", why="sorting reorders the stream, so "
                 "the published hashes MUST move -- if none moved, the fix did "
                 "not reach the code path and F1's stability is the OLD stability",
                 can_fail_because="an edit that never executes leaves every hash "
                                  "byte-identical to HEAD",
                 null_must_contain="zero hashes moved vs HEAD")
    c1.observe(n_moved > 0, {k: v.get("n_hashes_moved_vs_HEAD")
                             for k, v in ok_rows.items()})

    c3 = Control("C3_wallclock_term_not_at_its_threshold", why="F2's only firing "
                 "invariant is W9's falsifier, whose disjunction contains "
                 "`median_latency_us > 500.0`. If today's median sat near 500 the "
                 "flip could not be attributed to load rather than to this fix",
                 can_fail_because="a median within ~20% of 500 us would leave the "
                                  "attribution undecided and this control would "
                                  "refuse to license it",
                 null_must_contain="a median latency close to the 500 us threshold")
    c3.observe(median_us < 400.0,
               {"median_latency_us_now": median_us, "threshold_us": 500.0,
                "committed_at_HEAD_us": 508.71})

    c2 = Control("C2_invariants_were_found", why="F2 is vacuous if no invariant "
                 "field was located in the artifacts",
                 can_fail_because="a wrong INVARIANTS name list yields an empty "
                                  "set and a green F2 that checked nothing",
                 null_must_contain="a spike with zero invariants checked")
    c2.observe(all(v.get("invariants_checked") for v in ok_rows.values()),
               {k: v.get("invariants_checked") for k, v in ok_rows.items()})

    f1 = Falsifier("F1_still_hashseed_dependent",
                   refutes="that the sorted() fix removes process dependence",
                   fires_when="any 64-hex value differs between PYTHONHASHSEED=1 "
                              "and PYTHONHASHSEED=2",
                   null_must_contain="a hash differing across two hash seeds")
    f1.observe(n_differ > 0, {k: v.get("differ_across_hashseeds")
                              for k, v in ok_rows.items()})

    f2 = Falsifier("F2_benchmark_changed",
                   refutes="that the fix only reorders and does not alter what "
                           "the benchmark concludes",
                   fires_when="an invariant (honest_all_passed, mutations "
                              "rejected, event/record counts) differs from HEAD",
                   null_must_contain="an invariant differing from HEAD")
    f2.observe(n_inv > 0, {k: v.get("invariants_changed_vs_HEAD")
                           for k, v in ok_rows.items()})

    ok, problems = kfcheck.certify(
        HERE, deps=[os.path.join(ROOT, "spikes", "W7_streaming_witness"),
                    os.path.join(ROOT, "spikes", "W9_bound_streaming_witness")],
        artifacts=[out], controls=[c1, c2, c3], falsifiers=[f1, f2],
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="a hash still differs across hash seeds, or a benchmark "
                  "invariant moved",
        allow_dirty=True,
        note="H203: sorted(live_set) -- removing process-hash order from a "
             "published commitment.")
    for k in (c1, c2, c3, f1, f2):
        print(f"  {k.name}: fired={k.fired}")
    print(f"\ncertify ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
