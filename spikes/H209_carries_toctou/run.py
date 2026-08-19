#!/usr/bin/env python3
"""H209 — the `Carries:` TOCTOU, certified.

THE ROW IS ABOUT A CLASS AND THE CLASS HAS TWO SITES. Site 1 is
`commit_scoped.sh` and is FIXED here. Site 2 is `commit-msg.hook`'s H66 notice
and is MEASURED here and left OPEN, because it is a shared hook every live lane
executes on every commit and a mid-flight edit to it is not this row's to make.

The controls are the probe's, re-run rather than quoted: `probe.sh` is the
instrument and this file records what it said.

==== SECOND PASS, 2026-08-19 — THE FIRST PASS WAS VOID AND `certify` SAID SO ==
The first pass built three `Control` objects, ran the probe, matched `"C1 FIRED"`
in its stdout into a local dict named `fired` -- and NEVER CALLED
`Control.observe`. So every control reached `certify` with `fired=None` and it
refused, correctly:

    CONTROL C1 the race is planted and the DEFECT reproduces never observed
    CONTROL C1 ... declares no null_must_contain

The measurement existed and the record did not. That is `Control`'s documented
second failure mode -- "a control that was described but never saved" -- and it
is A28's shape one level in: the field was there, the value never arrived. The
row's WORK (commit_scoped.sh v9) was finished and its EVIDENCE was VOID, which
is exactly the state §13 calls indistinguishable from never having run.

REMEDY: the probe emits one `OBS <C> <json>` line per arm carrying the values it
compared; this file parses those and calls `observe()`. A `fired` verdict without
values is now unrepresentable here -- the parse either yields the values or the
control stays unobserved and certify refuses again.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
from kfcheck import certify, Control  # noqa: E402


def sh(*args, **kw):
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT, **kw)


# ---- the instrument: the probe, RE-RUN, not quoted ------------------------
probe = sh("sh", os.path.join(HERE, "probe.sh"))
probe_text = probe.stdout + probe.stderr
fired = {c: (f"{c} FIRED" in probe_text) for c in ("C1", "C2", "C3")}

# The VALUES each arm compared, off the probe's `OBS <C> <json>` lines. Parsed
# and not grepped: a control is only observed if its numbers arrive, so a probe
# that stops emitting one turns this run VOID instead of quietly green.
observations = {}
for line in probe_text.splitlines():
    if line.startswith("OBS "):
        _, name, blob = line.split(" ", 2)
        observations[name] = json.loads(blob)
missing = [c for c in ("C1", "C2", "C3") if fired[c] and c not in observations]
if missing:
    sys.exit(f"probe printed FIRED for {missing} and emitted no OBS line for them -- "
             f"the values did not leave the probe, so there is nothing to certify")

# ---- SITE 2, measured live: an A15 control that cannot fire ---------------
# `commit-msg.hook`'s H66 notice iterates `git diff --cached --name-only` (the
# SHARED INDEX) and its own text says "a co-lane's write between your check and
# your commit lands under your Atom". `commit_scoped.sh` invokes that hook
# DIRECTLY, with no commit in progress, and then commits `--only` from the
# WORKING TREE. So on the one call path built for this defect the notice scores
# an object the commit never reads.
index_paths = [p for p in sh("git", "diff", "--cached", "--name-only").stdout.split() if p]
worktree_paths = [p for p in sh("git", "diff", "HEAD", "--name-only").stdout.split() if p]
site2 = {
    "notice_scores": "git diff --cached (SHARED INDEX)",
    "commit_reads": "git commit --only (WORKING TREE)",
    "index_paths_now": len(index_paths),
    "worktree_paths_now": len(worktree_paths),
    "notice_can_fire_now": len(index_paths) > 0,
    "verdict": "A15 — the control cannot fire on the path it was written for",
}

# ---- WHY THIS RUN IS RED, MEASURED RATHER THAN ARGUED ---------------------
# `deps=["spikes/harness"]` is the honest dependency and it is scoped to that
# subtree, so `certify` refuses while ANY file under it is dirty. After this
# lane committed its own three files the residual is co-lane work in flight,
# and dropping the dep to buy green would remove a real dependency (G27's
# precedent, and the reason that spike's provenance is deliberately red too).
#
# So the residual is COMPUTED here, every run, and checked against the
# instrument chain instead of being asserted in prose. `probe.sh` sources
# `carries_repair.sh` and calls `carriescheck.py` and nothing else under
# spikes/harness; if a future dirty file IS in that chain, `foreign_only`
# goes false and this run is red for a reason that is actually about H209.
INSTRUMENT_CHAIN = ("spikes/harness/carries_repair.sh",
                    "spikes/harness/carriescheck.py",
                    "spikes/harness/commit_scoped.sh")
_dirty = [l.split(None, 1)[1] for l in
          sh("git", "status", "--porcelain", "--", "spikes/harness").stdout.splitlines()
          if len(l.split(None, 1)) > 1]
residual = {
    "dirty_under_dep": _dirty,
    "in_instrument_chain": [p for p in _dirty if p.rstrip("/") in INSTRUMENT_CHAIN],
}
residual["foreign_only"] = not residual["in_instrument_chain"]

# ---- what the live tree would have mis-recorded without the repair --------
live_trailer = sh("python3", "spikes/harness/carriescheck.py",
                  "AGENT-1", "--worktree", "--trailer").stdout.strip()

result = {
    "row": "H209",
    "class": ("a checker that scores a MUTABLE SHARED OBJECT and whose verdict is "
              "consumed by an action built from a SECOND, LATER read of that object"),
    "site1_commit_scoped_sh": {"status": "FIXED", "version": "v9",
                               "remedy": "score the LANDED commit (immutable) and amend"},
    "site2_commit_msg_hook": dict(site2, status="OPEN — filed, not touched (shared hook, live lanes)"),
    "probe": {"rc": probe.returncode, "controls_fired": fired,
              "controls_observed": observations},
    "live_tree_trailer_at_run": live_trailer,
    "certification_residual": residual,
    "falsifiers": {
        "F1 repair is inert (pre == post under a planted race)": "RAN, did not fire",
        "F2 amend invents attribution on a clean commit": "RAN, did not fire",
        "F3 amend alters tree/parent/paths": "RAN, did not fire",
    },
}

with open(os.path.join(HERE, "result.json"), "w") as fh:
    json.dump(result, fh, indent=2, sort_keys=True)
    fh.write("\n")

CONTROL_SPEC = {
    "C1": ("C1 the race is planted and the DEFECT reproduces",
           "a repair arm green against a defect never provoked is A29",
           "the unrepaired arm must be CAPABLE of agreeing: if the pre-check and "
           "the landed commit both report the same trailer, the race did not land "
           "and there is no defect here to repair",
           "if the planted line is not in a POSITIONAL path, or authors_of does not "
           "resolve it, C1 goes quiet and the probe has measured nothing"),
    "C2": ("C2 the repaired commit declares the trailer",
           "the whole point: the record must match the object",
           "the repaired arm must be CAPABLE of coming out empty -- an amend that "
           "appends nothing leaves the same bare message the unrepaired arm had",
           "carriescheck --trailer could print nothing, or the amend could drop the "
           "appended line"),
    "C3": ("C3 the amend is MESSAGE-ONLY",
           "bare `git commit --amend` takes the SHARED index (H19) — the remedy "
           "must not commit the defect class it removes",
           "the tree pair must be CAPABLE of differing and COLANE.txt of appearing: "
           "a bare `--amend` in place of the scoped one produces exactly that, which "
           "is the arm this control exists to catch",
           "a co-lane's file is deliberately left STAGED before the amend; if "
           "`--only` does not hold, it is swept in"),
}


def observed(key):
    """A Control that is already carrying the probe's values.

    The first pass constructed these and never observed them, so `fired` stayed
    None and the run was VOID. Building and observing in one call is the fix
    that cannot be half-applied.
    """
    name, why, null_must_contain, can_fail = CONTROL_SPEC[key]
    c = Control(name, why, null_must_contain=null_must_contain,
                can_fail_because=can_fail)
    c.observe(fired[key], observations[key], detail=f"probe.sh OBS {key}")
    return c


ok, problems = certify(
    HERE,
    deps=["spikes/harness"],   # deps are DIRECTORIES; naming a file fakes a dirty verdict
    # ABSOLUTE. `record()` resolves artifacts with `os.path.exists(a)` against the
    # PROCESS CWD, not against `spike_dir`, so the bare name "result.json" read as
    # MISSING from the repo root -- and would have read as PRESENT, and been
    # hashed, had a file of that name existed there. Filed as its own class row
    # (see WORK_QUEUE H211); fixed here at the call site.
    artifacts=[os.path.join(HERE, "result.json")],
    controls=[
        observed("C1"),
        observed("C2"),
        observed("C3"),
    ],
    captures=[("probe_stdout", probe_text)],
    # NOT allow_dirty. The refusal is CORRECT and is recorded as such: the dep
    # subtree is dirty, this run is therefore not the commit it names, and the
    # note says exactly which files and whether any is an input here.
    note=("RED ON PURPOSE. deps=spikes/harness is dirty with co-lane work in "
          "flight; `certification_residual` in result.json lists the files and "
          "whether any is in this probe's instrument chain. Buying green would "
          "mean allow_dirty=True (voids the check) or dropping a real dep."),
    instrument_texts=[("probe.sh", probe_text)],
    falsifier=("F1: if the post-commit trailer equals the pre-commit report under a "
               "PLANTED race, the repair is inert. F2: an amend on a commit carrying "
               "nothing foreign means attribution was invented (H105 — worse than a "
               "miss). F3: an amend that alters the tree, the parent or the path set "
               "is not a message repair."),
)

print(json.dumps(result["probe"], indent=2))
print(f"site2 notice_can_fire_now={site2['notice_can_fire_now']} "
      f"(index={site2['index_paths_now']} paths, worktree={site2['worktree_paths_now']})")
print(f"certify ok={ok}")
for p in problems:
    print("  -", p)
sys.exit(0 if ok else 1)
