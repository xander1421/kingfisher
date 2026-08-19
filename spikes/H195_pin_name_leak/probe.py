#!/usr/bin/env python3
"""H195 — the pin's NAME leaked, and the row I wrote about it was too wide.

MY OWN ROW, RAISED FROM S37's F2 AND LEFT OPEN FOR THREE CYCLES. It said 5 of 12
consumers silently resolve to S20's frozen pin and named F1 as the falsifier that
would demote it: *"the five consumers are pinned DELIBERATELY and repointing them
destroys a reproduction, in which case the row is a labelling problem and not a
resolution one."*

**F1 FIRED, FOR ALL FIVE.** S24, S27 and S36's `witnessed_job.py` each carry a
comment saying the inheritance is on purpose; `S36/attack.py`'s entire finding is
ABOUT the pinned verifier and cannot be reproduced against the live one at all.

AND I SHIPPED THE WRONG FIX FIRST. A patch that RELEASED the bare name after
S20's imports moved `S27_verify_floor/verify_floor.json`
`verifier_hash_bytes 22900.15 -> 0` and `slack_pct 0.0 -> -100.0`. A5 below
reproduces the mechanism in six lines. I had A/B'd the consumers on the md5 of
their STDOUT and called it "no collateral" — S27 publishes to a JSON FILE, so I
compared an artifact that could not carry the effect (A20, family A).

SO THE FIX IS DECLARATION, NOT RESOLUTION, and the gateable invariant is not
"nobody is pinned" — which is false and harmful — but **"nobody is pinned
SILENTLY"**.

TWO-SIDED. A4 asserts the resolution is UNCHANGED (still 5 pinned) and A6 that
the attacked number is UNCHANGED (still 37/37), because a labelling fix that
moved a measurement would be a different and worse thing.
"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
S20 = os.path.join(ROOT, "spikes", "S20_verify_kinds")
CONSUMERS = ["spikes/S20_verify_kinds/verify_kinds.py",
             "spikes/S24_range_crossover/range_crossover.py",
             "spikes/S27_verify_floor/verify_floor.py",
             "spikes/S36_witnessed_job/witnessed_job.py",
             "spikes/S36_witnessed_job/attack.py"]

fail = 0
obs = {}


def ck(name, got, want):
    global fail
    if got == want:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name} (want {want!r}, got {got!r})")
        fail += 1


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, cwd=ROOT)


# ---------------------------------------------------------------- A1 / A2 ----
# The declaration is what a checker can read. At HEAD there is none -- the
# intent lived only in comments, which is why the row could not tell a
# deliberate pin from an accident.
head_decl = sum(1 for c in CONSUMERS
                if "USES_S20_PIN" in sh("git", "show", f"HEAD:{c}").stdout)
now_decl = sum(1 for c in CONSUMERS
               if "USES_S20_PIN" in open(os.path.join(ROOT, c)).read())
ck("A1 at HEAD none of the 5 consumers declares its pin use", head_decl, 0)
ck("A2 all 5 declare it now", now_decl, 5)
obs["A1_A2"] = {"declared_at_head": head_decl, "declared_now": now_decl,
                "consumers": len(CONSUMERS)}

# ---------------------------------------------------------------- A3 / A4 ----
wm = sh(sys.executable, "spikes/S37_completeness_cutover/which_module.py")
print(wm.stdout.strip().splitlines()[-1] if wm.stdout else wm.stderr[-300:])
res = json.load(open(os.path.join(ROOT, "spikes", "S37_completeness_cutover",
                                  "which_module.json")))
ck("A3 zero consumers are pinned SILENTLY", res["n_silent_pin"], 0)
ck("A3b ...and the 5 that are pinned are all DECLARED", res["n_declared_pin"], 5)
ck("A3c ...with nothing left unresolved, which would hide a sixth",
   res["n_unresolved"], 0)
ck("A4 the RESOLUTION is unchanged: still 5 pinned, so the row was not "
   "'fixed' by unpinning", res["n_pinned_copy"], 5)
ck("A4b ...and the other 7 still resolve LIVE", res["n_live"], 7)
obs["A3_A4"] = {k: res[k] for k in ("n_live", "n_pinned_copy", "n_declared_pin",
                                    "n_silent_pin", "n_unresolved")}

# -------------------------------------------------------------------- A5 -----
# WHY RELEASING THE NAME IS HARMFUL, reproduced rather than recalled. S84's
# `counted` swaps `TW.hashlib` on the module IT bound. Hand it a function from a
# DIFFERENT trie_witness object and it counts nothing -- a counter on one module
# and the work on another, which is what put 0 into S27's verifier_hash_bytes.
sys.path.insert(0, S20)
import verify_kinds as S20M                                        # noqa: E402
pinned = sys.modules["trie_witness"]
_live_path = os.path.join(ROOT, "spikes", "W2_witnessed_trie", "trie_witness.py")
_spec = importlib.util.spec_from_file_location("trie_witness_live_h195", _live_path)
live = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live)

keys = sorted({bytes([i, i // 3, i % 5]) for i in range(64)})
root_p = pinned.build(keys)
q = keys[8][:1]
pf_p = pinned.prove_completeness(root_p, q)
_, _, b_pinned = S20M.counted(pinned.verify_completeness, root_p.h, q, pf_p)
root_l = live.build(keys)
pf_l = live.prove_completeness(root_l, q)
_, _, b_live = S20M.counted(live.verify_completeness, root_l.h, q, pf_l)
ck("A5 the counter sees the PINNED module's work", b_pinned > 0, True)
ck("A5b ...and sees ZERO of the LIVE module's, which is the 22900->0 mechanism",
   b_live, 0)
obs["A5"] = {"bytes_hashed_pinned": b_pinned, "bytes_hashed_live": b_live}

# -------------------------------------------------------------------- A6 -----
aj = json.load(open(os.path.join(ROOT, "spikes", "S36_witnessed_job",
                                 "attack.json")))
vid = aj.get("verifier_identity", {})
ck("A6 the attack artifact now names the verifier it measured",
   bool(vid.get("is_s20_pin")) and len(vid.get("sha256", "")) == 64, True)
ck("A6b ...and the finding itself is UNCHANGED, because this is a labelling fix",
   (aj["committed_verifier_accepts_replay"], aj["falsifier_fired"]), (37, True))
obs["A6"] = {"is_s20_pin": vid.get("is_s20_pin"),
             "sha256": vid.get("sha256"),
             "committed_verifier_accepts_replay":
                 aj["committed_verifier_accepts_replay"],
             "falsifier_fired": aj["falsifier_fired"]}

with open(os.path.join(HERE, "result.json"), "w") as fh:
    json.dump({"checks_failed": fail, "arms": obs}, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(f"\nchecks failed: {fail}")
sys.exit(1 if fail else 0)
