#!/usr/bin/env python3
"""Family E — the number is real, the model is wrong.

Every instance this project produced:
  - one point extrapolated as a rate            (4.21 MB/s from 173 KiB / 40 ms)
  - an affine model that does not hold          (WiFi: bandwidth 1.0 -> 28.3 MB/s)
  - harness cost published as system cost       (63 ms of adb, 35 ms of dumpsys)
  - a ratio quoted without its operating point  (29x in-process, 1.09x at 59 ms)
  - the wrong denominator unit                  (2-hop paths counted as pairs)

`check_affine` alone would have caught the first two.
"""


class ModelRefused(Exception):
    """The data does not support the model being asked of it."""


def fit_or_refuse(points, min_decade_span=1.0):
    """(intercept, slope) for y = a + b*x, or refuse.

    Refuses fewer than 2 points, or a span under `min_decade_span` decades:
    a rate derived from one point, or from points an inch apart, is an artifact
    of where you sampled.
    """
    pts = sorted((float(x), float(y)) for x, y in points)
    if len(pts) < 2:
        raise ModelRefused('a rate needs at least two points; one point is not a rate')
    lo, hi = pts[0][0], pts[-1][0]
    if lo <= 0:
        raise ModelRefused('non-positive x; cannot measure span in decades')
    import math
    span = math.log10(hi / lo)
    if span < min_decade_span:
        raise ModelRefused(
            f'x spans only {span:.2f} decades (< {min_decade_span}); '
            f'too narrow to separate intercept from slope')
    n = len(pts)
    sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0]**2 for p in pts); sxy = sum(p[0]*p[1] for p in pts)
    denom = n*sxx - sx*sx
    if denom == 0:
        raise ModelRefused('degenerate x')
    b = (n*sxy - sx*sy) / denom
    a = (sy - b*sx) / n
    return a, b


def check_affine(points, tol=0.25):
    """(ok, detail). Fit each ADJACENT pair; an affine relationship gives one
    slope. If adjacent slopes disagree by more than `tol` relative spread, the
    data is a curve and any two-point fit reports where you sampled.
    """
    pts = sorted((float(x), float(y)) for x, y in points)
    if len(pts) < 3:
        return False, 'need >= 3 points to test affinity'
    slopes = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x2 == x1:
            return False, 'duplicate x'
        slopes.append((y2 - y1) / (x2 - x1))
    lo, hi = min(slopes), max(slopes)
    if lo <= 0:
        return False, f'non-positive adjacent slope ({lo:.4g}); not affine'
    spread = (hi - lo) / lo
    if spread > tol:
        return (False,
                f'adjacent slopes span {lo:.4g}..{hi:.4g} ({spread:.0%} > {tol:.0%}): '
                f'NOT affine. Report the measured points, not a rate.')
    return True, f'adjacent slopes within {spread:.0%}; affine holds'


def attribute_intercept(total, components, tol=0.30):
    """(ok, detail). An intercept must be accounted for by named components.

    Publishing an unattributed intercept is how 63.2 ms of `adb` process spawn
    became a system constant, and how 35.1 ms of `dumpsys` became "per-job
    preflight is not viable".
    """
    named = sum(components.values())
    if total <= 0:
        return False, 'non-positive intercept'
    resid = abs(total - named) / total
    if resid > tol:
        return (False,
                f'intercept {total:.4g} but named components sum to {named:.4g} '
                f'({resid:.0%} unexplained > {tol:.0%}). Name every term or do '
                f'not publish it as a system cost.')
    return True, f'{named:.4g} of {total:.4g} attributed ({resid:.0%} residual)'


def ratio_with_operating_point(fixed, work):
    """A ratio between a fixed cost and a variable one carries the variable
    inside it. Returns (ratio, note) so the note travels with the number."""
    r = 1.0 + fixed / work
    return r, (f'{r:.2f}x AT work={work:g} (fixed={fixed:g}). '
               f'This ratio is 1 + fixed/work and collapses as work grows.')


def demo():
    # one point is not a rate
    try:
        fit_or_refuse([(173, 40)]); raise AssertionError('accepted one point')
    except ModelRefused as e:
        assert 'two points' in str(e)
    # two points an inch apart are not a rate either
    try:
        fit_or_refuse([(100, 10), (120, 12)]); raise AssertionError('accepted narrow span')
    except ModelRefused as e:
        assert 'decades' in str(e)
    a, b = fit_or_refuse([(1, 11), (10, 20), (100, 110)])
    assert b > 0

    # the real WiFi curve must be REFUSED as affine
    wifi = [(4, 14.4), (16, 25.8), (64, 31.6), (256, 53.2),
            (1024, 130.9), (4096, 295.4), (16384, 719.3)]
    ok, why = check_affine(wifi)
    assert not ok and 'NOT affine' in why, why

    # a genuinely affine set must PASS -- else the check is just a rejector
    aff = [(x, 50 + 2.0*x) for x in (1, 10, 100, 1000)]
    ok, why = check_affine(aff)
    assert ok, why

    # intercept attribution
    ok, _ = attribute_intercept(63.2, {'adb test -f': 16.6, 'adb mkdir': 18.0,
                                       'adb push': 12.0, 'usb setup': 14.0})
    assert ok
    ok, why = attribute_intercept(63.2, {'guessed': 5.0})
    assert not ok and 'unexplained' in why

    # ratios carry their operating point
    r1, n1 = ratio_with_operating_point(6.82, 0.247)
    r2, _ = ratio_with_operating_point(6.82, 59.0)
    assert round(r1) == 29 and round(r2, 2) == 1.12, (r1, r2)
    assert 'AT work=' in n1
    print('units: 11 assertions pass')


if __name__ == '__main__':
    demo()
