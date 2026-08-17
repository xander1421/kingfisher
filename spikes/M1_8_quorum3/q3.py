#!/usr/bin/env python3
"""M1.8 -- quorum-3 pipeline end to end. Coordinator + 3 worker processes.

Adjudication is BOINC's majority rule (sample_bitwise_validator.cc:17-18):
a result is accepted when >=2 of 3 replicas agree BYTE FOR BYTE. What must
match is (status, fuel_used, sorted_hash) -- fuel_used is in the key because
S57 established that equal output with unequal fuel is a divergence, not an
agreement.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'M1_5_shardstore'))
from shardstore import ShardStore
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'harness'))
from canon import canon, canon_alpha_strict, is_ground, AlphaLossy
import bansurface
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'M1_3_worker'))
import preflight

HERE = os.path.dirname(os.path.abspath(__file__))
BIN  = os.path.join(HERE, '..', 'S30_speed_duel', 'bin')
DEVDIR = '/data/local/tmp/m18'

ALPHA = False   # set by --alpha; opt-in per job class, never the default
MIN_DOMAINS = 3  # independent failure domains required among AGREEING workers


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
        return 'NO_RESULTS', None, 0, dispatched, returned
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
        agreeing = {e.get('domain') for e, kk in zip(envs, ks)
                    if kk == k and e is not None}
        domains = len(agreeing)
        if domains < MIN_DOMAINS:
            return 'INSUFFICIENT_DOMAINS', k, n, dispatched, returned, domains
        return ('UNANIMOUS' if n == dispatched else 'MAJORITY'), \
            k, n, dispatched, returned, domains
    return 'NO_QUORUM', None, n, dispatched, returned, 0

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
        stage_device(os.path.join(BIN, 'fuelrun.v2.android'))

    workers = [
        ('host-a', os.path.join(BIN, 'fuelrun.v2.host'), 'local'),
        ('host-b', os.path.join(BIN, 'fuelrun.v2.host'), 'local'),
    ]
    if not a.no_device:
        workers.append(('phone', os.path.join(BIN, 'fuelrun.v2.android'), 'adb'))
    else:
        workers.append(('host-c', os.path.join(BIN, 'fuelrun.v2.host'), 'local'))

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
        procs.append(subprocess.Popen(
            [sys.executable, os.path.join(HERE, 'worker.py'),
             '--id', wid, '--inbox', inbox, '--outbox', outbox,
             '--bin', binary, '--via', via, '--devdir', DEVDIR,
             '--store', a.store]))

    # M1.3: dispatch in work sessions. Preflight gates each session, not each
    # job -- 35.1 ms batched against a 68.8 ms job means per-job preflight would
    # cost 51%. A refusal stops dispatch; jobs already sent still drain.
    pol = preflight.Policy()
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
            envs.append(json.load(open(fp)) if os.path.exists(fp) else None)
        v, k, n, disp, ret, dom = adjudicate(envs)
        rows.append((p, v, n, k, envs, disp, ret, dom))

    for pr in procs: pr.terminate()

    # report
    tally = Counter(r[1] for r in rows)
    print(f'\n{"program":56} {"verdict":14} {"agree":5} fuel')
    for p, v, n, k, envs, disp, ret, dom in rows:
        flag = '' if v == 'UNANIMOUS' else '   <<<'
        fuel = (k[1] if k and k[1] is not None else '-')
        # agreed/returned(dispatched) -- a shrunken quorum must be visible
        shape = f'{n}/{ret}' + (f'({disp})' if ret != disp else '')
        print(f'{p[:44]:44} {v:20} {shape:>7} {dom}dom {str(fuel):>9}{flag}')
    print('\n' + '  '.join(f'{kk}={vv}' for kk, vv in sorted(tally.items())))
    accepted = tally['UNANIMOUS'] + tally['MAJORITY']
    insuf = tally['INSUFFICIENT_DOMAINS']
    if insuf:
        doms = sorted({e['domain'] for _,_,_,_,es,_,_,_ in rows
                       for e in es if e and e.get('domain')})
        print(f'\n!! INSUFFICIENT_DOMAINS on {insuf} job(s): agreement came from '
              f'fewer than {MIN_DOMAINS} independent failure domains.')
        for d in doms:
            print(f'     domain: {d}')
        print('   Workers sharing a binary and a host share every failure mode; '
              'their agreement is nearly free.')
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
                         'dispatched': d, 'returned': r, 'domains': dm}
                        for p, v, n, k, e, d, r, dm in rows]},
              open(os.path.join(HERE, 'result.json'), 'w'), indent=1)
    print('-> result.json')

main()
