#!/usr/bin/env python3
"""Pre-run provenance and control enforcement.

`claimcheck.py` audits a spike's WRITE-UP. Everything that went wrong in the
M1 series went wrong BEFORE the write-up:

  M1.1   built and shipped a patched `elders/hyperon-experimental` while the
         result claimed commit 3f76dc4. The tree was dirty and nobody looked.
  M1.1c  the positive control read STABLE because our own patch had silenced
         it. A dead control is indistinguishable from a real null.
  M1.3   published 35.1 ms of `adb`+`dumpsys` as a system cost (A18).
  M1.5b  extrapolated a rate from one point inside the fixed-cost regime (A18).
  soak   three probes returned empty / unevaluated and all read STABLE.

This records what a THIRD PARTY could re-derive -- commit hashes, binary
digests, device fingerprint, toolchain versions -- and refuses to certify a run
whose positive control did not fire.
"""
import hashlib, json, os, subprocess, sys, time


def _run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except Exception as e:
        return f'<error: {e}>'


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def repo_state(path):
    """HEAD is not enough. A dirty tree with HEAD=X is not X, and that is
    exactly how a patched build shipped under a stock commit hash."""
    head = _run(['git', 'rev-parse', 'HEAD'], cwd=path)
    dirty = _run(['git', 'status', '--porcelain'], cwd=path)
    diff = _run(['git', 'diff', 'HEAD'], cwd=path)
    return {
        'path': path,
        'head': head,
        'clean': dirty == '',
        'dirty_files': [l[3:] for l in dirty.splitlines()] if dirty else [],
        # a third party can reproduce the exact tree from head + this patch
        'diff_sha256': hashlib.sha256(diff.encode()).hexdigest() if diff else None,
        'diff_bytes': len(diff),
    }


def toolchain():
    return {
        'rustc': _run(['rustc', '--version']),
        'cargo_ndk': _run(['cargo', 'ndk', '--version']),
        'python': sys.version.split()[0],
        'uname': _run(['uname', '-mrs']),
    }


def device():
    if _run(['adb', 'get-state']) != 'device':
        return None
    props = ['ro.build.fingerprint', 'ro.build.id', 'ro.product.model',
             'ro.build.version.sdk', 'ro.board.platform']
    out = {p: _run(['adb', 'shell', f'getprop {p}']) for p in props}
    out['abi'] = _run(['adb', 'shell', 'getprop ro.product.cpu.abi'])
    return out


class Control:
    """A positive control that MUST fire, and whose OBSERVATIONS are persisted.

    Two failure modes, both seen:
      - a control that cannot fire (three in one session, all reading as clean
        nulls: an absent Python-ext atom, an unbound generator, a match against
        an atom never added);
      - a control that was described but never saved. A null computed inline and
        reported in prose is unfalsifiable afterwards: nobody can recheck a
        number that exists only in a sentence.

    So `observe` requires the actual values, not a boolean, and they land in
    provenance.json where a third party can recompute the verdict.
    """

    def __init__(self, name, why, null_must_contain=None):
        self.name, self.why = name, why
        # what the null/baseline must be CAPABLE of producing. A null that
        # cannot contain the structure under test is not a null: it will always
        # be beaten, and "beats null" then restates the structure's existence.
        self.null_must_contain = null_must_contain
        self.fired, self.values, self.detail = None, None, None

    def observe(self, fired, values, detail=''):
        if values is None:
            raise ValueError(
                f'control {self.name}: observations are required, not just a '
                f'verdict -- a control reported only in prose cannot be rechecked')
        self.fired = bool(fired)
        self.values = list(values) if not isinstance(values, dict) else values
        self.detail = detail
        return self.fired

    def as_dict(self):
        return {'name': self.name, 'must_fire_because': self.why,
                'null_must_contain': self.null_must_contain,
                'fired': self.fired, 'detail': self.detail,
                'observations': self.values}


def record(spike_dir, deps=(), artifacts=(), controls=(),
           allow_dirty=False, note=''):
    """Write provenance.json next to the spike. Returns (ok, provenance).

    ok is False when a dependency tree is dirty without acknowledgement, or a
    declared positive control did not fire. A caller that ignores `ok` and
    publishes anyway is doing the thing this module exists to stop.
    """
    prov = {
        'spike': os.path.basename(os.path.abspath(spike_dir)),
        'recorded_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'note': note,
        'repos': [repo_state(d) for d in deps],
        'artifacts': [{'path': a, 'sha256': sha256_file(a),
                       'bytes': os.path.getsize(a)}
                      for a in artifacts if os.path.exists(a)],
        'missing_artifacts': [a for a in artifacts if not os.path.exists(a)],
        'toolchain': toolchain(),
        'device': device(),
        'controls': [c.as_dict() for c in controls],
    }
    problems = []
    for r in prov['repos']:
        if not r['clean'] and not allow_dirty:
            problems.append(
                f"DIRTY TREE {r['path']} at {r['head'][:8]}: "
                f"{len(r['dirty_files'])} modified. The build is NOT {r['head'][:8]}.")
    for c in prov['controls']:
        if c['fired'] is None:
            problems.append(f"CONTROL {c['name']} never observed")
        elif c.get('observations') in (None, [], {}):
            problems.append(
                f"CONTROL {c['name']} carries no observations -- a control "
                f"reported in prose is not in the artefact and cannot be rechecked")
        elif not c['fired']:
            problems.append(
                f"CONTROL {c['name']} DID NOT FIRE -- run is VOID, not negative. "
                f"({c['must_fire_because']})")
    if prov['missing_artifacts']:
        problems.append(f"missing artifacts: {prov['missing_artifacts']}")
    prov['problems'] = problems
    prov['ok'] = not problems
    with open(os.path.join(spike_dir, 'provenance.json'), 'w') as f:
        json.dump(prov, f, indent=1)
    return prov['ok'], prov


def demo():
    import tempfile
    d = tempfile.mkdtemp()

    c_good = Control('posctl', 'must vary or the instrument is blind')
    c_good.observe(True, [f'hash{i}' for i in range(40)], '40/40 distinct')
    ok, p = record(d, deps=(), artifacts=(), controls=[c_good])
    assert ok, p['problems']

    c_dead = Control('posctl', 'must vary or the instrument is blind')
    c_dead.observe(False, ['same'] * 40, '1/40 distinct')

    # a control asserted with no data is refused at the point of observation
    try:
        Control('x', 'y').observe(True, None)
        raise AssertionError('should have refused a control with no observations')
    except ValueError:
        pass
    ok, p = record(d, controls=[c_dead])
    assert not ok and 'VOID' in p['problems'][0], p['problems']

    c_unobs = Control('posctl', 'x')
    ok, p = record(d, controls=[c_unobs])
    assert not ok and 'never observed' in p['problems'][0]

    # a dirty dependency must block by default and be recordable on purpose
    kf = os.path.expanduser('~/kingfisher/elders/hyperon-experimental')
    if os.path.isdir(os.path.join(kf, '.git')):
        st = repo_state(kf)
        assert len(st['head']) == 40
        ok, p = record(d, deps=[kf], controls=[c_good])
        if not st['clean']:
            assert not ok and 'DIRTY TREE' in p['problems'][0]
            assert p['repos'][0]['diff_sha256'] is not None
            ok2, _ = record(d, deps=[kf], controls=[c_good], allow_dirty=True)
            assert ok2, 'allow_dirty should permit an acknowledged dirty tree'

    assert sha256_file(__file__) == sha256_file(__file__)
    print('provenance: all assertions pass')


if __name__ == '__main__':
    demo()
