#!/usr/bin/env python3
"""H237 — a re-run that could not fail, because it did not run.

ROUTED BY AGENT-3 OVER THE SESSION BUS AND NOT CLAIMED BY THEM. They found
`bayesian_lift.py:293` answering a re-run out of `bayesian_lift.json` with no
`--force`. The half that makes it a soundness problem is 130 lines further down:
`controls[i].observe(res["controls"][...])` where, on the cached path, `res` came
straight out of that same file — so every control certifies the artifact against
itself, and the run prints `D6 Provenance Certified: ok=True` having computed
nothing. Family B (the instrument reports fiction) on A22 (a party supplying the
input to a check on itself).

IT MATTERS NOW BECAUSE 0.2274 IS THE BAR. ATOM-3's `CLAIM G-BAR` names G51's
0.2274 as the best arm that does not consult DEV — the number a new method must
clear. Any lane that "re-ran G51 to check the bar" got a cache read and a green
light.

TWO-SIDED, AND THE PRE-FIX SIDE IS AN A/B ON THE SAME FIXTURE: HEAD's script and
the working-tree script are both run against a directory that already contains a
`bayesian_lift.json`. Pre-fix must CERTIFY; post-fix must REFUSE. Without the
pre-fix arm, "post-fix refuses" cannot be distinguished from "post-fix is broken".

FALSIFIER, STATED BEFORE THE RUN: if the forced re-run does NOT reproduce
0.2274, this row is not about caching at all and gets much larger — A4 asserts
the reproduction rather than assuming it.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))          # spikes/
REPO = os.path.abspath(os.path.join(ROOT, ".."))
G51 = os.path.join(ROOT, "G51_bayesian_lift_scoring")
# The fixture must sit DIRECTLY under spikes/, because the script resolves
# `../harness`, `../G36_repro_g34` and `../S52_realkg` relative to its own file.
# TWO fixture dirs, not one, and both directly under `spikes/`. The script
# declares `bayesian_lift.py` in its own `artifacts=[...]`, so a copy named
# `pre.py` certifies ok=False for a FIXTURE reason -- which is how the first
# run of this probe reported A1 red while the transcript plainly showed the
# defect (loaded from cache, reached certify). An arm that goes red for a
# reason other than the one it names is worth no more than one that goes
# green for the wrong reason.
FIX_PRE = os.path.join(ROOT, ".h237_pre")
FIX_POST = os.path.join(ROOT, ".h237_post")

fail = 0
obs = {}


def ck(name, got, want):
    global fail
    if got == want:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} (want {want!r}, got {got!r})")
        fail += 1


# H216's lesson, and it was ok-1's: a killed process never runs its cleanup, so
# clear any stale fixture at START as well as in the finally.
for d in (FIX_PRE, FIX_POST):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    shutil.copy(os.path.join(G51, "bayesian_lift.json"),
                os.path.join(d, "bayesian_lift.json"))
try:
    # PINNED, NOT `HEAD` — and the first draft of this probe said `HEAD`, which
    # is H218's class landing in my own instrument the same evening I fixed it
    # there. Once the fix was committed, `HEAD` WAS the fix, so the "pre-fix" arm
    # ran the post-fix script and A1 reported the defect as absent. A pre-fix arm
    # that silently becomes a second post-fix arm is the worst possible failure
    # for an A/B: it reports the defect gone the moment the fix lands, whether or
    # not the fix works.
    PRE_FIX = "330df18"      # last commit of bayesian_lift.py before H237
    head_src = subprocess.run(
        ["git", "show", f"{PRE_FIX}:spikes/G51_bayesian_lift_scoring/bayesian_lift.py"],
        capture_output=True, text=True, cwd=REPO).stdout
    if "os.path.exists(out_json)" not in head_src:
        sys.exit(f"VOID: {PRE_FIX} does not carry the cache branch this row is "
                 "about; the pre-fix arm would measure nothing")
    open(os.path.join(FIX_PRE, "bayesian_lift.py"), "w").write(head_src)
    shutil.copy(os.path.join(G51, "bayesian_lift.py"),
                os.path.join(FIX_POST, "bayesian_lift.py"))

    def run(d):
        p = subprocess.run([sys.executable, "bayesian_lift.py"], cwd=d,
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    # ------------------------------------------------------------- A1 (pre) --
    rc_pre, out_pre = run(FIX_PRE)
    ck("A1 PRE-FIX (330df18) certifies a run that only READ the file",
       "D6 Provenance Certified: ok=True" in out_pre, True)
    ck("A1b ...and it did load rather than compute",
       "Loaded existing benchmark results" in out_pre, True)
    ck("A1c ...and exits 0, so nothing downstream could notice", rc_pre, 0)
    obs["A1_pre_fix"] = {"rc": rc_pre,
                         "certified": "Certified: ok=True" in out_pre,
                         "loaded_from_cache":
                             "Loaded existing benchmark results" in out_pre}

    # ------------------------------------------------------------ A2 (post) --
    rc_post, out_post = run(FIX_POST)
    ck("A2 POST-FIX refuses to certify a cache read",
       "D6 Provenance: REFUSED" in out_post, True)
    ck("A2b ...and certifies nothing at all",
       "Certified: ok=True" in out_post, False)
    ck("A2c ...and exits NONZERO, so a caller can act on it", rc_post, 2)
    ck("A2d ...while still printing the numbers, because reading them is fine",
       "MRR=" in out_post, True)
    obs["A2_post_fix"] = {"rc": rc_post,
                          "refused": "D6 Provenance: REFUSED" in out_post,
                          "certified": "Certified: ok=True" in out_post}

    # ------------------------------------------------------------------ A3 ---
    # THE MECHANISM, not just the outcome: on the cached path the values fed to
    # `Control.observe` are read out of the artifact being certified. Assert the
    # identity rather than describing it.
    cached = json.load(open(os.path.join(FIX_PRE, "bayesian_lift.json")))
    ctrl_keys = sorted(cached.get("controls", {}))
    fals_keys = sorted(cached.get("falsifiers", {}))
    ck("A3 the artifact carries the very control verdicts the run observes",
       len(ctrl_keys) > 0 and len(fals_keys) > 0, True)
    ck("A3b ...and all of them say ok, so self-certification is always green",
       all(cached["controls"][k].get("ok") for k in ctrl_keys), True)
    obs["A3_self_observation"] = {"controls_in_artifact": ctrl_keys,
                                  "falsifiers_in_artifact": fals_keys}

    # ------------------------------------------------------------------ A4 ---
    # F3: the forced re-run must reproduce 0.2274, or this row is not about
    # caching. Compares the CURRENT artifact (written by `--force`) against the
    # copy taken before that run.
    before_p = os.path.join(REPO, ".scratch", "g51_before.json")
    if os.path.exists(before_p):
        before = json.load(open(before_p))
        after = json.load(open(os.path.join(G51, "bayesian_lift.json")))

        def arms(d):
            return {k: round(v["mrr"], 4) for k, v in d.get("arms", {}).items()
                    if isinstance(v, dict) and "mrr" in v}
        a_before, a_after = arms(before), arms(after)
        ck("A4 the forced re-run reproduces every arm's MRR", a_after, a_before)
        ck("A4b ...and the arm ATOM-3's G-BAR calls THE REAL BAR is 0.2274",
           max(a_after.values()) >= 0.2274, True)
        obs["A4_reproduction"] = {"arms_before": a_before, "arms_after": a_after}
    else:
        print("SKIP A4 — no pre-force copy at .scratch/g51_before.json; the "
              "reproduction arm did not run and is NOT reported as passing")
        obs["A4_reproduction"] = {"ran": False}
finally:
    for d in (FIX_PRE, FIX_POST):
        shutil.rmtree(d, ignore_errors=True)

with open(os.path.join(HERE, "result.json"), "w") as fh:
    json.dump({"checks_failed": fail, "arms": obs}, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(f"\nchecks failed: {fail}")
sys.exit(1 if fail else 0)
