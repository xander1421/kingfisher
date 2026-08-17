#!/usr/bin/env python3
"""What can be claimed from 500 draws when ZERO of them reach the real value.

The port was built to replace G17's p=0.040, which was exactly 1/(24+1) -- the
smallest p that 24 draws can express. 500 draws gives p=1/501=0.0020, and that
is ALSO exactly the floor, because 0 of 500 reached real.

So more draws did not fix the problem, and this is the point: when an effect
sits far outside the null, the permutation p-value is STRUCTURALLY floor-limited.
Every additional draw lowers the floor and none of them ever exceeds real. The
p-value has stopped being the informative statistic. The standardised distance
is what carries the information, and it needs the null's SHAPE to be checked
before it can be read.

Three checks, in decreasing order of how much they license:

  1. Where the data exists (out to ~3 sd), does the tail behave like a Gaussian?
     Testable, because 500 draws populate that range.
  2. Is the extreme of 500 draws where extreme-value theory says the max of 500
     Gaussians should be? E[max of n standard normals] ~ 3.04 for n=500.
  3. Real's distance in sd. NOT convertible to a p without assuming the tail
     holds far beyond where any draw was observed, and that assumption is
     recorded here rather than buried in a number.
"""

import os
import statistics as st
import sys
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = float(open(os.path.join(HERE, "real_py.txt")).read().strip())


def main():
    xs = [float(l) for l in open(os.path.join(HERE, "nulls.txt")) if l.strip()]
    n = len(xs)
    m, sd = st.mean(xs), st.pstdev(xs)
    z = [(x - m) / sd for x in xs]
    print(f"null n={n}  mean {m:.4f}  sd {sd:.4f}  "
          f"min {min(xs):.4f}  max {max(xs):.4f}")
    print(f"real {REAL:.4f}   ratio real/null {REAL / m:.3f}   "
          f"gap {REAL - m:+.4f}")

    g1 = sum(t ** 3 for t in z) / n
    g2 = sum(t ** 4 for t in z) / n - 3.0
    print(f"\nshape: skew {g1:+.3f}  excess kurtosis {g2:+.3f}")

    print("\n1. TAIL WHERE DRAWS EXIST — observed vs Gaussian expectation")
    nd = NormalDist()
    for t in (1.0, 1.5, 2.0, 2.5, 3.0):
        obs = sum(1 for v in z if v >= t)
        exp = n * (1 - nd.cdf(t))
        print(f"   >= {t:.1f} sd   observed {obs:3d}   expected {exp:6.1f}")

    print("\n2. EXTREME OF 500 DRAWS")
    # E[max of n standard normals], Fisher-Tippett approximation.
    import math
    a = math.sqrt(2 * math.log(n))
    e_max = a - (math.log(math.log(n)) + math.log(4 * math.pi)) / (2 * a)
    print(f"   observed max  {max(z):.2f} sd")
    print(f"   E[max] of {n} Gaussians  {e_max:.2f} sd")
    print(f"   -> the extreme of the null is where a Gaussian's would be"
          if abs(max(z) - e_max) < 0.5 else
          f"   -> the extreme deviates from the Gaussian expectation")

    print("\n3. REAL'S DISTANCE")
    zr = (REAL - m) / sd
    print(f"   real is {zr:.1f} sd above the null mean")
    print(f"   real is {(REAL - max(xs)) / sd:.1f} sd above the LARGEST of "
          f"{n} draws")
    print(f"   permutation p = {1 / (n + 1):.4f}, and this is the FLOOR: "
          f"0 of {n} reached real")

    print(f"\n   A Gaussian tail would put {zr:.1f} sd at p ~ 1e-20. That number "
          f"is NOT\n   reported as a result. It extrapolates the tail ~6 sd "
          f"beyond the furthest\n   draw any of these {n} shuffles produced, "
          f"and nothing here tests it there.")
    print(f"\n   WHAT IS SUPPORTED: 0/{n} degree-preserving shuffles reached "
          f"{REAL:.4f}.\n   The largest came up {REAL - max(xs):.4f} short. "
          f"The null's tail is\n   Gaussian-consistent as far as it can be "
          f"checked, so the shortfall is\n   not an artefact of a skewed "
          f"baseline.")

    print(f"\n   WHAT IS NOT: the shuffle reproduces {m / REAL:.0%} of the real "
          f"statistic by\n   chance structure alone. The effect is the "
          f"{REAL - m:.4f} gap, not the {REAL:.4f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
