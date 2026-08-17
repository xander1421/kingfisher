#!/usr/bin/env python3
"""G16 — put G15's discovered rules through the substrate.

G15's honest caveat: mining is Python search over an index. MeTTa was not
involved, so the claim was "the mechanism works on this data", not "the graph
found it". This closes half of that: the discovered rules are expressed as MeTTa
forward-chaining rules, applied by hyperon, and the predictions compared against
what Python computed.

That is a cross-engine check, which makes it a control as well as a port —
MORK's `differential/run.py` is the precedent (two independently written engines
over one corpus, byte-compared). Agreement means the rule means the same thing
in both; disagreement means one of them is wrong and we find out which.

Then both devices, because a rule application is a computation like any other
and the determinism claim should extend to it.

SCOPE, stated up front: a 2-hop rule over 272k triples is a large join. This
runs the top rules over a SUBGRAPH restricted to entities touched by the rule's
body predicates, so the MeTTa program is tractable. That is a fair test of
agreement, not of scale.
"""

import json
import os
import re
import struct
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
BIN = os.path.join(SPIKES, "S52_realkg", "triples.bin")
MINE = os.path.join(SPIKES, "G15_analogy_realkg", "mine.json")
HOST = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")
ANDROID = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.android")
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
DEV = "/data/local/tmp/kingfisher_g16"


def load():
    d = open(BIN, "rb").read()
    nt = struct.unpack_from("<I", d, 0)[0]
    t = struct.unpack_from(f"<{nt*3}I", d, 12)
    return [(t[i*3], t[i*3+1], t[i*3+2]) for i in range(nt)]


def python_apply(triples, p, q):
    """Ground truth: every (a,c) reachable by a--p-->b--q-->c, c != a."""
    out = defaultdict(list)
    for pr, s, o in triples:
        if pr in (p, q):
            out[(pr, s)].append(o)
    res = set()
    for (pr, a), bs in out.items():
        if pr != p:
            continue
        for b in bs:
            for c in out.get((q, b), ()):
                if c != a:
                    res.add((a, c))
    return res


def emit(triples, p, q, path):
    """Only the edges the rule body can use — a scoped, fair subgraph."""
    lines = []
    for pr, s, o in triples:
        if pr in (p, q):
            lines.append(f"(edge p{pr} e{s} e{o})")
    lines.append(f"!(collapse (match &self (, (edge p{p} $a $b) "
                 f"(edge p{q} $b $c)) (derived $a $c)))")
    open(path, "w").write("\n".join(lines) + "\n")
    return len(lines) - 1


def run_host(path, fuel):
    out = subprocess.run([HOST, path, str(fuel)], capture_output=True,
                         text=True).stdout
    return out


def run_device(path, fuel):
    subprocess.run([ADB, "push", path, DEV + "/"], capture_output=True)
    return subprocess.run(
        [ADB, "shell", f"cd {DEV} && ./fuelrun {os.path.basename(path)} {fuel}"],
        capture_output=True, text=True).stdout


def fields(out):
    def f(k):
        m = re.search(rf"^{k}\s+(\S+)", out, re.M)
        return m.group(1) if m else "?"
    return f("status"), f("fuel_used"), f("raw_hash")


def main():
    triples = load()
    top = json.load(open(MINE))["top"]
    subprocess.run([ADB, "shell", f"mkdir -p {DEV}"], capture_output=True)
    subprocess.run([ADB, "push", ANDROID, DEV + "/fuelrun"], capture_output=True)
    subprocess.run([ADB, "shell", f"chmod 755 {DEV}/fuelrun"], capture_output=True)

    print(f"{'rule':>12}{'edges':>8}{'python':>9}{'metta':>8}{'agree':>7}"
          f"{'fuel':>11}  device")
    rows = []
    for rl in top[:5]:
        p, q, r = rl["p"], rl["q"], rl["r"]
        path = os.path.join(HERE, f"rule_{p}_{q}.metta")
        n_edges = emit(triples, p, q, path)
        if n_edges > 12000:
            print(f"  ({p},{q}) skipped, {n_edges} edges too large for this pass")
            continue
        py = python_apply(triples, p, q)
        out = run_host(path, 200_000_000)
        st, fu, hh = fields(out)
        mt = set()
        for a, c in re.findall(r"\(derived e(\d+) e(\d+)\)",
                               out.split("--- results ---", 1)[-1]):
            mt.add((int(a), int(c)))
        agree = (py == mt)
        dst, dfu, dhh = fields(run_device(path, 200_000_000))
        dev_ok = (dst == st and dfu == fu and dhh == hh)
        rows.append({"p": p, "q": q, "r": r, "edges": n_edges,
                     "python": len(py), "metta": len(mt), "agree": agree,
                     "status": st, "fuel": fu, "hash": hh,
                     "device_identical": dev_ok})
        print(f"  ({p:>3},{q:>3}){n_edges:>8}{len(py):>9}{len(mt):>8}"
              f"{'YES' if agree else 'NO':>7}{fu:>11}  "
              f"{'IDENTICAL' if dev_ok else 'DIFFERS'}")

    ok = [r for r in rows if r["agree"]]
    dev = [r for r in rows if r["device_identical"]]
    v = (f"CROSS-ENGINE AGREEMENT {len(ok)}/{len(rows)}, "
         f"DEVICE IDENTICAL {len(dev)}/{len(rows)}"
         if rows else "NO RULES SMALL ENOUGH TO RUN")
    print(f"\nVERDICT: {v}")

    json.dump({"rows": rows, "verdict": v,
               "conditions": {"platforms": [["macos", "aarch64"],
                                            ["android", "aarch64"]],
                              "data": "real:FB15k-237",
                              "concurrency": "single-process", "swept": {}},
               "cites": ["G15_analogy_realkg", "S52_realkg"]},
              open(os.path.join(HERE, "apply.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
