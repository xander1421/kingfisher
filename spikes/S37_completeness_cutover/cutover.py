#!/usr/bin/env python3
"""S37 — lift `verify_completeness_qbound` into `trie_witness.verify_completeness`.

A CUTOVER, NOT A MEASUREMENT. The tightened verifier was written and measured in
`spikes/S36_witnessed_job/attack.py` and then left there, while 12 consumers went
on importing the version it refutes. **S21's class: a fix that corrects the
instrument and leaves every consumer on the broken one is not a fix.**

WHAT WAS WRONG WITH v2, in one sentence: the COVER branch authenticated the
answer against the ROOT and never bound it to the QUERY, so a prover asked for
prefix `q` could return the complete, unforged, byte-identical honest proof for
a deeper prefix `q2` and it verified.

FALSIFIERS, PREREGISTERED IN `CHANNEL.md` BEFORE THIS RAN:
  F1  the cutover must not be free: honest 37/37 accept and replay 37/37 reject
      through the LIVE module, or it is not the same function and the lift is
      withdrawn.
  F2  every consumer re-run; if any changes verdict the cutover is a REGRESSION
      and the row stops, rather than the consumer being adjusted to fit.
  F3  the old version must have been genuinely weaker: a proof v2 ACCEPTS and v3
      REJECTS must be exhibited. If none exists the two are equivalent on this
      trie, the version bump is decoration, and I say so instead of shipping it.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
W2 = os.path.join(ROOT, "spikes", "W2_witnessed_trie")
S36D = os.path.join(ROOT, "spikes", "S36_witnessed_job")
S20D = os.path.join(ROOT, "spikes", "S20_verify_kinds")
PIN = os.path.join(S20D, "w2_head", "trie_witness.py")
SCRATCH = os.path.join(ROOT, ".scratch")

# ORDER MATTERS AND IS THE POINT OF THE ROW. W2 goes FIRST so `trie_witness`
# resolves LIVE. S36's own attack puts S20 first and therefore loads S20's
# FROZEN PIN instead -- measured in `which_module.py`, 5 of 12 consumers.
sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
sys.path.insert(0, S20D)
sys.path.insert(0, S36D)
sys.path.insert(0, W2)

import trie_witness as LIVE                                        # noqa: E402
assert os.path.realpath(LIVE.__file__) == \
    os.path.realpath(os.path.join(W2, "trie_witness.py")), LIVE.__file__

import witnessed_job as S36                                        # noqa: E402
import verify_kinds as S20M                                        # noqa: E402


def _by_path(name, path):
    """BY PATH, not by name. `import attack` resolves to W2's attack.py here --
    W2 is first on sys.path, which is exactly the shadowing this row is about,
    and it bit this file before it bit anything else. Two spikes both named
    their attack module `attack`."""
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


S36A = _by_path("s36_attack", os.path.join(S36D, "attack.py"))
from kfcheck import certify                                        # noqa: E402
from provenance import Control, Falsifier                          # noqa: E402


def load_pre_cutover():
    """The EXACT module this cutover replaced, read out of git rather than copied.

    Not the `w2_head` pin: that is an OLDER frozen HEAD (different sha256) and
    using it as "the old version" would be a citation to the wrong artifact --
    family C. `HEAD` here is the commit before the lift lands.
    """
    os.makedirs(SCRATCH, exist_ok=True)
    blob = subprocess.run(
        ["git", "show", "HEAD:spikes/W2_witnessed_trie/trie_witness.py"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    path = os.path.join(SCRATCH, "trie_witness_pre_s37.py")
    with open(path, "w") as fh:
        fh.write(blob)
    spec = importlib.util.spec_from_file_location("trie_witness_pre_s37", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["trie_witness_pre_s37"] = mod
    spec.loader.exec_module(mod)
    return mod, path


def corpus():
    """S36's OWN corpus and cheat construction, imported not retyped."""
    keys = S20M.S84M.read_keys(S36.KEYS)
    ks = sorted(set(keys))
    root = LIVE.build(ks)
    stride = max(1, len(ks) // S36A.JOBS)
    queries = [k[:S36A.PREFIX_LEN] for k in ks[::stride][:S36A.JOBS]]
    rows = []
    for q in queries:
        true_pf = LIVE.prove_completeness(root, q)
        answer = true_pf.get("keys") or []
        if len(answer) < 3:
            continue
        q2, sub = S36A.deeper_prefix(ks, q, answer)
        if q2 is None:
            continue
        replay = LIVE.prove_completeness(root, q2)
        rows.append({"q": q, "q2": q2, "honest": true_pf, "replay": replay,
                     "n_true": len(answer), "n_claimed": len(sub)})
    return root.h, rows


def main() -> int:
    pre, pre_path = load_pre_cutover()
    rh, rows = corpus()
    n = len(rows)

    # ---- F1: the lifted verifier, through the LIVE module ----
    honest_ok = sum(1 for r in rows if LIVE.verify_completeness(rh, r["q"], r["honest"]))
    replay_rej = sum(1 for r in rows if not LIVE.verify_completeness(rh, r["q"], r["replay"]))

    # ---- F3: v2 accepts what v3 rejects, exhibited ----
    pre_accepts_replay = [r for r in rows
                          if pre.verify_completeness(rh, r["q"], r["replay"])]
    pre_honest_ok = sum(1 for r in rows
                        if pre.verify_completeness(rh, r["q"], r["honest"]))
    worst = max(pre_accepts_replay, key=lambda r: r["n_true"] - r["n_claimed"],
                default=None)
    exhibit = None
    if worst:
        exhibit = {"q": worst["q"].hex(), "q2": worst["q2"].hex(),
                   "answers_true": worst["n_true"],
                   "answers_claimed": worst["n_claimed"],
                   "omitted": worst["n_true"] - worst["n_claimed"],
                   "pre_s37_accepts": True,
                   "post_s37_accepts":
                       LIVE.verify_completeness(rh, worst["q"], worst["replay"]),
                   "proof_is_unforged":
                       worst["replay"] == LIVE.prove_completeness(
                           LIVE.build(sorted(set(S20M.S84M.read_keys(S36.KEYS)))),
                           worst["q2"])}

    # ---- F2: consumers, from the two runs on disk ----
    before = open(os.path.join(HERE, "consumers_before.tsv")).read().splitlines()
    after = open(os.path.join(HERE, "consumers_after.tsv")).read().splitlines()
    consumers_same = before == after
    which = json.load(open(os.path.join(HERE, "which_module.json")))

    res = {
        "spike": "S37", "n_jobs": n,
        "post_cutover": {"honest_accepted": honest_ok, "replay_rejected": replay_rej},
        "pre_cutover": {"honest_accepted": pre_honest_ok,
                        "replay_accepted": len(pre_accepts_replay)},
        "exhibit": exhibit,
        "consumers": {"n": len(before), "identical_across_cutover": consumers_same,
                      "resolve_live": which["n_live"],
                      "resolve_pinned_copy": which["n_pinned_copy"]},
        "pre_cutover_source": "git HEAD:spikes/W2_witnessed_trie/trie_witness.py",
    }

    c1 = Control("C1_corpus_is_the_S36_one", why="the cutover must be judged on "
                 "the corpus that found the defect, not a fresh one",
                 can_fail_because="a different key file, PREFIX_LEN or JOBS "
                 "would change the job count away from S36's 37",
                 null_must_contain="a job count that is not 37")
    c1.observe(n == 37, {"n_jobs": n, "expected": 37,
                         "PREFIX_LEN": S36A.PREFIX_LEN, "JOBS": S36A.JOBS})

    c2 = Control("C2_pre_module_is_the_replaced_one", why="F3 must compare "
                 "against the EXACT version replaced, read from git",
                 can_fail_because="a pre module missing verify_completeness, or "
                 "one that already carries the v3 marker, is the wrong artifact",
                 null_must_contain="a pre-cutover module that already has path_prefix")
    c2.observe(hasattr(pre, "verify_completeness") and not hasattr(pre, "path_prefix"),
               {"has_verify_completeness": hasattr(pre, "verify_completeness"),
                "has_path_prefix_v3_marker": hasattr(pre, "path_prefix"),
                "source": pre_path})

    c3 = Control("C3_live_module_is_live", why="every arm must run the module "
                 "this cutover edited, not S20's frozen pin",
                 can_fail_because="sys.path order alone decides this, and 5 of "
                 "12 consumers get the pin instead",
                 null_must_contain="a LIVE handle resolving to w2_head")
    c3.observe(os.path.realpath(LIVE.__file__) ==
               os.path.realpath(os.path.join(W2, "trie_witness.py")),
               {"live": LIVE.__file__, "pin": PIN,
                "consumers_on_pin": which["n_pinned_copy"]})

    f1 = Falsifier("F1_cutover_is_not_free",
                   refutes="that the lifted verifier keeps S36's measured behaviour",
                   fires_when="honest accepted != 37 or replay rejected != 37 "
                              "through the LIVE module",
                   null_must_contain="an honest proof the lifted verifier rejects")
    f1.observe(not (honest_ok == n == replay_rej),
               {"n": n, "honest_accepted": honest_ok, "replay_rejected": replay_rej})

    f2 = Falsifier("F2_a_consumer_changed",
                   refutes="that the cutover is transparent to every consumer",
                   fires_when="any consumer's recorded verdict differs before vs "
                              "after the lift",
                   null_must_contain="a consumer row differing across the two runs")
    f2.observe(not consumers_same,
               {"n_consumers": len(before), "identical": consumers_same,
                "resolve_live": which["n_live"],
                "resolve_pinned_copy": which["n_pinned_copy"]})

    f3 = Falsifier("F3_old_was_not_weaker",
                   refutes="that the version bump removes a real soundness hole",
                   fires_when="no proof exists that the pre-cutover verifier "
                              "accepts and the lifted one rejects",
                   null_must_contain="zero replay proofs accepted by the pre "
                                     "module")
    f3.observe(len(pre_accepts_replay) == 0,
               {"pre_accepts_replay": len(pre_accepts_replay), "n": n,
                "worst_omitted": exhibit and exhibit["omitted"]})

    out = os.path.join(HERE, "result.json")
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2)

    print(json.dumps(res, indent=2))
    for k in (c1, c2, c3, f1, f2, f3):
        print(f"  {k.name}: fired={k.fired}")

    ok, problems = certify(
        HERE, deps=[W2, S36D], artifacts=[out],
        controls=[c1, c2, c3], falsifiers=[f1, f2, f3],
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="the lifted verifier rejects an honest proof, a consumer "
                  "changes verdict, or the old verifier was already sound",
        allow_dirty=True,
        note="S37: lift verify_completeness_qbound into trie_witness (v3).")
    print(f"\ncertify ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
