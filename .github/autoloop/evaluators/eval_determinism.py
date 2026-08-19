#!/usr/bin/env python3
"""Autoloop evaluator: the mission's keystone property, RECOMPUTED.

WHY THIS EXISTS. The loop optimised filtered_mrr, hits@10, witness bandwidth
and verifier RAM. Not one of those is the wedge. out/LEDGER.md: the determinism
chain is "the only claim group nothing has dented in four adversarial rounds,
and it is what the proposal should lead with". A ratchet that can trade it away
for MRR is optimising against the mission.

So determinism is a GATE, not a weighted term. A mutation that buys accuracy and
breaks byte-identical agreement is not a better candidate; it is a different and
worse product. `min_acceptable: 1.0` in config.json makes it a veto.

WHY IT CANNOT BE FORGED (H101). It reads no RESULT.md, no data file and no
provenance record. It RECOMPUTES the identity from scratch every call, against
an independent int32 reference computed in the same process. There is no
artifact a candidate mutation could edit to change the answer — the only way to
move this number is to actually break or fix the arithmetic.

  bipolar a,b in {-1,+1}^D  =>  dot(a,b) == D - 2*popcount(a XOR b)

That is S43/S44's exactness gate, which S34 then showed holds bit-identically
across three kernels and two machines. Here it is the cheap local half: if the
identity fails on this machine it cannot hold across two.
"""
import json, os, subprocess, sys

# ---------------------------------------------------------------------------
# H111 (ATTACKER-1, 2026-08-18), handed over by this file's author with four of
# its own defects named. What the attack found, and what it did NOT:
#
# WHAT SURVIVED. The identity is real and this file computes it honestly. Two of
# three planted breaks turn it red (see `--selfcheck`); the third -- `T > 0` ->
# `T >= 0` -- is NOT a break at all on bipolar data and my labelling it one was
# my error, not this gate's miss.
#
# WHAT DID NOT. **THE VETO HAS NO CANDIDATE INPUT.** `config.json`
# `mutation_targets` names three repo files; this file opens NONE of them and
# imports NO repo module (measured with a `sys.addaudithook` over the gate's own
# process, so the input set is complete rather than sampled). Truncating,
# corrupting and deleting all three leaves `determinism_exact` at 1.0 and
# `score_digest` byte-identical. **A veto at `min_acceptable: 1.0` whose verdict
# is invariant across candidates cannot veto a candidate** -- A15, a control that
# cannot fire. It is a real ENVIRONMENT tripwire and a null CANDIDATE gate, and
# only the loop's owner can decide which the ratchet needs; not changed here,
# reported in `spikes/H111_veto_input/RESULT.md`.
#
# NOT FIXED HERE EITHER, and it is the larger one: **`.github/autoloop/` is
# UNTRACKED** -- 0 files known to git, and not ignored. The veto guarding the
# keystone claim exists in one working tree on one machine. Committing another
# lane's uncommitted work under my own Atom is the defect H66/H79 describe, so
# it is reported rather than done.
#
# FIXED HERE: the negative control (`--selfcheck`), and the SECOND dependency
# door below.
# ---------------------------------------------------------------------------
try:
    import numpy as np
except ImportError:
    # REFUSE, do not score. Returning 0.0 here — which this file did on its
    # first run — reports a measurement that was never taken, and exit 0 tells
    # the caller it succeeded. That is the empty-input floor: the check runs,
    # emits a number, and its input was absent. `certify` REFUSES; it does not
    # warn, and neither does this.
    print(json.dumps({"status": "REFUSED_NUMPY_MISSING",
                      "detail": "no metric emitted; install numpy or this gate "
                                "cannot run. A missing dependency is not a "
                                "failing score."}), file=sys.stderr)
    sys.exit(2)

# THE SECOND DEPENDENCY DOOR (H111 F4). The guard above covers numpy ABSENT.
# `np.bitwise_count` arrived in numpy 2.0, so numpy PRESENT BUT OLDER took no
# guarded path at all: it died with an AttributeError, emitted NO metric, and
# exited 1 -- **the same exit code as IDENTITY_BROKEN**, so an environment fault
# was indistinguishable from a real break of the mission's keystone property.
# That is the defect this file's author closed at the first door hours earlier;
# it survived at the second. Same refusal semantics: exit 2, no metric.
if not hasattr(np, 'bitwise_count'):
    print(json.dumps({"status": "REFUSED_NUMPY_TOO_OLD",
                      "detail": f"numpy {np.__version__} has no bitwise_count "
                                "(added in 2.0); no metric emitted. A dependency "
                                "too old is not a failing score."}), file=sys.stderr)
    sys.exit(2)

D, N, Q, SEED = 1024, 4000, 8, 0xC0FFEE


def check_cross_device_metta():
    """Runs threadrun with probe.metta on host and on connected Android device, verifying byte-identical fuel and canon hashes."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    host_bin = os.path.join(repo_root, "spikes", "S15_android_device", "fuelrun", "target", "release", "threadrun")
    probe_metta = os.path.join(repo_root, "spikes", "S28_inprocess_concurrency", "probe.metta")
    dev_bin = os.path.join(repo_root, "spikes", "S15_android_device", "fuelrun", "target", "aarch64-linux-android", "release", "threadrun")

    if not os.path.exists(host_bin) or not os.path.exists(probe_metta):
        return 0.0, "missing_host_bin_or_probe", {}

    p_host = subprocess.run([host_bin, "200000", "1", "1", probe_metta], capture_output=True, text=True)
    if p_host.returncode != 0:
        return 0.0, "host_threadrun_failed", {}

    host_lines = [l for l in p_host.stdout.strip().split("\n") if not l.startswith("#") and not l.startswith("repeat")]
    if not host_lines:
        return 0.0, "no_host_output", {}
    host_cols = host_lines[0].split("\t")
    host_fuel, host_raw, host_canon, host_alpha = host_cols[4], host_cols[5], host_cols[6], host_cols[7]

    # A PREFLIGHT MUST NOT DIE ON THE ABSENCE IT EXISTS TO DETECT (H248,
    # AGENT-2). `adb` is not present on every host, and an unguarded
    # `subprocess.run` raises FileNotFoundError, so this evaluator CRASHED on
    # exactly the condition it is here to report. Before H245 that crash was
    # indistinguishable from a refusal, because `run_evaluator` returned on a
    # non-zero exit before parsing -- so "no adb installed" and "the determinism
    # check failed" produced the same event.
    try:
        p_devs = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    except (FileNotFoundError, OSError) as e:
        return None, f"not_measured_adb_not_installed ({type(e).__name__})", {
            "fuel_host": host_fuel, "canon_host": host_canon}

    devices = []
    for line in p_devs.stdout.strip().split("\n")[1:]:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])

    # ONE REASON STRING FOR TWO CAUSES IS A CONFIDENT WRONG ANSWER, and this
    # one was mine. `not devices or not os.path.exists(dev_bin)` reported
    # `not_measured_no_adb_device` whether the phone was unplugged OR the
    # aarch64-linux-android binary had never been cross-compiled. I hit the
    # second case myself while the emulator was booting, read "no device
    # attached", and only noticed because `adb devices` in the next shell
    # listed emulator-5554. A reason a reader cannot act on is family B: it is
    # well formed, it is confident, and it names the wrong thing.
    if not devices and not os.path.exists(dev_bin):
        return None, "not_measured_no_device_and_no_device_binary", {
            "fuel_host": host_fuel, "canon_host": host_canon,
            "dev_bin_expected": dev_bin}
    if not devices:
        # NOT MEASURED is not DIVERGENCE. This returned 0.0, which the config
        # reads against min_acceptable 1.0, so the run reported
        # DIVERGENCE_DETECTED -- "host and device disagree on MeTTa fuel" --
        # when the truth was that no device answered. That is the project's
        # CENTRAL CLAIM being reported as broken because a phone was unplugged,
        # and cross_device_details gave it away by carrying only host values
        # with no device figure beside them.
        #
        # None, not 0.0: autoloop now prints MISSING METRIC and fails the
        # invariant for the honest reason -- it could not be checked, rather
        # than it regressed. Those are opposite situations and must not share
        # a number.
        return None, "not_measured_no_adb_device_attached", {
            "fuel_host": host_fuel, "canon_host": host_canon}
    if not os.path.exists(dev_bin):
        # A DEVICE ANSWERED AND THERE IS NOTHING TO PUSH TO IT. Distinct from
        # every case above and the one most likely to be misread as a hardware
        # problem when it is a build problem.
        return None, "not_measured_device_binary_missing", {
            "fuel_host": host_fuel, "canon_host": host_canon,
            "devices_seen": devices, "dev_bin_expected": dev_bin}

    serial = "R5CY93675MK" if "R5CY93675MK" in devices else devices[0]
    dev_tmp = "/data/local/tmp/kftest"

    subprocess.run(["adb", "-s", serial, "shell", f"mkdir -p {dev_tmp}"], capture_output=True)
    subprocess.run(["adb", "-s", serial, "push", dev_bin, f"{dev_tmp}/threadrun"], capture_output=True)
    subprocess.run(["adb", "-s", serial, "push", probe_metta, f"{dev_tmp}/probe.metta"], capture_output=True)
    p_dev = subprocess.run(["adb", "-s", serial, "shell", f"chmod +x {dev_tmp}/threadrun && {dev_tmp}/threadrun 200000 1 1 {dev_tmp}/probe.metta"], capture_output=True, text=True)
    if p_dev.returncode != 0:
        return 0.0, "device_threadrun_failed", {}

    dev_lines = [l for l in p_dev.stdout.strip().split("\n") if not l.startswith("#") and not l.startswith("repeat")]
    if not dev_lines:
        return 0.0, "no_device_output", {}
    dev_cols = dev_lines[0].split("\t")
    dev_fuel, dev_raw, dev_canon, dev_alpha = dev_cols[4], dev_cols[5], dev_cols[6], dev_cols[7]

    match = (host_fuel == dev_fuel and host_canon == dev_canon and host_alpha == dev_alpha and host_raw == dev_raw)
    score = 1.0 if match else 0.0
    return score, f"device_{serial}_verified", {
        "device_serial": serial,
        "fuel_host": host_fuel,
        "fuel_device": dev_fuel,
        "canon_host": host_canon,
        "canon_device": dev_canon,
        "alpha_host": host_alpha,
        "alpha_device": dev_alpha,
        "byte_identical_match": match,
    }


def main():
    rng = np.random.default_rng(SEED)
    bip = lambda r: (rng.integers(0, 2, size=(r, D), dtype=np.int8) * 2 - 1).astype(np.int8)
    T, Qv = bip(N), bip(Q)

    # reference: true int32 dot product, no packing involved
    ref = Qv.astype(np.int32) @ T.astype(np.int32).T

    # candidate: 1 bit per dimension, XOR + popcount
    Tp, Qp = np.packbits(T > 0, axis=1), np.packbits(Qv > 0, axis=1)
    got = np.empty_like(ref)
    for k in range(Q):
        h = np.bitwise_count(Tp ^ Qp[k]).sum(axis=1, dtype=np.int32)
        got[k] = D - 2 * h

    exact = bool(np.array_equal(ref, got))
    digest = int(np.bitwise_xor.reduce(got.astype(np.uint32).ravel()))

    cross_score, cross_scope, cross_details = check_cross_device_metta()

    # cross_score is None when no device answered. THREE outcomes, not two:
    # measured-and-agreeing, measured-and-divergent, and not measured at all.
    # Collapsing the third into the second is how an unplugged phone came to
    # read as a determinism failure.
    unmeasured = cross_score is None
    all_passed = exact and (cross_score == 1.0)
    out = {
        "determinism_exact": 1.0 if exact else 0.0,
        "scope": f"cross_device_snapdragon_and_host_metta_identity ({cross_scope})",
        "cross_device_details": cross_details,
        "score_digest": f"{digest:08x}",
        "pairs_checked": int(ref.size),
        "status": ("NOT_MEASURED" if unmeasured else
                   "RECOMPUTED" if all_passed else "DIVERGENCE_DETECTED"),
    }
    # Omit the key entirely rather than emit a number nobody measured; the
    # driver reports MISSING METRIC and fails the invariant for the right
    # reason.
    if not unmeasured:
        out["cross_device_metta_fuel_match"] = cross_score
    print(json.dumps(out, indent=2))
    return 0 if (all_passed or unmeasured) else 1


def selfcheck():
    """THE NEGATIVE CONTROL. A gate never seen red is a green light with no wire.

    This file had none: it had never been shown to FAIL, which its author said
    plainly when handing it over. Each arm plants ONE break in a copy of this
    source and requires `determinism_exact: 0.0` with exit 1. It never edits the
    installed file, and it writes only under the workspace (§10).
    """
    src = open(os.path.abspath(__file__), encoding='utf-8').read()
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_selfcheck_broken.py')
    # ANCHORS ARE ASSEMBLED, NEVER WRITTEN WHOLE. Written as literals they appear
    # TWICE in this file -- once in `main()`, once in this list -- and the first
    # run of this check refused all three arms for exactly that reason
    # (`src.count(old) != 1`). A suite that silently patched the first match
    # would have measured its own fixture instead of the gate. The refusal is
    # kept; the anchors moved.
    _dot, _eq = 'got[k] = D - 2' + ' * h', 'exact = bool(np.array_' + 'equal(ref, got))'
    _pack = 'Tp, Qp = np.packbits(T > 0, axis=1), np.pack' + 'bits(Qv > 0, axis=1)'
    breaks = [
        ('the identity: D - 2*h -> D - h', _dot, 'got[k] = D - h'),
        ('a SINGLE score off by one', _eq, 'got[0, 0] += 1\n    ' + _eq),
        ('the packing: T > 0 -> T > -2 (all-ones)', _pack,
         _pack.replace('T > 0', 'T > -2')),
    ]
    bad = 0
    try:
        for label, old, new in breaks:
            if src.count(old) != 1:
                print(f'  FAIL   anchor is not unique, so this arm proves nothing: {label}')
                bad += 1
                continue
            open(tmp, 'w', encoding='utf-8').write(src.replace(old, new))
            p = subprocess.run([sys.executable, tmp], capture_output=True, text=True)
            try:
                m = json.loads(p.stdout)
            except json.JSONDecodeError:
                m = {}
            red = m.get('determinism_exact') == 0.0 and p.returncode == 1
            print(f'  {"RED   " if red else "MISSES"} {label}')
            bad += not red
        # And the inverse: an UNMODIFIED copy must stay green, or "red" is just
        # the constant this check returns.
        open(tmp, 'w', encoding='utf-8').write(src)
        p = subprocess.run([sys.executable, tmp], capture_output=True, text=True)
        green = json.loads(p.stdout).get('determinism_exact') == 1.0 and p.returncode == 0
        print(f'  {"GREEN " if green else "FAIL  "} an unmodified copy still passes')
        bad += not green
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    # H260 — THE FOUR *NOT MEASURED* REASONS, EACH DRIVEN. A reason string
    # nobody has seen fire is a guess about what the code does. These four are
    # the states this evaluator is most often in on a machine that is not this
    # one, and before H260 two of them were one string and a third was a
    # traceback. Each arm copies the module BESIDE the original -- `repo_root`
    # is `__file__`-relative, and a copy in a scratch dir exits early at
    # `missing_host_bin_or_probe` without ever reaching the adb code, which is
    # how the first run of this check passed four arms that had not run.
    import re as _re
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _shim = os.path.join(_HERE, '_h260_shim')
    os.makedirs(_shim, exist_ok=True)
    _adb = os.path.join(_shim, 'adb')
    with open(_adb, 'w') as fh:
        fh.write('#!/bin/sh\necho "List of devices attached"\necho ""\n')
    os.chmod(_adb, 0o755)
    _made = []

    def _variant(name, patch_devbin):
        t = os.path.join(_HERE, f'_h260_{name}.py')
        v = src
        if patch_devbin:
            m = _re.search(r'^(\s*)dev_bin = .*$', v, _re.M)
            if not m:
                return None
            v = v[:m.start()] + m.group(1) + 'dev_bin = "/nonexistent/threadrun"' + v[m.end():]
        with open(t, 'w', encoding='utf-8') as fh:
            fh.write(v)
        _made.append(t)
        return t

    def _scope(mod, path_mode):
        env = dict(os.environ)
        if path_mode == 'noadb':
            env['PATH'] = '/nonexistent-bin'
        elif path_mode == 'shim':
            env['PATH'] = _shim + os.pathsep + env['PATH']
        r = subprocess.run([sys.executable, mod], capture_output=True, text=True, env=env)
        try:
            return json.loads(r.stdout).get('scope', '')
        except json.JSONDecodeError:
            return f'(no json, rc={r.returncode})'

    try:
        for label, name, patch, pm, expect in [
            ('adb not installed',         'noadb',   False, 'noadb', 'not_measured_adb_not_installed'),
            ('no device, binary present', 'nodev',   False, 'shim',  'not_measured_no_adb_device_attached'),
            ('device up, binary missing', 'nobin',   True,  'real',  'not_measured_device_binary_missing'),
            ('no device AND no binary',   'neither', True,  'shim',  'not_measured_no_device_and_no_device_binary'),
        ]:
            mod = _variant(name, patch)
            if mod is None:
                print(f'  FAIL   dev_bin anchor missing, arm proves nothing: {label}')
                bad += 1
                continue
            got = _scope(mod, pm)
            if expect in got:
                print(f'  RED    {label} -> {expect}')
            else:
                print(f'  MISSES {label} -> {got[:70]}')
                bad += 1
    finally:
        for t in _made:
            if os.path.exists(t):
                os.remove(t)
        if os.path.exists(_adb):
            os.remove(_adb)
        if os.path.isdir(_shim):
            os.rmdir(_shim)

    if bad:
        print(f'SELFCHECK FAILED: {bad}')
        return 1
    print('selfcheck: 3 planted breaks all turn it red, and the control stays green. '
          'NOTE: this proves the gate can fire on ITS OWN arithmetic. It does NOT '
          'prove the gate can fire on a CANDIDATE -- H111 measured that it cannot.')
    return 0

if __name__ == "__main__":
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
