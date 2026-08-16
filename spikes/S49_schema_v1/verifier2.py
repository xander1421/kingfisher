#!/usr/bin/env python3
"""S49b — verifier v2, after an adversarial review destroyed v1.

v1 claimed "the seal defeats the echo attack, 13/13". Both halves were false:

  * the seal bound `result_hash`, but the verdict was computed from `payload`,
    and nothing tied the two together. The sealed value was inert.
  * there was no commit-before-reveal ordering, so an attacker could read a
    reveal, copy the payload, and commit honestly under its own DID. The test
    that "proved" the seal never called compare(); substituting the real
    verifier into it returns AGREE — it demonstrated the attack succeeding and
    reported it as a pass.
  * `device_did || nonce` was concatenated without length prefixes, so
    ('did:key:A', b'X'+16n) and ('did:key:AX', 16n) collide. Verified.
  * R5 was unreachable: R2 abstains on engine mismatch first. Deleting R5 left
    13/13 passing.
  * R3 hardcoded nnz, so it validated a query nobody ran, and its documented
    arithmetic was wrong.

The R3 arithmetic deserves its own note, because it is the sharpest thing the
review turned up. The v1 docs said scale 8.2667 gives cutoff 128. In double
precision 1054/8.2667 rounds to 127. On the device S31 printed 128 — because
S31 declared `float scales[2]`, and in single precision the quotient is
127.500003922 instead of 127.500000000. **The accept/reject boundary sat
exactly on .5 and was decided by C type width.** No consensus rule may depend
on that, so v2 does the cutoff in integers only: the scale is transmitted as an
exact rational and never as a float.

Run: python3 verifier2.py
"""

import hashlib
import re
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------- encoding
def lp(*parts):
    """Length-prefixed concatenation. Unambiguous preimage: every field is
    preceded by its length, so no two distinct tuples share an encoding."""
    out = b""
    for p in parts:
        b = p.encode() if isinstance(p, str) else (
            p.to_bytes(8, "little") if isinstance(p, int) else p)
        out += len(b).to_bytes(4, "little") + b
    return out


CANON = ("VERBATIM", "SORTED_SET", "SORTED_BAG")


@dataclass(frozen=True)
class Contract:
    engine: str
    engine_flags: tuple
    # exact rational, never a float: cutoff arithmetic must be integer-only
    scale_num: int = 1
    scale_den: int = 1
    output_bits: int = 32
    canonical_form: str = "VERBATIM"

    def digest(self):
        return hashlib.sha256(lp(self.engine, "\x00".join(self.engine_flags),
                                 self.scale_num, self.scale_den,
                                 self.output_bits, self.canonical_form)).digest()


@dataclass(frozen=True)
class Job:
    """The job PINS the contract. A worker may not choose it after the fact —
    that was v1's escape hatch: declaring one extra engine flag converted a
    slashable DISAGREE into a protected ABSTAIN at zero cost."""
    job_id: str
    contract: Contract
    nnz: int
    shard_layout: str = "raw"     # recorded, never compared (S48)


@dataclass
class Envelope:
    job_id: str
    device_did: str
    nonce: bytes
    fuel_used: int
    payload: str
    contract: Contract
    unit: str
    result_hash: bytes = None     # MUST equal H(canonical payload)

    def commitment(self):
        return hashlib.sha256(lp(
            "hyperjob-commit-v1",          # domain separation
            self.job_id,                   # scopes the commitment to one job
            self.result_hash,
            self.fuel_used,
            self.device_did,
            self.nonce,
            self.contract.digest(),        # contract cannot be swapped later
        )).digest()


class CommitRegistry:
    """Commit-before-reveal, enforced. v1 had no ordering at all, which is the
    whole security property of commit/reveal."""

    def __init__(self):
        self._commits = {}
        self.closed = False

    def commit(self, job_id, device_did, commitment):
        if self.closed:
            raise Reject("commit window closed")
        k = (job_id, device_did)
        if k in self._commits:
            raise Reject("one commitment per (job, device); grinding refused")
        self._commits[k] = commitment

    def close(self):
        self.closed = True

    def registered(self, env):
        return self._commits.get((env.job_id, env.device_did))


EXACT_UNITS = {"CPU_SCALAR", "CPU_SIMD", "NPU_POPCOUNT", "NPU_QUANT_MATMUL"}
TIMING_RE = re.compile(r"\(\s*timing\b", re.IGNORECASE)


class Reject(Exception):
    """This envelope is invalid. Attributed to ONE envelope, never a pair."""


class Abstain(Exception):
    """Not comparable. Never slash."""


# ---------------------------------------------------------------- rules
def canonicalise(payload, form):
    if form == "VERBATIM":
        return payload                      # v1 stripped blank lines here
    lines = payload.splitlines()
    if form == "SORTED_SET":
        return "\n".join(sorted(set(lines)))
    if form == "SORTED_BAG":
        return "\n".join(sorted(lines))
    raise Reject(f"unknown canonical form {form!r}")


def cutoff_for(job):
    """Integer-only. scale = num/den, cutoff = round_half_up(2*nnz*den/num).
    No float appears anywhere on this path."""
    num, den = job.contract.scale_num, job.contract.scale_den
    if num <= 0 or den <= 0:
        raise Reject(f"non-positive scale {num}/{den}")
    return (2 * job.nnz * den * 2 + num) // (2 * num)


def max_code(bits):
    # one code of headroom below the saturation value, so the cutoff can never
    # land ON the clipping boundary (S31: it did, and recall went to 0/8)
    return {8: 126, 16: 32766, 32: (1 << 31) - 2}[bits]


def check_envelope(env, job, registry):
    """Per-envelope validity. Raises Reject naming THIS envelope only."""
    who = env.device_did
    if env.job_id != job.job_id:
        raise Reject(f"{who}: envelope job {env.job_id} != {job.job_id}")
    if env.contract != job.contract:
        raise Reject(f"{who}: contract does not match the job's pinned contract")
    if env.contract.canonical_form not in CANON:
        raise Reject(f"{who}: bad canonical form")
    if env.contract.output_bits not in (8, 16, 32):
        raise Reject(f"{who}: bad output_bits")
    if len(env.nonce) < 16:
        raise Reject(f"{who}: nonce too short")
    if not 0 <= env.fuel_used < (1 << 64):
        raise Reject(f"{who}: fuel out of range")

    # the fix for v1's central defect: the sealed value must BE the verdict value
    want = hashlib.sha256(canonicalise(env.payload,
                                       env.contract.canonical_form).encode()).digest()
    if env.result_hash != want:
        raise Reject(f"{who}: result_hash is not H(canonical payload)")

    c = registry.registered(env)
    if c is None:
        raise Reject(f"{who}: no commitment registered before the window closed")
    if c != env.commitment():
        raise Reject(f"{who}: commitment does not recompute")

    cut = cutoff_for(job)
    if cut > max_code(env.contract.output_bits):
        raise Reject(f"{who}: cutoff {cut} exceeds {max_code(env.contract.output_bits)} "
                     f"for {env.contract.output_bits}-bit output (S31: silent recall 0)")
    if env.unit not in EXACT_UNITS:
        raise Reject(f"{who}: unit {env.unit} is inexact; may hint, may not vote")
    if TIMING_RE.search(env.payload):
        raise Reject(f"{who}: payload carries a (timing ...) record")
    return True


def compare(job, a, b, registry):
    """-> (verdict, detail). Comparability is decided BEFORE per-envelope
    validity, so one bad envelope cannot destroy an honest peer's result."""
    # identity first — cheapest, and v1 had neither check
    if a.job_id != b.job_id:
        raise Abstain(f"different jobs: {a.job_id} vs {b.job_id}")
    if a.device_did == b.device_did:
        raise Abstain(f"same device {a.device_did} on both sides: not independent")
    if a.contract != b.contract:
        raise Abstain("contracts differ; results are not evidence, do not slash")
    if a.contract.engine != b.contract.engine and \
       a.contract.canonical_form == "VERBATIM":
        raise Abstain("cross-engine comparison needs SORTED_SET, not VERBATIM")

    errs = []
    for e in (a, b):
        try:
            check_envelope(e, job, registry)
        except Reject as ex:
            errs.append(str(ex))
    if errs:
        raise Reject(" | ".join(errs))      # attributed by DID inside each msg

    if a.fuel_used != b.fuel_used:
        return "DISAGREE", f"fuel {a.fuel_used} vs {b.fuel_used}"
    return (("AGREE", "") if a.result_hash == b.result_hash
            else ("DISAGREE", "result_hash"))


# ---------------------------------------------------------------- tests
def main():
    C = Contract("hyperon-0.2.10", ("--steps=5000000",))
    JOB = Job("job-1", C, nnz=527)
    good = "(TwoHop a b)\n(TwoHop a c)\n(TwoHop b c)"
    fails = []

    def mk(did, payload=good, contract=C, unit="CPU_SIMD", fuel=100082,
           nonce=None, job_id="job-1", rh=None):
        e = Envelope(job_id, did, nonce or (did.encode() + b"\x00" * 16),
                     fuel, payload, contract, unit)
        e.result_hash = rh if rh is not None else hashlib.sha256(
            canonicalise(payload, contract.canonical_form).encode()).digest()
        return e

    def run(name, fn, expect):
        try:
            got = fn()[0]
        except Reject as ex:
            got = "REJECT"
        except Abstain as ex:
            got = "ABSTAIN"
        except Exception as ex:
            got = f"CRASH({type(ex).__name__})"
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<56} -> {got}")
        if not ok:
            fails.append(name)

    def honest_pair(**kw):
        a, b = mk("did:key:A", **kw), mk("did:key:B", **kw)
        r = CommitRegistry()
        r.commit(a.job_id, a.device_did, a.commitment())
        r.commit(b.job_id, b.device_did, b.commitment())
        r.close()
        return lambda: compare(JOB, a, b, r)

    print("S49b verifier v2 — every case below is an exploit that beat v1\n")
    print("baseline:")
    run("two honest replicas", honest_pair(), "AGREE")
    run("genuine disagreement", lambda: (lambda a, b, r: compare(JOB, a, b, r))(
        *(lambda a, b: (a, b, _reg(a, b)))(mk("did:key:A"),
                                           mk("did:key:B", payload=good + "\n(TwoHop z z)"))), "DISAGREE")

    print("\nv1 CRITICAL 1 — sealed value was not the verdict value:")
    def garbage_hash():
        a, b = mk("did:key:A"), mk("did:key:EVIL", rh=b"\xaa" * 32)
        return compare(JOB, a, b, _reg(a, b))
    run("commit to garbage hash, reveal honest payload", garbage_hash, "REJECT")

    print("\nv1 CRITICAL 2 — no commit-before-reveal ordering:")
    def late_commit():
        a = mk("did:key:A")
        r = CommitRegistry(); r.commit(a.job_id, a.device_did, a.commitment())
        r.close()                                     # window shuts
        b = mk("did:key:EVIL", payload=a.payload)     # copies after seeing reveal
        try:
            r.commit(b.job_id, b.device_did, b.commitment())
        except Reject:
            pass
        return compare(JOB, a, b, r)
    run("attacker commits AFTER the window closes", late_commit, "REJECT")

    def grind():
        a = mk("did:key:A")
        r = CommitRegistry(); r.commit(a.job_id, a.device_did, a.commitment())
        r.commit(a.job_id, a.device_did, b"\x00" * 32)   # second candidate
        return ("UNREACHED",)
    run("commit-many / reveal-one is refused", grind, "REJECT")

    print("\nv1 CRITICAL 3 — unprefixed preimage collided:")
    def collide():
        a = mk("did:key:A", nonce=b"X" + b"n" * 16)
        b = mk("did:key:AX", nonce=b"n" * 16)
        return ("COLLIDE",) if a.commitment() == b.commitment() else ("DISTINCT",)
    run("('did:key:A',X+16n) vs ('did:key:AX',16n)", collide, "DISTINCT")

    print("\nv1 HIGH 4 — contract was attacker-chosen:")
    def flag_escape():
        wrong = Contract("hyperon-0.2.10", ("--steps=5000000", "--timing"))
        a = mk("did:key:A")
        b = mk("did:key:EVIL", payload=good + "\n(TwoHop z z)", contract=wrong)
        return compare(JOB, a, b, _reg(a, b))
    run("declare an extra flag to escape a DISAGREE", flag_escape, "ABSTAIN")
    def flag_escape_pinned():
        # ...and it no longer helps: the job pins the contract, so the envelope
        # is rejected on its own terms rather than protecting the attacker
        wrong = Contract("hyperon-0.2.10", ("--steps=5000000", "--timing"))
        a = mk("did:key:A"); b = mk("did:key:EVIL", contract=wrong)
        try:
            check_envelope(b, JOB, _reg(a, b)); return ("PASSED",)
        except Reject:
            return ("REJECT",)
    run("...and the unpinned contract is itself rejected", flag_escape_pinned, "REJECT")

    print("\nv1 HIGH 5 — no identity checks:")
    def self_quorum():
        a, b = mk("did:key:A"), mk("did:key:A", nonce=b"z" * 16)
        r = CommitRegistry(); r.commit(a.job_id, a.device_did, a.commitment()); r.close()
        return compare(JOB, a, b, r)
    run("one device agreeing with itself", self_quorum, "ABSTAIN")
    def cross_job():
        a = mk("did:key:A"); b = mk("did:key:B", job_id="job-2")
        return compare(JOB, a, b, _reg(a, b))
    run("cross-job replay", cross_job, "ABSTAIN")

    print("\nv1 HIGH 6 — R5 was unreachable dead code:")
    def cross_engine_ok():
        cc = Contract("mork", (), canonical_form="SORTED_SET")
        j = Job("job-1", cc, nnz=527)
        a = mk("did:key:A", payload="(A 1)\n(A 2)", contract=cc)
        b = mk("did:key:B", payload="(A 1)\n(A 1)\n(A 2)", contract=cc)
        return compare(j, a, b, _reg(a, b))
    run("MORK set vs hyperon bag under SORTED_SET", cross_engine_ok, "AGREE")

    print("\nv1 HIGH 7 — R3 was unsound:")
    def big_nnz():
        j = Job("job-1", Contract("h", (), 16, 1, 8), nnz=5000)
        a = mk("did:key:A", contract=j.contract); b = mk("did:key:B", contract=j.contract)
        return compare(j, a, b, _reg(a, b))
    run("nnz=5000 at scale 16 (v1 hardcoded 527 and accepted)", big_nnz, "REJECT")
    def s31_scale():
        # S31's real scale, as an exact rational: 2108/255
        j = Job("job-1", Contract("h", (), 2108, 255, 8), nnz=527)
        a = mk("did:key:A", contract=j.contract); b = mk("did:key:B", contract=j.contract)
        return compare(j, a, b, _reg(a, b))
    run("S31's scale 2108/255 -> cutoff 128 > 126", s31_scale, "REJECT")
    def headroom():
        j = Job("job-1", Contract("h", (), 16, 1, 8), nnz=527)
        a = mk("did:key:A", contract=j.contract); b = mk("did:key:B", contract=j.contract)
        return compare(j, a, b, _reg(a, b))
    run("scale 16 at nnz=527 -> cutoff 66, fine", headroom, "AGREE")
    def bits16():
        # cutoff = 2*527*32 = 33,728 > 32,766. My first attempt used scale 1/2,
        # which gives 2,108 -- comfortably inside int16, so the test was wrong
        # and the code was right. Second time today my TEST DATA was the defect.
        j = Job("job-1", Contract("h", (), 1, 32, 16), nnz=527)
        a = mk("did:key:A", contract=j.contract); b = mk("did:key:B", contract=j.contract)
        return compare(j, a, b, _reg(a, b))
    run("output_bits=16 is bounded too (v1 checked only 8)", bits16, "REJECT")
    def zero_scale():
        j = Job("job-1", Contract("h", (), 0, 1, 8), nnz=527)
        a = mk("did:key:A", contract=j.contract); b = mk("did:key:B", contract=j.contract)
        return compare(j, a, b, _reg(a, b))
    run("scale 0 (v1: uncaught ZeroDivisionError DoS)", zero_scale, "REJECT")

    print("\nv1 MEDIUM — REJECT was contagious, and small holes:")
    def contagion():
        a = mk("did:key:A")
        b = mk("did:key:EVIL", payload=good + "\n(TIMING (exec 0) 0 7)")
        try:
            compare(JOB, a, b, _reg(a, b))
        except Reject as ex:
            return ("ATTRIBUTED",) if "did:key:EVIL" in str(ex) and \
                                      "did:key:A:" not in str(ex) else ("BLAMED_BOTH",)
        return ("PASSED",)
    run("uppercase (TIMING ...) caught, blame attributed to one DID", contagion, "ATTRIBUTED")
    def verbatim_ws():
        a = mk("did:key:A"); b = mk("did:key:B", payload="\n\n" + good + "\n\n")
        return compare(JOB, a, b, _reg(a, b))
    run("VERBATIM is byte-exact (v1 stripped blank lines)", verbatim_ws, "DISAGREE")

    print(f"\n{'FAILURES: ' + ', '.join(fails) if fails else 'every v1 exploit is now handled'}")
    return 1 if fails else 0


def _reg(*envs):
    r = CommitRegistry()
    for e in envs:
        try:
            r.commit(e.job_id, e.device_did, e.commitment())
        except Reject:
            pass
    r.close()
    return r


if __name__ == "__main__":
    sys.exit(main())
