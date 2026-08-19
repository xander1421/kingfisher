#!/usr/bin/env python3
"""H250 — two defects in the H239 veto, found by attacking it 20 minutes after
shipping it (§2: self-authored data first).

D1  THE VETO'S PROSE ARM IS EVALUATED BEFORE THE PROSE EXISTS. `record()` runs
    inside the spike's own run; `RESULT.md` is written afterwards. Measured on
    disk: 105 of 172 spikes write their write-up AFTER their provenance record,
    and 10 have none at all. So for the majority the veto ran against a haystack
    missing half its evidence -- A15, a control that cannot fire, in the
    mitigation for an A22.
    AND MY OWN H239 PROBE MEASURED THE WRONG STATE: its A4 arm reads MATURE
    spikes with their prose on disk, which is not the state production runs in.
    Fourth arm this span that named one condition and tested another -- this one
    inside the probe written to catch that.

D2  TWO DIFFERENT LEAVES CAN RENDER TO ONE DOTTED PATH, and `dict(json_leaves)`
    kept the LAST while `_leaf_drop` removed the FIRST. `{'a': {'b': 1}}` and
    `{'a.b': 2}` are both `.a.b`. The record then carried one leaf's value while
    the hash was taken over the artifact with the OTHER leaf removed: the correct
    hash of the wrong field. That is A24 -- and it is H211's defect, which this
    lane closed four hours earlier, reappearing inside the module written to
    close it. 119 artifacts on disk carry a dot or bracket in a key.

Both fixed by REFUSING, not resolving, which is the same choice H211 made.
"""
import json, os, subprocess, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import provenance as prov                                        # noqa: E402
import recheck                                                   # noqa: E402

_PIN = '82e635b'          # the commit that SHIPPED both defects (H239, v5/v2)

checks = []
def ck(name, cond, detail=''):
    checks.append((bool(cond), name, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def prefix_provenance():
    """v5 as shipped, loaded from the pinned commit — never from the worktree."""
    r = subprocess.run(['git', '-C', ROOT, 'show', f'{_PIN}:spikes/harness/provenance.py'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, f'cannot read {_PIN}: {r.stderr.strip()}'
    text = r.stdout
    if 'v5, 2026-08-19 (H239)' not in text:
        return None, f'{_PIN} does not carry provenance v5 — pre-fix arm VOID'
    if 'is AMBIGUOUS in' in text:
        return None, (f'{_PIN} already carries the H250 fix — the pre-fix arm '
                      f'would be a second post-fix arm and the run is VOID')
    m = types.ModuleType('prov_prefix')
    m.__dict__['__file__'] = f'{_PIN}:provenance.py'
    exec(compile(text, f'{_PIN}:provenance.py', 'exec'), m.__dict__)
    return m, ''


def main():
    print(__doc__.split('\n')[0])
    print(f"\n[pin] pre-fix arm = {_PIN}\n")

    # ---- D2: the dotted-path collision, PRE-FIX and POST-FIX ---------------
    doc = {'a': {'b': 1}, 'a.b': 2}
    ck('B0 two distinct leaves really do render to one path',
       [k for k, _ in prov.json_leaves(doc)] == ['.a.b', '.a.b'],
       str([k for k, _ in prov.json_leaves(doc)]))

    pre, why = prefix_provenance()
    with tempfile.TemporaryDirectory(prefix='.h250_', dir=HERE) as d:
        art = os.path.join(d, 'x.json')
        with open(art, 'w') as f:
            json.dump(doc, f)
        if pre is None:
            ck('B1a PRE-FIX arm is loadable and pinned', False, why)
        else:
            h, dropped, probs = pre.reproduction_hash(art, ['.a.b'], '')
            # THE DEFECT: it accepts, records ONE leaf's value, and drops the OTHER.
            ck('B1a PRE-FIX accepts the ambiguous path — no problem raised',
               not probs, f'problems={probs}')
            ck('B1b PRE-FIX records the value of one leaf while removing the '
               'other — the correct hash of the wrong field (A24)',
               dropped and dropped[0]['value'] == 2 and
               pre._leaf_drop(doc, '.a.b') == {'a': {}, 'a.b': 2},
               f"recorded value={dropped[0]['value'] if dropped else None}, "
               f"removed leaf={pre._leaf_drop(doc, '.a.b')}")
        h, dropped, probs = prov.reproduction_hash(art, ['.a.b'], '')
        ck('B1c LIVE REFUSES the ambiguous path rather than resolving it',
           h is None and any('AMBIGUOUS' in p for p in probs),
           (probs[0][:88] if probs else 'no problem raised'))

    # ---- D1: the prose arm cannot fire at record time ----------------------
    import glob
    after = before = none = 0
    for p in sorted(glob.glob(os.path.join(ROOT, 'spikes', '*', 'provenance.json'))):
        r = os.path.join(os.path.dirname(p), 'RESULT.md')
        if not os.path.exists(r):
            none += 1
        elif os.path.getmtime(r) > os.path.getmtime(p):
            after += 1
        else:
            before += 1
    ck('B2 the majority of spikes write their prose AFTER their record, so the '
       'record-time veto reads a haystack that does not exist yet',
       after > before, f'after={after} before={before} none={none}')

    sd = os.path.join(ROOT, 'spikes', 'S84_verify_cost')
    pj = json.load(open(os.path.join(sd, 'provenance.json')))
    val = dict(prov.json_leaves(json.load(
        open(os.path.join(sd, 'verifycost.json'))))).get('.wall_us_citable')
    cert_only = json.dumps({k: pj.get(k) for k in
                            ('controls', 'falsifiers', 'falsifiers_fired', 'note')},
                           default=str)
    full = prov._citation_haystack(sd, pj)
    ck('B3a a REAL measured field (S84 .wall_us_citable) is REFUSED with the '
       'prose and ALLOWED without it — the disarm is not hypothetical',
       bool(prov._repro_veto('.wall_us_citable', val, full)) and
       not prov._repro_veto('.wall_us_citable', val, cert_only))

    # B3b: the read-time veto catches what the record-time veto let through.
    with tempfile.TemporaryDirectory(prefix='.h250b_', dir=HERE) as d:
        art = os.path.join(d, 'm.json')
        payload = {'score': 0.5, 'wall_us_citable': False}
        with open(art, 'w') as f:
            json.dump(payload, f)
        # record with NO prose on disk -- exactly the production state.
        ok, p = prov.record(d, deps=(), artifacts=['m.json'],
                            no_deps_reason='fixture',
                            reproduction_excludes={'m.json': ['.wall_us_citable']})
        ck('B3b the record-time veto ALLOWS it, because the prose is not '
           'written yet (the defect, reproduced)',
           p['artifacts'][0].get('repro_sha256') is not None,
           str(p['artifacts'][0].get('repro_excluded')))
        # now the spike's write-up lands, as it always does, and cites the field.
        with open(os.path.join(d, 'RESULT.md'), 'w') as f:
            f.write('The headline of this spike is `wall_us_citable`.\n')
        with open(art, 'w') as f:
            json.dump({'score': 0.5, 'wall_us_citable': True}, f)
        r = recheck.check_record(os.path.join(d, 'provenance.json'))
        ck('B3c and the READ-TIME veto refuses it — a load-bearing field cannot '
           'be laundered through an exclusion declared before the prose existed',
           r['status'] == 'DRIFTED' and
           any('REFUSED at read time' in w for _, _, w in r['artifacts']),
           r['status'] + ': ' + next((w[-95:] for _, _, w in r['artifacts']), ''))

    # ---- B4: H239 STILL WORKS. A fix that breaks the row it defends is not one.
    G54 = os.path.join(ROOT, 'spikes', 'G54_slice_gated_lift', 'slice_gated.json')
    published = open(G54, 'rb').read()
    rd = json.loads(published)
    rd['elapsed_sec'] = 628.72
    with tempfile.TemporaryDirectory(prefix='.h250c_', dir=HERE) as d:
        art = os.path.join(d, 'slice_gated.json')
        with open(art, 'wb') as f:
            f.write(published)
        prov.record(d, deps=(), artifacts=['slice_gated.json'],
                    no_deps_reason='fixture',
                    reproduction_excludes={'slice_gated.json': ['.elapsed_sec']})
        with open(art, 'wb') as f:
            f.write((json.dumps(rd, indent=2) + '\n').encode())
        r = recheck.check_record(os.path.join(d, 'provenance.json'))
        ck('B4a G54\'s honest reproduction still reads REPRODUCED after both '
           'fixes', r['status'] == recheck.REPRODUCED, r['status'])
        rd2 = json.loads(published)
        rd2['elapsed_sec'] = 628.72
        rd2['arms']['A_prior']['mrr'] = 0.9 if isinstance(
            rd2.get('arms', {}).get('A_prior', {}), dict) else None
        with open(art, 'wb') as f:
            f.write((json.dumps(rd2, indent=2) + '\n').encode())
        r2 = recheck.check_record(os.path.join(d, 'provenance.json'))
        ck('B4b and a real scientific change still reads DRIFTED — the '
           'read-time veto did not widen the hole', r2['status'] == 'DRIFTED',
           r2['status'])

    bad = [c for c in checks if not c[0]]
    print(f"\nH250 probe: {len(checks) - len(bad)} pass, {len(bad)} fail")
    for _, n, dt in bad:
        print(f"  FAILED  {n}  {dt}")
    out = {'row': 'H250', 'pin_prefix': _PIN,
           'prose_after_record': after, 'prose_before_record': before,
           'no_prose': none,
           'checks_pass': len(checks) - len(bad), 'checks_fail': len(bad),
           'arms': [{'name': n, 'pass': ok, 'detail': dt} for ok, n, dt in checks]}
    with open(os.path.join(HERE, 'result.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write('\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
