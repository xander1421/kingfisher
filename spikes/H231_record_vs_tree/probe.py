#!/usr/bin/env python3
# probe.py v1 — H231, ok-1, 2026-08-19.
"""H231 · a metric that scores the COMMITTED RECORD, computed from the WORKING TREE.

Five arms. Each prints FIRED / did-not-fire against a prediction recorded in
RESULT.md BEFORE this file was run. No seed is needed: every arm is either a
pure function of its own literals or a subprocess of a checker in this tree,
and the two that touch git build their own repository under `.scratch/`.

Run:  python3 spikes/H231_record_vs_tree/probe.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, ".github", "autoloop", "evaluators"))
import eval_hygiene as EH  # noqa: E402

SCRATCH = os.path.join(ROOT, ".scratch", "h231_probe")   # §10: inside the workspace
results = []


def arm(name, fired, detail):
    results.append((name, fired, detail))
    print(f"  {'FIRED        ' if fired else 'did not fire '} {name}: {detail}")


def a1_reachable():
    """F1a · can a real checker refuse with NOTHING on stdout?

    journalcheck.py resolves ROOT as `<its own dir>/../..`, so a copy placed two
    directories deep under a root with no WORK_QUEUE.md exercises its real
    refusal path -- the module is not modified and nothing is stubbed.
    """
    d = os.path.join(SCRATCH, "fakeroot", "spikes", "harness")
    shutil.rmtree(os.path.join(SCRATCH, "fakeroot"), ignore_errors=True)
    os.makedirs(d)
    shutil.copy(os.path.join(ROOT, "spikes", "harness", "journalcheck.py"), d)
    p = subprocess.run([sys.executable, os.path.join(d, "journalcheck.py")],
                       capture_output=True, text=True)
    refused_silently = p.returncode != 0 and p.stdout.strip() == ""
    arm("F1a real checker refuses with empty stdout",
        refused_silently,
        f"rc={p.returncode} stdout={p.stdout.strip()!r} "
        f"stderr[:40]={p.stderr.strip()[:40]!r}")
    return refused_silently


def a2_consequence():
    """F1b · does that (rc, stdout) pair publish CLEAN under v2's rule?

    v2 is reconstructed here from its two committed properties -- stdout only,
    and escalate githygiene alone -- rather than checked out, so the arm keeps
    working after v2 is gone from the tree.
    """
    def v2(ref, jnl, git, dirty):
        ok_r, out_r = ref
        ok_j, out_j = jnl
        vio = (EH.attribute("refcheck", out_r if not ok_r else "", dirty) +
               EH.attribute("journalcheck", out_j if not ok_j else "", dirty))
        verdict = ("CLEAN" if not vio else
                   "VIOLATED" if any(v["in_record"] for v in vio) else
                   "NOT_MEASURED")
        if not git[0] and verdict != "VIOLATED":
            verdict = "VIOLATED"
        return verdict

    silent_refusal = {"refcheck": (True, ""), "journalcheck": (False, ""),
                      "githygiene": (True, "")}
    old = v2(silent_refusal["refcheck"], silent_refusal["journalcheck"],
             silent_refusal["githygiene"], set())
    new, _ = EH.record_verdict(silent_refusal, set())
    arm("F1b v2 published CLEAN for it, v3 does not",
        old == "CLEAN" and new == "VIOLATED", f"v2={old} v3={new}")
    return old == "CLEAN" and new == "VIOLATED"


def a3_githygiene_hole():
    """F3 · did githygiene have the same hole in v2? (predicted: no.)"""
    silent_git = {"refcheck": (True, ""), "journalcheck": (True, ""),
                  "githygiene": (False, "")}
    new, _ = EH.record_verdict(silent_git, set())
    arm("F3 githygiene had the hole too", new != "VIOLATED",
        f"v2 escalated it at the call site; v3 rule gives {new}")
    return new != "VIOLATED"


def a4_refusal_vocabulary():
    """F4 · does refcheck gate on a marker outside {UNRESOLVED}?

    Read from the module, not from memory: every `print` that reaches stdout on
    a refusing run. `KNOWN ROW SHAPE` is printed on GREEN runs too, which is why
    it is not a refusal marker and why v3 gates it only when rc != 0.
    """
    src = open(os.path.join(ROOT, "spikes", "harness", "refcheck.py"),
               encoding="utf-8").read()
    body = src[:src.index("def selfcheck")] if "def selfcheck" in src else src
    markers = set()
    for line in body.split("\n"):
        t = line.strip()
        if t.startswith("print(") and "'  " in t.replace('"', "'"):
            frag = t.replace('"', "'").split("'  ", 1)[1]
            word = frag.split()[0].strip("{}':,+")
            if word.isupper() and len(word) > 3:
                markers.add(word)
    unknown = markers - {"UNRESOLVED", "KNOWN"}
    arm("F4 refcheck gates on a marker v3 cannot parse", bool(unknown),
        f"stdout markers={sorted(markers)} unhandled={sorted(unknown)}")
    return bool(unknown)


def a5_live_verdict():
    """F5 · does v3 change the verdict on the live tree? (predicted: no.)

    The live refusal today attributes to a dirty file, so NOT_MEASURED must
    survive the fix. A fix that also moved today's number would be indis-
    tinguishable from a fix that only moved today's number.
    """
    p = subprocess.run([sys.executable,
                        os.path.join(ROOT, ".github", "autoloop",
                                     "evaluators", "eval_hygiene.py")],
                       capture_output=True, text=True, cwd=ROOT)
    import json
    d = json.loads(p.stdout)
    v = d["hygiene_record_verdict"]
    arm("F5 v3 moved the live verdict", v not in ("NOT_MEASURED", "CLEAN"),
        f"verdict={v} score={d['hygiene_score']} dirty={d['tree_dirty']} "
        f"violations={d['hygiene_violations']}")
    return v not in ("NOT_MEASURED", "CLEAN")


def main():
    print("H231 probe — arms and their PREREGISTERED predictions in RESULT.md\n")
    a1 = a1_reachable()
    a2 = a2_consequence()
    a3 = a3_githygiene_hole()
    a4 = a4_refusal_vocabulary()
    a5 = a5_live_verdict()
    shutil.rmtree(SCRATCH, ignore_errors=True)
    print("\nsummary: F1a=%s F1b=%s F3=%s F4=%s F5=%s" %
          tuple("FIRED" if x else "no" for x in (a1, a2, a3, a4, a5)))
    # The finding needs BOTH halves of F1: reachable precondition AND the
    # wrong verdict. Either alone is an argument rather than a defect.
    return 0 if (a1 and a2) else 1


if __name__ == "__main__":
    sys.exit(main())
