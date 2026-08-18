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
    # THE VERDICT IS `array_equal`, NOT THE DIGEST. H111 F5 was stated to stop me
    # attacking the wrong thing: the XOR fold IS weak -- order-insensitive and
    # self-cancelling, so a permutation, a duplicated pair and a zeroed pair all
    # collide (measured, `spikes/H111_veto_input/probe.py` A6) -- but it is a
    # REPORTING field and nothing reads it for the verdict, so the weakness is
    # not load-bearing HERE. It becomes load-bearing the moment anyone compares
    # two digests and calls agreement a reproduction. Named, so that cannot
    # happen by accident.
    digest = int(np.bitwise_xor.reduce(got.astype(np.uint32).ravel()))
    print(json.dumps({
        "determinism_exact": 1.0 if exact else 0.0,
        # SCOPE AS AN EMITTED FIELD, not as prose in a docstring nobody re-reads.
        # "determinism gate is green" is three documents away from this file, and
        # claim decay is the failure no tool catches. This is ONE numpy checked
        # against ONE numpy, in ONE process, on ONE machine. S34 established the
        # cross-kernel, cross-machine property; this is the cheap local half and
        # says so in its own output.
        "scope": "single_process_single_numpy_local_identity",
        "not_verified_here": "cross-machine, cross-kernel (that is S34)",
        "score_digest": f"{digest:08x}",
        "digest_algorithm": "xor-fold, ORDER-INSENSITIVE and SELF-CANCELLING; "
                            "reporting only, never the verdict",
        "pairs_checked": int(ref.size),
        "status": "RECOMPUTED" if exact else "IDENTITY_BROKEN",
    }, indent=2))
    return 0 if exact else 1


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
    if bad:
        print(f'SELFCHECK FAILED: {bad}')
        return 1
    print('selfcheck: 3 planted breaks all turn it red, and the control stays green. '
          'NOTE: this proves the gate can fire on ITS OWN arithmetic. It does NOT '
          'prove the gate can fire on a CANDIDATE -- H111 measured that it cannot.')
    return 0

if __name__ == "__main__":
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
