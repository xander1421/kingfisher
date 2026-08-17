#!/usr/bin/env python3
"""M1.8 worker — one process, one device. Polls a filesystem inbox, runs
fuelrun on the job, writes an envelope to the outbox.

Filesystem transport is prime-rl's testing trick (PORT_PLAN M1.7) and it is
also the honest shape here: the phone always dials, and adb is a pull.
A fresh fuelrun process per job is required, not an optimisation --
PORT_PLAN M1.3 gives two independent derivations (S60/A8 atomspace pollution,
and process-global NEXT_VARIABLE_ID).
"""
import argparse, hashlib, json, os, platform, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'M1_5_shardstore'))
from shardstore import ShardStore, cid_of, parse_cid

def run_local(binary, prog, fuel):
    return subprocess.run([binary, prog, str(fuel)],
                          capture_output=True, text=True, timeout=300)

def run_adb(binary, prog, fuel, devdir):
    cmd = f'cd {devdir} && ./{os.path.basename(binary)} {prog} {fuel}'
    return subprocess.run(['adb', 'shell', cmd],
                          capture_output=True, text=True, timeout=300)

def device_fetch(store, cid, devdir):
    """M1.5 on the device side: the phone runs from a CID-named cache and the
    blob crosses the wire only on a miss. Returns (device_path, bytes_pushed)."""
    dpath = f'{devdir}/shards/{cid}'
    # Verify the cached blob ON THE DEVICE before trusting it. Host-side `get`
    # re-hashes; the device previously trusted its own cache file, so a corrupt
    # or substituted shard was caught only by quorum -- i.e. by three devices
    # disagreeing, which is the expensive way to find a bit flip.
    # The CID *is* the hash, so verification needs no extra metadata.
    probe = subprocess.run(
        ['adb', 'shell', f'test -f {dpath} && sha256sum {dpath} || true'],
        capture_output=True, text=True).stdout.split()
    if probe:
        want = parse_cid(cid)[2:].hex()      # strip the 0x12 0x20 multihash prefix
        if probe[0] == want:
            return dpath, 0                  # verified hit
        # present but wrong: evict rather than run it
        subprocess.run(['adb', 'shell', f'rm -f {dpath}'], capture_output=True)
    data = store.get(cid)
    if data is None:
        raise FileNotFoundError(f'shard {cid} not in store')
    local = os.path.join(store.root, 'push.tmp')
    with open(local, 'wb') as f:
        f.write(data)
    subprocess.run(['adb', 'shell', f'mkdir -p {devdir}/shards'], check=True)
    subprocess.run(['adb', 'push', local, dpath], check=True, capture_output=True)
    return dpath, len(data)

def parse(out):
    """fuelrun prints 'key value' lines. Missing keys must be visible, not
    defaulted -- S57 v1 hardcoded status='ok' and recorded a FUEL_EXHAUSTED
    program as OK."""
    kv = {}
    for line in out.splitlines():
        p = line.split(None, 1)
        if len(p) == 2:
            kv[p[0]] = p[1].strip()
    need = ('status', 'fuel_used', 'sorted_hash', 'raw_hash', 'n_results')
    missing = [k for k in need if k not in kv]
    if missing:
        return None, f'NO_PARSE missing={",".join(missing)}'
    return kv, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', required=True)
    ap.add_argument('--inbox', required=True)
    ap.add_argument('--outbox', required=True)
    ap.add_argument('--bin', required=True)
    ap.add_argument('--via', choices=['local', 'adb'], default='local')
    ap.add_argument('--devdir', default='/data/local/tmp/m18')
    ap.add_argument('--store', required=True)
    a = ap.parse_args()
    store = ShardStore(a.store)
    os.makedirs(a.outbox, exist_ok=True)

    # FAILURE DOMAINS, per fault class. A single scalar count conflates classes
    # that have different domain structures: two workers can be independent for
    # a compiler bug and identical for a libm bug. So the worker declares a
    # VECTOR and the adjudicator counts each axis separately.
    #
    #   binary    a bad build, a mis-applied patch, a codegen bug
    #   host      kernel, clock source, page tables, CPU errata, thermal state
    #   os        libc/libm -- the S59 divergence class
    #   isa       instruction semantics, float behaviour
    #   operator  collusion and Sybil -- the only axis Q1's capture model is about
    #
    # Each is what it says and nothing more. `binary` differing does NOT imply
    # `host` differs, and counting a single number would let the strongest axis
    # speak for the weakest -- which is the whole failure this replaces.
    bin_sha = hashlib.sha256(open(a.bin, 'rb').read()).hexdigest()[:12]
    if a.via == 'adb':
        serial = subprocess.run(['adb', 'get-serialno'], capture_output=True,
                                text=True).stdout.strip() or 'device'
        host_id = f'adb:{serial}'
        os_id = subprocess.run(
            ['adb', 'shell', 'getprop ro.build.version.release'],
            capture_output=True, text=True).stdout.strip() or '?'
        os_id = f'android-{os_id}'
        isa = subprocess.run(['adb', 'shell', 'getprop ro.product.cpu.abi'],
                             capture_output=True, text=True).stdout.strip() or '?'
    else:
        host_id = f'host:{platform.node()}'
        os_id = f'{platform.system().lower()}-{platform.release()}'
        isa = platform.machine()
    # Normalise the ISA string before using it as a domain key. macOS reports
    # `arm64`, Android reports `arm64-v8a`; they are the SAME ISA and counting
    # them as two domains is the key flattering itself -- the exact defect this
    # module's own comment warns about, committed in this module.
    def norm_isa(v):
        v = v.lower()
        if v.startswith(('arm64', 'aarch64')):
            return 'aarch64'
        if v in ('x86_64', 'amd64'):
            return 'x86_64'
        return v
    isa = norm_isa(isa)

    domains = {
        'binary': f'bin:{bin_sha}',
        'host': host_id,
        'os': os_id,
        'isa': isa,
        # every worker here is run by us. Stated, not omitted: on the axis Q1's
        # 72% capture figure is actually about, this quorum has ONE domain.
        'operator': os.environ.get('KF_OPERATOR', 'operator:self'),
    }
    domain = f'{host_id}|bin:{bin_sha}'   # legacy scalar, kept for the display
    idle = 0
    while idle < 60:
        jobs = sorted(f for f in os.listdir(a.inbox) if f.endswith('.job'))
        if not jobs:
            time.sleep(0.05); idle += 1; continue
        idle = 0
        for jf in jobs:
            jp = os.path.join(a.inbox, jf)
            try:
                job = json.load(open(jp))
            except Exception:
                continue
            os.remove(jp)
            if job.get('op') == 'stop':
                return
            t0 = time.time()
            pushed = 0
            try:
                # M1.5: the job names a CID, never a path. Resolve it locally.
                cid = job['shard_cid']
                if a.via == 'adb':
                    prog, pushed = device_fetch(store, cid, a.devdir)
                else:
                    data = store.get(cid)
                    if data is None:
                        raise FileNotFoundError(f'shard {cid} not in store')
                    prog = os.path.join(store.root, f'run-{a.id}.metta')
                    with open(prog, 'wb') as f:
                        f.write(data)
                r = (run_adb(a.bin, prog, job['fuel'], a.devdir)
                     if a.via == 'adb' else
                     run_local(a.bin, prog, job['fuel']))
                kv, err = parse(r.stdout)
                if r.returncode != 0 and kv is None:
                    env = {'status': 'CRASH', 'detail': r.stderr[-300:]}
                elif err:
                    env = {'status': err}
                else:
                    env = {k: kv[k] for k in
                           ('status','fuel_used','raw_hash','sorted_hash',
                            'n_results','arch','os') if k in kv}
                    # capture the results block so the coordinator can
                    # canonicalise variable ids before comparing (M1.1c)
                    if '--- results ---' in r.stdout:
                        env['results_text'] = r.stdout.split(
                            '--- results ---', 1)[1].strip()
            except subprocess.TimeoutExpired:
                env = {'status': 'TIMEOUT'}
            except FileNotFoundError as e:
                env = {'status': 'SHARD_MISSING', 'detail': str(e)}
            env.update(domain=domain, domains=domains,
                       bin_sha256=bin_sha, host_id=host_id,
                       worker=a.id, job_id=job['job_id'],
                       shard_cid=job['shard_cid'], fuel_limit=job['fuel'],
                       bytes_pushed=pushed,
                       wall_ms=round((time.time()-t0)*1000, 1))
            tmp = os.path.join(a.outbox, job['job_id'] + '.tmp')
            with open(tmp, 'w') as f:
                json.dump(env, f)
            os.rename(tmp, os.path.join(a.outbox, job['job_id'] + '.env'))

main()
