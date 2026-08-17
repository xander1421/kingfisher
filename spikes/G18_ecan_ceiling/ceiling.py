#!/usr/bin/env python3
"""G18 — does the 1024 ceiling cap the attention architecture, and can chunking escape it?

G16 found `collapse` panics at >=1024 results (`trie.rs:539`, a 10-bit arity
field). G5's ECAN uses `collapse` for every fold — total rent, total stimulus,
and the BSP generation swap. It ran on 60 nodes.

So the question this raises and nobody has asked: **at what graph size does the
attention epoch stop working at all?** If it is ~1023 nodes, the entire
per-context attention design from G5-G12 has a hard ceiling three orders of
magnitude below a real shard, and every result in that range is a toy.

Two things measured here:

  1 WHERE IT DIES. Sweep N and find the first size that panics. Predicted 1024
    from the constant; measured, because a fold might build its expression
    differently from a bare collapse.
  2 WHETHER CHUNKING ESCAPES IT. Fold over batches of <1023 and combine. If a
    chunked epoch produces byte-identical importance to the unchunked one where
    both work, the ceiling is an implementation detail rather than an
    architectural bound.

CONTROL (A15): the chunked path must be verified to produce the SAME answer, not
merely to survive. A chunked fold that silently drops a batch would also "escape
the ceiling". So at every N where both run, the two must agree exactly — and the
agreement check must be capable of failing, which is tested by perturbing one
batch on purpose.

PRE-REGISTERED: chunking escapes the ceiling AND agrees exactly below it.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(os.path.dirname(HERE), "S30_speed_duel", "bin",
                      "fuelrun.v2.host")
SCALE, RENT, SEED = 1000, 50, 1000
CHUNK = 500


def run(path, fuel=400_000_000):
    r = subprocess.run([RUNNER, path, str(fuel)], capture_output=True, text=True)
    out = r.stdout + r.stderr
    st = re.search(r"^status\s+(\S+)", out, re.M)
    fu = re.search(r"^fuel_used\s+(\d+)", out, re.M)
    panic = "panicked" in out
    site = re.search(r"trie\.rs:(\d+)", out)
    return {"status": "PANIC" if panic else (st.group(1) if st else "?"),
            "fuel": int(fu.group(1)) if fu else None,
            "site": site.group(1) if site else None,
            "body": out.split("--- results ---", 1)[-1]}


def facts(n):
    L = []
    for i in range(n):
        L.append(f"(imp 0 n{i} {SEED})")
        L.append(f"(stim n{i} {i % 7})")
    return L


def prog_plain(n, path):
    """G5's shape: one collapse over every node."""
    L = facts(n)
    L.append(f"!(let $rs (collapse (match &self (imp 0 $c $v) "
             f"(/ (* $v {RENT}) {SCALE}))) (add-atom &self (total-rent "
             f"(foldl-atom $rs 0 $a $b (+ $a $b)))))")
    L.append("!(match &self (total-rent $t) (RENT $t))")
    open(path, "w").write("\n".join(L) + "\n")


def prog_chunked(n, path, chunk=CHUNK, sabotage=None):
    """Partition nodes into buckets, fold each bucket, then fold the subtotals.
    Every collapse stays under the arity limit by construction."""
    L = []
    nb = (n + chunk - 1) // chunk
    for i in range(n):
        L.append(f"(imp 0 n{i} {SEED})")
        L.append(f"(stim n{i} {i % 7})")
        L.append(f"(bucket n{i} b{i // chunk})")
    for b in range(nb):
        # SABOTAGE: drop one bucket's contribution, to prove the agreement
        # check can fail. A chunked fold that skipped a batch would otherwise
        # look like a clean escape from the ceiling.
        if sabotage is not None and b == sabotage:
            L.append(f"(subtotal b{b} 0)")
            continue
        L.append(f"!(let $rs (collapse (match &self "
                 f"(, (imp 0 $c $v) (bucket $c b{b})) "
                 f"(/ (* $v {RENT}) {SCALE}))) "
                 f"(add-atom &self (subtotal b{b} "
                 f"(foldl-atom $rs 0 $a $b (+ $a $b)))))")
    L.append(f"!(let $ss (collapse (match &self (subtotal $b $s) $s)) "
             f"(add-atom &self (total-rent (foldl-atom $ss 0 $a $b (+ $a $b)))))")
    L.append("!(match &self (total-rent $t) (RENT $t))")
    open(path, "w").write("\n".join(L) + "\n")


def rent_of(res):
    m = re.search(r"\(RENT (\d+)\)", res["body"])
    return int(m.group(1)) if m else None


def main():
    sizes = [200, 800, 1000, 1023, 1024, 1200, 3000]
    print(f"{'N':>6}  {'plain':<22}{'chunked':<22}{'agree':>7}")
    rows = []
    first_panic = None
    for n in sizes:
        pp = os.path.join(HERE, f"plain_{n}.metta")
        cp = os.path.join(HERE, f"chunk_{n}.metta")
        prog_plain(n, pp)
        prog_chunked(n, cp)
        rp, rc = run(pp), run(cp)
        vp, vc = rent_of(rp), rent_of(rc)
        if rp["status"] == "PANIC" and first_panic is None:
            first_panic = n
        agree = ("-" if vp is None or vc is None else
                 ("YES" if vp == vc else "NO"))
        sp = rp["status"] + (f"@{rp['site']}" if rp["site"] else "")
        sc = rc["status"] + (f"@{rc['site']}" if rc["site"] else "")
        print(f"{n:>6}  {sp+' rent='+str(vp):<22}{sc+' rent='+str(vc):<22}"
              f"{agree:>7}")
        rows.append({"n": n, "plain": sp, "plain_rent": vp,
                     "chunked": sc, "chunked_rent": vc, "agree": agree})

    # ---- CONTROL: the agreement check must be able to fail ----
    n = 1000
    cp = os.path.join(HERE, "sabotage.metta")
    prog_chunked(n, cp, sabotage=0)
    rs = run(cp)
    good = [r for r in rows if r["n"] == n][0]["chunked_rent"]
    bad = rent_of(rs)
    fired = (bad is not None and good is not None and bad != good)
    print(f"\nCONTROL sabotage: drop bucket 0 at N={n}")
    print(f"  honest rent {good}   sabotaged rent {bad}   "
          f"{'FIRES' if fired else 'DID NOT FIRE — agreement check is blind'}")

    escapes = all(r["chunked"].startswith("OK") for r in rows)
    agrees = all(r["agree"] in ("YES", "-") for r in rows)
    if not fired:
        v = "VOID — the agreement control could not fail"
    elif escapes and agrees and first_panic:
        v = (f"CHUNKING ESCAPES — plain panics at N={first_panic}, chunked runs "
             f"to {sizes[-1]} and agrees exactly wherever both run")
    elif not escapes:
        v = "CHUNKING DOES NOT ESCAPE — the chunked path panics too"
    else:
        v = "CHUNKING DISAGREES — escapes the ceiling but changes the answer"
    print(f"\nVERDICT: {v}")

    json.dump({"sizes": sizes, "rows": rows, "chunk": CHUNK,
               "first_panic": first_panic, "control_fired": fired,
               "verdict": v,
               "conditions": {"data": "synthetic-uniform",
                              "concurrency": "single-process",
                              "swept": {"n_nodes": sizes}},
               "cites": ["G5_ecan_metta", "G16_rules_in_metta"]},
              open(os.path.join(HERE, "ceiling.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
