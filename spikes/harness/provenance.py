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


def newest_source_mtime(path, exclude=()):
    """Newest mtime among tracked source files, and the HEAD commit time.

    Used to answer: could this artifact have been built from this tree? An
    artifact older than the source it claims to come from could not have been.
    """
    # SCOPED TO `path`, not to the repo. Unscoped `git log -1` returns the
    # monorepo's HEAD time, so a commit by ANY agent to ANY unrelated spike
    # raised the staleness floor for every artifact in the tree -- a false
    # positive that fired the moment two agents ran concurrently.
    # `.md` is EXCLUDED from the floor on both halves: a write-up is not a build
    # input, and a documentation correction must not mark an artifact stale. Checked
    # rather than assumed convenient -- for B1, W4 and S72 the only later commits
    # touched RESULT.md alone, while N1's touched pfx.c/pf_pad.c, and N1 is still
    # flagged. Suppressing md keeps the real signal and drops the false one.
    # The exclusions must apply to BOTH halves of the floor. Fixing only the
    # dirty loop left the commit side self-referential: once `provenance.json`
    # was committed it became the newest tracked non-md file in the spike dir and
    # poisoned that dir's floor permanently -- every historical artifact read as
    # stale again, one cycle after the same bug was fixed on the other half.
    excl_spec = [':(exclude)*.md', ':(exclude)provenance.json']
    for x in exclude:
        try:
            rel = os.path.relpath(os.path.realpath(x), os.path.realpath(path))
        except ValueError:
            continue
        if not rel.startswith('..'):
            excl_spec.append(f':(exclude){rel}')
    head_ts = _run(['git', 'log', '-1', '--format=%ct', '--', '.'] + excl_spec,
                   cwd=path)
    head_ts = int(head_ts) if head_ts.isdigit() else 0
    newest, newest_file = head_ts, '<HEAD commit>'
    # only the dirty ones can be newer than HEAD, and scanning every tracked
    # file in a large repo is slow for no gain.
    #
    # THIS LOOP WAS DEAD until 2026-08-17. `git status --porcelain` prints paths
    # relative to the REPO ROOT, and they were joined onto `path` (the dep dir),
    # so every getmtime raised OSError and was swallowed by `continue`. The
    # consequence is the exact case A24 exists for: patch a source, do not commit
    # it, run a binary built before the patch -- and the floor stayed at the last
    # commit, so nothing fired. Resolve against the root and scope the pathspec.
    # ...and a third bug in the same three lines: `_run` strips the whole output,
    # which eats the leading space of porcelain's two-column status field, so the
    # fixed `l[3:]` slice was off by one on the first line. Split on whitespace
    # instead, which is correct whether or not the line was stripped.
    root = _run(['git', 'rev-parse', '--show-toplevel'], cwd=path) or path
    dirty = [l.split(None, 1)[-1]
             for l in _run(['git', 'status', '--porcelain', '--', '.']
                           + excl_spec, cwd=path).splitlines()
             if l.split(None, 1)]
    # An artifact is not its own source, and `record` writes provenance.json INTO
    # spike_dir -- so when spike_dir is also a dep, the tool's own output became
    # the newest "source" and every historical artifact read as stale. Exclude
    # the declared artifacts and the record itself.
    excl = {os.path.realpath(x) for x in exclude}
    for f in dirty:
        fp = os.path.join(root, f)
        if not os.path.exists(fp) or os.path.realpath(fp) in excl:
            continue
        m = int(os.path.getmtime(fp))
        if m > newest:
            newest, newest_file = m, f
    return newest, newest_file


def artifact_time(path):
    """When this artifact last changed, on the SAME clock as the staleness floor.

    E1 compared an artifact's **mtime** against its dep tree's **commit time**.
    A file is always written before it is committed, so every committed artifact
    inside its own dep tree read as stale by the commit latency -- Q1's
    `quorumsim.py` by 43 seconds, and all five D6 retro-fit targets. Mixing an
    mtime with a commit timestamp is the bug; the two clocks are not comparable.

    Tracked and clean -> its last-commit time, comparable with the HEAD floor.
    Dirty or untracked -> its mtime, comparable with the dirty-file floor.
    """
    d = os.path.dirname(os.path.abspath(path)) or '.'
    base = os.path.basename(path)
    dirty = _run(['git', 'status', '--porcelain', '--', base], cwd=d)
    if not dirty:
        ts = _run(['git', 'log', '-1', '--format=%ct', '--', base], cwd=d)
        if ts.isdigit():
            return int(ts), 'last-commit'
    return int(os.path.getmtime(path)), 'mtime'


def manifest_state(path):
    """Hash every Cargo.toml / Cargo.lock under a dependency tree.

    A binary digest pins WHICH artifact (A24). It does not pin the FEATURE SET
    it was built with, and features change behaviour invisibly: enabling
    hyperon's `das` feature changes `integration_tests__das__test.metta` from
    fuel 107 to fuel 580. **Fuel is the unit of payment and part of the quorum
    agreement key**, so two honest devices built with different features
    disagree on it and neither is wrong.

    Cheap proxy for the resolved feature set: the manifests that determine it.
    """
    out = {}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ('.git', 'target', 'node_modules')]
        for f in files:
            if f in ('Cargo.toml', 'Cargo.lock'):
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, path)
                try:
                    out[rel] = sha256_file(fp)[:16]
                except OSError:
                    pass
    combined = hashlib.sha256(
        json.dumps(out, sort_keys=True).encode()).hexdigest()[:16]
    return {'files': len(out), 'combined_sha256': combined, 'per_file': out}


def repo_state(path):
    """HEAD is not enough. A dirty tree with HEAD=X is not X, and that is
    exactly how a patched build shipped under a stock commit hash."""
    # A dep must be a DIRECTORY inside a git repo. Passing a FILE made
    # subprocess raise NotADirectoryError, which _run swallowed into the string
    # '<error: ...>'; that is not '', so `clean` came out False and certify
    # refused with "DIRTY TREE q3.py at <error: : 1 modified" -- a fabricated
    # verdict about a real tree. Family B inside the family-C module: the
    # instrument reported fiction rather than admitting it could not answer.
    if not os.path.isdir(path):
        raise NotADirectoryError(
            f'repo_state({path!r}): deps must be DIRECTORIES inside a git repo, '
            f'not files. Naming a file silently produced a fake dirty verdict.')
    if _run(['git', 'rev-parse', '--show-toplevel'], cwd=path).startswith('<error'):
        raise ValueError(f'repo_state({path!r}): not inside a git repository')

    head = _run(['git', 'rev-parse', 'HEAD'], cwd=path)
    # SCOPED to this subtree (`-- .`), not repo-wide. Repo-wide made the gate
    # unusable the moment a second agent had anything uncommitted anywhere: an
    # unrelated spike's edits marked THIS build dirty, and the only way past a
    # gate that is permanently red is allow_dirty=True, which voids it. Scoping
    # keeps the check honest -- each declared dep is checked against its own
    # subtree, and a spike that depends on a shared module must name it.
    dirty = _run(['git', 'status', '--porcelain', '--', '.'], cwd=path)
    diff = _run(['git', 'diff', 'HEAD', '--', '.'], cwd=path)
    return {
        'path': path,
        'head': head,
        'clean': dirty == '',
        # Second site of the defect this file NAMES at line 81 and fixes at 84:
        # _run strips the output, eating the leading space of porcelain's
        # two-column status, so l[3:] is off by one on the FIRST line only --
        # which is why 10 of 13 provenance.json files carry an unresolvable first
        # entry ("ISSION_LOOP.md", "claude/hooks/loop_gate.sh"). Family C, in the
        # module whose job is deciding the artifact is not what you think.
        'dirty_files': [l.split(None, 1)[1] if len(l.split(None, 1)) > 1 else l
                        for l in dirty.splitlines()] if dirty else [],
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

    def __init__(self, name, why, null_must_contain=None, can_fail_because=None):
        self.name, self.why = name, why
        # HOW this control could have come out the other way. A control whose
        # failure mode cannot be described is usually one that has none --
        # three dead controls in one session each read as a clean null.
        if not can_fail_because:
            raise ValueError(
                f'control {name}: state `can_fail_because` -- what observation '
                f'would have made this control NOT fire? If you cannot say, it '
                f'may not be able to fail at all (A15).')
        self.can_fail_because = can_fail_because
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
        # A control whose observations are all identical distinguished nothing,
        # whatever verdict it reported.
        if isinstance(self.values, list) and len(self.values) > 1 \
                and len(set(map(str, self.values))) == 1:
            self.constant = True
        else:
            self.constant = False
        self.detail = detail
        return self.fired

    def as_dict(self):
        return {'name': self.name, 'must_fire_because': self.why,
                'can_fail_because': self.can_fail_because,
                'null_must_contain': self.null_must_contain,
                'fired': self.fired, 'detail': self.detail,
                'constant_observations': getattr(self, 'constant', None),
                'observations': self.values}


def record(spike_dir, deps=(), artifacts=(), controls=(),
           allow_dirty=False, note='', no_deps_reason=''):
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
        'manifests': {d: manifest_state(d) for d in deps},
        'artifacts': [{'path': a, 'sha256': sha256_file(a),
                       'bytes': os.path.getsize(a),
                       'mtime': int(os.path.getmtime(a))}
                      for a in artifacts if os.path.exists(a)],
        'missing_artifacts': [a for a in artifacts if not os.path.exists(a)],
        'toolchain': toolchain(),
        'device': device(),
        'controls': [c.as_dict() for c in controls],
    }
    prov['no_deps_reason'] = no_deps_reason
    problems = []

    # D6 E1/E2 HOLE, closed 2026-08-17. `deps=()` skipped the staleness AND the
    # dirty-tree loops below entirely, so a spike that declared no dependency
    # tree got no A24 check at all -- and 2 of the 4 provenance.json on disk were
    # recorded that way. Declaring nothing is now a claim that must be justified,
    # not the quiet default.
    if not deps and not no_deps_reason:
        problems.append(
            'NO DEPS DECLARED and no no_deps_reason given -- staleness (A24) and '
            'dirty-tree checks are both silently skipped when deps is empty. '
            'Name the corpus/source tree, or state why there is none.')

    # STALENESS. A digest pins WHICH artifact, never WHAT IS IN IT. Both agents
    # on this project independently reasoned about a patched tree while running
    # a binary built before the patches; in one case the provenance file
    # recorded the correct sha256 of the wrong binary and nobody noticed,
    # because an accurate hash of a stale artifact looks exactly like an
    # accurate hash of a fresh one.
    _excl = [a['path'] for a in prov['artifacts']] + \
            [os.path.join(spike_dir, 'provenance.json')]
    for d in deps:
        src_ts, src_file = newest_source_mtime(d, exclude=_excl)
        prov.setdefault('source_mtimes', {})[d] = {
            'newest': src_ts, 'from': src_file}
        for a in prov['artifacts']:
            a_ts, a_clock = artifact_time(a['path'])
            a['compared_ts'], a['compared_clock'] = a_ts, a_clock
            if a_ts < src_ts:
                age = (src_ts - a_ts) / 3600.0
                problems.append(
                    f"STALE ARTIFACT {os.path.basename(a['path'])} predates "
                    f"{os.path.basename(d)} source by {age:.1f}h "
                    f"(newest source: {src_file}; artifact clock: {a_clock}). "
                    f"It cannot have been built from the tree recorded here.")

    for r in prov['repos']:
        if not r['clean'] and not allow_dirty:
            problems.append(
                f"DIRTY TREE {r['path']} at {r['head'][:8]}: "
                f"{len(r['dirty_files'])} modified. The build is NOT {r['head'][:8]}.")
    for c in prov['controls']:
        if c['fired'] is None:
            problems.append(f"CONTROL {c['name']} never observed")
        elif c.get('constant_observations'):
            problems.append(
                f"CONTROL {c['name']} has CONSTANT observations across all arms "
                f"-- it distinguished nothing, whatever it reported")
        elif c.get('observations') in (None, [], {}):
            problems.append(
                f"CONTROL {c['name']} carries no observations -- a control "
                f"reported in prose is not in the artefact and cannot be rechecked")
        elif not c['fired']:
            problems.append(
                f"CONTROL {c['name']} DID NOT FIRE -- run is VOID, not negative. "
                f"({c['must_fire_because']})")
        # `null_must_contain` was RECORDED and never CHECKED -- a field shaped
        # like enforcement that was documentation. Absence is now refused. This
        # catches an omitted statement, NOT a vacuous one: no check here can tell
        # a real failing input from plausible filler, which is why D6 F1 stays
        # human-verified.
        if c.get('null_must_contain') in (None, ''):
            problems.append(
                f"CONTROL {c['name']} declares no null_must_contain -- a null "
                f"that cannot contain the effect is not a null (A20), and a "
                f"control with no stated failing input is W1's failure mode")
    if prov['missing_artifacts']:
        problems.append(f"missing artifacts: {prov['missing_artifacts']}")
    prov['problems'] = problems
    prov['ok'] = not problems

    # provenance.json has THREE writers -- record(), kfcheck.certify() (which
    # rewrites it after calling record), and retrofit_d6.py (which patches its
    # d6_retrofit block in). Last-writer-wins silently erased whichever ran
    # first. Carry forward top-level keys this function does not author, so the
    # file is additive instead of clobbering, and NAME what was carried so a
    # stale block cannot masquerade as fresh. `certify` inherits this because its
    # own dict is the one returned here.
    dest = os.path.join(spike_dir, 'provenance.json')
    if os.path.exists(dest):
        try:
            with open(dest) as f:
                old = json.load(f)
            carried = [k for k in old if k not in prov]
            for k in carried:
                prov[k] = old[k]
            if carried:
                prov['carried_from_previous_record'] = carried
        except (ValueError, OSError):
            pass
    with open(dest, 'w') as f:
        json.dump(prov, f, indent=1)
    return prov['ok'], prov


def demo():
    import tempfile
    d = tempfile.mkdtemp()

    NR = 'synthetic control test, there is no source tree'

    def ctl(name='posctl', why='must vary or the instrument is blind'):
        return Control(name, why, null_must_contain='40 identical hashes',
                       can_fail_because='a deterministic program would give 40 identical hashes')

    c_good = ctl()
    c_good.observe(True, [f'hash{i}' for i in range(40)], '40/40 distinct')
    ok, p = record(d, deps=(), artifacts=(), controls=[c_good], no_deps_reason=NR)
    assert ok, p['problems']

    # deps=() used to disable the staleness AND dirty-tree checks silently
    ok, p = record(d, deps=(), controls=[c_good])
    assert not ok and 'NO DEPS DECLARED' in p['problems'][0], p['problems']

    # null_must_contain was recorded and never checked
    c_nonull = Control('posctl', 'why', can_fail_because='x')
    c_nonull.observe(True, ['v'])
    ok, p = record(d, controls=[c_nonull], no_deps_reason=NR)
    assert not ok and 'null_must_contain' in p['problems'][0], p['problems']

    c_dead = ctl()
    c_dead.observe(False, ['same'] * 40, '1/40 distinct')
    ok, p = record(d, controls=[c_dead])
    assert not ok and any('CONSTANT' in x or 'VOID' in x for x in p['problems']), p['problems']

    # a control asserted with no data is refused at the point of observation
    try:
        Control('x', 'y', can_fail_because='declared').observe(True, None)
        raise AssertionError('should have refused a control with no observations')
    except ValueError:
        pass
    ok, p = record(d, controls=[c_dead], no_deps_reason=NR)
    # either diagnosis is correct: it did not fire, AND its observations were
    # constant. The constant check is the stronger one and reports first.
    assert not ok and any(('VOID' in x or 'CONSTANT' in x) for x in p['problems']), \
        p['problems']

    c_unobs = ctl()
    ok, p = record(d, controls=[c_unobs], no_deps_reason=NR)
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

    # manifest hashing must notice a feature change, which a binary digest cannot
    kf2 = os.path.expanduser('~/kingfisher/spikes/S15_android_device/fuelrun')
    if os.path.isfile(os.path.join(kf2, 'Cargo.toml')):
        m1 = manifest_state(kf2)
        assert m1['files'] >= 1 and len(m1['combined_sha256']) == 16
        import tempfile as _tf, shutil as _sh
        tmp = _tf.mkdtemp()
        _sh.copy(os.path.join(kf2, 'Cargo.toml'), tmp)
        before = manifest_state(tmp)['combined_sha256']
        with open(os.path.join(tmp, 'Cargo.toml'), 'a') as fh:
            fh.write('\n# feature change\n')
        assert manifest_state(tmp)['combined_sha256'] != before, \
            'a manifest edit must change the combined hash'

    # --- staleness: an artifact older than the source cannot come from it
    import time as _t
    kf = os.path.expanduser('~/kingfisher/elders/hyperon-experimental')
    if os.path.isdir(os.path.join(kf, '.git')):
        old_art = os.path.join(d, 'stale.bin')
        with open(old_art, 'wb') as f:
            f.write(b'x')
        os.utime(old_art, (1_600_000_000, 1_600_000_000))   # year 2020
        ok, p = record(d, deps=[kf], artifacts=[old_art],
                       controls=[c_good], allow_dirty=True)
        assert not ok and any('STALE ARTIFACT' in x for x in p['problems']), \
            p['problems']
        # a freshly written artifact passes
        fresh = os.path.join(d, 'fresh.bin')
        with open(fresh, 'wb') as f:
            f.write(b'x')
        ok, p = record(d, deps=[kf], artifacts=[fresh],
                       controls=[c_good], allow_dirty=True)
        assert ok, p['problems']

    # --- the DIRTY-FILE half of the staleness floor, in a throwaway git repo.
    # This is the A24 case: patch a source, do not commit it, run an artifact
    # built before the patch. It was DEAD until 2026-08-17 (porcelain prints
    # repo-root-relative paths; they were joined onto the dep dir, so every
    # getmtime raised OSError and was swallowed). The old assertion above could
    # not see it, because a year-2020 artifact fails on the HEAD floor alone --
    # a control that only exercises one of two mechanisms cannot detect the
    # other one being broken.
    g = tempfile.mkdtemp()
    _run(['git', 'init', '-q'], cwd=g)
    _run(['git', 'config', 'user.email', 't@example.invalid'], cwd=g)
    _run(['git', 'config', 'user.name', 'test'], cwd=g)
    src = os.path.join(g, 'src.c')
    with open(src, 'w') as f:
        f.write('int main(void){return 0;}\n')
    _run(['git', 'add', '.'], cwd=g)
    _run(['git', 'commit', '-qm', 'init'], cwd=g)
    head = _run(['git', 'log', '-1', '--format=%ct', '--', '.'], cwd=g)
    head = int(head) if head.isdigit() else 0
    art = os.path.join(d, 'built_before_patch.bin')
    with open(art, 'wb') as f:
        f.write(b'x')
    os.utime(art, (head + 10, head + 10))          # built AFTER the commit
    ok, p = record(d, deps=[g], artifacts=[art], controls=[c_good],
                   allow_dirty=True)
    assert ok, ('an artifact newer than the dep commit must pass', p['problems'])
    with open(src, 'a') as f:                      # patch, do NOT commit
        f.write('// patched after the build\n')
    os.utime(src, (head + 20, head + 20))
    ok, p = record(d, deps=[g], artifacts=[art], controls=[c_good],
                   allow_dirty=True)
    assert not ok and any('STALE ARTIFACT' in x for x in p['problems']), \
        ('the dirty-file staleness floor did not fire -- the A24 loop is dead',
         p['problems'])

    # provenance.json has three writers; a re-record must not silently erase a
    # key another writer added. FAILS IF the foreign key is gone after re-record.
    c2 = ctl()
    c2.observe(True, ['a', 'b'], '2 distinct')
    record(d, controls=[c2], no_deps_reason=NR)
    pj = os.path.join(d, 'provenance.json')
    with open(pj) as f:
        doc = json.load(f)
    doc['foreign_block'] = {'written_by': 'another writer'}
    with open(pj, 'w') as f:
        json.dump(doc, f)
    record(d, controls=[c2], no_deps_reason=NR)
    with open(pj) as f:
        doc2 = json.load(f)
    assert doc2.get('foreign_block') == {'written_by': 'another writer'}, \
        'a re-record erased another writer\'s block'
    assert 'foreign_block' in doc2.get('carried_from_previous_record', []), \
        'a carried key must be named, or a stale block masquerades as fresh'

    print('provenance: all assertions pass')


if __name__ == '__main__':
    demo()
