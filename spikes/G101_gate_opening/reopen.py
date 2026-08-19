#!/usr/bin/env python3
"""G101 — open `9559856568a9...`, the most-cited digest in the G-series.

Run: PYTHONUNBUFFERED=1 python3 spikes/G101_gate_opening/reopen.py

WHAT IS BROKEN, IN ONE LINE
  G59's `official.json` publishes `gate.sha256`, `gate.n_g51_on: 157` and
  `gate.n_g51_off: 66`. The digest is taken over a payload whose fifth key is
  `use_g51` -- the 223-entry per-predicate table that DECIDES the headline arm --
  and that key is dropped where the file is written (`official.py:282-285`, which
  stores sha256/n_g51_on/n_g51_off only). `freeze_gate` itself RETURNS the whole
  payload -- the loss is at the publication site, not at the digest site.
  Nine artifacts cite the digest. None publishes the object. G100 filed 27 sites
  of this class and fixed none; this is the most-cited one.

WHY A RECONSTRUCTION AND NOT A POINTER
  `HANDOFF.AGENT-2.md` cycle 8 NEXT-1 says the pred_gate citers "all resolve to
  one table G75 already publishes, so a pointer costs no re-run at all." That is
  WRONG and it is my own note. `G75_complex_gate/hybrid.json` carries the digest
  at `/g59_pred_gate/sha256` -- a CITATION of G59, not a publication. F2 below is
  that claim turned into a mechanical check instead of being quietly dropped.

WHAT THIS DOES NOT TOUCH
  `spikes/G59_official_split/` is GROK-2's spike and nothing here writes into it.
  The reconstruction re-uses G59's own `freeze_gate` by import, so the table is
  produced by the code that produced the digest, not by a second implementation
  of it -- a rebuilt table that disagreed with the digest is the defect one level
  up (G99's v2 note).

  Only official VALID is scored. TEST is not, because the gate is fitted on valid
  alone and the arms are not being re-published here.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
CORPUS = os.path.join(ROOT, "corpus", "fb15k237")

sys.path.insert(0, os.path.join(SPIKES, "harness"))
sys.path.insert(0, os.path.join(SPIKES, "G51_bayesian_lift_scoring"))
sys.path.insert(0, os.path.join(SPIKES, "G54_slice_gated_lift"))
sys.path.insert(0, os.path.join(SPIKES, "G59_official_split"))

import bayesian_lift as G51  # noqa: E402
import kfcheck  # noqa: E402
import official as G59  # noqa: E402
from provenance import Control, Falsifier  # noqa: E402

# The digest as PUBLISHED by G59, copied from official.json. F1 compares the
# reconstruction against this and nothing in this file can move it.
PINNED_DIGEST = "9559856568a9639f6626824db55f1b46431a1fa501a4a66c8e141538528bc609"
PINNED_ON, PINNED_OFF = 157, 66


def digest_of(payload):
    """G59's serialisation, byte for byte (official.py:146-147): sort_keys over
    the payload WITHOUT its own sha256 field."""
    body = {k: v for k, v in payload.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def json_files():
    for pat in ("**/*.json",):
        for p in glob.glob(os.path.join(SPIKES, pat), recursive=True):
            if os.sep + "G101_gate_opening" + os.sep in p:
                continue          # our own output is not evidence of a prior publication
            yield p


def bool_tables(obj, path, out, min_entries):
    """Every dict of >= min_entries whose values are all bools -- the only shape
    `use_g51` can have in JSON. Sound as an ABSENCE test: no serialisation
    recovers 223 predicate->bool entries from an artifact that has no such
    container."""
    if isinstance(obj, dict):
        vals = list(obj.values())
        if len(vals) >= min_entries and vals and all(isinstance(v, bool) for v in vals):
            out.append((path, obj))
        for k, v in obj.items():
            bool_tables(v, path + "/" + str(k), out, min_entries)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bool_tables(v, path + f"[{i}]", out, min_entries)


def main():
    t0 = time.time()

    # ---- rebuild G59's VALID scoring path, using G59's own functions ----------
    hashes = {n: G59.sha256_file(os.path.join(CORPUS, n)) for n in G59.EXPECTED}
    train_txt = G59.load_split_txt(os.path.join(CORPUS, "train.txt"))
    valid_txt = G59.load_split_txt(os.path.join(CORPUS, "valid.txt"))
    test_txt = G59.load_split_txt(os.path.join(CORPUS, "test.txt"))
    train, valid, test, npred, nent = G59.pack_ids(train_txt, valid_txt, test_txt)
    print(f"official n train={len(train)} valid={len(valid)} test={len(test)} "
          f"npred={npred} nent={nent}", flush=True)

    # C1: the inputs are the ones G59 recorded. Derived from a comparison, never
    # asserted -- a control whose verdict is a literal cannot fail (H201).
    g59 = json.load(open(os.path.join(SPIKES, "G59_official_split", "official.json")))
    c1_pairs = {n: (hashes[n], g59["file_sha256"].get(n)) for n in sorted(hashes)}
    c1_ok = all(a == b for a, b in c1_pairs.values())
    print(f"C1 input hashes match G59 = {c1_ok}", flush=True)

    all_tri = train + valid + test
    out_adj, in_adj, pair_tr, byp, rev = G51.build_graph_index(train)
    true_sp, true_po = G51.build_filter_index(all_tri)
    idx = G59.slim_index(train)

    print("mining 2-hop on official train ...", flush=True)
    t_mine = time.time()
    rules = G51.mine_2hop_rules(out_adj, pair_tr, byp, rev)
    rules_by_head = defaultdict(list)
    for r in rules:
        rules_by_head[r["head"]].append((r["body"], r["conf"]))
    print(f"mined {len(rules)} in {time.time() - t_mine:.1f}s", flush=True)

    print("scoring official VALID (the gate's fitting set) ...", flush=True)
    t_dev = time.time()
    dev_rows = G59.score_split(valid, nent, rules_by_head, out_adj, in_adj,
                               true_sp, true_po, idx)
    payload, _use = G59.freeze_gate(dev_rows)
    print(f"VALID {len(dev_rows)} rows in {time.time() - t_dev:.1f}s -> "
          f"{payload['sha256'][:12]} on={payload['n_g51_on']} off={payload['n_g51_off']}",
          flush=True)

    # ---- F1 : does the reconstruction reproduce the PUBLISHED digest? --------
    f1_fired = payload["sha256"] != PINNED_DIGEST
    n_entries = len(payload["use_g51"])
    print(f"F1 digest mismatch = {f1_fired}  ({n_entries} entries)", flush=True)

    # C2: the two integers G59 DID publish must fall out of the table we rebuilt,
    # so the five published numbers and the object stay one record (H39).
    on_derived = int(sum(1 for v in payload["use_g51"].values() if v))
    off_derived = int(sum(1 for v in payload["use_g51"].values() if not v))
    c2_ok = (on_derived, off_derived) == (PINNED_ON, PINNED_OFF)
    print(f"C2 counts derive from table: on={on_derived} off={off_derived} ok={c2_ok}", flush=True)

    # ---- F3 / C3 : does the digest actually PIN the table? -------------------
    # Flip exactly one entry and rehash. If the digest is unchanged, publishing
    # the table proves nothing about what G59 ran.
    victim = sorted(payload["use_g51"])[0]
    mutated = dict(payload["use_g51"])
    mutated[victim] = not mutated[victim]
    mut_payload = {k: v for k, v in payload.items() if k != "sha256"}
    mut_payload["use_g51"] = mutated
    mut_digest = digest_of(mut_payload)
    c3_ok = mut_digest != payload["sha256"]
    f3_fired = not c3_ok
    print(f"F3 one-entry flip leaves digest unchanged = {f3_fired} "
          f"(p={victim}: {mut_digest[:12]})", flush=True)

    # ---- F2 : was the object published somewhere all along? -----------------
    found = []
    n_scanned = 0
    for p in json_files():
        n_scanned += 1
        try:
            doc = json.load(open(p))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue
        hits = []
        bool_tables(doc, os.path.relpath(p, ROOT), hits, min_entries=100)
        for where, tbl in hits:
            cand = {k: v for k, v in payload.items() if k != "sha256"}
            cand["use_g51"] = {str(k): bool(v) for k, v in sorted(
                tbl.items(), key=lambda kv: int(kv[0]) if str(kv[0]).lstrip("-").isdigit() else kv[0])}
            found.append((where, len(tbl), digest_of(cand) == PINNED_DIGEST))
    f2_fired = any(reproduces for _, _, reproduces in found)
    print(f"F2 object already published elsewhere = {f2_fired} "
          f"({n_scanned} json scanned, {len(found)} bool-table candidates)", flush=True)

    # ---- F4 : how many artifacts cite this digest? --------------------------
    grep = subprocess.run(["grep", "-rl", PINNED_DIGEST[:12], SPIKES],
                          capture_output=True, text=True)
    citers = sorted({os.path.relpath(p, ROOT) for p in grep.stdout.split("\n")
                     if p and os.sep + "G101_gate_opening" + os.sep not in p})
    citing_spikes = sorted({c.split(os.sep)[1] for c in citers if c.startswith("spikes" + os.sep)})
    f4_fired = len(citing_spikes) != 9
    print(f"F4 citing-spike count != 9 = {f4_fired}  ({len(citing_spikes)}: "
          f"{', '.join(citing_spikes)})", flush=True)

    # C4: the published artifact must be openable WITHOUT re-running any of the
    # above -- that is the whole point of the row. verify.py is the standing
    # check; this control is the same assertion made against the bytes we write.
    out = {
        "spike": "G101",
        "opens": {
            "digest": PINNED_DIGEST,
            "published_by": "spikes/G59_official_split/official.json:gate.sha256",
            "computed_by": "spikes/G59_official_split/official.py:freeze_gate (official.py:128-148)",
            "serialisation": "sha256(json.dumps({k:v for k,v in payload.items() if k!='sha256'}, sort_keys=True).encode())",
        },
        "payload": {k: v for k, v in payload.items() if k != "sha256"},
        "recomputed_sha256": None,
        "n_entries": n_entries,
        "n_g51_on_derived": on_derived,
        "n_g51_off_derived": off_derived,
        "citing_spikes": citing_spikes,
        "citing_files": citers,
        "inputs": {"file_sha256": hashes, "n_valid_rows": len(dev_rows),
                   "n_rules_2hop": len(rules), "min_dev_n": G59.MIN_DEV_N},
        "controls": {
            "C1_inputs_match_g59": {"pairs": {k: list(v) for k, v in c1_pairs.items()}, "ok": c1_ok},
            "C2_counts_derive_from_table": {"on": on_derived, "off": off_derived,
                                            "published": [PINNED_ON, PINNED_OFF], "ok": c2_ok},
            "C3_digest_pins_the_table": {"victim_key": victim, "mutated_sha256": mut_digest,
                                         "original_sha256": payload["sha256"], "ok": c3_ok},
            "C4_opens_from_artifact_alone": {"ok": None},
        },
        "falsifiers": {
            "F1_reconstruction_does_not_reproduce_digest": {
                "reconstructed": payload["sha256"], "pinned": PINNED_DIGEST, "fired": f1_fired},
            "F2_object_already_published_elsewhere": {
                "n_json_scanned": n_scanned, "candidates": [list(f) for f in found], "fired": f2_fired},
            "F3_digest_does_not_pin_the_table": {
                "victim_key": victim, "mutated_sha256": mut_digest, "fired": f3_fired},
            "F4_citing_spike_count_is_not_nine": {
                "n": len(citing_spikes), "spikes": citing_spikes, "fired": f4_fired},
        },
        "elapsed_sec": None,
    }
    out["recomputed_sha256"] = digest_of(out["payload"])
    out_json = os.path.join(HERE, "gate_open.json")
    out["elapsed_sec"] = round(time.time() - t0, 2)
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=False)
        f.write("\n")

    reread = json.load(open(out_json))
    c4_ok = digest_of(reread["payload"]) == PINNED_DIGEST and len(reread["payload"]["use_g51"]) == n_entries
    out["controls"]["C4_opens_from_artifact_alone"]["ok"] = c4_ok
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=False)
        f.write("\n")
    print(f"C4 re-read from disk opens the digest = {c4_ok}", flush=True)

    controls = [
        Control("C1_inputs_match_g59",
                why="the reconstruction must run on the files G59 recorded, not on whatever is in corpus/ today",
                can_fail_because="corpus/fb15k237 replaced or re-fetched",
                null_must_contain="a file sha256 differing from official.json's"),
        Control("C2_counts_derive_from_table",
                why="G59 published 157/66; if the rebuilt table does not yield them, table and integers are two records that can drift",
                can_fail_because="a table of the wrong size, or a gate fitted on different rows",
                null_must_contain="on/off pair != 157/66"),
        Control("C3_digest_pins_the_table",
                why="a digest invariant to its object pins nothing and publishing the object proves nothing",
                can_fail_because="a serialisation that drops use_g51 -- which is exactly what official.json does",
                null_must_contain="mutated digest equal to the original"),
        Control("C4_opens_from_artifact_alone",
                why="the deliverable is an artifact a third party can open with no re-run; re-reading it from disk is that test",
                can_fail_because="serialisation not recorded, or json round-trip changing key order/types",
                null_must_contain="re-read digest != pinned"),
    ]
    controls[0].observe(c1_ok, out["controls"]["C1_inputs_match_g59"])
    controls[1].observe(c2_ok, out["controls"]["C2_counts_derive_from_table"])
    controls[2].observe(c3_ok, out["controls"]["C3_digest_pins_the_table"])
    controls[3].observe(c4_ok, out["controls"]["C4_opens_from_artifact_alone"])

    falsifiers = [
        Falsifier("F1_reconstruction_does_not_reproduce_digest",
                  refutes="that G59's gate is recoverable from the committed tree",
                  fires_when="reconstructed sha256 != the published 9559856568a9...",
                  null_must_contain="both digests, so a mismatch is readable"),
        Falsifier("F2_object_already_published_elsewhere",
                  refutes="G100's NO_OPENING verdict at these sites, and this row's premise",
                  fires_when="any JSON in spikes/ carries a >=100-entry bool table re-deriving the digest",
                  null_must_contain="the candidate list, empty or not"),
        Falsifier("F3_digest_does_not_pin_the_table",
                  refutes="that opening the digest tells anyone what G59 ran",
                  fires_when="flipping one entry leaves the digest unchanged",
                  null_must_contain="the mutated digest"),
        Falsifier("F4_citing_spike_count_is_not_nine",
                  refutes="the 'most-cited digest in the G-series' framing",
                  fires_when="the mechanical count of citing spikes != 9",
                  null_must_contain="the count and the list"),
    ]
    falsifiers[0].observe(f1_fired, out["falsifiers"]["F1_reconstruction_does_not_reproduce_digest"])
    falsifiers[1].observe(f2_fired, out["falsifiers"]["F2_object_already_published_elsewhere"])
    falsifiers[2].observe(f3_fired, out["falsifiers"]["F3_digest_does_not_pin_the_table"])
    falsifiers[3].observe(f4_fired, out["falsifiers"]["F4_citing_spike_count_is_not_nine"])

    ok, problems = kfcheck.certify(
        HERE,
        deps=[os.path.join(SPIKES, "G59_official_split"),
              os.path.join(SPIKES, "G51_bayesian_lift_scoring"),
              os.path.join(SPIKES, "G54_slice_gated_lift"),
              CORPUS],
        artifacts=[os.path.join(HERE, "reopen.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("gate_open_json", json.dumps(out, sort_keys=True))],
        falsifier="the reconstruction moves the digest, OR the object was published all along, OR the digest does not pin the table",
        allow_dirty=True,
        note="G101: reconstructs and publishes use_g51, the 223-entry object behind G59's gate.sha256.",
    )
    print(f"\nD6 certify ok={ok}", flush=True)
    for pr in problems:
        print(f"  PROBLEM: {pr}", flush=True)
    print(f"elapsed {out['elapsed_sec']:.1f}s", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
