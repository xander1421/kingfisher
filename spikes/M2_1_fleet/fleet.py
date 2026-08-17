#!/usr/bin/env python3
"""M2.1 — a fleet of real worker processes with per-device shard caches.

S61, S69 and S70 all modelled locality: fetches per job, coverage, imbalance.
None of them executed anything. This runs N real worker processes, each with
its OWN content-addressed store, so residency genuinely differs per worker and
a "fetch" copies real bytes.

The question S61 asked and could not measure: how much does locality-aware
dispatch actually save, and what does it cost in load imbalance?

Not simulated: MeTTa evaluation, the shard store, the CIDs, the byte counts.
Simulated: the devices are host processes. That is stated, not hidden -- see
DETECTION_FLOORS on why host processes are one failure domain.
"""
import argparse, json, os, random, shutil, subprocess, sys, time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
MAXSKEW = 2   # jobs above the fleet mean before a device becomes ineligible
sys.path.insert(0, os.path.join(HERE, '..', 'M1_5_shardstore'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from shardstore import ShardStore, cid_of
import bansurface

BIN = os.path.join(HERE, '..', 'S30_speed_duel', 'bin', 'known', 'fuelrun.host')


class Device:
    """One worker process with its own cache. `store` IS the cache: a shard is
    resident iff it is in this device's store, which the coordinator can check
    directly because the coordinator owns the directory (A22: observed)."""

    def __init__(self, idx, root, cap_bytes):
        self.idx = idx
        self.wid = f'dev{idx:02d}'
        self.dir = os.path.join(root, self.wid)
        os.makedirs(os.path.join(self.dir, 'in'), exist_ok=True)
        os.makedirs(os.path.join(self.dir, 'out'), exist_ok=True)
        self.store = ShardStore(os.path.join(self.dir, 'store'), cap_bytes)
        self.jobs = 0
        self.bytes_in = 0
        self.proc = None

    def holds(self, cid):
        return self.store.has(cid)

    def seed(self, cid, data):
        """A fetch. Returns bytes moved -- 0 if already resident."""
        if self.store.has(cid):
            return 0
        self.store.put(data)
        self.bytes_in += len(data)
        return len(data)

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, '..', 'M1_8_quorum3', 'worker.py'),
             '--id', self.wid,
             '--inbox', os.path.join(self.dir, 'in'),
             '--outbox', os.path.join(self.dir, 'out'),
             '--bin', BIN, '--via', 'local',
             '--store', os.path.join(self.dir, 'store')],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def choose(devices, cid, k, policy, rng):
    """Which k devices run this job."""
    if policy == 'random':
        return rng.sample(devices, k)
    resident = [d for d in devices if d.holds(cid)]
    rest = [d for d in devices if not d.holds(cid)]
    rng.shuffle(resident); rng.shuffle(rest)
    if policy == 'locality_pure':
        # residency ONLY. This is the policy S61 actually modelled, and the one
        # its 102x imbalance warning is about: whoever was seeded first keeps
        # winning, because winning does not make anyone else resident.
        return (resident + rest)[:k]
    if policy == 'locality_lb':
        # residency, then least-loaded WITHIN each group. Two ingredients, and
        # the first version of this experiment credited the second one's effect
        # to the first.
        resident.sort(key=lambda d: d.jobs)
        rest.sort(key=lambda d: d.jobs)
        return (resident + rest)[:k]
    if policy == 'locality_capped':
        # k8s podtopologyspread's maxSkew, applied to load rather than topology:
        # prefer residency, but a device already more than `skew` jobs above the
        # fleet mean is not eligible however well it matches. The tiebreak alone
        # only halves the imbalance under skewed demand; a hard cap bounds it.
        mean = sum(d.jobs for d in devices) / max(len(devices), 1)
        cap = mean + MAXSKEW
        elig_r = [d for d in resident if d.jobs <= cap]
        elig_o = [d for d in rest if d.jobs <= cap]
        elig_r.sort(key=lambda d: d.jobs); elig_o.sort(key=lambda d: d.jobs)
        picked = (elig_r + elig_o)[:k]
        if len(picked) < k:      # cap must never shrink the quorum (M1.8c)
            spare = [d for d in resident + rest if d not in picked]
            spare.sort(key=lambda d: d.jobs)
            picked += spare[:k - len(picked)]
        return picked
    if policy == 'loadbalance':
        # least-loaded only, residency ignored -- isolates how much of any
        # imbalance improvement is the tiebreak rather than locality.
        all_d = sorted(devices, key=lambda d: d.jobs)
        return all_d[:k]
    raise ValueError(policy)


def run(policy, progs, corpus, args, rng_seed=None):
    rng_seed = args.seed if rng_seed is None else rng_seed
    rng = random.Random(rng_seed)
    root = os.path.join(HERE, 'run', policy)
    shutil.rmtree(root, ignore_errors=True)
    devices = [Device(i, root, args.cap_mb << 20) for i in range(args.fleet)]

    master = {}
    for p in progs:
        data = open(os.path.join(corpus, p), 'rb').read()
        master[cid_of(data)] = data
    cids = list(master)

    # pre-seed: each device starts holding a random `prefill` fraction, so the
    # first pass is not trivially all-miss. S61 warmed into steady state and
    # measured a policy that cannot reach it (its own finding); prefill avoids
    # inheriting that.
    for d in devices:
        for c in rng.sample(cids, int(len(cids) * args.prefill)):
            d.seed(c, master[c])
    seeded_bytes = sum(d.bytes_in for d in devices)
    for d in devices:
        d.bytes_in = 0
        d.start()
    time.sleep(0.3)

    # DEMAND SHAPE. The first version dispatched each program exactly once --
    # uniform demand. S61's 102x imbalance is a SKEWED-demand result: a few
    # shards are hot and whoever holds them gets every job. Measuring locality
    # under uniform demand and concluding there is no tension would be
    # answering a different question than the one S61 asked.
    if args.zipf > 0:
        w = [1.0 / ((i + 1) ** args.zipf) for i in range(len(progs))]
        tot = sum(w)
        order = list(range(len(progs)))
        rng.shuffle(order)                      # popularity is not filename order
        jobs = rng.choices([progs[o] for o in order],
                           weights=w, k=args.njobs or len(progs))
    else:
        jobs = list(progs)

    t0 = time.time()
    dispatched = []
    for i, p in enumerate(jobs):
        cid = cid_of(master[cid_of(open(os.path.join(corpus, p), 'rb').read())])
        jid = f'j{i:04d}'
        chosen = choose(devices, cid, args.quorum, policy, rng)
        for d in chosen:
            d.seed(cid, master[cid])          # fetch on miss, counted
            d.jobs += 1
            job = {'job_id': jid, 'shard_cid': cid, 'fuel': args.fuel, 'name': p}
            tmp = os.path.join(d.dir, 'in', jid + '.tmp')
            with open(tmp, 'w') as f:
                json.dump(job, f)
            os.rename(tmp, os.path.join(d.dir, 'in', jid + '.job'))
        dispatched.append((jid, cid, [d.wid for d in chosen]))

    # collect
    agree = Counter()
    for jid, cid, wids in dispatched:
        keys = []
        for wid in wids:
            d = next(x for x in devices if x.wid == wid)
            fp = os.path.join(d.dir, 'out', jid + '.env')
            while not os.path.exists(fp) and time.time() - t0 < 900:
                time.sleep(0.01)
            if os.path.exists(fp):
                e = json.load(open(fp))
                keys.append((e.get('status'), e.get('fuel_used'),
                             e.get('sorted_hash')))
        c = Counter(keys).most_common(1)
        agree['unanimous' if c and c[0][1] == len(wids) and len(keys) == len(wids)
              else 'other'] += 1
    for d in devices:
        d.proc.terminate()

    loads = [d.jobs for d in devices]
    return {
        'policy': policy,
        'fleet': args.fleet,
        'fetch_bytes': sum(d.bytes_in for d in devices),
        'prefill_bytes': seeded_bytes,
        'fetches': sum(1 for d in devices for _ in range(0)) or None,
        'load_max': max(loads), 'load_min': min(loads),
        'imbalance': (max(loads) / max(1, min(loads))),
        'unanimous': agree['unanimous'], 'other': agree['other'],
        'wall_s': round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=os.path.join(
        HERE, '..', 'S57_hyperon_corpus', 'corpus'))
    ap.add_argument('--fleet', type=int, default=12)
    ap.add_argument('--quorum', type=int, default=3)
    ap.add_argument('--prefill', type=float, default=0.25)
    ap.add_argument('--cap-mb', type=int, default=64)
    ap.add_argument('--fuel', type=int, default=2000000)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--seed', type=lambda x: int(x,0), default=0xC0FFEE)
    ap.add_argument('--zipf', type=float, default=0.0,
                    help='demand skew exponent; 0 = uniform, 1.0 = classic Zipf')
    ap.add_argument('--njobs', type=int, default=0)
    a = ap.parse_args()

    progs = sorted(f for f in os.listdir(a.corpus) if f.endswith('.metta'))
    progs = [p for p in progs
             if bansurface.admit(open(os.path.join(a.corpus, p), 'rb').read())[0]]
    if a.limit:
        progs = progs[:a.limit]
    print(f'fleet {a.fleet} devices, quorum {a.quorum}, {len(progs)} admitted '
          f'programs, prefill {a.prefill:.0%}')

    rows = [run(pol, progs, a.corpus, a)
            for pol in ('random', 'loadbalance', 'locality_pure', 'locality_lb')]
    print(f"\n{'policy':10} {'fetch KiB':>10} {'load max/min':>13} {'imbal':>7} "
          f"{'unanimous':>10} {'wall s':>7}")
    for r in rows:
        print(f"{r['policy']:10} {r['fetch_bytes']/1024:10.1f} "
              f"{str(r['load_max'])+'/'+str(r['load_min']):>13} "
              f"{r['imbalance']:6.1f}x {r['unanimous']:>10} {r['wall_s']:7.1f}")
    by = {r['policy']: r for r in rows}
    b = by['random']
    print()
    for name in ('loadbalance', 'locality_pure', 'locality_lb'):
        r = by[name]
        db = 100 * (b['fetch_bytes'] - r['fetch_bytes']) / max(b['fetch_bytes'], 1)
        print(f"  {name:14} transfer {db:+6.1f}% vs random   "
              f"imbalance {r['imbalance']:.1f}x (random {b['imbalance']:.1f}x)")
    json.dump(rows, open(os.path.join(HERE, 'result.json'), 'w'), indent=1)


main()
