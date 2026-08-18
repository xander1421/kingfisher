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

v2, 2026-08-17 (H20). DEFECT REMOVED: this module could not express a NEGATIVE
result. `Control` is "a positive control that MUST fire" and `record` refuses one
that did not with "run is VOID, not negative" -- correct for an instrument check,
and wrong for a falsifier, whose FIRING is the finding. S80 stated its falsifier
as a Control, the falsifier fired, and `certify` reported the run void; the
result could not be published until the control was restructured by hand, and
every spike whose falsifier fires would have had to reinvent that. A21 -- a test
that cannot express its verdict -- inside the module that enforces A21.
`Falsifier` is additive: no provenance.json already on disk changes shape, no
recorded verdict moves, and a falsifier is still refused for everything a control
is refused for EXCEPT its verdict. `demo()` asserts the difference in one place,
driving the SAME observation through both types.

v3, 2026-08-18 (H98). DEFECT REMOVED: AN EXCLUSION LIST OF FILES APPLIED TO A
`git status --porcelain` OUTPUT THAT CAN NAME A DIRECTORY. For a wholly-untracked
tree porcelain emits ONE line naming the DIRECTORY (`?? spikes/H88_sentinel_branch/`),
not its files -- measured against a tracked spike, which lists per file. Every
exclusion this module owns is a set of FILE paths, so none of them could match:
the declared artifacts, `provenance.json`, and the `:(exclude)*.md` pathspec were
all defeated at once, and `getmtime(<dir>)` is bumped by the creation of each file
inside it -- INCLUDING THE ARTIFACTS THEMSELVES. So a spike writing two artifacts
made the first stale against its own containing directory, and writing RESULT.md
afterwards made every artifact stale, which is precisely what the `.md` suppression
at line 61 exists to prevent. It is the hazard the comment at `_newest_file_mtime`
says was already fixed for files, recurring one level up through the directory
that holds them -- two copies of one rule, and only the file copy had it.
SCOPE: every spike's FIRST certify, i.e. every cycle (§13/H71: every cycle creates
a new spike directory). DIRECTION IS FALSE-RED, never false-green -- but the
bypass a refused lane reaches for is dropping `artifacts=`, which voids the whole
A24 staleness path, and `allow_dirty=True` does NOT suppress it (measured on the
run that found this). Fixed by expanding a porcelain-named directory into its
files and RE-APPLYING in Python the exclusions the pathspec could not deliver.
`demo()` builds an untracked subdirectory of two files and asserts the earlier one
is not stale against the later one's directory bump.
NOT FIXED HERE, REPORTED INSTEAD: `stranded.sh:145` carries the same class in the
FALSE-GREEN direction (`[ -f "$p" ] || continue` silently drops every untracked
directory -- 117 files in 15 directories at the time of writing, including the
`H86_stranded_cost` spike itself). It is ATOM-3's module and was being written to
two minutes before this edit, so it is livechat's, not mine (H19/H66).
"""
import hashlib, json, os, re, subprocess, sys, time


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


def _porcelain_files(fp, root):
    """Yield the SOURCE FILES a `git status --porcelain` path stands for.

    H98. Porcelain collapses a wholly-untracked tree to a single line naming the
    DIRECTORY. Callers here match that path against sets of FILE paths -- the
    declared artifacts, `provenance.json` -- and apply `:(exclude)*.md` as a
    pathspec, and NONE of those can match a directory. So for every new spike the
    exclusions silently did nothing while the directory's own mtime, which each
    artifact write bumps, became the staleness floor.

    The `.md` and `provenance*.json` filters are re-applied HERE because a
    pathspec cannot reach inside a path git never expanded. Keeping them in one
    place would be better; they are duplicated deliberately and named in both, on
    the reasoning that a rule stated twice is a defect only when one copy can be
    changed without the other being found -- one grep for endswith('.md') across
    this module finds both.
    """
    if not os.path.isdir(fp):
        yield fp
        return
    for dirpath, dirnames, filenames in os.walk(fp):
        dirnames[:] = [x for x in dirnames
                       if x not in ('.git', 'target', '__pycache__')]
        for fn in filenames:
            if fn.endswith('.md') or re.match(r'provenance.*\.json$', fn):
                continue
            yield os.path.join(dirpath, fn)


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
        if not os.path.exists(fp):
            continue
        for g in _porcelain_files(fp, root):
            if os.path.realpath(g) in excl:
                continue
            m = int(os.path.getmtime(g))
            if m > newest:
                newest, newest_file = m, os.path.relpath(g, root)
    return newest, newest_file


def _newest_file_mtime(root, exclude=()):
    """Newest real mtime under a dep tree, on the mtime clock.

    Skips .git and target/: a cargo target dir is both enormous and always
    newer than its own source, so including it would make every artifact look
    stale against a tree nobody edited.
    """
    skip = {os.path.realpath(x) for x in exclude}
    newest = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if x not in ('.git', 'target', '__pycache__')]
        for fn in filenames:
            if fn.endswith('.md') or fn == 'provenance.json':
                continue
            # The declared ARTIFACTS live in this tree too, and a spike that
            # writes two of them writes one after the other -- so without this
            # the later artifact becomes the "newest source" and makes the
            # earlier one stale against its own sibling. The primary staleness
            # path already excludes them; this fallback has to agree.
            if os.path.realpath(os.path.join(dirpath, fn)) in skip:
                continue
            try:
                newest = max(newest, int(os.path.getmtime(os.path.join(dirpath, fn))))
            except OSError:
                pass
    return newest


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
    # Same two exclusions the staleness half already applies (see excl_spec):
    # certify WRITES provenance.json into the spike dir, so without excluding it
    # every certify dirtied the subtree it had just scoped the check to and the
    # next run refused -- a gate that poisons itself on second use. *.md is
    # excluded for the reason given above: a writeup edit does not change what
    # was built, and the writeup is authored AFTER certify passes.
    _spec = ['--', '.', ':(exclude)provenance.json', ':(exclude)*.md']
    dirty = _run(['git', 'status', '--porcelain'] + _spec, cwd=path)
    diff = _run(['git', 'diff', 'HEAD'] + _spec, cwd=path)
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

    kind = 'control'

    def as_dict(self):
        return {'name': self.name, 'must_fire_because': self.why,
                'can_fail_because': self.can_fail_because,
                'null_must_contain': self.null_must_contain,
                'fired': self.fired, 'detail': self.detail,
                'kind': self.kind,
                'constant_observations': getattr(self, 'constant', None),
                'observations': self.values}


class Falsifier(Control):
    """A test whose FIRING is the finding. Its outcome does NOT gate `ok`.

    H20, 2026-08-17. `Control` is "a positive control that MUST fire", and
    `record` refuses a control that did not with *"run is VOID, not negative"*.
    That is right for an instrument check and wrong for a falsifier, and the
    difference had never been expressible here:

        S80 stated its falsifier as a Control that fires when the claim holds.
        The falsifier FIRED -- a real, informative negative, the most valuable
        outcome a spike can have -- and `certify` could only report the run VOID.
        The finding could not be published until the control was restructured by
        hand, and every spike whose falsifier fires would have to reinvent that.

    That is A21 -- a test that cannot express its verdict -- inside the module
    that enforces A21.

    WHAT IS STILL REFUSED, because this is not an escape hatch: a falsifier with
    no observations, one that was never observed at all, one with constant
    observations, and one that does not say what outcome would have been the
    other way. Only the FIRED/NOT-FIRED verdict is released from gating `ok`.
    A falsifier that cannot fire is as dead as a control that cannot (A15), and
    `fires_when` is the field that has to say how.

    ADDITIVE ON PURPOSE: no existing spike passes `falsifiers=`, so no
    provenance.json already on disk changes shape and no verdict already
    recorded moves. `certify` still takes its prose `falsifier=` string -- that
    states the claim's refutation in words, and this mechanises one.
    """
    kind = 'falsifier'

    def __init__(self, name, refutes, fires_when, null_must_contain=None):
        super().__init__(name, refutes, null_must_contain=null_must_contain,
                         can_fail_because=fires_when)
        self.fires_when = fires_when
        self.refutes = refutes

    def as_dict(self):
        d = super().as_dict()
        d['refutes'] = self.refutes
        d['fires_when'] = self.fires_when
        d['must_fire_because'] = None          # it must NOT be required to fire
        d['verdict'] = ('REFUTED — the falsifier fired' if self.fired
                        else 'survived — the falsifier did not fire'
                        if self.fired is not None else None)
        return d


class RecordCollision(Exception):
    """A DIFFERENT run is about to overwrite this spike's provenance record.

    v3, 2026-08-17, H49. Refuses rather than warns (§12.13).
    """


def record(spike_dir, deps=(), artifacts=(), controls=(), falsifiers=(),
           allow_dirty=False, note='', no_deps_reason='',
           record_name='provenance.json'):
    """Write `record_name` next to the spike. Returns (ok, provenance).

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
        # H20: recorded beside the controls and NOT gated on their verdict.
        'falsifiers': [f.as_dict() for f in falsifiers],
        'falsifiers_fired': [f.name for f in falsifiers if f.fired],
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
            # A DETERMINISTIC pipeline regenerates an artifact byte-identically,
            # so git makes no new blob and the file keeps an older last-commit
            # than a source file that did change. The commit clock then reports
            # "cannot have been built from this tree" about an artifact that was
            # literally just rebuilt from it -- the success case of reproducible
            # output reading as a failure. On this project that is the common
            # case, and a gate that refuses forever gets bypassed with
            # allow_dirty, which voids it entirely.
            #
            # Second opinion, on ONE clock (mtime vs mtime -- never mixed, that
            # was the E1 bug). Stale only if BOTH clocks agree it is.
            # CAVEAT, stated because it is a real hole: after a fresh clone every
            # mtime is the checkout time, so this fallback passes for everything.
            # It weakens the check to "clone-time evidence only" on a fresh
            # clone; the commit clock remains the primary and is unaffected.
            if a_ts < src_ts:
                src_mt = _newest_file_mtime(d, exclude=_excl)
                if src_mt and int(os.path.getmtime(a['path'])) >= src_mt:
                    a['compared_clock'] = 'regenerated (mtime >= newest source mtime)'
                    continue
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
    # H20 -- FALSIFIERS: everything a control is refused for EXCEPT the verdict.
    # A falsifier that fired is the most valuable outcome a spike can produce, so
    # `ok` must survive it; a falsifier that was never run, never observed, or
    # cannot say what the other outcome would have been is as dead as a control
    # that cannot fail (A15), and is refused exactly as one.
    for f in prov.get('falsifiers', []):
        if f['fired'] is None:
            problems.append(f"FALSIFIER {f['name']} never observed -- declared "
                            f"and not run is the state every error that survived "
                            f"this project was in")
        elif f.get('constant_observations'):
            problems.append(
                f"FALSIFIER {f['name']} has CONSTANT observations -- it "
                f"distinguished nothing, whatever it reported")
        elif f.get('observations') in (None, [], {}):
            problems.append(
                f"FALSIFIER {f['name']} carries no observations -- a verdict "
                f"reported in prose cannot be rechecked")
        if f.get('null_must_contain') in (None, ''):
            problems.append(
                f"FALSIFIER {f['name']} declares no null_must_contain -- the "
                f"outcome space has to be able to contain BOTH answers or the "
                f"verdict was decided by the setup (A20)")
        if not f.get('fires_when'):
            problems.append(
                f"FALSIFIER {f['name']} declares no fires_when -- a falsifier "
                f"that cannot say what would refute the claim cannot refute it")
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
    dest = os.path.join(spike_dir, record_name)
    if os.path.exists(dest):
        try:
            with open(dest) as f:
                old = json.load(f)
            # v3, 2026-08-17, H49. THE CARRY-FORWARD ABOVE CANNOT HELP FOR THE
            # KEYS THIS FUNCTION AUTHORS. `controls`, `falsifiers` and
            # `artifacts` are always in `prov`, so they are never carried, and a
            # DIFFERENT RUN recording into the same directory replaces them
            # outright. Earned the same day, by the author of the carry-forward:
            # an ATTACK cycle called certify(HERE) with HERE = the target spike's
            # own directory, and S79's provenance.json -- five controls and the
            # absence.json digest -- became the attack's three controls and
            # attack.json. The spike's D6 evidence was destroyed on disk and the
            # live file read as a complete, passing record of a run nobody made.
            # Recoverable from git, which is not the point: WORK_QUEUE cited five
            # controls and the file showed three.
            #
            # DECIDABLE, and this is why it refuses rather than warns: a
            # legitimate RE-RUN of the same spike records the same artifacts. A
            # different run records different ones. Disjoint artifact basenames
            # mean the two records are about different work, and the remedy is in
            # the message rather than in a convention nobody reads.
            def _basenames(rec):
                return {os.path.basename(a.get('path', '')) for a in
                        rec.get('artifacts', []) if a.get('path')}
            old_a, new_a = _basenames(old), _basenames(prov)
            if old_a and new_a and not (old_a & new_a):
                raise RecordCollision(
                    '%s already records a DIFFERENT run: artifacts %s, and this '
                    'one records %s. Overwriting would destroy that run\'s '
                    'controls and digests. Pass record_name="provenance.<what>.'
                    'json" -- an attack on a spike belongs beside it, not on top '
                    'of it.' % (dest, sorted(old_a), sorted(new_a)))
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

    # --- H98: a porcelain line that names a DIRECTORY, not a file --------------
    # THE CONTROLLED REPRODUCTION, and it has to be controlled: at repo scope the
    # defect is MASKED whenever any other lane touches a tracked file, because
    # that file's own porcelain line sets a higher floor than the directory ever
    # reaches. Measured, and it is why a whole-repo sweep reported 0 flips one
    # minute after the same fix demonstrably flipped H88 -- the instant another
    # lane saved `stranded.sh`, its mtime dominated every directory-derived floor
    # in the tree. A defect that only bites when the new spike IS the newest thing
    # is a defect that bites exactly at certify time, and nowhere else.
    import tempfile as _tf2
    g2 = _tf2.mkdtemp()
    _run(['git', 'init', '-q'], cwd=g2)
    _run(['git', 'config', 'user.email', 't@example.invalid'], cwd=g2)
    _run(['git', 'config', 'user.name', 'test'], cwd=g2)
    with open(os.path.join(g2, 'tracked.txt'), 'w') as f:
        f.write('committed source\n')
    _run(['git', 'add', '-A'], cwd=g2)
    # THE COMMIT DATE IS PINNED, and v1 of this fixture did not pin it. The floor
    # has TWO sources -- the HEAD commit and the dirty files -- and a sandbox
    # committed just now puts HEAD at the current second, so backdated artifacts
    # were stale against HEAD and the assertion fired for a reason that had
    # nothing to do with H98. A fixture that does not control every clock it
    # compares is measuring whichever one it forgot.
    _base = 1_700_000_000
    _env = dict(os.environ, GIT_AUTHOR_DATE='@%d +0000' % (_base - 1000),
                GIT_COMMITTER_DATE='@%d +0000' % (_base - 1000))
    subprocess.run(['git', 'commit', '-qm', 'base'], cwd=g2, env=_env,
                   capture_output=True)
    # A NEW SPIKE: one wholly-untracked directory, two artifacts written in
    # order, then a RESULT.md written last -- the exact shape of every cycle.
    sp = os.path.join(g2, 'spikes', 'NEW')
    os.makedirs(sp)
    # THE FIXTURE MUST CONTAIN A SOURCE FILE, and v1 of it did not -- which made
    # it the right measurement of the wrong question. With ONLY declared
    # artifacts and a .md inside, the `:(exclude)` pathspecs suppress every path
    # in that directory and git prints no porcelain line at all, so even v2 read
    # a clean floor and the reproduction passed against the unfixed code. A real
    # spike always carries its driver (§5: "a number without its generator does
    # not exist"), that driver is neither an artifact nor a .md, and its presence
    # is what makes git emit the directory line the defect rides on.
    drv = os.path.join(sp, 'driver.py')
    with open(drv, 'w') as f:
        f.write('# the generator\n')
    a1, a2 = os.path.join(sp, 'first.out'), os.path.join(sp, 'second.out')
    for i, a in enumerate((a1, a2)):
        with open(a, 'w') as f:
            f.write('artifact\n')
        os.utime(a, (_base + i, _base + i))
    with open(os.path.join(sp, 'RESULT.md'), 'w') as f:
        f.write('# writeup\n')
    # The directory mtime is bumped by each creation and is NEWER than both
    # artifacts -- that is the whole mechanism, so assert it rather than assume.
    # the driver PREDATES its outputs, which is the only ordering that can occur
    os.utime(drv, (_base - 100, _base - 100))
    dir_mt = int(os.path.getmtime(os.path.join(g2, 'spikes')))
    assert dir_mt > int(os.path.getmtime(a2)), \
        'reproduction is void: the directory mtime must exceed its artifacts'
    assert _run(['git', 'status', '--porcelain', '--', '.'], cwd=g2).strip() \
        .endswith('spikes/'), 'reproduction is void: porcelain must collapse to a directory'
    # v3: the floor comes from the FILES, and both declared artifacts are
    # excluded, so the only survivor is... nothing. RESULT.md is dropped by the
    # .md rule that a pathspec could not deliver here. Floor falls back to HEAD.
    # THE NEGATIVE CONTROL, and it is the half that decides the assertion below
    # means anything: under v2 the porcelain directory IS the floor, so the first
    # artifact was stale against its own sibling's creation. Computed here from
    # the same fixture rather than asserted from the changelog.
    assert dir_mt > int(os.path.getmtime(a1)), (
        'fixture is void: v2 floor (%s) must exceed the artifact (%s), or there '
        'was never anything to fix' % (dir_mt, int(os.path.getmtime(a1))))
    assert int(os.path.getmtime(drv)) < int(os.path.getmtime(a1)), \
        'fixture is void: the driver must predate the artifacts it produced'
    n, nf = newest_source_mtime(g2, exclude=[a1, a2])
    assert n < int(os.path.getmtime(a1)), (
        'H98 REGRESSION: an artifact is stale against its own containing '
        'directory again -- floor %s from %r, artifact %s'
        % (n, nf, int(os.path.getmtime(a1))))
    # ...and for the RIGHT REASON. A floor that fell back to HEAD would satisfy
    # the line above while proving the expansion never ran, which is how v1 of
    # this fixture passed against unfixed code.
    assert nf.endswith('driver.py'), (
        'the floor must come from the expanded source file, not %r -- a HEAD '
        'fallback passes the assertion above without the fix' % (nf,))
    # and the exclusion must still be capable of failing: an UNDECLARED file
    # inside that same directory must raise the floor, or the fix has simply
    # stopped looking at untracked directories altogether.
    # and the floor must still RISE when real source moves: touching the driver
    # past the artifacts has to make them stale, or the fix has simply stopped
    # looking inside untracked directories, which would be a false GREEN.
    os.utime(drv, (_base + 500, _base + 500))
    n2, nf2 = newest_source_mtime(g2, exclude=[a1, a2])
    assert n2 == _base + 500 and nf2.endswith('driver.py'), \
        'the expansion must still SEE source edits inside the directory: %s %s' % (n2, nf2)
    _sh2 = __import__('shutil')
    _sh2.rmtree(g2, ignore_errors=True)

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
        # record_name, because this is a SECOND, different synthetic run sharing
        # one scratch dir with the stale-artifact arm above -- exactly the shape
        # H49 refuses, and the first thing the new refusal caught was this
        # self-test. Two different runs in one directory is the confusion; giving
        # the second its own record is the remedy, not a loosening.
        ok, p = record(d, deps=[kf], artifacts=[fresh],
                       controls=[c_good], allow_dirty=True,
                       record_name='provenance.fresh.json')
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
    # record_name again: a third synthetic run in the same scratch dir. H49's
    # refusal caught all three on its first execution, which is the check
    # earning its place before it ever saw a real spike.
    ok, p = record(d, deps=[g], artifacts=[art], controls=[c_good],
                   allow_dirty=True, record_name='provenance.a24.json')
    assert ok, ('an artifact newer than the dep commit must pass', p['problems'])
    with open(src, 'a') as f:                      # patch, do NOT commit
        f.write('// patched after the build\n')
    os.utime(src, (head + 20, head + 20))
    ok, p = record(d, deps=[g], artifacts=[art], controls=[c_good],
                   allow_dirty=True, record_name='provenance.a24.json')
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

    # ---- H20: a falsifier that FIRES must not void the run -------------------
    # The one assertion that could not pass before this existed, and that states
    # the whole defect: the SAME observation, expressed as a Control, voids the
    # run; expressed as a Falsifier, it is recorded and `ok` survives.
    #
    # Earned in S80, whose falsifier fired -- a real negative, the most valuable
    # outcome a spike can have -- and `certify` could only say "run is VOID, not
    # negative", so the finding could not be published until the control was
    # restructured by hand. A21 inside the module that enforces A21.
    if True:
        as_control = Control('same_observation', 'why',
                             null_must_contain='both outcomes',
                             can_fail_because='the ordering matches')
        as_control.observe(False, {'ordering': 'differs'})
        ok_c, p_c = record(d, controls=[as_control], no_deps_reason=NR)
        assert not ok_c and any('VOID' in x for x in p_c['problems']), p_c['problems']

        f = Falsifier('same_observation',
                      refutes='the claim that the orderings agree',
                      fires_when='the ordering differs',
                      null_must_contain='both outcomes')
        f.observe(True, {'ordering': 'differs'})
        ok_f, p_f = record(d, falsifiers=[f], no_deps_reason=NR)
        assert ok_f, p_f['problems']
        assert p_f['falsifiers_fired'] == ['same_observation'], p_f['falsifiers_fired']
        assert p_f['falsifiers'][0]['verdict'].startswith('REFUTED'), p_f['falsifiers'][0]

        # ...and it is NOT an escape hatch. Everything else a control is refused
        # for, a falsifier is refused for too.
        f2 = Falsifier('never_run', 'a claim', 'an observation', 'both outcomes')
        ok2, p2 = record(d, falsifiers=[f2], no_deps_reason=NR)
        assert not ok2 and any('never observed' in x for x in p2['problems']), p2['problems']

        f3 = Falsifier('no_null', 'a claim', 'an observation')
        f3.observe(False, {'x': 1})
        ok3, p3 = record(d, falsifiers=[f3], no_deps_reason=NR)
        assert not ok3 and any('null_must_contain' in x for x in p3['problems']), p3['problems']

        try:
            Falsifier('no_fires_when', 'a claim', '')
            raise AssertionError('a falsifier with no fires_when must be refused')
        except ValueError:
            pass

        # regression: a dead CONTROL still voids the run, unchanged by all this
        dead = Control('still_gated', 'why', null_must_contain='n',
                       can_fail_because='c')
        dead.observe(False, {'x': 1})
        ok4, p4 = record(d, controls=[dead], no_deps_reason=NR)
        assert not ok4 and any('VOID' in x for x in p4['problems']), p4['problems']

    # ---- H49: a DIFFERENT run must not overwrite a spike's record ----------
    # Verified to fail when the refusal is removed: delete the RecordCollision
    # raise and the first assert below goes AssertionError instead.
    d2 = tempfile.mkdtemp()
    a1 = os.path.join(d2, 'spike.json')
    a2 = os.path.join(d2, 'attack.json')
    open(a1, 'w').write('{"real": 1}')
    open(a2, 'w').write('{"attack": 1}')

    def _c(name):
        c = Control(name, 'why', null_must_contain='n', can_fail_because='c')
        c.observe(True, [1, 2])
        return c

    record(d2, artifacts=[a1], controls=[_c('spike_control')],
           no_deps_reason=NR)
    try:
        record(d2, artifacts=[a2], controls=[_c('attack_control')],
               no_deps_reason=NR)
    except RecordCollision as e:
        assert 'record_name' in str(e), str(e)
    else:
        raise AssertionError(
            'a run recording attack.json overwrote a record describing '
            'spike.json -- the spike\'s controls and digests are gone and the '
            'file reads as a complete passing record of a run nobody made')
    # the original survived untouched
    got = json.load(open(os.path.join(d2, 'provenance.json')))
    assert [c['name'] for c in got['controls']] == ['spike_control'], got
    # and the remedy the message names actually works
    record(d2, artifacts=[a2], controls=[_c('attack_control')],
           no_deps_reason=NR, record_name='provenance.attack.json')
    side = json.load(open(os.path.join(d2, 'provenance.attack.json')))
    assert [c['name'] for c in side['controls']] == ['attack_control'], side
    # a genuine RE-RUN of the same spike still overwrites, which is the whole
    # reason this refuses on DISJOINT artifacts rather than on any overwrite
    ok5, _p5 = record(d2, artifacts=[a1], controls=[_c('spike_control')],
                      no_deps_reason=NR)
    assert ok5

    print('provenance: all assertions pass')


if __name__ == '__main__':
    demo()
