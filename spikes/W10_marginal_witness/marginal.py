#!/usr/bin/env python3
"""witness_bandwidth_savings_pct is CUMULATIVE, so it moves with corpus size.
The marginal statistic does not.

THE DEFECT. eval_verification.py:69 computes

    savings = (1 - cum_witness_bw / cum_full_bw) * 100

over the WHOLE corpus to date. Both terms accumulate and cum_full grows faster,
so the score rises as more data is appended REGARDLESS OF WITNESS QUALITY. I
showed that earlier: ~+0.4pp per epoch of any content, so the 4.6pp gap to the
80 target closes by appending ~12 files. And PROGRAM.md:42 sets the bar
">= 70.0% (Current: 75.37%)" -- the threshold written on the same line as the
value it gates, which is the same calibration defect G46 found under
filtered_mrr, where the bar was set from a leak-blended number.

THE FIX IS A DIFFERENT STATISTIC, NOT A DIFFERENT THRESHOLD. Per epoch:

    marginal = (1 - delta_witness / delta_full) * 100

MEASURED over W6's 66 epochs:
    cumulative (reported)      75.37%
    marginal, last 20 epochs   85.52% median
    marginal, all 66 epochs    85.52% median   <- identical, hence size-independent

Two things follow, and they point opposite ways:
  * the reported metric UNDERSTATES steady state. Early epochs are catastrophic
    (epoch 1: witness 18281 bytes to attest 2558, -614.66%) and the cumulative
    ratio spends the rest of the corpus diluting them.
  * it is still the gameable one, because that dilution is what makes the number
    go up. A metric that improves when you add data and cannot get worse from a
    bad witness is not measuring the witness.

Median, not mean: per-epoch savings ranges 21.35% to 98.50%, so one pathological
file would drag a mean and says nothing about typical behaviour.

    python3 marginal.py            # report both statistics
    python3 marginal.py --json     # machine-readable
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'W6_incremental_witness', 'incremental.json')


def load():
    with open(SRC) as f:
        return json.load(f)['corpus_benchmark']['epoch_records']


def marginals(er):
    """Per-epoch savings. Epochs adding no bytes are SKIPPED, not counted as
    0% -- a division by zero silently scored as a bad epoch would look exactly
    like a bad witness."""
    out, pf, pw = [], 0, 0
    for r in er:
        f, w = r['cum_full_bw'], r['cum_witness_bw']
        df, dw = f - pf, w - pw
        pf, pw = f, w
        if df <= 0:
            continue
        out.append((r['epoch_index'], 100.0 * (1 - dw / df)))
    return out


def main():
    er = load()
    m = marginals(er)
    vals = [v for _, v in m]
    cum = 100.0 * (1 - er[-1]['cum_witness_bw'] / er[-1]['cum_full_bw'])
    half = len(vals) // 2
    res = {
        'epochs': len(er),
        'epochs_scored': len(vals),
        'cumulative_pct': round(cum, 2),
        'marginal_median_pct': round(statistics.median(vals), 2),
        'marginal_median_first_half': round(statistics.median(vals[:half]), 2),
        'marginal_median_second_half': round(statistics.median(vals[half:]), 2),
        'marginal_min_pct': round(min(vals), 2),
        'marginal_max_pct': round(max(vals), 2),
        'worst_epoch': min(m, key=lambda x: x[1])[0],
    }
    # THE SIZE-INDEPENDENCE CHECK, and it is the whole claim. If the marginal
    # median drifts between halves the way the cumulative does, it is just a
    # slower version of the same defect and must not replace it.
    drift = abs(res['marginal_median_first_half'] - res['marginal_median_second_half'])
    res['halves_drift_pp'] = round(drift, 2)
    res['size_independent'] = drift < 5.0

    if '--json' in sys.argv:
        print(json.dumps(res, indent=1))
        return 0
    for k, v in res.items():
        print(f'  {k:30s} {v}')
    print()
    print(f"cumulative {res['cumulative_pct']}%  vs  marginal median {res['marginal_median_pct']}%")
    print('size-independent:' , 'YES' if res['size_independent'] else
          f"NO -- halves differ by {drift:.2f}pp, same defect one step slower")
    return 0


if __name__ == '__main__':
    sys.exit(main())
