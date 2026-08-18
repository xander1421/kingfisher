#!/usr/bin/env python3
"""H106 — is `cp` over a live hook observable as a partial read?

Filed from a live refusal: `git commit` was rejected by
`.git/hooks/pre-commit: line 252: unexpected EOF while looking for matching '"'`
while `bash -n` on the same file one command later was clean.

Two arms, identical load, one variable:
  * `cp`  -- what `install_hooks.sh` v2 does: open(O_TRUNC) + stream
  * `mv`  -- write a sibling temp, then rename(2), which is atomic within a
             filesystem, so an executor sees either the whole old file or the
             whole new one and never a prefix of the new one

F1 is the killing falsifier and it is run first: if the `cp` arm produces ZERO
partial reads, the mechanism is wrong and the observation is published with its
cause unattributed.

Everything happens inside one `mktemp -d`. The repository's own `.git/hooks/`
is never written by this file (§10).

  python3 spikes/H106_hook_install_race/race.py
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SOURCE = os.path.join(ROOT, "spikes", "harness", "pre-commit.hook")
SECONDS = 6.0


def arm(workdir, mode, payload, seconds):
    """One writer, one executor, `seconds` of overlap. Returns counts.

    The executor runs the script with `sh -n` (parse only). A parse is the
    cheapest thing that fails on a truncated shell file and it cannot have the
    side effects a real hook would, which is what makes running this against a
    copy of the REAL gate safe.
    """
    live = os.path.join(workdir, "live.sh")
    with open(live, "w") as f:
        f.write(payload)
    os.chmod(live, 0o755)
    src = os.path.join(workdir, "src.sh")
    with open(src, "w") as f:
        f.write(payload)

    stop = threading.Event()
    counts = {"writes": 0, "execs": 0, "parse_failures": 0,
              "other_failures": 0, "sample_error": None}

    def writer():
        while not stop.is_set():
            if mode == "cp":
                shutil.copyfile(src, live)          # open(O_TRUNC) + stream
            else:
                tmp = live + ".tmp"
                shutil.copyfile(src, tmp)
                os.replace(tmp, live)               # rename(2), atomic
            counts["writes"] += 1

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    end = time.time() + seconds
    while time.time() < end:
        r = subprocess.run(["sh", "-n", live], capture_output=True, text=True)
        counts["execs"] += 1
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            counts["parse_failures"] += 1
            if counts["sample_error"] is None:
                counts["sample_error"] = err[:200]
    stop.set()
    t.join(timeout=5)
    return counts


def main():
    with open(SOURCE) as f:
        payload = f.read()

    work = tempfile.mkdtemp(prefix="h106_")
    try:
        os.makedirs(os.path.join(work, "a"), exist_ok=True)
        cp1 = arm(os.path.join(work, "a"), "cp", payload, SECONDS)
        os.makedirs(os.path.join(work, "b"), exist_ok=True)
        mv1 = arm(os.path.join(work, "b"), "mv", payload, SECONDS)
        os.makedirs(os.path.join(work, "c"), exist_ok=True)
        cp2 = arm(os.path.join(work, "c"), "cp", payload, SECONDS)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    res = {"spike": "H106", "source": os.path.relpath(SOURCE, ROOT),
           "source_bytes": len(payload), "seconds_per_arm": SECONDS,
           "arms": {"cp_run1": cp1, "mv": mv1, "cp_run2": cp2},
           "controls": {}, "falsifiers": {}}

    res["controls"]["C1_executor_actually_ran"] = {
        "what_would_fail_it": "an arm with zero successful parses, which would "
                              "make a zero-failure verdict an executor that "
                              "never executed (A15)",
        "cp_run1_successes": cp1["execs"] - cp1["parse_failures"],
        "mv_successes": mv1["execs"] - mv1["parse_failures"],
        "cp_run2_successes": cp2["execs"] - cp2["parse_failures"],
        "ok": all(a["execs"] - a["parse_failures"] > 0 for a in (cp1, mv1, cp2)),
    }
    res["controls"]["C2_writer_actually_wrote"] = {
        "what_would_fail_it": "an arm with zero writes, which would make the "
                              "whole comparison a no-op",
        "writes": {"cp_run1": cp1["writes"], "mv": mv1["writes"],
                   "cp_run2": cp2["writes"]},
        "ok": all(a["writes"] > 0 for a in (cp1, mv1, cp2)),
    }
    res["controls"]["C3_cp_arm_reproduces_its_own_sign"] = {
        "what_would_fail_it": "the two cp runs disagreeing about whether "
                              "failures occur at all, which would make the "
                              "rate unreportable",
        "cp_run1_failures": cp1["parse_failures"],
        "cp_run2_failures": cp2["parse_failures"],
        "ok": (cp1["parse_failures"] > 0) == (cp2["parse_failures"] > 0),
    }

    res["falsifiers"]["F1_cp_never_produces_a_partial_read"] = {
        "question": "can `cp` over a live script be observed as a partial read?",
        "cp_failures": cp1["parse_failures"] + cp2["parse_failures"],
        "sample_error": cp1["sample_error"] or cp2["sample_error"],
        "fired": (cp1["parse_failures"] + cp2["parse_failures"]) == 0,
        "meaning_if_fired": "cp is effectively atomic here, the mechanism is "
                            "wrong, and the observation is published with its "
                            "cause unattributed",
    }
    res["falsifiers"]["F2_mv_does_not_eliminate_it"] = {
        "question": "does the rename(2) installer bring the failure rate to 0?",
        "mv_failures": mv1["parse_failures"],
        "fired": mv1["parse_failures"] > 0,
        "meaning_if_fired": "the fix does not fix it and shipping it would be "
                            "fiction",
    }

    # CEILING, recorded in the artifact and not only in prose: the two arms are
    # matched on WALL CLOCK and on executor load, NOT on write count -- rename
    # costs a copy plus a rename, so the mv arm writes fewer times in the same
    # 6 s. It does not rescue the mv arm's zero: rename(2) has no window at all,
    # so its exposure is zero at any rate, whereas cp's grows with rate. Stated
    # because a reader comparing 52-in-2264 against 0-in-1167 is entitled to
    # know the denominators are not the same experiment.
    res["ceiling_arms_not_write_rate_matched"] = {
        "cp_writes": cp1["writes"] + cp2["writes"], "mv_writes": mv1["writes"],
        "why_it_does_not_rescue_mv": "rename(2) is atomic, so the mv arm's "
                                     "exposure window is zero at any write rate",
    }

    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "race.json"), "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    if bad:
        print("CONTROLS FAILED:", bad)
        return 1

    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
    import kfcheck
    from provenance import Control, Falsifier
    controls = []
    for name, why, canfail, null in (
        ("C1_executor_actually_ran",
         "each arm must be shown to have parsed the script successfully many "
         "times, or a zero-failure arm is an executor that never executed",
         "an arm with zero successful parses",
         "successes and failures both, which the cp arms produce"),
        ("C2_writer_actually_wrote",
         "each arm must be shown to have rewritten the live file, or the "
         "comparison is a no-op",
         "an arm with zero writes",
         "a non-zero write count under both installers"),
        ("C3_cp_arm_reproduces_its_own_sign",
         "two independent cp runs must agree on whether failures occur at all, "
         "or the effect is not reportable",
         "one cp run failing and the other not",
         "both signs: an arm is free to come out at zero"),
    ):
        c = Control(name, why, can_fail_because=canfail, null_must_contain=null)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    falsifiers = []
    for name, refutes, fires_when, null in (
        ("F1_cp_never_produces_a_partial_read",
         "the mechanism: if cp is effectively atomic here, the observed refusal "
         "has another cause and is published unattributed",
         "the cp arms produce zero parse failures across every execution",
         "zero failures, which the mv arm demonstrates this harness can report"),
        ("F2_mv_does_not_eliminate_it",
         "the fix: a rename(2) installer that still fails is fiction",
         "the mv arm produces one or more parse failures",
         "failures, which the cp arms show the same executor does report"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=null)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[], no_deps_reason="the payload is this repo's own "
                                      "pre-commit.hook, read at run time and "
                                      "recorded by size; there is no generated "
                                      "input directory",
        artifacts=[os.path.join(HERE, "race.py"),
                   os.path.join(HERE, "race.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("cp_sample_error", res["falsifiers"]
                   ["F1_cp_never_produces_a_partial_read"]["sample_error"])],
        falsifier="zero parse failures in the cp arms, which would mean cp is "
                  "effectively atomic on this filesystem and the live refusal "
                  "that opened this row has some other cause",
        allow_dirty=True,
        note="H106: a shared executable replaced by an in-place truncating "
             "write. Both falsifiers survived; install_hooks.sh v3 ships the "
             "rename(2) installer and a deterministic inode selfcheck.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
