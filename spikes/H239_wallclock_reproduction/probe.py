#!/usr/bin/env python3
"""H239 — a hashed wall clock makes an honest reproduction look like a regression.

TWO-SIDED BY CONSTRUCTION, because a post-fix green proves nothing about a fix.
Arm A drives the POSITIVE fixture (an honest reproduction) through the PRE-FIX
`recheck` extracted from a PINNED COMMIT and through the live one; arm B drives
302 real mutations of the same artifact through the live one and requires every
single one to still read DRIFTED.

WHY THE PRE-FIX ARM IS PINNED TO A SHA AND NOT TO `HEAD`: four hours before this
was written, H237's pre-fix arm read `HEAD`, my fix landed at `HEAD`, and the arm
silently became a second post-fix arm reporting the defect absent. A pre-fix arm
that tracks a moving ref reports success the moment the fix lands, whether or not
the fix works. `_PIN` is guarded: if that object does not carry v1, the run VOIDS.

THE FIXTURE IS NOT INVENTED. It is G54's published `slice_gated.json` — the
artifact behind `C_dev_gated 0.2313`, which `--eval` names as source — plus the
one field a live lane's forced recompute actually moved. That recompute was
independently confirmed here before any of this was built: setting
`.elapsed_sec` to 628.72 in the published file reproduces AGENT-3's recomputed
sha256 `411731fb…` EXACTLY, all 8648 bytes. So arm A is not a simulation of a
reproduction, it is the reproduction.
"""
import copy, hashlib, importlib.util, json, os, subprocess, sys, tempfile, types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import provenance as prov                                        # noqa: E402
import recheck                                                   # noqa: E402

_PIN = '1fcc761'                       # the commit that INTRODUCED recheck v1
G54 = os.path.join(ROOT, 'spikes', 'G54_slice_gated_lift', 'slice_gated.json')
PUBLISHED_SHA = '67a5de046597b0f1'     # provenance.json, G54
RECOMPUTED_SHA = '411731fbcec3224d'    # AGENT-3's forced recompute, 1204a61
ELAPSED_PUBLISHED, ELAPSED_RECOMPUTED = 886.92, 628.72

checks = []
def ck(name, cond, detail=''):
    checks.append((bool(cond), name, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return bool(cond)


def load_prefix_recheck():
    """The PINNED pre-fix module, loaded from git, never from the worktree."""
    src = subprocess.run(['git', '-C', ROOT, 'show', f'{_PIN}:spikes/harness/recheck.py'],
                         capture_output=True, text=True)
    if src.returncode != 0:
        return None, f'cannot read {_PIN}: {src.stderr.strip()}'
    text = src.stdout
    if 'VERSION = 1' not in text or 'REPRODUCED' in text:
        return None, (f'{_PIN} does not carry recheck v1 — the pre-fix arm would '
                      f'be a second post-fix arm and the run is VOID')
    mod = types.ModuleType('recheck_prefix')
    mod.__dict__['__file__'] = f'{_PIN}:recheck.py'
    exec(compile(text, f'{_PIN}:recheck.py', 'exec'), mod.__dict__)
    return mod, ''


def write_record(d, artifact_name, excludes):
    ok, p = prov.record(
        d, deps=(), artifacts=[artifact_name],
        no_deps_reason='fixture: the artifact IS the subject, there is no source tree',
        reproduction_excludes=excludes)
    return p


def main():
    print(__doc__.split('\n')[0])
    print(f"\n[fixture] G54 published artifact, pin {_PIN}\n")

    published = open(G54, 'rb').read()
    ck('A0a fixture is the published artifact',
       hashlib.sha256(published).hexdigest().startswith(PUBLISHED_SHA),
       hashlib.sha256(published).hexdigest()[:16])

    doc = json.loads(published)
    leaves = dict(prov.json_leaves(doc))
    ck('A0b the artifact has 303 leaves, exactly one of them a wall clock',
       len(leaves) == 303 and doc.get('elapsed_sec') == ELAPSED_PUBLISHED,
       f'{len(leaves)} leaves, elapsed_sec={doc.get("elapsed_sec")}')

    # THE POSITIVE FIXTURE, and it is a reconstruction of a REAL run, asserted
    # against that run's published hash rather than against my own expectation.
    repro_doc = copy.deepcopy(doc)
    repro_doc['elapsed_sec'] = ELAPSED_RECOMPUTED
    repro_bytes = (json.dumps(repro_doc, indent=2) + '\n').encode()
    ck('A0c the honest-reproduction fixture IS AGENT-3\'s recompute, byte for byte',
       hashlib.sha256(repro_bytes).hexdigest().startswith(RECOMPUTED_SHA),
       f'{hashlib.sha256(repro_bytes).hexdigest()[:16]} vs published {RECOMPUTED_SHA}')
    ck('A0d and it is NOT byte-identical to the published artifact '
       '(or REPRODUCED would be trivially true)', repro_bytes != published,
       f'{len(repro_bytes)} B vs {len(published)} B, differ')

    with tempfile.TemporaryDirectory(prefix='.h239_', dir=HERE) as d:
        art = os.path.join(d, 'slice_gated.json')
        open(art, 'wb').write(published)
        p = write_record(d, 'slice_gated.json', {'slice_gated.json': ['.elapsed_sec']})
        a = p['artifacts'][0]
        ck('A1a the exclusion was ALLOWED and recorded in the clear',
           a.get('repro_excluded') == [{'path': '.elapsed_sec', 'value': ELAPSED_PUBLISHED}],
           str(a.get('repro_excluded')))
        ck('A1b repro_sha256 is recorded and is NOT the byte sha256 '
           '(they answer different questions)',
           a.get('repro_sha256') and a['repro_sha256'] != a['sha256'],
           f"repro {str(a.get('repro_sha256'))[:16]} vs byte {a['sha256'][:16]}")

        # ---- A2: the honest reproduction, PRE-FIX and POST-FIX -------------
        open(art, 'wb').write(repro_bytes)
        pre, why = load_prefix_recheck()
        if pre is None:
            ck('A2a PRE-FIX arm is loadable and pinned', False, why)
        else:
            r1 = pre.check_record(os.path.join(d, 'provenance.json'))
            ck('A2a PRE-FIX recheck calls the honest reproduction DRIFTED '
               '(the defect, reproduced)', r1['status'] == 'DRIFTED', r1['status'])
        r2 = recheck.check_record(os.path.join(d, 'provenance.json'))
        ck('A2b LIVE recheck calls it REPRODUCED',
           r2['status'] == recheck.REPRODUCED, r2['status'])
        ck('A2c and it NAMES the field that moved, with both values',
           any('elapsed_sec' in w and '886.92' in w and '628.72' in w
               for _, _, w in r2['artifacts']),
           next((w for _, _, w in r2['artifacts']), ''))

        # ---- A3 (F2): 302 REAL MUTATIONS MUST STILL READ DRIFTED -----------
        # The anti-weakening arm. Every other leaf of the same artifact, one at
        # a time. If any goes quiet, the fix is a weaker gate (5) and is
        # withdrawn whatever the rest of this file says.
        others = [k for k in leaves if k != '.elapsed_sec']
        ck('A3a the negative arm has 302 real mutations to make',
           len(others) == 302, f'{len(others)}')
        quiet = []
        for k in others:
            m = copy.deepcopy(doc)
            m['elapsed_sec'] = ELAPSED_RECOMPUTED     # the honest change, PLUS:
            v = leaves[k]
            if isinstance(v, bool):        nv = not v
            elif isinstance(v, (int, float)): nv = v + 1
            elif isinstance(v, str):       nv = v + 'X'
            else:                          nv = 'MUTATED'
            cur, toks = m, __import__('re').findall(r'\.([^.\[]+)|\[(\d+)\]', k)
            for i, (key, idx) in enumerate(toks):
                last = i == len(toks) - 1
                tgt = key if key else int(idx)
                if last: cur[tgt] = nv
                else:    cur = cur[tgt]
            open(art, 'wb').write((json.dumps(m, indent=2) + '\n').encode())
            st = recheck.check_record(os.path.join(d, 'provenance.json'))['status']
            if st != 'DRIFTED':
                quiet.append((k, st))
        ck('A3b every one of the 302 still reads DRIFTED — the fix is not a '
           'weaker gate', not quiet, f'{len(quiet)} went quiet: {quiet[:5]}')

    # ---- A4: THE VETO, on real load-bearing fields from three real spikes ---
    # Two arms, because arm 1 alone is a grep on the NAME and `elapsed_sec` and
    # `wall_us_citable` are the same shape to a grep (A30).
    veto_cases = [
        ('H203_stream_order_determinism', 'result.json',
         '.w9_falsifier_wallclock_term.median_latency_us_now', True, 'name'),
        ('H86_stranded_cost', 'h86.json',
         '.timings.v1_2026-08-17T21:36.wall_s', True, 'value'),
        ('S84_verify_cost', 'verifycost.json', '.wall_us_citable', True, 'name'),
        ('G51_bayesian_lift_scoring', 'bayesian_lift.json', '.elapsed_sec', False, '-'),
    ]
    for spike, art_name, leaf, must_refuse, arm in veto_cases:
        sd = os.path.join(ROOT, 'spikes', spike)
        src = os.path.join(sd, art_name)
        if not os.path.exists(src):
            ck(f'A4 {spike} fixture present', False, src); continue
        pj = json.load(open(os.path.join(sd, 'provenance.json')))
        hay = prov._citation_haystack(sd, pj)
        val = dict(prov.json_leaves(json.load(open(src)))).get(leaf)
        why = prov._repro_veto(leaf, val, hay)
        ck(f'A4 {spike}{leaf} — ' +
           ('REFUSED, it is the science' if must_refuse else 'ALLOWED, it is a wall clock'),
           bool(why) == must_refuse, (why[:90] if why else 'allowed') + f'  [{arm} arm]')

    # A5: arm 2 is not decoration — remove it and H86's measurement becomes
    # excludable. Asserted by checking the NAME arm alone on that leaf.
    sd = os.path.join(ROOT, 'spikes', 'H86_stranded_cost')
    pj = json.load(open(os.path.join(sd, 'provenance.json')))
    hay = prov._citation_haystack(sd, pj)
    import re as _re
    name_only = _re.search(r'(?<![A-Za-z0-9_])wall_s(?![A-Za-z0-9_])', hay) is not None
    ck('A5 the VALUE arm is load-bearing: H86 wall_s is invisible to the NAME '
       'arm and caught by the VALUE arm', not name_only,
       f'name-arm hit={name_only} (if this ever becomes True the arm is untested, not wrong)')

    # A6: default is inert. No declaration -> repro_sha256 == sha256, so a
    # record already on disk cannot reach REPRODUCED except byte-identically.
    with tempfile.TemporaryDirectory(prefix='.h239b_', dir=HERE) as d:
        art = os.path.join(d, 'x.json')
        open(art, 'w').write(json.dumps({'a': 1, 'elapsed_sec': 1.0}))
        p = write_record(d, 'x.json', None)
        a = p['artifacts'][0]
        ck('A6a no declaration -> repro_sha256 == sha256 (inert for every '
           'record already on disk)', a['repro_sha256'] == a['sha256'])
        open(art, 'w').write(json.dumps({'a': 1, 'elapsed_sec': 2.0}))
        st = recheck.check_record(os.path.join(d, 'provenance.json'))['status']
        ck('A6b and the same wall-clock move still reads DRIFTED when it was '
           'never declared', st == 'DRIFTED', st)

        # A7: a declaration that matches nothing is a problem, not a pass.
        p = write_record(d, 'x.json', {'x.json': ['.no_such_leaf']})
        ck('A7a a declared leaf that is not in the artifact is REFUSED',
           any('no_such_leaf' in s for s in p.get('problems', [])),
           str([s for s in p.get('problems', []) if 'REPRO' in s])[:110])
        p = write_record(d, 'x.json', {'not_an_artifact.json': ['.a']})
        ck('A7b a declaration aimed at a file this spike does not record is '
           'REFUSED', any('not_an_artifact.json' in s for s in p.get('problems', [])),
           str([s for s in p.get('problems', []) if 'REPRO' in s])[:110])

    bad = [c for c in checks if not c[0]]
    print(f"\nH239 probe: {len(checks) - len(bad)} pass, {len(bad)} fail")
    for _, n, d in bad:
        print(f"  FAILED  {n}  {d}")

    # THIS ARTIFACT CARRIES NO WALL CLOCK, WHICH IS THE ROW APPLIED TO ITSELF.
    # A duration here would make this file the 103rd instance of the defect it
    # is about, and would need the very declaration it exists to justify.
    out = {
        'row': 'H239',
        'pin_prefix_recheck': _PIN,
        'fixture': 'spikes/G54_slice_gated_lift/slice_gated.json',
        'published_sha256_prefix': PUBLISHED_SHA,
        'recomputed_sha256_prefix': RECOMPUTED_SHA,
        'elapsed_sec_published': ELAPSED_PUBLISHED,
        'elapsed_sec_recomputed': ELAPSED_RECOMPUTED,
        'leaves_total': 303,
        'leaves_mutated_in_negative_arm': 302,
        'checks_pass': len(checks) - len(bad),
        'checks_fail': len(bad),
        'arms': [{'name': n, 'pass': ok, 'detail': dt} for ok, n, dt in checks],
    }
    with open(os.path.join(HERE, 'result.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write('\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
