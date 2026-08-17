#!/usr/bin/env python3
"""Write the artefacts the Rust null needs, so nothing is transcribed by hand.

Two files:

  split.txt    the 80/20 split index order, from Python's random.Random(0xC0FFEE)
               .shuffle. Reproducing Mersenne Twister in Rust to get the same
               split is not worth it, and a DIFFERENT split would silently make
               the Rust `real` incomparable to Python's.

  real_py.txt  the real-graph statistic as Python computes it, to full float
               precision.

The second file exists because of a bug in my own port. The equivalence gate
read `|real - 0.441| < 0.0005`, where 0.441 was a number I typed after reading a
rounded printout. Python's actual value is 0.4405, so |0.4405 - 0.441| = 0.0005
and a byte-perfect Rust port would FAIL the gate on the boundary -- and, because
the gate exits 2, would have looked like a porting error rather than a typo.

The general form is the same defect agent-1 found in the quorum's ISA axis: a
value SELF-DECLARED from a display instead of OBSERVED from the thing itself.
The gate now reads what Python actually computed.
"""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "G17_composition_redo"))
import redo as R  # noqa: E402

TOP_N = 12
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    nt, npred, nent, tri = R.load()
    idx = list(range(nt))
    random.Random(0xC0FFEE).shuffle(idx)
    with open(os.path.join(HERE, "split.txt"), "w") as f:
        f.write("\n".join(map(str, idx)) + "\n")

    cut = int(nt * 0.8)
    train = [tri[i] for i in idx[:cut]]
    test = [tri[i] for i in idx[cut:]]
    rules, _, _ = R.evaluate(train, test, npred, "real")
    real = sum(x["ho_conf"] for x in rules[:TOP_N]) / TOP_N
    with open(os.path.join(HERE, "real_py.txt"), "w") as f:
        f.write(repr(real) + "\n")

    print(f"split.txt    {nt} indices, cut at {cut}")
    print(f"real_py.txt  {real!r}")
    print(f"top-{TOP_N} ho_conf: "
          + " ".join(f"{x['ho_conf']:.4f}" for x in rules[:TOP_N]))
    # The tie-break matters: Python sorts by (-ho_conf, -ho_pairs). Report
    # whether any tie spans the top-N boundary, because that is exactly where a
    # differently-ordered sort would pick a different 12th rule.
    if len(rules) > TOP_N:
        edge = rules[TOP_N - 1]["ho_conf"]
        tied = sum(1 for x in rules if x["ho_conf"] == edge)
        print(f"boundary ho_conf {edge:.6f}, {tied} rule(s) tied at it"
              + ("  <-- tie-break is load-bearing" if tied > 1 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
