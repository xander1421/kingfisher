#!/usr/bin/env python3
"""H188 — S91's five seats are ONE computation, replicated by assignment.

ATTACK on `spikes/S91_multi_agent_quorum/`, answering the operator's explicit
`REQUEST ADVERSARIAL REVIEW TO CLAUDE`.

NO CODE IS RETYPED (MISSION_LOOP §12.2 -- a copy is a second site). This module
IMPORTS `S91/run.py` and drives S91's OWN `main()`, `execute_job_on_agent`,
`load_corpus_jobs` and `audit_6axis_independence`. Every arm below is measured
by the instrument that produced the number under attack. The only thing patched
is `run.HERE`, so S91's own `main()` writes its artifacts into `arms/<arm>/`
instead of over a co-lane's committed `result.json`.

PREREGISTERED IN CHANNEL.md BEFORE THIS RAN. Each falsifier kills the row:

  F1  a tripwire object raising on ANY read is passed as `agent` for all 74
      jobs. If it raises even once, `agent` IS read and the row is withdrawn.
  F2  S91's corpus digest is sha256("CANONICAL_V1:" + source), i.e. INJECTIVE
      ON SOURCE TEXT. A real result hash cannot be. If S91's 67 corpus digests
      are not ~67-distinct, or if the real chain's committed outputs do NOT
      collapse, the "hashes inputs, not results" claim is wrong.
  F3  patch `run.PIN_F001` to a wrong value and re-run S91's own main(). If
      `valid_accepted` or `divergences` moves, the pin IS checked and the
      tautology claim is wrong.
"""
from __future__ import annotations

import contextlib
import glob
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))

import kfcheck
from provenance import Control, Falsifier

S91_DIR = ROOT / "spikes" / "S91_multi_agent_quorum"
S91_RESULT = S91_DIR / "result.json"
M1_OUT = ROOT / "spikes" / "M1_8_quorum3" / "run" / "host-a" / "out"
FLOORS = ROOT / "spikes" / "M1_8_quorum3" / "DETECTION_FLOORS.md"
ARMS = HERE / "arms"


def load_s91():
    spec = importlib.util.spec_from_file_location("s91_run", S91_DIR / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Tripwire(dict):
    """Raises on ANY read. If S91's worker touches its `agent` at all, this
    fires. Deliberately a dict subclass so it is type-compatible with the real
    roster entries -- a probe that fails for the wrong reason proves nothing."""

    class Touched(Exception):
        pass

    def __getitem__(self, k):
        raise Tripwire.Touched(f"agent[{k!r}] was read")

    def get(self, k, default=None):
        raise Tripwire.Touched(f"agent.get({k!r}) was read")

    def __contains__(self, k):
        raise Tripwire.Touched(f"{k!r} in agent was tested")

    def keys(self):
        raise Tripwire.Touched("agent.keys() was read")

    def __iter__(self):
        raise Tripwire.Touched("agent was iterated")


def reads_the_agent(agent, job):
    """NEGATIVE CONTROL for the tripwire. A worker that DOES consult its seat
    identity -- which is what a multi-seat verifier must do. If this does not
    trip the tripwire, the tripwire is inert and arm A proves nothing (H124)."""
    return {"digest": hashlib.sha256(agent["binary"].encode()).hexdigest()}


def run_arm(mod, name, patch):
    """Drive S91's OWN main() with one patched constant, into arms/<name>/."""
    out = ARMS / name
    out.mkdir(parents=True, exist_ok=True)
    saved = {k: getattr(mod, k) for k in patch}
    saved["HERE"] = mod.HERE
    for k, v in patch.items():
        setattr(mod, k, v)
    mod.HERE = out
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            mod.main()
    finally:
        for k, v in saved.items():
            setattr(mod, k, v)
    (out / "stdout.txt").write_text(buf.getvalue())
    return json.loads((out / "result.json").read_text())


def main() -> int:
    mod = load_s91()
    ARMS.mkdir(parents=True, exist_ok=True)
    published = json.loads(S91_RESULT.read_text())
    jobs = mod.load_corpus_jobs()
    findings = {}

    # ---- ARM 0: reproduce S91's committed numbers through its own main() ----
    arm0 = run_arm(mod, "arm0_baseline", {})
    repro_adj = arm0["adjudication"] == published["adjudication"]
    repro_axes = arm0["independence_axes"] == published["independence_axes"]
    findings["arm0"] = {"adjudication": arm0["adjudication"],
                        "axes": arm0["independence_axes"],
                        "matches_committed": bool(repro_adj and repro_axes)}

    # ---- ARM A: is the seat identity read at all? (F1) ----
    touched = []
    for job in jobs:
        try:
            mod.execute_job_on_agent(Tripwire(), job)
        except Tripwire.Touched as e:
            touched.append((job["id"], str(e)))
    # NEGATIVE CONTROL: a worker that does read the seat must trip it.
    try:
        reads_the_agent(Tripwire(), jobs[0])
        tripwire_live = False
    except Tripwire.Touched:
        tripwire_live = True
    # and the same reference worker on a REAL seat must succeed, so the
    # tripwire is what stopped it and not the function being broken.
    ref_on_real_seat = reads_the_agent(mod.ROSTER[0], jobs[0])["digest"][:12]
    findings["armA"] = {"jobs_probed": len(jobs), "seat_reads": len(touched),
                        "tripwire_live": tripwire_live,
                        "ref_on_real_seat_digest": ref_on_real_seat}

    # ---- ARM B: what is the digest a digest OF? (F2) ----
    corpus_jobs = [j for j in jobs if j["type"] == "corpus"]
    s91_digests = [mod.execute_job_on_agent(a, j)["digest"]
                   for j in corpus_jobs for a in mod.ROSTER[:1]]
    per_seat = {j["id"]: len({mod.execute_job_on_agent(a, j)["digest"]
                              for a in mod.ROSTER}) for j in jobs}
    real = []
    for p in sorted(glob.glob(str(M1_OUT / "*.env"))):
        real.append(json.load(open(p))["sorted_hash"])
    findings["armB"] = {
        "s91_corpus_jobs": len(corpus_jobs),
        "s91_distinct_digests": len(set(s91_digests)),
        "real_chain_jobs": len(real),
        "real_chain_distinct_hashes": len(set(real)),
        "real_chain_empty_hash_count": real.count(hashlib.sha256(b"").hexdigest()),
        "max_distinct_digests_per_job_across_5_seats": max(per_seat.values()),
    }

    # ---- ARM C: the frozen pin (F3) ----
    bad = "0" * 64
    armC = run_arm(mod, "armC_wrong_pin", {"PIN_F001": bad})
    findings["armC"] = {"patched_PIN_F001": bad,
                        "adjudication": armC["adjudication"],
                        "identical_to_baseline":
                            armC["adjudication"] == arm0["adjudication"]}

    # ---- ARM D: the independence axes are string cardinality in a literal ----
    fiction = [dict(m, operator_id=f"op_atlantis_seat_{i}", host_id=f"host:atlantis_{i}")
               for i, m in enumerate(mod.ROSTER)]
    armD1 = run_arm(mod, "armD1_fictional_operators", {"ROSTER": fiction})
    collapsed = [dict(m, operator_id="operator:self") for m in mod.ROSTER]
    armD2 = run_arm(mod, "armD2_one_operator", {"ROSTER": collapsed})
    findings["armD"] = {
        "fictional_axes": armD1["independence_axes"],
        "fictional_F3_fired": armD1["falsifiers"]["F3_6axis_violation"]["fired"],
        "collapsed_axes": armD2["independence_axes"],
        "collapsed_F3_fired": armD2["falsifiers"]["F3_6axis_violation"]["fired"],
    }

    # ---- ARM E: the contradiction, resolved MECHANICALLY (§12.4) ----
    floors = FLOORS.read_text()
    binding_line = "operator  1      <- binding" in floors
    # WHITESPACE-NORMALISED, AND THE FIRST FORM DID NOT RESOLVE. A contiguous
    # literal match returned False because the sentence is WRAPPED across a
    # newline in the source ("...without an\nattestation root."). That is
    # MISSION_LOOP 12.4 turned on this probe's own author: I quoted the sentence
    # into CHANNEL.md by eye and the mechanical check refused it. Reported, not
    # buried -- a citation that resolves only after being loosened is a weaker
    # citation, and the LINE above is the one that carries the claim anyway.
    norm = " ".join(floors.split())
    binding_sentence = ("`operator` remains the binding axis at 1 and cannot be "
                        "raised without an attestation root.") in norm
    real_ops = {json.load(open(p))["domains"]["operator"]
                for p in sorted(glob.glob(str(M1_OUT / "*.env")))}
    findings["armE"] = {"floors_line_present": binding_line,
                        "floors_sentence_present": binding_sentence,
                        "real_chain_operator_strings": sorted(real_ops),
                        "s91_operator_axis": published["independence_axes"]["operator"]}

    # ---------------------------- controls ----------------------------
    c1 = Control("C1_reproduces_S91", why="arm0 must reproduce S91's committed "
                 "adjudication and axes through S91's own main()",
                 can_fail_because="any drift between run.py and result.json, or "
                 "a patch of mine leaking across arms, makes them differ",
                 null_must_contain="an arm0 whose numbers differ from the "
                 "committed result.json")
    c1.observe(repro_adj and repro_axes,
               {"committed": published["adjudication"], "arm0": arm0["adjudication"],
                "axes_match": repro_axes})

    c2 = Control("C2_tripwire_is_live", why="the negative control must trip the "
                 "same tripwire, or arm A's silence is an inert probe",
                 can_fail_because="a Tripwire that raised on nothing would let "
                 "reads_the_agent() return normally",
                 null_must_contain="a worker that reads agent['binary'] and is "
                 "not caught")
    c2.observe(tripwire_live, {"reader_tripped": tripwire_live,
                               "same_reader_on_real_seat_ok": bool(ref_on_real_seat)})

    c3 = Control("C3_axis_audit_responds", why="collapsing the operator strings "
                 "to one must move the axis and fire S91's own F3, or arm D1 "
                 "shows nothing -- an audit that never moves is not an audit",
                 can_fail_because="an axis count hard-wired to 5 would report 5 "
                 "for the collapsed roster too",
                 null_must_contain="a collapsed roster still reporting operator=5")
    c3.observe(armD2["independence_axes"]["operator"] == 1
               and armD2["falsifiers"]["F3_6axis_violation"]["fired"],
               {"fictional_operator_axis": armD1["independence_axes"]["operator"],
                "collapsed_operator_axis": armD2["independence_axes"]["operator"]})

    # --------------------------- falsifiers ---------------------------
    f1 = Falsifier("F1_seat_is_read",
                   refutes="that S91's five seats are one computation",
                   fires_when="execute_job_on_agent reads its `agent` argument "
                   "for any of the 74 jobs",
                   null_must_contain="a seat read on at least one job")
    f1.observe(len(touched) > 0, {"jobs_probed": len(jobs),
                                  "seat_reads": len(touched),
                                  "tripwire_live": tripwire_live})

    f2 = Falsifier("F2_digest_is_a_result",
                   refutes="that S91 hashes job INPUTS rather than reduction "
                   "RESULTS",
                   fires_when="S91's corpus digests are not ~injective on "
                   "source, or the real chain's committed hashes do not collapse",
                   null_must_contain="a real chain whose distinct-hash count "
                   "equals its job count")
    f2.observe(not (len(set(s91_digests)) == len(corpus_jobs)
                    and len(set(real)) < len(real)),
               {"s91_distinct": len(set(s91_digests)), "s91_jobs": len(corpus_jobs),
                "real_distinct": len(set(real)), "real_jobs": len(real)})

    f3 = Falsifier("F3_pin_is_checked",
                   refutes="that F001/F002 'pin match' is expected == expected",
                   fires_when="patching PIN_F001 to a wrong value moves "
                   "valid_accepted or divergences",
                   null_must_contain="an adjudication that differs under a "
                   "wrong pin")
    f3.observe(armC["adjudication"] != arm0["adjudication"],
               {"baseline": arm0["adjudication"], "wrong_pin": armC["adjudication"]})

    res = {"spike": "H188", "target": "spikes/S91_multi_agent_quorum",
           "findings": findings,
           "controls": {c.name: {"fired": c.fired} for c in (c1, c2, c3)},
           "falsifiers": {f.name: {"fired": f.fired} for f in (f1, f2, f3)}}
    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    for k, v in findings.items():
        print(f"{k}: {json.dumps(v)}")
    print()
    for c in (c1, c2, c3):
        print(f"  {c.name}: fired={c.fired}")
    for f in (f1, f2, f3):
        print(f"  {f.name}: fired={f.fired}")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(S91_DIR)],
        artifacts=[str(out_json)],
        controls=[c1, c2, c3], falsifiers=[f1, f2, f3],
        captures=[("result_json", json.dumps(res, sort_keys=True)),
                  ("arm0_stdout", (ARMS / "arm0_baseline" / "stdout.txt").read_text())],
        falsifier="S91's worker reads its seat, or its pin is really compared, "
                  "or its axis audit measures something observed",
        allow_dirty=True,
        note="H188: attack on S91 -- five seats, one computation.")
    print(f"\ncertify ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
