#!/usr/bin/env python3
"""M1.8 -- quorum-3 pipeline end to end. Coordinator + 3 worker processes.

Adjudication is BOINC's majority rule (sample_bitwise_validator.cc:17-18):
a result is accepted when >=2 of 3 replicas agree BYTE FOR BYTE. What must
match is (status, fuel_used, sorted_hash) -- fuel_used is in the key because
S57 established that equal output with unequal fuel is a divergence, not an
agreement.
"""
import argparse, hashlib, json, os, platform, shutil, subprocess, sys, time
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'M1_5_shardstore'))
from shardstore import ShardStore
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'harness'))
from canon import canon, canon_alpha_strict, is_ground, AlphaLossy
import bansurface
from instrument import check_nonempty
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'M1_3_worker'))
import preflight

HERE = os.path.dirname(os.path.abspath(__file__))
# known-provenance binaries, built from the tree recorded in provenance.json.
# The old S30 fuelrun.v2.* were prebuilt 16:16 the previous day -- BEFORE every
# patch -- so earlier M1 runs measured a stock binary against a patched tree.
BIN  = os.path.join(HERE, '..', 'S30_speed_duel', 'bin', 'known')
DEVDIR = '/data/local/tmp/m18'

ALPHA = False   # set by --alpha; opt-in per job class, never the default
MIN_DOMAINS = 3  # independent failure domains required among AGREEING workers

# Axes the domain key can separate. Each is only itself: `binary` differing does
# not imply `host` does.
DOMAIN_AXES = ('binary', 'manifest', 'host', 'os', 'isa', 'operator')

# worker_id -> coordinator-OBSERVED domain vector. Never worker-declared.
OBSERVED = {}

# Fault classes NO axis separates, so replication cannot detect them at ANY
# quorum size. Recorded because a domain count that omits them reads as
# stronger than it is.
UNSEPARABLE = {
    'shared implementation bug': 'every honest evaluator computes the same '
        'wrong answer. Replication catches disagreement, never a shared bug.',
    'shared abort (G18 1022-match panic)': 'verified identical on macos-arm64 '
        'and android-aarch64 -- determinism extends to the crash, so quorum '
        'is structurally incapable here however many devices exist.',
}


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return ''


FUELRUN_SRC = os.path.join(HERE, '..', 'S15_android_device', 'fuelrun')
HYPERON_SRC = os.path.expanduser('~/kingfisher/elders/hyperon-experimental')


def operator_label(via):
    """Who the coordinator records as operator.

    Production: always UNATTESTED (no attestation root).
    DEV (KF_DEV_SINGLE_OPERATOR=1): phone (adb/app) is DEV:PHONE, host is
    DEV:HOST — a seat label so one human can see operator=2 on that axis.
    Not an attestation root. Manifest still binds. Verdict is still not
    UNANIMOUS (DEV_SINGLE_OPERATOR).
    """
    if os.environ.get('KF_DEV_SINGLE_OPERATOR') == '1':
        return 'DEV:PHONE' if via in ('adb', 'app') else 'DEV:HOST'
    return 'UNATTESTED'


def observed_domains(wid, binary, via):
    """Domain identity the COORDINATOR observes, never what the worker declares.

    A worker declaring its own independence is worth exactly what a worker's
    claim about its own correctness is worth. For an honest worker `arm64` vs
    `arm64-v8a` is a normalisation bug; for a dishonest one it is the attack --
    emit distinct host/operator strings and inflate the domain count, achieving
    the same capture through the field built to stop it. Third appearance of
    self-reported identity as a defect (S62 `backend_class`, M1.5 binary hash,
    this).

    So each axis is filled from something the coordinator controls or measures,
    and an axis with no attestation root collapses to ONE domain rather than
    being taken on trust.
    """
    # the coordinator hashes the binary it dispatched -- not the one the worker
    # says it ran. (It still cannot prove the worker EXECUTED this binary; that
    # needs attestation. Recorded below.)
    bin_sha = hashlib.sha256(open(binary, 'rb').read()).hexdigest()[:12]

    if via in ('adb', 'app'):
        serial = subprocess.run(['adb', 'get-serialno'], capture_output=True,
                                text=True).stdout.strip() or 'unknown-device'
        host = f'adb:{serial}'          # observed from OUR adb connection
        rel = subprocess.run(['adb', 'shell', 'getprop ro.build.version.release'],
                             capture_output=True, text=True).stdout.strip()
        os_id, isa = f'android-{rel or "?"}', 'aarch64'
    else:
        host = f'host:{platform.node()}'   # the coordinator's own machine
        os_id = f'{platform.system().lower()}-{platform.release()}'
        # read the ISA off the BINARY, not off the coordinator. An x86-64 build
        # running under Rosetta on this arm64 host is a different ISA domain,
        # and `platform.machine()` would have reported the host's and silently
        # merged them -- the same self-flattering-key defect one level up.
        arches = _run(['lipo', '-archs', binary])
        isa = arches.split()[0] if arches and 'error' not in arches.lower() \
            else platform.machine()
    isa = 'aarch64' if isa.lower().startswith(('arm64', 'aarch64')) else \
          ('x86_64' if isa.lower() in ('x86_64', 'amd64') else isa.lower())

    # A Cargo FEATURE changes fuel_used (analysis/FEATURE_EQUIVALENCE.md: 107 vs
    # 580 on one program). Two binaries from the same manifest share every
    # feature-induced fault, so they are ONE domain on that axis however
    # different their digests are.
    try:
        sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
        from provenance import manifest_state
        # the app is built from the hyperon workspace (libhyperonc takes
        # workspace defaults); fuelrun has its own Cargo.toml. Different
        # manifests, so this axis rises honestly rather than by relabelling.
        if via == 'app':
            src = HYPERON_SRC
        elif 'min' in os.path.basename(binary):
            src = os.path.join(HERE, '..', 'S15_android_device', 'fuelrun_min')
        else:
            src = FUELRUN_SRC
        man = manifest_state(src)['combined_sha256'] if os.path.isdir(src) else 'unknown'
    except Exception:
        man = 'unknown'

    return {
        'binary': f'bin:{bin_sha}',
        'manifest': f'man:{man}',
        'host': host,
        'os': os_id,
        'isa': isa,
        # Production: UNATTESTED (no attestation root). DEV flag: phone vs
        # host seat labels only — see operator_label().
        'operator': operator_label(via),
    }


def observed_residency(devdir):
    """Which CIDs the device actually holds, read from the device.

    A22: `prefer_cached_cids` (`hyperjob_v0:114`) makes matching depend on which
    shards a device holds, and the schema has no field for it -- so the natural
    implementation is the device declaring its own cache, i.e. a worker telling
    the matcher which jobs it should win. That is a direct route to the S69/S70
    residency capture.

    The worker's `bytes_pushed` is the same defect in miniature: it is the
    worker reporting whether it already had the shard. Neither is used for
    residency. This is.
    """
    out = subprocess.run(['adb', 'shell', f'ls {devdir}/shards 2>/dev/null'],
                         capture_output=True, text=True).stdout
    return {l.strip() for l in out.splitlines() if l.strip().startswith('b')}


def key(e):
    """Agreement key. `sorted_hash` is hashed by fuelrun from raw output, which
    embeds hyperon's process-global variable counter (`$x#24605`) whenever a
    result carries a data-origin variable -- M1.1c measured 40 distinct hashes
    in 40 runs of one such program. Two honest devices would disagree.

    Where fuelrun gives us the result TEXT we canonicalise it (renumber
    variables by first appearance) and key on that instead. Where it gives us
    only its own hash, we cannot, and the envelope is flagged so the gap is
    visible rather than silently trusted."""
    if e is None: return None

    # SOUNDNESS. `results_text` was guarded for ABSENCE and not for EMPTINESS, so
    # canon('') -> '' -> sha256('') = e3b0c442..., and three workers returning an
    # empty results block keyed IDENTICALLY and adjudicated UNANIMOUS -- agreement
    # on nothing. `sorted_hash` of '' or None agreed the same way. Because key()
    # prefers results_text when present, an empty block also silently DISCARDED
    # the worker's own sorted_hash.
    #
    # An empty capture is not a measurement, so such a worker did not answer:
    # returning None routes it into the existing non-answer path
    # (`live = [k for k in ks if k is not None]`) and out through
    # REDUCED_QUORUM / NO_RESULTS, which already refuse to call a short quorum
    # clean. No new verdict, no new branch.
    #
    # instrument.check_nonempty already refused both '' and the empty-hash
    # constants; q3.py never called it. The guard existed at the shared site and
    # was not wired -- found by a fresh reviewer 2026-08-17.
    # ONLY for a worker claiming SUCCESS. A worker reporting a FAILED status
    # legitimately has no result member, and this function's own contract says
    # agreement that a job FAILED is a different verdict from agreement on a
    # RESULT. The first version of this guard omitted that condition and turned
    # `adj([crash, crash, crash])` from AGREED_FAILURE into NO_RESULTS --
    # test_adjudicate.py:62 caught it. Fixed the site, broke its sibling: the
    # exact class this repo spent a day cataloguing, committed while cataloguing
    # it. The test that caught it was written by another atom.
    if e.get('status') not in FAILED_STATUS:
        _res = e.get('results_text')
        _cand = _res if _res is not None else e.get('sorted_hash')
        _ok, _why = check_nonempty(_cand, 'result member')
        if not _ok:
            e['empty_result'] = _why
            return None

    txt = e.get('results_text')
    if txt is not None:
        # alpha is lossless ONLY on a ground result set. A non-ground result can
        # be carried into another query, where "which of my variables landed
        # where" stops being vacuous. Fall back rather than weaken silently.
        if ALPHA:
            try:
                norm = canon_alpha_strict(txt)
            except AlphaLossy:
                e['alpha_refused'] = True
                norm = canon(txt)
        else:
            norm = canon(txt)
        return (e.get('status'), e.get('fuel_used'),
                hashlib.sha256(norm.encode()).hexdigest())
    return (e.get('status'), e.get('fuel_used'), e.get('sorted_hash'))

# statuses that mean "nobody produced an answer", as opposed to "the answer is X"
FAILED_STATUS = {'CRASH', 'TIMEOUT', 'SHARD_MISSING', 'NO_PARSE'}


def adjudicate(envs):
    """Returns (verdict, key, agree_count).

    Four outcomes, not three. Agreement that a job FAILED is not agreement on a
    RESULT, and the two need different handling: disagreement means somebody is
    wrong, a crash means nobody answered. Conflating them would let three
    aborting workers be counted as a successful quorum.

    A panicking `fuelrun` exits 134 (SIGABRT) and prints no fields, so its
    envelope carries status CRASH and no fuel_used -- hence the None-safe key.
    """
    ks = [key(e) for e in envs]
    live = [k for k in ks if k is not None]
    dispatched, returned = len(ks), len(live)
    if not live:
        # Was a 5-tuple while every sibling path and the only production caller
        # (q3.py, `v, k, n, disp, ret, dom = adjudicate(envs)`) use 6, so total
        # quorum loss -- the BEST case for the crafted-job availability attack
        # described below -- took the coordinator down with a ValueError instead
        # of recording NO_RESULTS. test_adjudicate.py asserted only [0], so the
        # suite exercised the function differently from the caller and could not
        # see it. Found by a fresh reviewer 2026-08-17.
        return 'NO_RESULTS', None, 0, dispatched, returned, 0
    k, n = Counter(live).most_common(1)[0]

    # A worker that never answered SHRANK the quorum. Counting agreement over
    # only the survivors turns an availability failure into a clean verdict,
    # and that is exploitable: the panic threshold is result CARDINALITY, which
    # depends on the shard, and the job author chooses the program. An
    # adversary can author a job that crosses hyperon's 1024-result limit on an
    # honest device's shard but not on their own, killing the honest workers
    # and leaving their own nodes as the whole quorum. Cost: one crafted job --
    # no stake, no Sybils, no collusion. Q1's 72% capture figure assumed quorum
    # SIZE was fixed; it is not. So a short quorum is never a clean verdict.
    if returned < dispatched:
        return 'REDUCED_QUORUM', k, n, dispatched, returned, 0
    if n >= 2:
        if k[0] in FAILED_STATUS:
            return 'AGREED_FAILURE', k, n, dispatched, returned, 0

        # INDEPENDENCE. REDUCED_QUORUM catches workers that died; it does not
        # catch workers that were never independent. Two workers sharing a
        # binary and a host share every failure mode, so their agreement is
        # nearly free -- dispatched=3, returned=3, and the failure-domain count
        # is 2. Capture arithmetic (Q1) runs on domains, not seats. Same shape
        # as k8s podtopologyspread: topologyKey names what you claim
        # independence over, maxSkew bounds concentration within it.
        agree_envs = [e for e, kk in zip(envs, ks) if kk == k and e is not None]
        # per-fault-class counts. A scalar would let the strongest axis speak
        # for the weakest.
        per_class = {}
        for ax in DOMAIN_AXES:
            per_class[ax] = len({OBSERVED.get(e.get('worker'), {}).get(ax)
                                 for e in agree_envs})
        # The binding constraint is the WEAKEST axis, not the count of seats.
        domains = min(per_class.values()) if per_class else 0
        for e in agree_envs:
            e['_per_class'] = per_class
        if domains < MIN_DOMAINS:
            # DEV only: one human may walk the agreement path. This is NOT
            # operator=2. The verdict must never be UNANIMOUS/MAJORITY or it
            # lands in `accepted`. Unset / anything but "1" stays refuse.
            if os.environ.get('KF_DEV_SINGLE_OPERATOR') == '1':
                return 'DEV_SINGLE_OPERATOR', k, n, dispatched, returned, domains
            return 'INSUFFICIENT_DOMAINS', k, n, dispatched, returned, domains
        return ('UNANIMOUS' if n == dispatched else 'MAJORITY'), \
            k, n, dispatched, returned, domains
    return 'NO_QUORUM', None, n, dispatched, returned, 0


def dissenters(envs):
    """WHO disagreed -- the defendant the verdict does not name (M1.13).

    NOT added to `adjudicate`'s return, deliberately. Its arity is asserted by
    `test_adjudicate.py` ("arity uniform at 6") and both production callers
    unpack a fixed six names (`v, k, n, disp, ret, dom = adjudicate(envs)`),
    so appending a seventh field is the exact shape of the 5-vs-6 defect
    recorded at the NO_RESULTS branch above -- which took the coordinator down
    with a ValueError while the suite stayed green, because the test exercised
    the function differently from the caller. The defendant therefore travels
    as a ROW FIELD, next to the envelopes it is derived from.

    ABSENCE IS NOT DISSENT, and this is the whole content of the function.
    A worker whose key is None did not ANSWER; it did not DISAGREE. S26's
    `cheat_attr.dissenters()` -- which the M1.13 sidecar calls directly --
    computes `kk != k` over the raw key list, so on a quorum of three honest
    answers plus one silent worker it returns that silent worker as the
    dissenter. MEASURED, not read: blanking `phone`'s result member on a
    live-key row makes it name `['phone']`. On a NO_RESULTS row it is saved by
    coincidence -- the no-majority sentinel and the did-not-answer sentinel are
    both None, so `None != None` is False -- which is one sentinel carrying two
    meanings in the branch that cannot tell them apart (H88). A field that a
    protocol pays or slashes on must never accuse a worker of lying for being
    offline; REDUCED_QUORUM already refuses a short quorum, and that is the
    correct handling of a worker that vanished.

    Named ONLY under a real majority (n >= 2). Under NO_QUORUM every live key
    is a plurality of one, so there is no majority to dissent FROM and naming
    one invents a defendant out of a tie; under NO_RESULTS there is nothing to
    dissent from at all. Both return [].
    """
    ks = [key(e) for e in envs]
    live = [k for k in ks if k is not None]
    if not live:
        return []
    k, n = Counter(live).most_common(1)[0]
    if n < 2:
        return []
    return [e.get('worker') for e, kk in zip(envs, ks)
            if kk is not None and kk != k]

def stage_device(android_bin):
    subprocess.run(['adb', 'shell', f'mkdir -p {DEVDIR}/corpus'], check=True)
    subprocess.run(['adb', 'push', android_bin, DEVDIR + '/'],
                   check=True, capture_output=True)
    subprocess.run(['adb', 'shell',
                    f'chmod +x {DEVDIR}/{os.path.basename(android_bin)}'],
                   check=True)
    # NOTE: the corpus is deliberately NOT pushed. M1.5 means the device
    # fetches each shard by CID on a cache miss and never sees the rest.

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=os.path.join(
        HERE, '..', 'S57_hyperon_corpus', 'corpus'))
    ap.add_argument('--fuel', type=int, default=2000000)
    ap.add_argument('--limit', type=int, default=0, help='0 = whole corpus')
    ap.add_argument('--work', default=os.path.join(HERE, 'run'))
    ap.add_argument('--no-device', action='store_true')
    ap.add_argument('--store', default=os.path.join(HERE, 'run', 'store'))
    ap.add_argument('--cap-mb', type=int, default=64)
    ap.add_argument('--keep-device-cache', action='store_true')
    ap.add_argument('--min-domains', type=int, default=3,
                    help='independent failure domains required among AGREEING '
                         'workers. Two workers sharing a binary and a host are '
                         'one domain, and their agreement is nearly free.')
    ap.add_argument('--alpha', action='store_true',
                    help='alpha-canonicalise results before comparing. Fixes '
                         'mechanism 1 (which variable represents an aliased '
                         'class) but changes the notion of equality -- opt-in '
                         'per job class, see harness/canon.py')
    ap.add_argument('--chunk', type=int, default=16,
                    help='jobs per work session; preflight runs once per session '
                         '(M1.3: batched preflight is 0.51x a job, so per-job is '
                         'not viable -- amortise it)')
    ap.add_argument('--battery-floor', type=int, default=90,
                    help='minimum battery percentage required for device preflight')
    ap.add_argument('--temp-max', type=float, default=40.0,
                    help='maximum device temperature (C) allowed for preflight')
    a = ap.parse_args()
    global ALPHA, MIN_DOMAINS
    ALPHA = a.alpha
    MIN_DOMAINS = a.min_domains

    progs = sorted(f for f in os.listdir(a.corpus) if f.endswith('.metta'))
    if a.limit: progs = progs[:a.limit]

    # MISSION_LOOP 10: device work is gated, and the gate result is recorded
    gate = None
    if not a.no_device:
        g = subprocess.run([os.path.join(HERE, '..', 'quiet.sh'), '--device'],
                           capture_output=True, text=True)
        gate = g.stdout.strip() or g.stderr.strip()
        if g.returncode != 0:
            print('device gate REFUSED:', gate); sys.exit(2)
        print('gate:', gate)
        stage_device(os.path.join(BIN, 'fuelrun.android'))

    # host-x86 is an x86-64 build of the same source, run under Rosetta. It is a
    # distinct `binary` and `isa` domain and the SAME `host` and `os` domain --
    # which is exactly why the count is per-axis. It restores the cross-ISA
    # property S57's headline had and this quorum had lost.
    # host-min is built from a DIFFERENT manifest (pkg_mgmt only, no das), so it
    # is a second `manifest` domain. That axis was binding at 1; the cost is one
    # program in 65, now banned at admission as feature-gated.
    # Each worker exists to raise a DIFFERENT axis, not to add a seat:
    #   host-a    das build, arm64      -- baseline
    #   host-min  pkg_mgmt-only build   -- second `manifest` domain
    #   host-x86  das build, x86_64     -- second `isa` domain
    #   phone     android               -- second `host` and `os` domain
    # Replacing rather than adding cost `isa` when `host-min` went in, which is
    # what the per-axis vector is for: it made the regression visible.
    workers = [
        ('host-a', os.path.join(BIN, 'fuelrun.host'), 'local'),
        ('host-min', os.path.join(BIN, 'fuelrun.host.min'), 'local'),
        ('host-x86', os.path.join(BIN, 'fuelrun.host.x86_64'), 'local'),
    ]
    if not a.no_device:
        # The REAL app as a quorum member is written (`worker_app.py`) and does
        # NOT work -- see APP_WORKER_BLOCKED.md. Reverted to the adb-driven
        # verifier so the pipeline stays functional; this understates the
        # `binary` and `manifest` axes and that is recorded rather than hidden.
        workers.append(('phone', os.path.join(BIN, 'fuelrun.android'), 'adb'))
    else:
        workers.append(('host-c', os.path.join(BIN, 'fuelrun.host'), 'local'))

    # Fill the coordinator-observed domain table BEFORE any worker runs, so
    # nothing a worker says can influence it.
    global OBSERVED
    OBSERVED = {wid: observed_domains(wid, binary, via)
                for wid, binary, via in workers}
    print('observed domains (coordinator-side, not worker-declared):')
    for wid, d in OBSERVED.items():
        print(f'  {wid:8} ' + '  '.join(f'{k}={v}' for k, v in d.items()))

    shutil.rmtree(a.work, ignore_errors=True)
    if not a.no_device and not a.keep_device_cache:
        subprocess.run(['adb', 'shell', f'rm -rf {DEVDIR}/shards'],
                       capture_output=True)   # cold cache unless asked otherwise

    # M1.5: ingest the corpus into the content-addressed store first. The job
    # carries a CID; nothing downstream ever names a path.
    store = ShardStore(a.store, cap_bytes=a.cap_mb << 20)
    # ADMISSION (S59 ban surface). M1.8b: quorum-of-3 launders a
    # nondeterministic job 21.5% of the time, so replication cannot be the
    # control -- this is where it has to be stopped.
    cids, refused_admission = [], []
    kept = []
    for p in progs:
        data = open(os.path.join(a.corpus, p), 'rb').read()
        ok, why = bansurface.admit(data)
        if not ok:
            refused_admission.append((p, [k for k, _ in why]))
            continue
        kept.append(p)
        cids.append(store.put(data))
    if refused_admission:
        print(f'admission: REFUSED {len(refused_admission)} program(s) on the '
              f'nondeterminism ban surface')
        for p, k in refused_admission:
            print(f'  - {p}  ({", ".join(k)})')
    progs = kept
    uniq = len(set(cids))
    print(f'store: {len(progs)} programs -> {uniq} distinct CIDs, '
          f'{store.total_bytes()/1024:.1f} KiB, cap {a.cap_mb} MiB')

    procs = []
    for wid, binary, via in workers:
        inbox  = os.path.join(a.work, wid, 'in')
        outbox = os.path.join(a.work, wid, 'out')
        os.makedirs(inbox); os.makedirs(outbox)
        if via == 'app':
            procs.append(subprocess.Popen(
                [sys.executable, os.path.join(HERE, 'worker_app.py'),
                 '--id', wid, '--inbox', inbox, '--outbox', outbox,
                 '--store', a.store, '--apk', binary],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        else:
            procs.append(subprocess.Popen(
                [sys.executable, os.path.join(HERE, 'worker.py'),
                 '--id', wid, '--inbox', inbox, '--outbox', outbox,
                 '--bin', binary, '--via', via, '--devdir', DEVDIR,
                 '--store', a.store]))

    # M1.3: dispatch in work sessions. Preflight gates each session, not each
    # job -- 35.1 ms batched against a 68.8 ms job means per-job preflight would
    # cost 51%. A refusal stops dispatch; jobs already sent still drain.
    pol = preflight.Policy(battery_floor_pct=a.battery_floor, temp_max_c=a.temp_max)
    dispatch_at = {}
    sessions, dispatched, refusals = 0, 0, []
    for start in range(0, len(progs), a.chunk):
        if not a.no_device:
            sig = preflight.probe()
            ok, why = preflight.decide(sig, pol)
            sessions += 1
            if not ok:
                delay = preflight.Backoff(pol).on_refusal()
                refusals.append({'after_jobs': dispatched, 'reason': why,
                                 'backoff_s': delay})
                print(f'  preflight REFUSED after {dispatched} jobs: {why} '
                      f'(would back off {delay}s)')
                break
        for i in range(start, min(start + a.chunk, len(progs))):
            jid = f'j{i:04d}'
            for wid, _, via in workers:
                job = {'job_id': jid, 'shard_cid': cids[i], 'fuel': a.fuel,
                       'name': progs[i]}
                d = os.path.join(a.work, wid, 'in')
                tmp = os.path.join(d, jid + '.tmp')
                with open(tmp, 'w') as f: json.dump(job, f)
                os.rename(tmp, os.path.join(d, jid + '.job'))
            dispatch_at[jid] = time.time()
            dispatched += 1
    progs = progs[:dispatched]
    print(f'dispatched {dispatched} jobs in {sessions} work session(s), '
          f'{len(refusals)} refusal(s)')

    # collect
    rows, t0 = [], time.time()
    for i, p in enumerate(progs):
        jid = f'j{i:04d}'
        envs = []
        for wid, _, _ in workers:
            fp = os.path.join(a.work, wid, 'out', jid + '.env')
            while not os.path.exists(fp) and time.time() - t0 < 1800:
                time.sleep(0.02)
            e = json.load(open(fp)) if os.path.exists(fp) else None
            if e is not None:
                # A22: `wall_ms` and hyperjob's `Timings` are worker-supplied and
                # sit outside the agreement key, so nothing compares them -- and
                # a device profits by understating cost once scheduling reads
                # them. The coordinator brackets the envelope itself: it cannot
                # see execution time, but it can see when the answer arrived,
                # which is what scheduling actually needs.
                e['observed_ms'] = round(
                    (os.path.getmtime(fp) - dispatch_at[jid]) * 1000, 1)
            envs.append(e)
        for e in envs:
            if not e:
                continue
            decl, obs = e.get('domains') or {}, OBSERVED.get(e.get('worker'), {})
            diff = {ax: (decl.get(ax), obs.get(ax)) for ax in DOMAIN_AXES
                    if ax in decl and decl.get(ax) != obs.get(ax)}
            if diff:
                # not fatal by itself -- honest workers differ on `operator`,
                # which we pin to UNATTESTED. But a worker claiming a host or
                # binary we did not observe is trying to buy a domain.
                e['domain_mismatch'] = {k2: {'declared': d0, 'observed': o0}
                                        for k2, (d0, o0) in diff.items()}
        v, k, n, disp, ret, dom = adjudicate(envs)
        rows.append((p, v, n, k, envs, disp, ret, dom))

    for pr in procs: pr.terminate()

    # report
    tally = Counter(r[1] for r in rows)
    print(f'\n{"program":56} {"verdict":14} {"agree":5} fuel')
    for p, v, n, k, envs, disp, ret, dom in rows:
        flag = '' if v == 'UNANIMOUS' else '   <<<'
        # M1.13: a verdict with no defendant cannot be paid or slashed on.
        accused = dissenters(envs)
        if accused:
            flag += ' dissent=' + ','.join(str(w) for w in accused)
        fuel = (k[1] if k and k[1] is not None else '-')
        # agreed/returned(dispatched) -- a shrunken quorum must be visible
        shape = f'{n}/{ret}' + (f'({disp})' if ret != disp else '')
        print(f'{p[:44]:44} {v:20} {shape:>7} {dom}dom {str(fuel):>9}{flag}')
    print('\n' + '  '.join(f'{kk}={vv}' for kk, vv in sorted(tally.items())))
    accepted = tally['UNANIMOUS'] + tally['MAJORITY']
    dev_ok = tally['DEV_SINGLE_OPERATOR']
    insuf = tally['INSUFFICIENT_DOMAINS']
    if dev_ok:
        print(f'\n!! DEV_SINGLE_OPERATOR on {dev_ok} job(s): '
              f'KF_DEV_SINGLE_OPERATOR=1. Agreement exercised; NOT accepted. '
              f'operator stays UNATTESTED.')
    if insuf:
        pc = next((e['_per_class'] for _,_,_,_,es,_,_,_ in rows
                   for e in es if e and e.get('_per_class')), {})
        print(f'\n!! INSUFFICIENT_DOMAINS on {insuf} job(s): the WEAKEST axis has '
              f'fewer than {MIN_DOMAINS} domains.')
        for ax in DOMAIN_AXES:
            n_ax = pc.get(ax, 0)
            mark = '  <-- binding' if n_ax == min(pc.values(), default=0) else ''
            print(f'     {ax:9} {n_ax} domain(s){mark}')
        print('   Fault classes NO axis separates (quorum cannot help at any size):')
        for name, why in UNSEPARABLE.items():
            print(f'     - {name}: {why}')
    if not a.no_device:
        held = observed_residency(DEVDIR)
        pushed_claim = sum(1 for _,_,_,_,es,_,_,_ in rows for e in es
                           if e and e.get('worker') == 'phone'
                           and e.get('bytes_pushed', 0) > 0)
        need = set(cids)
        print(f'\nresidency (observed on device, not worker-reported): '
              f'{len(need & held)}/{len(need)} of this run\'s shards held, '
              f'{len(held)} total on device; {pushed_claim} fetched this run')
    ow = [e['observed_ms'] for _,_,_,_,es,_,_,_ in rows for e in es
          if e and e.get('worker') == 'phone' and 'observed_ms' in e]
    wc = [float(e['wall_ms']) for _,_,_,_,es,_,_,_ in rows for e in es
          if e and e.get('worker') == 'phone' and 'wall_ms' in e]
    if ow and wc:
        import statistics as _st
        print(f'timing  phone: worker-declared median {_st.median(wc):.1f} ms | '
              f'coordinator-observed median {_st.median(ow):.1f} ms '
              f'(observed = queue + adb + poll granularity; an UPPER BOUND, not a check)')

    mism = [(e['worker'], e['domain_mismatch'])
            for _,_,_,_,es,_,_,_ in rows for e in es
            if e and e.get('domain_mismatch')]
    if mism:
        seen_ax = sorted({ax for _, d in mism for ax in d})
        print(f'\n!! DOMAIN MISMATCH on {len(mism)} envelope(s), axes {seen_ax}: '
              f'a worker declared a domain the coordinator did not observe. '
              f'Only the observed value was counted.')
        w, d = mism[0]
        print(f'     e.g. {w}: {d}')
    short = tally['REDUCED_QUORUM']
    if short:
        print(f'\n!! REDUCED_QUORUM on {short} job(s): fewer workers returned '
              f'than were dispatched. Never payable -- a short quorum is an '
              f'availability failure, and a craftable one.')
    failed = tally['AGREED_FAILURE']
    print(f'accepted {accepted}/{len(rows)}'
          + (f'   |  AGREED_FAILURE {failed} (deterministic, but no result -- '
             f'NOT accepted)' if failed else ''))

    pushed = sum(e.get('bytes_pushed', 0) for _, _, _, _, es, _, _, _ in rows
                 for e in es if e)
    if ALPHA:
        refused = sum(1 for _, _, _, _, es, _, _, _ in rows for e in es
                      if e and e.get('alpha_refused'))
        nonground = sum(1 for _, _, _, _, es, _, _, _ in rows for e in es
                        if e and e.get('results_text') is not None
                        and not is_ground(e['results_text']))
        print(f'alpha: {nonground} envelope(s) non-ground -> {refused} fell back '
              f'to canon (alpha is lossless only on ground results)')
    print(f'device cache: {pushed/1024:.1f} KiB crossed the wire '
          f'({uniq} distinct shards)')

    json.dump({'gate': gate, 'fuel': a.fuel, 'bytes_pushed': pushed,
               'normalisation': 'canon_alpha' if ALPHA else 'canon',
               'sessions': sessions, 'chunk': a.chunk, 'refusals': refusals,
               'admission_refused': [{'program': p, 'reasons': k}
                                     for p, k in refused_admission],
               'workers': [w[0] for w in workers],
               'tally': dict(tally),
               'rows': [{'program': p, 'verdict': v, 'agree': n,
                         'key': k, 'envelopes': e,
                         'dispatched': d, 'returned': r, 'domains': dm,
                         'defendants': dissenters(e),
                         'domains_per_class': next(
                             (x.get('_per_class') for x in e if x), None)}
                        for p, v, n, k, e, d, r, dm in rows]},
              open(os.path.join(HERE, 'result.json'), 'w'), indent=1)
    print('-> result.json')

main()
