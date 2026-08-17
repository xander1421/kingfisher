#!/usr/bin/env python3
"""Retro-fit D6 onto the five spikes that cite it without a provenance record.

D6's consequence 2: Q1, S72, N1, W4, B1 each cite "per D6" and none has a
`provenance.json`. Its falsifier F2 reads 6/6 failing (W1 is INVALID, skipped).

THE ONE RULE THIS TOOL OBEYS
----------------------------
Every observation is EXTRACTED from a file the spike already committed. Nothing
is retyped from its `RESULT.md` prose. Retyping a prose number into JSON and
calling the result provenance is D6's own H5 hole -- "a page can state a figure
that appears nowhere in its own artefact" -- performed deliberately.

So a control whose observation is not on disk is recorded as **PROSE_ONLY** and
makes the record `ok=false`. That is the honest outcome, not a failure of the
tool: it is D6 R4 ("observations persisted in the artefact, not in prose")
measured on four months of this project's own output instead of asserted.

  python3 retrofit_d6.py            # write the records
  python3 retrofit_d6.py --dry      # report feasibility only
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import provenance as P

PROSE_ONLY = object()          # sentinel: stated in RESULT.md, absent from disk


def load_json(spike, name):
    p = os.path.join(SPIKES, spike, name)
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return json.load(f)


def read_text(spike, name):
    p = os.path.join(SPIKES, spike, name)
    return open(p, errors='replace').read() if os.path.isfile(p) else None


# ---------------------------------------------------------------- Q1
def q1():
    j = load_json('Q1_quorum_sim', 'quorumsim.json')
    if not j or 'controls' not in j:
        return None
    out = []
    for name, c in j['controls'].items():
        obs = {k: v for k, v in c.items() if k not in ('fails_if',)}
        out.append((name, c['fails_if'],
                    f"the recorded values would read otherwise: {obs}",
                    bool(c.get('pass')), obs))
    return out, ('quorumsim.json', 'quorumsim.py')


# ---------------------------------------------------------------- B1
def b1():
    j = load_json('B1_bundling_real', 'bundling.json')
    if not j or 'B' not in j:
        return None
    B = j['B']
    comp = [(int(k), v['compression_vs_B1']) for k, v in sorted(B.items(), key=lambda x: int(x[0]))]
    monotone = all(comp[i][1] <= comp[i + 1][1] for i in range(len(comp) - 1))
    out = [
        ('B1_store_matches_S11_scaled',
         'B=1 store != 34.83 MB -- a different encoding than S11 measured',
         'store_mb for B=1 reads anything but 34.83',
         abs(B['1']['store_mb'] - 34.83072) < 1e-3,
         {'store_mb': B['1']['store_mb'], 'bundles': B['1']['bundles']}),
        ('B64_median_matches_S52',
         'B=64 median fraction checked != ~0.2% -- a different query or clustering',
         'store_frac_checked_median for B=64 departs from S52 0.2%',
         B.get('64') is not None and B['64']['store_frac_checked_median'] <= 0.01,
         {'B64_median_frac': B.get('64', {}).get('store_frac_checked_median'),
          'B64_p90_frac': B.get('64', {}).get('store_frac_checked_p90')}),
        ('curve_monotone_in_B',
         'non-monotone compression means the metric is not measuring compression cost',
         'the compression_vs_B1 series stops rising with B',
         monotone, {'compression_vs_B1': comp}),
        ('B1_checks_zero_pct_of_store',
         'if B=1 required checking anything, the scoring is broken',
         'store_frac_checked_median for B=1 reads nonzero',
         B['1']['store_frac_checked_median'] == 0.0,
         {'B1_median_frac': B['1']['store_frac_checked_median'],
          'B1_p90_frac': B['1']['store_frac_checked_p90']}),
    ]
    return out, ('bundling.json', 'bundling.py')


# ---------------------------------------------------------------- W4
def w4():
    t = read_text('W4_prefilter_readset', 'ampl.txt')
    if not t:
        return None
    n = {k: int(v) for k, v in re.findall(
        r'(bundles in index|score-pass bundle reads|cutoff-pass bundle reads)\s+(\d+)', t)}
    ratio = re.search(r'total / score-pass\s+([\d.]+)x', t)
    ratio = float(ratio.group(1)) if ratio else None
    sc, cu = n.get('score-pass bundle reads'), n.get('cutoff-pass bundle reads')
    # CLOSED 2026-08-17: the table was rk_inst's STDOUT and the original run
    # redirected only stderr, so the observation was printed and discarded.
    # Recovered by rebuilding the same source; the stderr half of that run
    # reproduces the committed ampl.txt byte for byte.
    tbl = read_text('W4_prefilter_readset', 'readset_table.txt')
    row = re.search(r'\(pred,subj\)\s+[\d.]+\s+([\d.]+)%\s+[\d.]+\s+([\d.]+)%'
                    r'\s+[\d.]+\s+([\d.]+)%', tbl or '')
    cells = [float(x) for x in row.groups()] if row else None
    out = [
        ('table_reproduces_S52',
         'any cell differs from S52 0.2/1.0/8.8% for (pred,subj) -- the '
         'instrumented binary would not be the measured engine'
         if cells else PROSE_ONLY,
         'the (pred,subj) row reads anything but 0.2/1.0/8.8',
         cells == [0.2, 1.0, 8.8],
         {'pred_subj_pct_store_checked': cells,
          's52_published': [0.2, 1.0, 8.8],
          'note': 'count fraction, load-insensitive; the median-us column of the '
                  'same table is NOT valid (quiet.sh refused) and is not used'}
         if cells else None),
        ('counters_are_nonzero',
         'zero score-pass reads would mean the counter is not on the hot path',
         'score-pass bundle reads reads 0',
         bool(sc), {'score_pass_reads': sc, 'bundles_in_index': n.get('bundles in index')}),
        ('cutoff_reads_exceed_score_reads',
         'if equal, the cutoff loop is not scanning and the 78x claim is wrong',
         'cutoff-pass reads equal or fall below score-pass reads',
         bool(sc and cu and cu > sc), {'score_pass': sc, 'cutoff_pass': cu}),
        ('amplification_is_bounded',
         'an unbounded ratio would put the counter inside score_row',
         'the total/score-pass ratio is unbounded or absent',
         bool(ratio and 1.0 < ratio < 1e6), {'ratio': ratio}),
    ]
    return out, ('ampl.txt', 'rk_inst.c', 'readset_table.txt')


# ---------------------------------------------------------------- N1
def n1():
    pre, post = load_json('N1_prefilter_cost', 'gate_pre.json'), \
                load_json('N1_prefilter_cost', 'gate_post.json')
    cond = load_json('N1_prefilter_cost', 'conditions.json')
    if not (pre and post):
        return None
    mhz = None
    if cond:
        m = re.search(r'(\d+)\s*MHz', str(cond.get('conditions', {}).get('clock', '')))
        mhz = int(m.group(1)) if m else None
    out = [
        ('clock_plausibility_gate',
         'a clock outside 500-5000 MHz aborts; S53 folded 769,190,472 MHz',
         'the recorded clock falls outside 500-5000 MHz',
         bool(mhz and 500 <= mhz <= 5000), {'clock_mhz': mhz}),
        ('gates_captured_pre_and_post',
         'non-quiet either side invalidates the scaling curve',
         'either gate records quiet=false',
         bool(pre.get('quiet') and post.get('quiet')),
         {'pre_quiet': pre.get('quiet'), 'post_quiet': post.get('quiet'),
          'pre_thermal_m': pre.get('thermal_m'), 'post_thermal_m': post.get('thermal_m')}),
        ('perfect_scaling_at_T2_T3', PROSE_ONLY,
         'sub-linear scaling would mean bandwidth-bound, not compute-bound',
         None, None),
        ('T4_collapse_reproduces', PROSE_ONLY,
         'T=4 merely slow rather than 337x slow would make the diagnosis wrong',
         None, None),
    ]
    return out, ('gate_pre.json', 'gate_post.json', 'conditions.json')


# ---------------------------------------------------------------- S72
def s72():
    post = load_json('S72_c3_cpuset', 'gate_post.json')
    if not post:
        return None
    out = [
        ('gate_green_before_and_after', PROSE_ONLY,
         'quiet.sh non-quiet either side -- thermal drift invalidates the curve',
         None, None),                      # gate_pre.json does not exist on disk
        ('per_instance_GOPs_from_binary', PROSE_ONLY,
         'a derived figure would hide the bandwidth effect', None, None),
        ('exactness_digest_unchanged', PROSE_ONLY,
         'any kernel differing from f4e64fb7d70b9b0c altered results', None, None),
        ('monotone_aggregate', PROSE_ONLY,
         'aggregate falling with more workers means the pin is not honoured',
         None, None),
        ('gate_post_recorded_quiet',
         'the one control whose observation IS on disk: the post-run gate',
         'gate_post.json records quiet=false',
         bool(post.get('quiet')),
         {'quiet': post.get('quiet'), 'thermal_m': post.get('thermal_m'),
          'cpu_busy_pct': post.get('device_cpu_busy_pct'),
          'refusals': post.get('refusals')}),
    ]
    return out, ('gate_post.json', 'k4.sh')


TARGETS = [('Q1_quorum_sim', q1), ('B1_bundling_real', b1),
           ('W4_prefilter_readset', w4), ('N1_prefilter_cost', n1),
           ('S72_c3_cpuset', s72)]


def main():
    dry = '--dry' in sys.argv
    summary = []
    for spike, fn in TARGETS:
        got = fn()
        if got is None:
            summary.append({'spike': spike, 'status': 'NO_ARTIFACT',
                            'extracted': 0, 'prose_only': 0, 'ok': False})
            print(f'{spike:24} NO_ARTIFACT — nothing on disk to extract from')
            continue
        rows, arts = got
        controls, prose = [], []
        for name, fails_if, can_fail, fired, obs in rows:
            if fails_if is PROSE_ONLY or obs is None:
                prose.append(name)
                continue
            c = P.Control(name, fails_if, null_must_contain='the stated failing input',
                          can_fail_because=can_fail)
            c.observe(fired, obs)
            controls.append(c)
        d = os.path.join(SPIKES, spike)
        note = (f'D6 retro-fit. {len(controls)} of {len(rows)} controls have '
                f'observations ON DISK and are recorded here. '
                + (f'PROSE_ONLY (stated in RESULT.md, absent from every artefact, '
                   f'NOT reconstructed): {prose}. ' if prose else '')
                + 'No value was retyped from prose; see harness/retrofit_d6.py.')
        ok = False
        if not dry:
            ok, prov = P.record(d, deps=(d,),
                                artifacts=[os.path.join(d, a) for a in arts],
                                controls=controls, allow_dirty=True, note=note)
            probs = prov['problems']
        else:
            probs = []
        # a spike with any PROSE_ONLY control cannot be D6-compliant retroactively
        status = ('COMPLIANT' if (ok and not prose) else
                  'PARTIAL' if controls else 'NOT_RECONSTRUCTABLE')
        summary.append({'spike': spike, 'status': status,
                        'extracted': len(controls), 'prose_only': prose,
                        'ok': ok, 'problems': probs})
        # `ok=true` from record() only means the EXTRACTABLE subset checks out --
        # prose-only controls are skipped, not failed, so they cannot lower it.
        # Write the real status into the record so nobody reads ok=true as
        # compliance.
        if not dry:
            pj = os.path.join(d, 'provenance.json')
            with open(pj) as f:
                doc = json.load(f)
            doc['d6_retrofit'] = {
                'status': status, 'controls_on_disk': len(controls),
                'controls_stated': len(rows), 'prose_only': prose,
                'ok_covers_only_the_extractable_subset': True}
            doc['ok'] = bool(ok and not prose)
            with open(pj, 'w') as f:
                json.dump(doc, f, indent=1)
        print(f'{spike:24} {status:20} {len(controls)}/{len(rows)} on disk'
              + (f'  prose-only: {prose}' if prose else ''))
        for p in probs:
            print(f'    ! {p}')
    with open(os.path.join(HERE, 'retrofit_d6.json'), 'w') as f:
        json.dump({'targets': summary}, f, indent=1)
    nc = sum(1 for s in summary if s['status'] == 'COMPLIANT')
    print(f'\n{nc}/{len(summary)} reconstructable to full D6 compliance from '
          f'committed artefacts alone.')
    return summary


if __name__ == '__main__':
    main()
