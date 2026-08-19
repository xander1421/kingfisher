#!/usr/bin/env python3
"""H218 — `carries_repair()` operated on an object it never identified.

ROUTED, NOT FOUND (A22). ok-1 attacked the remedy this lane shipped one cycle
earlier as H209 and measured it on the SHIPPED file rather than a copy. The
sentence of mine that was false is quoted in `carries_repair.sh` v2's rationale
block and is not paraphrased here.

THE CONTROLS ARE THE PROBE'S, RE-RUN RATHER THAN QUOTED. `probe.sh` is the
instrument; this file records what it said. Each arm emits `OBS <C> <json>`
carrying the values it compared, so a control whose numbers do not arrive leaves
this run VOID instead of quietly green — H209's own second-pass lesson, one row
old and mine.

WHAT WOULD HAVE MADE THE FIX MEANINGLESS, AND IS THEREFORE A CONTROL: the fix
could be achieved by making the function DEAD (C1 catches that), or the fixture
could fail to stage the interleave at all, in which case the post-fix green
measures nothing (C2 catches that, and it is asserted POSITIVE for that reason).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
from kfcheck import certify, Control  # noqa: E402

probe = subprocess.run(["sh", os.path.join(HERE, "probe.sh")],
                       capture_output=True, text=True, cwd=ROOT)
text = probe.stdout + probe.stderr
print(text)

obs = {}
for line in text.splitlines():
    if line.startswith("OBS "):
        _, name, blob = line.split(" ", 2)
        obs[name] = json.loads(blob)

missing = [c for c in ("C1", "C2", "C3", "C7") if c not in obs]
if missing:
    sys.exit(f"VOID: probe emitted no observation for {missing}; "
             "the arms did not run, so nothing below is evidence")

c1 = Control(
    "C1_healthy_case_still_fires",
    why="the whole fix could be obtained by making the function do nothing at "
        "all, and every interleaved arm would then be green on a corpse",
    can_fail_because="a refusal placed too early — before the trailer is "
                     "computed — leaves an own-lane commit with no `Carries:` "
                     "and C1 goes red",
    null_must_contain="a healthy own-lane run producing no trailer")
c1.observe(obs["C1"]["trailer_on_own_commit"] != ""
           and obs["C1"]["atom_at_head"] == "AGENT-1", obs["C1"])

c2 = Control(
    "C2_defect_reproduces_pre_fix",
    why="the fixture must actually stage the interleave. If the PRE-FIX "
        "function leaves lane B's commit alone here, the defect was never "
        "reproduced and the post-fix green measures nothing",
    can_fail_because="a fixture whose second commit lands after the repair, or "
                     "one whose foreign lines are absent so the trailer is "
                     "empty and v1 returns early, would show `unchanged`",
    null_must_contain="a pre-fix run leaving HEAD equal to lane B's sha")
c2.observe(obs["C2"]["outcome"] == "rewritten", obs["C2"])

c3 = Control(
    "C3_post_fix_leaves_colane_commit_alone",
    why="the claim of this row is exactly this and nothing wider",
    can_fail_because="dropping the identity assertion — the first v2 draft did, "
                     "and this arm came back `rewritten`, which is how that "
                     "draft was refuted",
    null_must_contain="a post-fix run whose HEAD differs from lane B's sha")
c3.observe(obs["C3"]["outcome"] == "unchanged", obs["C3"])

c7 = Control(
    "C7_compare_and_swap_primitive",
    why="`the function refused` can be true for the wrong reason. The swap "
        "rests on `git update-ref <ref> <new> <old>` rejecting a stale <old>, "
        "so that primitive is asserted directly, in BOTH directions",
    can_fail_because="a git that ignored the expected-value argument would "
                     "accept the stale one, and a broken invocation would "
                     "refuse both — the second arm separates those",
    null_must_contain="update-ref accepting a stale expected value")
c7.observe(obs["C7"]["stale_expected_value"] == "refused"
           and obs["C7"]["current_expected_value"] == "accepted", obs["C7"])

ok, problems = certify(
    HERE,
    deps=["spikes/harness"],
    # ABSOLUTE, per H211: `record()` resolves artifacts against the PROCESS CWD,
    # not against spike_dir, so a bare name reads as MISSING from the repo root.
    artifacts=[os.path.join(HERE, "result.json")],
    controls=[c1, c2, c3, c7],
    captures=[("probe_stdout", text)],
    falsifier=(
        "Either of two results would have refuted this row's claim, and both "
        "are arms rather than prose: (a) the post-fix run still rewriting the "
        "co-lane commit — C3 `rewritten`, which is what the FIRST v2 draft "
        "actually returned and why the identity assertion exists; or (b) the "
        "post-fix run refusing everything, including its own lane's commit — "
        "C1 empty, the fix obtained by killing the function. Stated before the "
        "run; both ran."),
    note=("The dep subtree `spikes/harness` carries this row's own edit to "
          "`carries_repair.sh` plus co-lane work. If certify refuses on a dirty "
          "dep the refusal is CORRECT and stays recorded: this run is not the "
          "commit it names. Re-run after the commit lands for a clean record."),
)
print(f"\ncertify ok={ok}")
for p in problems:
    print("  " + p)
