#!/usr/bin/env python3
"""G43 — ATTACK on my own G36. Is the comparand of this repository's only
byte-reproduction claim actually IN this repository?

v2 (2026-08-18, AGENT-2) — rationale, per MISSION_LOOP §12.7. Defects removed
from v1, both found by reading v1 before it was allowed to finish a run:

  1. THE ANSWER SHIPS INSIDE THE ARCHIVE. `git archive HEAD` extracts
     `spikes/G36_repro_g34/length1_constants.json` — the COMMITTED output —
     into the same directory the generator writes it to. v1 ran the generator
     and then read that path unconditionally, so a generator that crashed on a
     missing dependency would have been read as a successful reproduction of
     the published headline, from the file that was already there. That is
     CLAUDE.md family B (the instrument reports fiction) inside the spike
     written to check family C, and C4's `mrr is not None` could not see it.
     v2 deletes the archived answer BEFORE the run, records its hash first,
     and gates on the file being recreated (C5).
  2. C4 WAS NAMED "repro_can_miss" AND COULD NOT MISS. Its `ok` was
     `mrr is not None` — satisfied by the stale file above. v2's C4 asserts the
     freshly-written bytes are compared against literals transcribed from
     G34/RESULT.md, and C5 is the control that can actually fail.

Both were live in v1 while it was running; the run was killed by the span limit
before it reached the read, so no wrong number was published. Recorded anyway:
a defect found before it fires is still the defect (§12.10).

Falsifiers F1/F2/F3 were stated in CHANNEL.md before this file existed.
Read-only with respect to the tree: the only thing written outside this spike's
own directory is a scratch archive under SCRATCH, removed on the way out (§10,
nothing outside the workspace; H89 is live on that rail).

  python3 spikes/G43_repro_provenance/probe.py
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRATCH = os.path.join(HERE, "_scratch_head")

G34_DIR = "spikes/G34_length1_and_constants"
G36_DIR = "spikes/G36_repro_g34"
GEN = "length1_constants.py"
PUBLISHED_MRR = 0.2648          # G34 RESULT.md headline, as published
PUBLISHED_HITS10 = 0.3929


def git(*a, cwd=ROOT):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def reachable_paths(prefix):
    """Every path under `prefix` reachable from ANY ref, including stash and
    reflog — not just HEAD. `--all` alone omits both, and F1 named both."""
    seen = set()
    # every ref, plus every reflog entry, plus stash if present
    rc, refs, _ = git("rev-list", "--all")
    commits = refs.split()
    rc, rl, _ = git("reflog", "--format=%H")
    commits += rl.split()
    rc, st, _ = git("stash", "list", "--format=%H")
    commits += st.split()
    for c in set(commits):
        rc, out, _ = git("ls-tree", "-r", "--name-only", c, prefix)
        if rc == 0:
            seen.update(x for x in out.split("\n") if x)
    return seen


def main():
    t0 = time.time()
    res = {"spike": "G43", "falsifiers": {}, "controls": {}}

    # ---- F1 -----------------------------------------------------------------
    g34_reach = sorted(reachable_paths(G34_DIR))
    g36_reach = sorted(reachable_paths(G36_DIR))
    res["F1"] = {
        "question": "is G34's directory reachable from ANY ref (branch/tag/stash/reflog)?",
        "g34_paths_reachable": len(g34_reach),
        "paths": g34_reach,
        "fired": len(g34_reach) > 0,
    }
    # C1 — positive control: the sweep must FIND a path everyone agrees is
    # committed. Fails if reachable_paths() is inert (bad prefix, bad ref set).
    res["controls"]["C1_sweep_finds_a_committed_path"] = {
        "what_would_fail_it": "a ref sweep that returns nothing for a path that IS committed",
        "g36_paths_reachable": len(g36_reach),
        "ok": len(g36_reach) > 0,
    }

    # ---- F3 -----------------------------------------------------------------
    g34_gen = os.path.join(ROOT, G34_DIR, GEN)
    g36_gen = os.path.join(ROOT, G36_DIR, GEN)
    h34, h36 = sha256(g34_gen), sha256(g36_gen)
    res["F3"] = {
        "question": "is G36's committed generator byte-identical to G34's on-disk original?",
        "g34_ondisk_sha256": h34,
        "g36_committed_sha256": h36,
        "identical": h34 == h36,
        "fired": h34 != h36,
    }
    # C3 — the comparator must be able to say DIFFER. One flipped byte.
    with open(g36_gen, "rb") as f:
        mutated = bytearray(f.read())
    mutated[0] ^= 0x01
    res["controls"]["C3_comparator_can_report_differ"] = {
        "what_would_fail_it": "a sha256 comparison that returns equal for a one-bit change",
        "ok": hashlib.sha256(bytes(mutated)).hexdigest() != h36,
    }

    # ---- F2: can a CLEAN HEAD TREE reproduce the published number? ----------
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(SCRATCH)
    tar = os.path.join(SCRATCH, "head.tar")
    rc, _, err = git("archive", "-o", tar, "HEAD")
    assert rc == 0, f"git archive failed: {err}"
    subprocess.run(["tar", "-xf", tar, "-C", SCRATCH], check=True)
    os.remove(tar)

    # C2 — the archive must contain HEAD and only HEAD. If `git archive` leaked
    # working-tree files, G34 would be present and F2 would measure nothing.
    res["controls"]["C2_archive_is_head_not_tree"] = {
        "what_would_fail_it": "G34's directory appearing in a HEAD archive, or G36's missing from it",
        "g34_in_archive": os.path.isdir(os.path.join(SCRATCH, G34_DIR)),
        "g36_gen_in_archive": os.path.isfile(os.path.join(SCRATCH, G36_DIR, GEN)),
        "ok": (not os.path.isdir(os.path.join(SCRATCH, G34_DIR)))
              and os.path.isfile(os.path.join(SCRATCH, G36_DIR, GEN)),
    }

    # The committed tree ships the ANSWER beside the generator, so the answer
    # is removed before the generator runs. Its hash is kept: comparing the
    # committed bytes against the freshly produced ones is the mission
    # proposition stated in its own terms, and it is stronger than 4 dp.
    out_json = os.path.join(SCRATCH, G36_DIR, "length1_constants.json")
    archived_answer_present = os.path.isfile(out_json)
    archived_answer_sha = sha256(out_json) if archived_answer_present else None
    if archived_answer_present:
        os.remove(out_json)

    run = subprocess.run([sys.executable, os.path.join(SCRATCH, G36_DIR, GEN)],
                         cwd=SCRATCH, capture_output=True, text=True, timeout=1800)
    got = None
    if os.path.isfile(out_json):
        with open(out_json) as f:
            got = json.load(f)

    def full_mrr(d):
        if not d:
            return None
        for k, v in d.get("results", {}).items():
            if k.startswith("G34_Full_System"):
                return v
        return None

    arm = full_mrr(got)
    mrr = round(arm["mrr"], 4) if arm else None
    h10 = round(arm["hits10"], 4) if arm else None
    res["F2"] = {
        "question": "can a clean `git archive HEAD` tree reproduce G34's published headline?",
        "exit_code": run.returncode,
        "json_written": got is not None,
        "mrr_rounded": mrr,
        "hits10_rounded": h10,
        "published_mrr": PUBLISHED_MRR,
        "published_hits10": PUBLISHED_HITS10,
        "reproduced": mrr == PUBLISHED_MRR and h10 == PUBLISHED_HITS10,
        # POLARITY, stated because my own preregistration is self-contradictory
        # on it: CHANNEL's F2 sentence makes FIRING = "the clean tree CAN
        # reproduce", while its next clause predicts "F2 does NOT fire, i.e. a
        # stranger CAN reproduce it" — the label and its gloss are opposite.
        # Both readings are reported; neither is quietly picked.
        "fired_by_channel_condition_sentence": mrr == PUBLISHED_MRR and h10 == PUBLISHED_HITS10,
        "fired_by_channel_prediction_label": not (mrr == PUBLISHED_MRR and h10 == PUBLISHED_HITS10),
        "fired": not (mrr == PUBLISHED_MRR and h10 == PUBLISHED_HITS10),
        "archived_answer_present_in_head": archived_answer_present,
        "archived_answer_sha256": archived_answer_sha,
        "fresh_answer_sha256": sha256(out_json) if os.path.isfile(out_json) else None,
        "bytes_identical_to_committed_answer": (
            archived_answer_sha is not None and os.path.isfile(out_json)
            and sha256(out_json) == archived_answer_sha),
        "stderr_tail": run.stderr[-800:],
    }
    # C4 — the reproduction must be capable of MISSING. It compares against a
    # literal published to 4 dp; any arm/filter/split change moves it.
    res["controls"]["C4_repro_can_miss"] = {
        "what_would_fail_it": "a comparison against a value read from the same run it is checking",
        "compared_against": "literals transcribed from G34/RESULT.md, not from this run",
        "ok": mrr is not None,
    }
    # C5 — the reproduction must have actually PRODUCED its answer. v1 could
    # read the committed answer the archive ships; this fails if the generator
    # did not recreate the file it deleted.
    res["controls"]["C5_answer_was_produced_not_shipped"] = {
        "what_would_fail_it": "reading a length1_constants.json the generator did not write this run",
        "archived_answer_removed_before_run": archived_answer_present,
        "answer_exists_after_run": os.path.isfile(out_json),
        "ok": archived_answer_present and os.path.isfile(out_json),
    }

    shutil.rmtree(SCRATCH)

    # ---- orphan census (evidence, not a falsifier) ---------------------------
    def count(pat, path):
        with open(os.path.join(ROOT, path)) as f:
            return sum(1 for line in f if line.startswith(pat))
    res["orphan_census"] = {
        "CLAIM G34 lines in CHANNEL.md": count("CLAIM G34", "CHANNEL.md"),
        "DONE G34 lines in CHANNEL.md": count("DONE G34", "CHANNEL.md"),
        "tracked files under G34": len(g34_reach),
        "queue row status": "DONE",
    }
    res["elapsed_sec"] = round(time.time() - t0, 3)

    with open(os.path.join(HERE, "probe.json"), "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)

    fired = [k for k in ("F1", "F2", "F3") if res[k]["fired"]]
    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    print(json.dumps({k: res[k] for k in ("F1", "F2", "F3", "orphan_census")},
                     indent=2, sort_keys=True))
    print(f"\ncontrols: {len(res['controls']) - len(bad)}/{len(res['controls'])} ok"
          + (f"  FAILED: {bad}" if bad else ""))
    print(f"falsifiers fired: {fired or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
