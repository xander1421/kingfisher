#!/usr/bin/env python3
"""G43 — D6 certification over the RECORDED probe run.

Separate from `probe.py` on purpose: the probe is a 5,376 s run (a full
81,636-query evaluation inside a `git archive HEAD` tree) and certification
must be re-runnable without re-running it. It reads `probe.json` — the
artifact the probe wrote — and certifies THAT, so every control observation
in `provenance.json` is traceable to a value on disk rather than recomputed
here from a different state.

  python3 spikes/G43_repro_provenance/certify.py
"""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "harness"))
import kfcheck                                          # noqa: E402
from provenance import Control, Falsifier               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
G36 = os.path.join(ROOT, "spikes", "G36_repro_g34")
PROBE = os.path.join(HERE, "probe.json")


def main():
    with open(PROBE) as f:
        r = json.load(f)
    F1, F2, F3, C = r["F1"], r["F2"], r["F3"], r["controls"]

    controls = [
        Control("C1_sweep_finds_a_committed_path",
                "the ref sweep must find a path that IS committed, else F1's "
                "zero is inertness rather than absence",
                can_fail_because="a bad prefix or an empty ref set returns 0 "
                                 "for G36 too",
                null_must_contain="paths under a directory that IS committed "
                                  "(G36's), so a zero for G34 is absence"),
        Control("C2_archive_is_head_not_tree",
                "the F2 tree must be HEAD and not the working tree, else the "
                "reproduction runs against the very files under test",
                can_fail_because="G34's directory appearing inside the archive",
                null_must_contain="both answers: an archive that leaks the "
                                  "working tree would show G34 present"),
        Control("C3_comparator_can_report_differ",
                "the sha256 comparison behind F3 must be able to say DIFFER",
                can_fail_because="a one-bit mutation hashing equal",
                null_must_contain="a DIFFER verdict, produced here from a "
                                  "one-bit mutation of the same file"),
        Control("C4_repro_can_miss",
                "F2 compares against literals transcribed from G34/RESULT.md, "
                "not against a value read from the run being checked",
                can_fail_because="the generator writing no arm, so there is "
                                 "nothing to compare",
                null_must_contain="a MISS: any arm, filter or split change "
                                  "moves the 4 dp literals it compares to"),
        Control("C5_answer_was_produced_not_shipped",
                "the answer read by F2 must be one the generator WROTE this "
                "run; the HEAD archive ships a committed copy at that path",
                can_fail_because="the generator failing to recreate the file "
                                 "the probe deleted before running it",
                null_must_contain="the shipped-answer case: v1 read exactly "
                                  "that file and this control is what sees it"),
    ]
    for c in controls:
        obs = C[c.name]
        c.observe(obs["ok"], {k: v for k, v in obs.items() if k != "ok"})

    falsifiers = [
        Falsifier("F1_G34_reachable_from_some_ref",
                  refutes="that G36 compared against an artifact no clone "
                          "contains; if G34 is reachable from ANY ref the "
                          "whole row is withdrawn",
                  fires_when="git ls-tree over every ref, reflog entry and "
                             "stash finds one path under G34's directory",
                  null_must_contain="a reachable path, which C1 proves the "
                                    "same sweep does return for G36"),
        Falsifier("F2_clean_HEAD_tree_reproduces",
                  refutes="that the finding is larger than attribution; a "
                          "clean HEAD tree returning 0.2648 / 0.3929 means "
                          "the mission proposition survives on G36's copy",
                  fires_when="the freshly written answer's rounded mrr and "
                             "hits10 differ from the published literals",
                  null_must_contain="a differing number: the literals come "
                                    "from G34/RESULT.md, not from this run"),
        Falsifier("F3_generators_differ",
                  refutes="the 'same program' claim this row rests on",
                  fires_when="G36's committed generator and G34's on-disk "
                             "original hash differently",
                  null_must_contain="a DIFFER verdict, which C3 demonstrates "
                                    "the same comparator produces"),
    ]
    falsifiers[0].observe(F1["fired"],
                          {"g34_paths_reachable": F1["g34_paths_reachable"],
                           "paths": F1["paths"]})
    falsifiers[1].observe(F2["fired"],
                          {"mrr_rounded": F2["mrr_rounded"],
                           "hits10_rounded": F2["hits10_rounded"],
                           "published_mrr": F2["published_mrr"],
                           "published_hits10": F2["published_hits10"],
                           "reproduced": F2["reproduced"],
                           "fired_by_channel_condition_sentence":
                               F2["fired_by_channel_condition_sentence"],
                           "fired_by_channel_prediction_label":
                               F2["fired_by_channel_prediction_label"]})
    falsifiers[2].observe(F3["fired"],
                          {"g34_ondisk_sha256": F3["g34_ondisk_sha256"],
                           "g36_committed_sha256": F3["g36_committed_sha256"],
                           "identical": F3["identical"]})

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G36],
        artifacts=[os.path.join(HERE, "probe.py"), PROBE,
                   os.path.join(HERE, "probe.out")],
        controls=controls, falsifiers=falsifiers,
        captures=[("probe.out", open(os.path.join(HERE, "probe.out")).read())],
        falsifier="G34's directory turning out to be reachable from some ref "
                  "(F1), which would make G36's 'the committed one' true and "
                  "retire the row entirely",
        allow_dirty=True,
        note="G43: is the comparand of this repo's only byte-reproduction "
             "claim actually in this repo? Certifies the recorded probe run "
             "(elapsed_sec=%.0f), not a fresh one." % r["elapsed_sec"])
    print(f"\nD6 Provenance Certified: ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
