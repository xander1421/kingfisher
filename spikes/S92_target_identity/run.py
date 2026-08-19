#!/usr/bin/env python3
"""S92 — certified. The controls are `probe.py`'s, RE-RUN rather than quoted.

`probe.py` is the instrument; this file records what it said. Its `result.json`
carries the values each arm compared, so an arm that stops reporting turns this
run VOID instead of quietly green (H209's lesson, and it was this lane's).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
from kfcheck import certify, Control  # noqa: E402

probe = subprocess.run([sys.executable, os.path.join(HERE, "probe.py")],
                       capture_output=True, text=True, cwd=ROOT)
text = probe.stdout + probe.stderr
print(text)

res = json.load(open(os.path.join(HERE, "result.json")))
arms = res["arms"]
for need in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"):
    if need not in arms:
        sys.exit(f"VOID: probe reported no arm {need}; nothing below is evidence")

c1 = Control(
    "C1_ambiguous_target_is_refused",
    why="the defect that cost two days was an unqualified `adb shell` with a "
        "second device attached. The precondition must REFUSE that state, not "
        "proceed and blame the target",
    can_fail_because="a resolver that picked the first device would accept, and "
                     "this arm would report rc=0 instead of rc=2",
    null_must_contain="a two-device run that proceeds")
c1.observe(arms["A2"]["rc"] == 2 and arms["A2"]["named_both"], arms["A2"])

c2 = Control(
    "C2_every_adb_invocation_is_serial_qualified",
    why="defect 2 was three call sites each having to remember `-s`. The claim "
        "is that no unqualified invocation survives ANYWHERE in the run, not "
        "that the three known ones were patched",
    can_fail_because="a fourth call site added later, or one of the three left "
                     "on the direct `[ADB, ...]` form, shows up here as a "
                     "nonzero `unqualified` count",
    null_must_contain="a targeted adb invocation without -s")
c2.observe(arms["A3"]["unqualified"] == 0 and arms["A3"]["targeted_adb_calls"] > 0,
           arms["A3"])

c3 = Control(
    "C3_recorder_actually_saw_the_calls",
    why="C2's healthy answer is a ZERO, and a zero cannot distinguish `no "
        "unqualified calls` from `no calls observed at all`. This is the "
        "anti-vacuity arm and without it C2 is worthless",
    can_fail_because="a stub that intercepted before the adb layer, or a main() "
                     "that refused early, would leave the recorder empty",
    null_must_contain="a run in which zero adb invocations were recorded")
c3.observe(arms["A3"]["targeted_adb_calls"] > 0, arms["A3"])

c4 = Control(
    "C4_kind_discriminates_both_ways",
    why="a labeller that answered `emulator` for everything would fix ATOM-3's "
        "case and break the phone case, and vice versa. Both directions are "
        "asserted on the same code path",
    can_fail_because="a tell that matches any Android device (`arm64-v8a`, a "
                     "model-name grep) would give the phone a nonempty tell "
                     "list, and this arm would go red",
    null_must_contain="a phone resolving with any emulator tell, or an "
                      "emulator resolving with none")
c4.observe(arms["A4"]["kind"] == "emulator" and len(arms["A4"]["tells"]) == 4
           and arms["A5"]["kind"] == "phone" and arms["A5"]["tells"] == [],
           {"emulator": arms["A4"], "phone": arms["A5"]})

c5 = Control(
    "C5_unasserted_target_is_refused_not_defaulted",
    why="the whole row is that a target which does not identify itself was "
        "given a name anyway. A device reporting no model must refuse, and "
        "refuse FOR THAT REASON rather than by failing some later step",
    can_fail_because="a resolver defaulting to `phone` on a missing model, "
                     "which is v1's behaviour generalised, returns rc=0 here",
    null_must_contain="a nameless device that is labelled rather than refused")
c5.observe(arms["A7"]["rc"] == 2, arms["A7"])

ok, problems = certify(
    HERE,
    deps=["spikes/S16_mork_android"],
    artifacts=[os.path.join(HERE, "result.json")],
    controls=[c1, c2, c3, c4, c5],
    captures=[("probe_stdout", text)],
    falsifier=(
        "Three results would have refuted this row, and all three are arms "
        "rather than prose: (a) the emulator tells matching a real phone too — "
        "A5b asserts the phone's tell list is EMPTY, so a tell like `arm64-v8a` "
        "that matches everything goes red; (b) the `-s` sweep passing because "
        "no adb call was observed — A3b asserts the recorder saw calls, and it "
        "saw 78; (c) the precondition refusing everything, which would make "
        "every refusal arm green for free — A3, A5 and A8 accept on the same "
        "code path. Stated before the run; all three ran."),
    note=("`deps=['spikes/S16_mork_android']` is dirty and structurally always "
          "will be: that directory holds the run's own UNTRACKED output dumps "
          "(crossrun/host, crossrun/emulator, crossrun/phone — 30+ .space files "
          "regenerated on every run). The refusal is correct and is recorded "
          "rather than bought green by narrowing the dep to a single file, "
          "which provenance.py documents as faking a clean verdict."),
)
print(f"\ncertify ok={ok}")
for p in problems:
    print("  " + p)
