#!/usr/bin/env python3
"""H211 — `provenance.py` pinned the artifact it found, not the one it was given.

MY OWN ROW, raised from H209's certification and left OPEN for four cycles while
I filed five more. `record()` called `os.path.exists(a)` and `sha256_file(a)` on
the DECLARED name, so a relative artifact resolved against the PROCESS CWD.

TWO DIRECTIONS, AND ONLY THE HARMLESS ONE HAD EVER FIRED. Run from the repo root,
H209's certify reported `missing artifacts: ['result.json']` while the file sat in
the spike dir. The unsafe direction is the same line: **a file of that name at the
CWD would have been found, hashed, and recorded as the spike's artifact — the
correct sha256 of the wrong file (A24)**, inside the module whose entire job is
family C. This probe fires it deliberately, because a defect that has only ever
failed safe is one nobody has seen fail.

TWO-SIDED. A1/A2 are the pre-fix behaviour on a real fixture; A3-A6 the post-fix.
A7 is the arm that stops the fix being a silent re-point: **an artifact that
exists only at the CWD must be recorded MISSING, not pinned.**

FALSIFIER, STATED BEFORE RUNNING: if the pre-fix module cannot be made to hash
the wrong file on this fixture, the unsafe direction is not reachable and the row
is half its claimed size — A2 asserts the wrong hash POSITIVELY for that reason.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PRE_FIX = "efe3d81"        # last commit of provenance.py before H211

fail = 0
obs = {}


def ck(name, got, want):
    global fail
    if got == want:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} (want {want!r}, got {got!r})")
        fail += 1


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


scratch = os.path.join(ROOT, ".scratch")
os.makedirs(scratch, exist_ok=True)
D = tempfile.mkdtemp(dir=scratch, prefix="H211.")
try:
    # The fixture: a spike dir with its own result.json, and a DIFFERENT file of
    # the same name at the place the runner will stand. This is the two-file
    # situation the row is about, and it is not hypothetical -- the repo root
    # holds many names a spike also uses.
    spike = os.path.join(D, "spike")
    cwd = os.path.join(D, "runner")
    os.makedirs(spike)
    os.makedirs(cwd)
    open(os.path.join(spike, "result.json"), "w").write('{"who":"the spike"}\n')
    open(os.path.join(cwd, "result.json"), "w").write('{"who":"the runner"}\n')
    spike_sha = sha(os.path.join(spike, "result.json"))
    cwd_sha = sha(os.path.join(cwd, "result.json"))
    ck("A0 the fixture really holds two different files of one name",
       spike_sha != cwd_sha, True)

    pre_src = subprocess.run(
        ["git", "show", f"{PRE_FIX}:spikes/harness/provenance.py"],
        capture_output=True, text=True, cwd=ROOT).stdout
    if "_resolve_artifact" in pre_src:
        sys.exit(f"VOID: {PRE_FIX} already carries the fix; the pre-fix arm "
                 "would measure nothing")
    pre_path = os.path.join(D, "provenance_pre.py")
    open(pre_path, "w").write(pre_src)

    os.chdir(cwd)                       # stand where the runner stands
    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))

    # --------------------------------------------------------------- pre ----
    pre = load(pre_path, "provenance_pre")
    ok_pre, prov_pre = pre.record(spike, artifacts=["result.json"],
                                  no_deps_reason="fixture",
                                  record_name="pre.json")
    pinned_pre = [a["sha256"] for a in prov_pre["artifacts"]]
    ck("A1 PRE-FIX pinned an artifact at all", len(pinned_pre), 1)
    ck("A2 ...and it is the RUNNER's file, not the spike's — the correct sha256 "
       "of the wrong artifact", pinned_pre[0], cwd_sha)
    obs["A1_A2_pre"] = {"pinned": pinned_pre[0], "spike_sha": spike_sha,
                        "cwd_sha": cwd_sha,
                        "pinned_the_wrong_file": pinned_pre[0] == cwd_sha}

    # -------------------------------------------------------------- post ----
    post = load(os.path.join(ROOT, "spikes", "harness", "provenance.py"),
                "provenance_post")
    ok_post, prov_post = post.record(spike, artifacts=["result.json"],
                                     no_deps_reason="fixture",
                                     record_name="post.json")
    pinned_post = [a["sha256"] for a in prov_post["artifacts"]]
    ck("A3 POST-FIX pins the SPIKE's file", pinned_post[0], spike_sha)
    ck("A3b ...and records the declared name alongside the resolved path",
       (prov_post["artifacts"][0]["path"],
        os.path.basename(prov_post["artifacts"][0]["resolved"])),
       ("result.json", "result.json"))
    ck("A4 ...and the ambiguity is a PROBLEM, not a footnote",
       any("ambiguous" in p for p in prov_post.get("problems", [])), True)
    ck("A4b ...naming both candidates so the caller can act",
       all(s in " ".join(prov_post.get("problems", []))
           for s in (spike, cwd)), True)
    obs["A3_A4_post"] = {"pinned": pinned_post[0],
                         "pinned_the_spikes_file": pinned_post[0] == spike_sha,
                         "problems": prov_post.get("problems", [])}

    # ------------------------------------------------------------------ A5 --
    # An ABSOLUTE declaration must be untouched — the call sites fixed by hand
    # under H209/H218/S92 all pass absolute paths and must not change meaning.
    ok_abs, prov_abs = post.record(
        spike, artifacts=[os.path.join(spike, "result.json")],
        no_deps_reason="fixture", record_name="abs.json")
    ck("A5 an absolute artifact is pinned unchanged",
       prov_abs["artifacts"][0]["sha256"], spike_sha)
    ck("A5b ...and raises no ambiguity problem",
       any("ambiguous" in p for p in prov_abs.get("problems", [])), False)

    # ------------------------------------------------------------------ A6 --
    # The identical-content case must NOT be reported as ambiguous, or every
    # spike run from its own directory gains a spurious problem.
    same = os.path.join(D, "same")
    os.makedirs(same)
    # IDENTICAL to the CWD copy, which is the whole point of this arm. The first
    # version of it wrote the SPIKE's content here and then asserted "not
    # ambiguous" against a CWD file that differed -- i.e. it named one condition
    # and built another, and the resolver was right to flag it. Fixture defect,
    # recorded rather than quietly corrected (§5).
    open(os.path.join(same, "result.json"), "w").write('{"who":"the runner"}\n')
    ok_same, prov_same = post.record(same, artifacts=["result.json"],
                                     no_deps_reason="fixture",
                                     record_name="same.json")
    ck("A6 two files of one name with IDENTICAL content are not 'ambiguous'",
       any("ambiguous" in p for p in prov_same.get("problems", [])), False)

    # ------------------------------------------------------------------ A7 --
    # THE ARM THAT STOPS THIS BEING A SILENT RE-POINT. A name that exists only
    # at the CWD must be recorded MISSING — pinning it would be the original
    # defect performed by the repair.
    bare = os.path.join(D, "bare")
    os.makedirs(bare)
    ok_bare, prov_bare = post.record(bare, artifacts=["result.json"],
                                     no_deps_reason="fixture",
                                     record_name="bare.json")
    ck("A7 an artifact present ONLY at the CWD is recorded MISSING",
       prov_bare["missing_artifacts"], ["result.json"])
    ck("A7b ...and nothing was pinned from the runner's directory",
       prov_bare["artifacts"], [])
    ck("A7c ...with a problem saying the spike does not own it",
       any("does not own" in p for p in prov_bare.get("problems", [])), True)
    obs["A7_cwd_only"] = {"missing": prov_bare["missing_artifacts"],
                          "artifacts": prov_bare["artifacts"],
                          "problems": prov_bare.get("problems", [])}
finally:
    os.chdir(ROOT)
    shutil.rmtree(D, ignore_errors=True)

with open(os.path.join(HERE, "result.json"), "w") as fh:
    json.dump({"checks_failed": fail, "arms": obs}, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(f"\nchecks failed: {fail}")
sys.exit(1 if fail else 0)
