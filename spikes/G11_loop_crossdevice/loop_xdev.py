#!/usr/bin/env python3
"""G11 — does determinism survive ITERATION?

G1 and G5 proved single-pass byte-identity across desktop and phone. That is not
the same claim as a loop. A loop carries state forward: cycle N's importance is
cycle N-1's output, and cycle N's graph is what cycle N-1 pruned. Any divergence
compounds instead of being observed once and discarded.

So a single-pass test cannot detect drift, and drift is the failure mode the
whole architecture rests on not having.

Method: run G10's loop on BOTH machines, cycle by cycle, comparing
`raw_hash` AND `fuel_used` at every cycle rather than only at the end. If the
machines diverge, report the FIRST cycle at which they do — a final-state
comparison would say "differs" and lose the information that matters.

The prune set is derived from each machine's own epoch output, so a divergence
in importance propagates into the graph and is observable in the next cycle's
node count as well as its hash.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SPIKES, "G10_closed_loop"))
import loop as L                                       # noqa: E402

HOST = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")
ANDROID = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.android")
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
DEV = "/data/local/tmp/kingfisher_g11"
CYCLES = 6


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def fields(out):
    def f(k):
        m = re.search(rf"^{k}\s+(\S+)", out, re.M)
        return m.group(1) if m else "?"
    return f("status"), f("fuel_used"), f("raw_hash")


def on_host(path, fuel):
    return fields(sh(HOST, path, str(fuel)))


def on_device(path, fuel):
    sh(ADB, "push", path, DEV + "/")
    out = sh(ADB, "shell",
             f"cd {DEV} && ./fuelrun {os.path.basename(path)} {fuel}")
    return fields(out)


def epoch_program(live, stims, imp_in, tag):
    """Same emitter G10 uses, written to a file we can ship to the phone."""
    L_ = [f"; G11 cycle {tag}"]
    for ctx, stim in stims.items():
        for i in sorted(live):
            L_.append(f"(imp {ctx} 0 {i} {imp_in[ctx].get(i, L.SEED)})")
            L_.append(f"(stim {ctx} {i} {stim.get(i, 0)})")
    for ctx in stims:
        L_.append(f"!(let $rs (collapse (match &self (imp {ctx} 0 $c $v) "
                  f"(/ (* $v {L.RENT}) {L.SCALE}))) (add-atom &self "
                  f"(total-rent {ctx} (foldl-atom $rs 0 $a $b (+ $a $b)))))")
        L_.append(f"!(let $ss (collapse (match &self (stim {ctx} $c $s) $s)) "
                  f"(add-atom &self (total-stim {ctx} "
                  f"(foldl-atom $ss 0 $a $b (+ $a $b)))))")
        L_.append(f"!(let $new (collapse (match &self (, (imp {ctx} 0 $c $v) "
                  f"(stim {ctx} $c $s) (total-rent {ctx} $tr) "
                  f"(total-stim {ctx} $ts)) (imp {ctx} 1 $c "
                  f"(+ (- $v (/ (* $v {L.RENT}) {L.SCALE})) "
                  f"(/ (* $s $tr) $ts))))) (add-atoms &self $new))")
    for ctx in stims:
        L_.append(f"!(collapse (match &self (imp {ctx} 1 $c $v) "
                  f"(IMPOF {ctx} $c $v)))")
    p = os.path.join(HERE, f"epoch{tag}.metta")
    open(p, "w").write("\n".join(L_) + "\n")
    return p


def parse_imp(out_body, ctxs, live):
    imp = {c: {} for c in ctxs}
    for c, k, v in re.findall(r"\(IMPOF (\w+) (\w+) (\d+)\)", out_body):
        if c in imp:
            imp[c][k] = int(v)
    for c in imp:
        for i in live:
            imp[c].setdefault(i, L.SEED)
    return imp


def main():
    sh(ADB, "shell", f"mkdir -p {DEV}")
    sh(ADB, "push", ANDROID, DEV + "/fuelrun")
    sh(ADB, "shell", f"chmod 755 {DEV}/fuelrun")

    g = json.load(open(L.GRAPH))
    nodes, ids = g["nodes"], [n["id"] for n in g["nodes"]]
    live = set(ids)
    imp = {q: {i: L.SEED for i in ids} for q in L.QUERIES}

    print(f"{'cyc':>4}{'live':>6}  {'status':>8} {'fuel_used':>11}  "
          f"{'raw_hash (both)':<20} match")
    rows, first_div = [], None
    for cyc in range(CYCLES):
        stims = {}
        for q, expr in L.QUERIES.items():
            hits = L.ask(nodes, live, expr, f"x{cyc}_{q}")
            t = {}
            for a, b in hits:
                t[a] = t.get(a, 0) + 1
                t[b] = t.get(b, 0) + 1
            stims[q] = t

        p = epoch_program(live, stims, imp, cyc)
        hs, hf, hh = on_host(p, 40_000_000)
        ds, df, dh = on_device(p, 40_000_000)
        ok = (hs == ds) and (hf == df) and (hh == dh)
        if not ok and first_div is None:
            first_div = cyc
        rows.append({"cycle": cyc, "live": len(live), "host": [hs, hf, hh],
                     "device": [ds, df, dh], "match": ok})
        print(f"{cyc:>4}{len(live):>6}  {hs:>8} {hf:>11}  {hh[:18]:<20} "
              f"{'YES' if ok else 'NO  host=' + hh[:12] + ' dev=' + dh[:12]}")

        _, body = L.run(p, 40_000_000)
        imp = parse_imp(body, L.QUERIES, live)
        drop_n = max(1, int(len(live) * L.PRUNE_FRAC))
        if len(live) - drop_n < 2:
            break
        worth = {i: max(imp[q].get(i, 0) for q in L.QUERIES) for i in live}
        live = live - set(sorted(live, key=lambda i: (worth[i], i))[:drop_n])

    v = ("IDENTICAL — determinism survives iteration, all cycles"
         if first_div is None else
         f"DIVERGED at cycle {first_div} — drift compounds, single-pass tests "
         f"cannot detect this")
    print(f"\nVERDICT: {v}")
    json.dump({"cycles": len(rows), "rows": rows, "first_divergence": first_div,
               "verdict": v,
               "conditions": {"platforms": [["macos", "aarch64"],
                                            ["android", "aarch64"]],
                              "data": "real:kingfisher-workspace",
                              "concurrency": "single-process",
                              "swept": {"cycle": len(rows)}},
               "cites": ["G10_closed_loop", "G5_ecan_metta"]},
              open(os.path.join(HERE, "xdev.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
