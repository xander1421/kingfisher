#!/usr/bin/env python3
"""Can this test express the verdict you are looking for?

A permutation test with n draws reports p = (k+1)/(n+1) where k is the number
of null draws at least as extreme as the observed value. So the SMALLEST p it
can ever produce is 1/(n+1), whatever the data.

  n=10  -> min p = 0.0909   cannot reach alpha=0.05 even at 0/10
  n=19  -> min p = 0.0500   alpha=0.05 becomes reachable
  n=99  -> min p = 0.0100

Reporting "0/10, p=0.091, not significant" is as wrong as calling it
significant: the test was incapable of the verdict before it ran. Same family
as a positive control that cannot fire (A15) and a null that cannot contain the
effect (A20) -- an instrument that cannot produce the answer being sought.
"""
import math


def min_achievable_p(n_draws: int) -> float:
    if n_draws < 1:
        raise ValueError('n_draws must be >= 1')
    return 1.0 / (n_draws + 1)


def draws_needed(alpha: float) -> int:
    """Smallest n whose minimum achievable p is <= alpha."""
    if not 0 < alpha < 1:
        raise ValueError('alpha must be in (0,1)')
    return math.ceil(1.0 / alpha) - 1


def permutation_p(observed, null_draws, higher_is_extreme=True):
    """The standard (k+1)/(n+1) estimator, with the add-one that stops a
    p of exactly 0 being reported from a finite sample."""
    n = len(null_draws)
    if n == 0:
        raise ValueError('no null draws')
    k = sum(1 for d in null_draws
            if (d >= observed if higher_is_extreme else d <= observed))
    return (k + 1) / (n + 1)


def check(observed, null_draws, alpha=0.05):
    """(ok, verdict, detail). ok is False when the test could not have reached
    alpha regardless of the data -- that is UNDERPOWERED, not NEGATIVE."""
    n = len(null_draws)
    floor = min_achievable_p(n)
    p = permutation_p(observed, null_draws)
    if floor > alpha:
        return (False, 'UNDERPOWERED',
                f'{n} draws can express p no smaller than {floor:.4f}; '
                f'alpha={alpha} was unreachable before the run. '
                f'Need >= {draws_needed(alpha)} draws.')
    return (True, 'SIGNIFICANT' if p <= alpha else 'NOT_SIGNIFICANT',
            f'p={p:.4f} over {n} draws (floor {floor:.4f})')


def demo():
    assert abs(min_achievable_p(10) - 1/11) < 1e-12
    assert abs(min_achievable_p(19) - 0.05) < 1e-12
    assert draws_needed(0.05) == 19
    assert draws_needed(0.01) == 99

    # G17's shape: 0 of 10 null draws reach the observed value
    nulls = [0.327] * 10
    ok, verdict, detail = check(0.441, nulls, alpha=0.05)
    assert not ok and verdict == 'UNDERPOWERED', (verdict, detail)
    assert abs(permutation_p(0.441, nulls) - 1/11) < 1e-12

    # same data, enough draws -> now the verdict is expressible
    ok, verdict, _ = check(0.441, [0.327] * 19, alpha=0.05)
    assert ok and verdict == 'SIGNIFICANT', verdict

    # a genuine null must still come back NOT_SIGNIFICANT, not UNDERPOWERED
    ok, verdict, _ = check(0.30, [0.30] * 19 + [0.35] * 10, alpha=0.05)
    assert ok and verdict == 'NOT_SIGNIFICANT', verdict

    # p can never be 0 from a finite sample
    assert permutation_p(1.0, [0.0] * 50) == 1/51
    print('power: 9 assertions pass')


if __name__ == '__main__':
    demo()
