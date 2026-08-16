#!/usr/bin/env python3
"""S35 — generate the SAME semantic workload for MORK and for hyperon.

Every throughput number in this workspace (383k steps/s, the fleet TPS model)
was measured on hyperon. MORK is the engine that exists to replace it, and it
has only ever been run on device in S16, where it was checked for agreement,
never for speed against hyperon.

Two questions this workload answers:
  1. how much faster is MORK on identical work (the fleet TPS denominator)
  2. do the two engines AGREE — cross-ENGINE verification, where S16 was
     cross-architecture with one engine. If they agree, a quorum can mix
     engines and get independence from an engine bug. If they do not, the
     `engine` field in hyperjob_v0.proto must be BINDING on every replica.

The task: given a directed graph of Inheritance edges, derive every 2-hop
pair. One rule application, no fixpoint, because MORK forward-chains to
fixpoint and hyperon is query-driven -- restricting to one derivation step is
the largest class of work both express naturally and identically.

  MORK     (exec 0 (, (Inheritance $x $y) (Inheritance $y $z)) (, (TwoHop $x $z)))
  hyperon  !(match &self (, (Inheritance $x $y) (Inheritance $y $z)) (TwoHop $x $z))
"""

import random
import sys

n_nodes = int(sys.argv[1]) if len(sys.argv) > 1 else 200
n_edges = int(sys.argv[2]) if len(sys.argv) > 2 else 600
seed = 0xC0FFEE

rng = random.Random(seed)
edges = set()
# a chain guarantees a long derivation path; random edges add fan-out
for i in range(n_nodes - 1):
    edges.add((f"n{i}", f"n{i+1}"))
while len(edges) < n_edges:
    a, b = rng.randrange(n_nodes), rng.randrange(n_nodes)
    if a != b:
        edges.add((f"n{a}", f"n{b}"))
edges = sorted(edges)

facts = "\n".join(f"(Inheritance {a} {b})" for a, b in edges)

with open("job.mm2", "w") as f:
    f.write(";; S35: 2-hop derivation, MORK arm\n")
    f.write(";; @steps 1\n\n")
    f.write(facts)
    f.write("\n\n(exec 0 (, (Inheritance $x $y) (Inheritance $y $z))\n"
            "        (, (TwoHop $x $z)))\n")

with open("job.metta", "w") as f:
    f.write("; S35: 2-hop derivation, hyperon arm\n")
    f.write(facts)
    f.write("\n\n!(match &self (, (Inheritance $x $y) (Inheritance $y $z))"
            " (TwoHop $x $z))\n")

# ground truth, computed here so both engines are checked against a third party
out = set()
adj = {}
for a, b in edges:
    adj.setdefault(a, []).append(b)
for a, b in edges:
    for c in adj.get(b, []):
        out.add((a, c))
with open("expected.txt", "w") as f:
    for a, c in sorted(out):
        f.write(f"(TwoHop {a} {c})\n")

print(f"nodes={n_nodes} edges={len(edges)} expected_twohop={len(out)}")
