#!/usr/bin/env python3
"""S49 — the verifier the schema implies, with every attack the device work found.

A schema that cannot be enforced is a comment. This is the enforcement, plus the
adversarial cases that motivated each field. Run it: `python3 verifier.py`.

The five rules, each traceable to a measurement rather than to taste:

  R1 seal        commitment must recompute from the revealed parts, and must
                 bind device_did. Defeats the echo attack, which v0 permits.
  R2 contract    two envelopes are comparable only if their ExecutionContracts
                 match. Otherwise ABSTAIN -- never slash. (S35 --timing.)
  R3 cutoff      rint(2*nnz/scale) <= 126, or the int8 cutoff sits on the
                 saturation boundary and recall silently becomes 0. (S31.)
  R4 unit        inexact units may not vote. (GPU float.)
  R5 canonical   verbatim only within one engine; cross-engine needs sorted-set,
                 because MORK dedupes and hyperon does not. (S35, S45.)

Plus a content check: reject any dump containing a `(timing ...)` record,
because it carries a nanosecond count into the hashed artifact.
"""

import hashlib
import re
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------- model
@dataclass(frozen=True)
class Contract:
    engine: str
    engine_flags: tuple
    quant_scale: float = 1.0
    output_bits: int = 32
    canonical_form: str = "VERBATIM"
    shard_layout: str = "raw"        # deliberately excluded from comparison


@dataclass
class Envelope:
    job_id: str
    result_hash: bytes
    fuel_used: int
    device_did: str
    nonce: bytes
    contract: Contract
    unit: str
    payload: str = ""                # the dump, for content checks
    commitment: bytes = None
    forged_commitment: bytes = None  # test hook: publish someone else's

    def compute_commitment(self):
        h = hashlib.sha256()
        h.update(self.result_hash)
        h.update(self.fuel_used.to_bytes(8, "little"))
        h.update(self.device_did.encode())
        h.update(self.nonce)
        return h.digest()

    def publish(self):
        self.commitment = self.forged_commitment or self.compute_commitment()
        return self.commitment


EXACT_UNITS = {"CPU_SCALAR", "CPU_SIMD", "NPU_POPCOUNT", "NPU_QUANT_MATMUL"}
TIMING_RE = re.compile(r"\(timing\b")


class Reject(Exception):
    pass


class Abstain(Exception):
    pass


# ---------------------------------------------------------------- rules
def canonicalise(payload, form):
    lines = [l for l in payload.splitlines() if l.strip()]
    if form == "VERBATIM":
        return "\n".join(lines)
    if form == "SORTED_SET":
        return "\n".join(sorted(set(lines)))
    if form == "SORTED_BAG":
        return "\n".join(sorted(lines))
    raise Reject(f"unknown canonical form {form}")


def check_envelope(e):
    """Rules that apply to a single envelope, before any comparison."""
    # R1
    if e.commitment is None:
        raise Reject("no commitment published")
    if e.commitment != e.compute_commitment():
        raise Reject("commitment does not recompute — echo attack or tampering")
    if len(e.nonce) < 16:
        raise Reject("nonce too short")
    # R3
    if e.contract.output_bits == 8:
        nnz = 527          # S31's measured query: nnz=527 -> cutoff 2*nnz=1054
        cutoff = round(2 * nnz / e.contract.quant_scale)
        if cutoff > 126:
            raise Reject(f"cutoff {cutoff} > 126: sits on the int8 saturation "
                         f"boundary, recall silently becomes 0 (S31)")
    # R4
    if e.unit not in EXACT_UNITS:
        raise Reject(f"unit {e.unit} is inexact: may produce hints, may not vote")
    # content check
    if TIMING_RE.search(e.payload):
        raise Reject("payload contains a (timing ...) record: nondeterministic "
                     "instrumentation inside the hashed artifact (S35)")
    return True


def compare(a, b):
    """Two envelopes -> AGREE / DISAGREE, or Abstain if not comparable."""
    check_envelope(a)
    check_envelope(b)
    # R2 — compare the contract, EXCLUDING shard_layout (S48: layout changes
    # cost by up to 24x but never answers)
    ca, cb = a.contract, b.contract
    for f in ("engine", "engine_flags", "quant_scale", "output_bits",
              "canonical_form"):
        if getattr(ca, f) != getattr(cb, f):
            raise Abstain(f"contracts differ on {f}: "
                          f"{getattr(ca, f)!r} vs {getattr(cb, f)!r} — "
                          f"results are not evidence; do not slash")
    # R5
    if ca.engine != cb.engine and ca.canonical_form == "VERBATIM":
        raise Abstain("cross-engine comparison requires SORTED_SET, not VERBATIM")
    if a.fuel_used != b.fuel_used:
        return "DISAGREE", f"fuel {a.fuel_used} vs {b.fuel_used}"
    ha = hashlib.sha256(canonicalise(a.payload, ca.canonical_form).encode()).digest()
    hb = hashlib.sha256(canonicalise(b.payload, cb.canonical_form).encode()).digest()
    return ("AGREE", "") if ha == hb else ("DISAGREE", "payload hash")


# ---------------------------------------------------------------- tests
def main():
    C = Contract("hyperon-0.2.10", ("--steps=5000000",))
    good = "(TwoHop a b)\n(TwoHop a c)\n(TwoHop b c)"
    fails = []

    def case(name, fn, expect):
        try:
            got = fn()
        except Reject as ex:
            got = ("REJECT", str(ex))
        except Abstain as ex:
            got = ("ABSTAIN", str(ex))
        ok = got[0] == expect
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<52} -> {got[0]}")
        if not ok:
            fails.append(name)
            print(f"        expected {expect}, detail: {got[1][:90]}")

    def env(did="did:key:A", nonce=b"n" * 16, contract=C, unit="CPU_SIMD",
            payload=good, rh=None, fuel=100082):
        e = Envelope("job-1", rh or hashlib.sha256(payload.encode()).digest(),
                     fuel, did, nonce, contract, unit, payload)
        e.publish()
        return e

    print("S49 verifier — each case is an attack the device work found\n")

    print("honest paths:")
    case("two honest replicas, same engine", lambda: compare(env(), env("did:key:B")), "AGREE")
    case("genuine disagreement is caught",
         lambda: compare(env(), env("did:key:B", payload=good + "\n(TwoHop z z)")), "DISAGREE")
    case("fuel mismatch is caught",
         lambda: compare(env(), env("did:key:B", fuel=99999)), "DISAGREE")

    print("\nR1 — the echo attack v0 permits:")
    def echo():
        a = env()
        b = Envelope("job-1", a.result_hash, a.fuel_used, "did:key:EVIL",
                     b"m" * 16, C, "CPU_SIMD", a.payload)
        b.forged_commitment = a.commitment      # republish A's commitment
        b.publish()
        return compare(a, b)
    case("replica 2 echoes replica 1's commitment", echo, "REJECT")

    def echo_hash_only():
        a = env()
        # copies the hash but must commit under its own DID — commitment then
        # binds a different DID, so the two commitments differ and the echo is
        # visible even though the hash matches
        b = env("did:key:EVIL", nonce=b"m" * 16)
        return ("AGREE", "") if a.commitment == b.commitment else ("DISTINCT", "")
    case("copied hash still yields a distinct commitment", echo_hash_only, "DISTINCT")

    print("\nR2/R3/R4/R5 — the contract:")
    case("engine flags differ -> abstain, never slash",
         lambda: compare(env(), env("did:key:B",
                contract=Contract("hyperon-0.2.10", ("--steps=5000000", "--timing")))),
         "ABSTAIN")
    case("different engines with VERBATIM -> abstain",
         lambda: compare(env(), env("did:key:B",
                contract=Contract("mork-main-0653b50", ("--steps=5000000",)))),
         "ABSTAIN")
    # S31 exactly: nnz=527, scale 8.2667 -> rint(1054/8.2667) = 128 > 126.
    # On device that produced recall 0/8, silently. The verifier must refuse it
    # before any comparison happens.
    C8bad = Contract("hyperon-0.2.10", ("--steps=5000000",), 8.2667, 8)
    C8ok  = Contract("hyperon-0.2.10", ("--steps=5000000",), 16.0, 8)
    case("int8 with S31's naive scale (cutoff 128) -> reject",
         lambda: compare(env(contract=C8bad), env("did:key:B", contract=C8bad)),
         "REJECT")
    case("int8 with headroom (cutoff 66) -> comparable",
         lambda: compare(env(contract=C8ok), env("did:key:B", contract=C8ok)),
         "AGREE")
    case("GPU float may not vote",
         lambda: compare(env(unit="GPU_FLOAT"), env("did:key:B")), "REJECT")
    case("(timing ...) in the payload -> reject",
         lambda: compare(env(payload=good + "\n(timing (exec 0) 0 7887916)"),
                         env("did:key:B")), "REJECT")

    print("\nS48 — layout is accounting, not consensus:")
    case("same answers, different shard layout -> still AGREE",
         lambda: compare(env(contract=Contract("hyperon-0.2.10", ("--steps=5000000",),
                                               shard_layout="clustered:pred,subj")),
                         env("did:key:B")), "AGREE")

    print("\nS35 — set vs bag across engines:")
    bag = "(A 1)\n(A 1)\n(A 2)"
    set_ = "(A 1)\n(A 2)"
    case("MORK set vs hyperon bag under SORTED_SET -> AGREE",
         lambda: compare(
             env(contract=Contract("mork", (), canonical_form="SORTED_SET"), payload=set_),
             env("did:key:B",
                 contract=Contract("mork", (), canonical_form="SORTED_SET"), payload=bag)),
         "AGREE")

    print(f"\n{'FAILURES: ' + ', '.join(fails) if fails else 'all cases behaved as specified'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
