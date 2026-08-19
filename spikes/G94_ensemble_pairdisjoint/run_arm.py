#!/usr/bin/env python3
"""G94 — train an arm on the PAIR-DISJOINT split by swapping only the data.

`sys.modules["official"] = pdsplit` BEFORE importing the trainer, so
G76/G79/G72 resolve `import official as G59` to the pair-disjoint source and are
otherwise byte-identical to the runs that produced their published numbers.

Order matters and is the whole trick: the trainer binds G59 at import time, so
the injection has to happen first. Forking the trainer instead would put the
model under test at the same time as the split.

    python3 run_arm.py distmult|rotate|complex
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pdsplit                                    # noqa: E402  materialises + asserts
sys.modules["official"] = pdsplit                 # <-- the swap

ARMS = {"distmult": (".", "distmult"),
        "rotate":   ("G79_rotate_all_entity", "rotate"),
        "complex":  ("G72_complex_all_entity", "complex")}

arm = sys.argv[1] if len(sys.argv) > 1 else "distmult"
d, mod = ARMS[arm]
# The trainer is a hash-verified COPY in this directory (TRAINER_PROVENANCE.txt).
# EMB_PATH/HIST_PATH are os.path.join(HERE, ...), so running it here makes it
# retrain on the pair-disjoint corpus and keeps its artefacts out of G76 --
# where a pair-disjoint .npz would otherwise be picked up by their next run.
tdir = HERE if d == "." else os.path.join(SPIKES, d)
sys.path.insert(0, tdir)
os.chdir(tdir)
print(f"[G94] arm={arm} module={mod} corpus={pdsplit.CORPUS}", flush=True)
t0 = time.time()
m = __import__(mod)
rc = m.main() if hasattr(m, "main") else 0
print(f"[G94] {arm} finished rc={rc} in {time.time()-t0:.0f}s", flush=True)
sys.exit(rc or 0)
