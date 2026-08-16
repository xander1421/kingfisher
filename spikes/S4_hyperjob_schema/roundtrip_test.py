#!/usr/bin/env python3
"""S4 — round-trip encode/decode test for the hyperjob v0 schema.

Builds a fully-populated Hyperjob and ResultEnvelope, serialises, parses,
and asserts equality; then checks the two properties the schema exists to
guarantee:

  1. encoding is deterministic (same message -> same bytes), because
     result_hash is signed and two devices must produce identical envelopes;
  2. an unknown future field survives a round trip through an old parser
     (proto3 unknown-field retention), so v0 devices can relay v1 envelopes
     without invalidating the signature.

Run:  protoc --python_out=. hyperjob_v0.proto && python3 roundtrip_test.py
"""

import hashlib
import sys

import hyperjob_v0_pb2 as pb


def build_job():
    j = pb.Hyperjob(
        version="v0",
        job_id="job-0001",
        shard_cid=pb.Cid(multihash=b"\x12\x20" + b"\xab" * 32, text="bafyshard"),
        metta_program_inline=b"!(match &shard (likes alice $x) $x)",
        engine=pb.ENGINE_METTA_EXACT,
        fuel=pb.FuelLimit(max_steps=100_000, deadline_secs=600,
                          max_heap_bytes=256 << 20),
        seed=0xC0FFEE,
        replication=pb.ReplicationPolicy(
            mode=pb.REPLICATION_QUORUM, redundancy=3, quorum=2,
            challenge_window_secs=0, audit_rate=0.0,
            exclude_device_groups=["operator:acme", "attest-root:xyz"],
        ),
        device=pb.DevicePreferences(
            require_charging=True, require_unmetered_network=True,
            require_device_idle=True, min_battery_pct=90,
            max_thermal_status=1.0, require_npu_int8=False,
            min_ram_bytes=2 << 30,
            prefer_cached_cids=[pb.Cid(multihash=b"\x12\x20" + b"\xcd" * 32,
                                       text="bafycached")],
        ),
        labels={"tenant": "kingfisher", "class": "exact"},
    )
    return j


def build_envelope(job):
    e = pb.ResultEnvelope(
        version="v0",
        job_id=job.job_id,
        status=pb.RESULT_OK,
        result_hash=hashlib.sha256(b"(bob) (carol)").digest(),
        result_cid=pb.Cid(multihash=b"\x12\x20" + b"\xef" * 32, text="bafyres"),
        fuel_used=41_337,
        seed_echo=job.seed,
        lsh_commitment=pb.LshCommitment(
            k=4, modulus=65479, nodes=[11, 22, 33, 44],
            coeffs=[1234, 5678, 4321, 8765],
        ),
        timings=pb.Timings(queue_ms=12, fetch_shard_ms=340,
                           execute_ms=1180, total_ms=1532),
        device_did="did:key:z6MkExample",
        attestation=b"play-integrity-token",
    )
    e.signature = hashlib.sha256(e.SerializeToString()).digest()  # stand-in
    return e


def main():
    failures = []

    def check(name, cond):
        print(f"{'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            failures.append(name)

    job = build_job()
    wire = job.SerializeToString()
    back = pb.Hyperjob.FromString(wire)
    check("hyperjob round-trips", back == job)
    check("fuel survives", back.fuel.max_steps == 100_000)
    check("replication survives", (back.replication.mode == pb.REPLICATION_QUORUM
                                   and back.replication.quorum == 2))
    check("locality hint survives",
          back.device.prefer_cached_cids[0].text == "bafycached")

    env = build_envelope(job)
    ewire = env.SerializeToString()
    eback = pb.ResultEnvelope.FromString(ewire)
    check("envelope round-trips", eback == env)
    check("seed echoes the job", eback.seed_echo == job.seed)
    check("fuel_used present", eback.fuel_used == 41_337)
    check("lsh modulus is prime-looking (odd, >2^15)",
          eback.lsh_commitment.modulus % 2 == 1
          and eback.lsh_commitment.modulus > 2 ** 15)

    # 1. deterministic encoding — the signature depends on it
    check("encoding is byte-stable across 100 re-serialisations",
          len({job.SerializeToString() for _ in range(100)}) == 1)
    check("encoding is byte-stable after a parse round trip",
          back.SerializeToString() == wire)

    # 2. forward compatibility: a v1 field must survive a v0 parser
    v1 = pb.ResultEnvelope.FromString(ewire)
    v1_extra = ewire + b"\xf8\x3e\x2a"  # field 999, varint 42 — unknown to v0
    relayed = pb.ResultEnvelope.FromString(v1_extra)
    check("unknown v1 field is retained through a v0 parse",
          relayed.SerializeToString() == v1_extra)
    check("unknown field does not disturb known fields",
          relayed.fuel_used == v1.fuel_used and relayed.job_id == v1.job_id)

    # bisection probe/response
    probe = pb.BisectionProbe(job_id=job.job_id, step_index=20_000)
    resp = pb.BisectionResponse(job_id=job.job_id, step_index=20_000,
                                state_hash=hashlib.sha256(b"state").digest())
    check("bisection messages round-trip",
          pb.BisectionProbe.FromString(probe.SerializeToString()) == probe
          and pb.BisectionResponse.FromString(resp.SerializeToString()) == resp)

    print(f"\nHyperjob wire size: {len(wire)} B   "
          f"ResultEnvelope wire size: {len(ewire)} B")
    print("FAILURES:", failures if failures else "none")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
