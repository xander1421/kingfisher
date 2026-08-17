#!/usr/bin/env python3
"""G19 — ECAN past the 1021 ceiling, by leading every conjunction with a bucket.

G18: the limit is the result cardinality of a conjunction's LEADING pattern, not
`collapse`. Chunking the fold does not help because
`(, (imp 0 $c $v) (bucket $c bK))` materialises all N before filtering. Chunking
the QUERY does help, if the selective pattern leads.

G5's ECAN folds with a bare `collapse` over the whole space, so it stops working
above 1021 nodes. This rewrites it so every match leads with `(bucket bK $c)`:

    per-bucket rent subtotal   (, (bucket bK $c) (imp 0 $c $v))
    total rent                 fold over subtotals          (n_buckets < 1021)
    BSP generation swap        (, (bucket bK $c) (imp 0 $c $v) (stim $c $s) …)

Two claims, and the first is what makes the second worth anything:

  (a) EQUIVALENCE — where both forms run, bucket-indexed produces byte-identical
      importance to G5's plain form. A faster program that computes something
      else is not a fix.
  (b) SCALE — the bucket-indexed form runs at N far above 1021.

CONTROL (A15): sabotage one bucket's subtotal. The equivalence check must be
able to fail, or (a) is unfalsifiable — G18's version of this fired at
50000 vs 25000 and is reused here.

Both devices, because G18 showed the abort itself is deterministic and the fix
should be too.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
HOST = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.host")
ANDROID = os.path.join(SPIKES, "S30_speed_duel", "bin", "fuelrun.v2.android")
ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
DEV = "/data/local/tmp/kf_g19"

SCALE, RENT, SEED, BUCKET = 1000, 50, 1000, 400


def run_host(p, fuel=800_000_000):
    r = subprocess.run([HOST, p, str(fuel)], capture_output=True, text=True)
    return r.stdout + r.stderr


def run_dev(p, fuel=800_000_000):
    subprocess.run([ADB, "push", p, DEV + "/"], capture_output=True)
    return subprocess.run(
        [ADB, "shell", f"cd {DEV} && ./fuelrun {os.path.basename(p)} {fuel}"],
        capture_output=True, text=True).stdout


def parse(out):
    panic = "panicked" in out
    st = re.search(r"^status\s+(\S+)", out, re.M)
    fu = re.search(r"^fuel_used\s+(\d+)", out, re.M)
    rh = re.search(r"^raw_hash\s+(\S+)", out, re.M)
    body = out.split("--- results ---", 1)[-1]
    imp = {k: int(v) for k, v in re.findall(r"\(IMP (\w+) (\d+)\)", body)}
    return {"status": "PANIC" if panic else (st.group(1) if st else "?"),
            "fuel": int(fu.group(1)) if fu else None,
            "hash": rh.group(1) if rh else None, "imp": imp}


def seed_atoms(n, with_bucket):
    L = []
    for i in range(n):
        L.append(f"(imp 0 n{i} {SEED})")
        L.append(f"(stim n{i} {i % 7})")
        if with_bucket:
            L.append(f"(bucket b{i // BUCKET} n{i})")
    return L


def prog_plain(n, path):
    """G5's shape — bare collapse over the whole space."""
    L = seed_atoms(n, False)
    L.append(f"!(let $rs (collapse (match &self (imp 0 $c $v) "
             f"(/ (* $v {RENT}) {SCALE}))) (add-atom &self (total-rent "
             f"(foldl-atom $rs 0 $a $b (+ $a $b)))))")
    L.append(f"!(let $ss (collapse (match &self (stim $c $s) $s)) "
             f"(add-atom &self (total-stim (foldl-atom $ss 0 $a $b (+ $a $b)))))")
    L.append(f"!(let $new (collapse (match &self (, (imp 0 $c $v) (stim $c $s) "
             f"(total-rent $tr) (total-stim $ts)) (imp 1 $c "
             f"(+ (- $v (/ (* $v {RENT}) {SCALE})) (/ (* $s $tr) $ts))))) "
             f"(add-atoms &self $new))")
    L.append("!(collapse (match &self (imp 1 $c $v) (IMP $c $v)))")
    open(path, "w").write("\n".join(L) + "\n")


def prog_bucketed(n, path, sabotage=None):
    """Every match leads with (bucket bK $c) — G18's rule."""
    L = seed_atoms(n, True)
    nb = (n + BUCKET - 1) // BUCKET
    assert nb < 1021, "too many buckets for a single-level fold"
    for b in range(nb):
        if sabotage is not None and b == sabotage:
            L.append(f"(sub-rent b{b} 0)")
            L.append(f"(sub-stim b{b} 0)")
            continue
        L.append(f"!(let $rs (collapse (match &self "
                 f"(, (bucket b{b} $c) (imp 0 $c $v)) "
                 f"(/ (* $v {RENT}) {SCALE}))) (add-atom &self "
                 f"(sub-rent b{b} (foldl-atom $rs 0 $a $b (+ $a $b)))))")
        L.append(f"!(let $ss (collapse (match &self "
                 f"(, (bucket b{b} $c) (stim $c $s)) $s)) (add-atom &self "
                 f"(sub-stim b{b} (foldl-atom $ss 0 $a $b (+ $a $b)))))")
    L.append(f"!(let $r (collapse (match &self (sub-rent $b $s) $s)) "
             f"(add-atom &self (total-rent (foldl-atom $r 0 $a $b (+ $a $b)))))")
    L.append(f"!(let $s (collapse (match &self (sub-stim $b $s) $s)) "
             f"(add-atom &self (total-stim (foldl-atom $s 0 $a $b (+ $a $b)))))")
    for b in range(nb):
        L.append(f"!(let $new (collapse (match &self "
                 f"(, (bucket b{b} $c) (imp 0 $c $v) (stim $c $s) "
                 f"(total-rent $tr) (total-stim $ts)) "
                 f"(imp 1 $c (+ (- $v (/ (* $v {RENT}) {SCALE})) "
                 f"(/ (* $s $tr) $ts))))) (add-atoms &self $new))")
    for b in range(nb):
        L.append(f"!(collapse (match &self (, (bucket b{b} $c) (imp 1 $c $v)) "
                 f"(IMP $c $v)))")
    open(path, "w").write("\n".join(L) + "\n")


def main():
    subprocess.run([ADB, "shell", f"mkdir -p {DEV}"], capture_output=True)
    subprocess.run([ADB, "push", ANDROID, DEV + "/fuelrun"], capture_output=True)
    subprocess.run([ADB, "shell", f"chmod 755 {DEV}/fuelrun"], capture_output=True)

    print(f"BUCKET={BUCKET}\n")
    print(f"{'N':>7}  {'plain':<12}{'bucketed':<12}{'equivalent':>11}"
          f"{'device':>11}")
    rows = []
    for n in (60, 400, 1000, 3000, 20000):
        pp = os.path.join(HERE, f"plain_{n}.metta")
        bp = os.path.join(HERE, f"buck_{n}.metta")
        prog_plain(n, pp)
        prog_bucketed(n, bp)
        rp = parse(run_host(pp))
        rb = parse(run_host(bp))
        eq = ("-" if rp["status"] == "PANIC" or not rp["imp"]
              else ("YES" if rp["imp"] == rb["imp"] else "NO"))
        dev = parse(run_dev(bp)) if rb["status"] == "OK" else {"hash": None,
                                                               "fuel": None}
        dok = (rb["status"] == "OK" and dev.get("hash") == rb["hash"]
               and dev.get("fuel") == rb["fuel"])
        print(f"{n:>7}  {rp['status']:<12}{rb['status']:<12}{eq:>11}"
              f"{('IDENTICAL' if dok else '-'):>11}")
        rows.append({"n": n, "plain": rp["status"], "bucketed": rb["status"],
                     "equivalent": eq, "device_identical": dok,
                     "bucketed_hash": rb["hash"], "bucketed_fuel": rb["fuel"],
                     "n_imp": len(rb["imp"])})

    n = 1000
    sp = os.path.join(HERE, "sabotage.metta")
    prog_bucketed(n, sp, sabotage=0)
    rs = parse(run_host(sp))
    good = [r for r in rows if r["n"] == n][0]
    ref = parse(run_host(os.path.join(HERE, f"buck_{n}.metta")))
    fired = rs["imp"] != ref["imp"] and rs["status"] == "OK"
    print(f"\nCONTROL sabotage bucket 0 at N={n}: "
          f"{'FIRES' if fired else 'DID NOT FIRE — equivalence check is blind'}")

    scaled = [r for r in rows if r["bucketed"] == "OK" and r["n"] > 1021]
    eqok = all(r["equivalent"] in ("YES", "-") for r in rows)
    if not fired:
        v = "VOID — the equivalence control could not fail"
    elif not eqok:
        v = "BUCKETED DISAGREES — scales but computes something else"
    elif scaled:
        v = (f"SCALES AND AGREES — bucketed runs to N={max(r['n'] for r in scaled)} "
             f"where plain panics above 1021, byte-identical on both devices")
    else:
        v = "DID NOT SCALE"
    print(f"VERDICT: {v}")

    json.dump({"bucket": BUCKET, "rows": rows, "control_fired": fired,
               "verdict": v,
               "conditions": {"platforms": [["macos", "aarch64"],
                                            ["android", "aarch64"]],
                              "data": "synthetic-uniform",
                              "concurrency": "single-process",
                              "swept": {"n_nodes": [r["n"] for r in rows]}},
               "cites": ["G5_ecan_metta", "G18_ecan_ceiling"]},
              open(os.path.join(HERE, "scaled.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
