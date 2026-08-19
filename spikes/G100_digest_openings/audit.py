#!/usr/bin/env python3
"""G100 — which published digests in the G-series can actually be opened?

Run: python3 spikes/G100_digest_openings/audit.py   (a few seconds, reads only)

G99 named a class -- A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS (family C) --
fixed ONE site, and closed with `SCOPE: G88's artifact only`. That records the
gap honestly and does not discharge it. §12.2: name the class, then grep the
whole tree for it before closing the row. This is that grep, and it is a cycle
late.

WHAT THE VERDICT MEANS, because the sound half and the guessed half must not be
reported as one number.

  NO_OPENING is SOUND, not heuristic. It is emitted only when a digest pins a
  per-key SELECTION STRUCTURE and the artifact carrying it contains no container
  of comparable size at all. You cannot reconstruct a 446-entry table from an
  artifact whose largest container is five integers, under ANY serialisation --
  so no assumption about how the digest was computed is needed to say the object
  is absent. That is the whole reason the detector keys on CONTAINER SIZE rather
  than on trying to guess the serialisation and recompute.

  OPENABLE_VERIFIED is also sound: the table is present AND its digest
  re-derives byte-identically under the serialisation the producing spike used.

  OPENABLE_STRUCTURE_PRESENT is the WEAK verdict and is labelled weak wherever it
  appears. A container of the right size is present, but its serialisation was
  not discovered, so this says "an opening plausibly exists", never "the digest
  opens". It is NOT counted as clean in the headline.

  v2, 2026-08-19 (AGENT-2, G101). DEFECT REMOVED: **the cross-artifact index
  indexed only TABLE-SHAPED containers, so it could not see a repair of its own
  class.** G101 opened `9559856568a9...` by publishing the 223-entry `use_g51`
  table inside the digest's PAYLOAD -- a five-key dict whose sort_keys hash IS
  the digest, which is the shape any correctly repaired site takes, since the
  object is republished under the serialisation the digest was computed with.
  v1's index skipped every container that was not itself a >=20-entry table, so
  it hashed the 223-entry table and never the payload wrapping it, and the nine
  G59-gate sites stayed NO_OPENING after the object had been published. A
  detector that cannot see the repair it exists to motivate reports the same
  number forever. v2 additionally indexes EVERY dict/list container under bare
  sort_keys; a digest equal to such a hash is an opening by construction, so
  this widens what is found without weakening what it means.

  Digests over FILES (`file_sha256/train.txt`, `artifacts[].sha256`,
  `*_emb_sha256`, `diff_sha256`) are OUT OF POPULATION. Their object is a file on
  disk, which is the normal pinning idiom and not this class. Excluding them is a
  scope limit and is printed as one, because H105's class is a correct scope
  limit plus a habit that overstates it.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)

# A digest whose NAME says it pins an in-run selection structure -- a per-key
# table, mask or gate -- rather than a file. Matched on the key name and on the
# name of the object it sits beside.
STRUCTURE_WORDS = ("choice", "select", "selector", "gate", "mask", "cap",
                   "head_choice", "pred_gate", "dir_gate")
# Names whose object is a FILE. Out of population; see the docstring.
FILE_WORDS = ("file_sha256", "emb_sha256", "diff_sha256", "corpus_sha256",
              "embedding_sha256", "rules_cache_sha256", "triples_bin_sha256",
              "witness_trace_sha256", "source_sha256")
# The smallest container that could plausibly BE a per-key table. G88's is 446;
# the largest merely-summary container in this population is 5 (the arm counts).
MIN_TABLE = 20


def is_hex64(v):
    return isinstance(v, str) and len(v) == 64 and all(
        c in "0123456789abcdef" for c in v.lower())


def table_shaped(kind, size, obj):
    """Could this container BE a per-key selection table?

    SIZE ALONE IS NOT THE TEST, and my first draft used it -- which put my OWN
    G95, G96 and G98 in the soft bucket on the strength of `null_draws`, a list
    of 1000 FLOATS that is not a table of anything. A detector whose loose rule
    happens to flatter its author's spikes is the A22 shape, in the instrument.

    A per-key table maps a key to an ARM NAME, so the realistic encodings are a
    dict of string values, or a list of pairs. A list of numbers is neither, and
    rejecting it is sound: no serialisation recovers 446 key->arm entries from
    1000 floats.
    """
    if size < MIN_TABLE:
        return False
    if kind == "dict":
        vals = list(obj.values())
        return sum(1 for v in vals if isinstance(v, str)) >= 0.9 * len(vals)
    return all(isinstance(v, (list, dict)) and len(v) == 2 for v in obj[:50])


def containers(node, out):
    """Every dict/list in the artifact, with its size."""
    if isinstance(node, dict):
        out.append(("dict", len(node), node))
        for v in node.values():
            containers(v, out)
    elif isinstance(node, list):
        out.append(("list", len(node), node))
        for v in node[:200]:
            containers(v, out)
    return out


def digest_sites(node, path=""):
    """(path, key, value, parent) for every 64-hex string in the artifact."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if is_hex64(v):
                out.append((path + "/" + k, k, v, node))
            out += digest_sites(v, path + "/" + k)
    elif isinstance(node, list):
        for i, v in enumerate(node[:200]):
            out += digest_sites(v, path + "/[]")
    return out


def in_population(dpath, key):
    low = (dpath + " " + key).lower()
    if any(w in low for w in FILE_WORDS):
        return False
    return any(w in low for w in STRUCTURE_WORDS)


def try_reopen(art, dpath, digest, tables):
    """Re-derive the digest from a candidate table under known serialisations.

    Only serialisations ACTUALLY USED by spikes in this repo are tried, and each
    is named in the returned reason. A failure here never upgrades to NO_OPENING
    -- absence is decided by container size alone (see the docstring).
    """
    # min_n is nested differently by different spikes (G88 emits `choice_min_n`
    # at top level, G98 puts it under `selector_mask`), so it is SEARCHED FOR
    # rather than read from a fixed path. Discovering the serialisation is this
    # function's job; requiring every spike to use G88's field names would be
    # tuning the artifacts to the detector instead of the other way round.
    min_ns = []

    def find_min_n(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if k.endswith("min_n") and isinstance(v, int):
                    min_ns.append(v)
                find_min_n(v)
        elif isinstance(n, list):
            for v in n[:50]:
                find_min_n(v)
    find_min_n(art)
    for label, size, tbl in tables:
        if label != "dict" or size < MIN_TABLE:
            continue
        cands = []
        for min_n in dict.fromkeys(min_ns):
            # mix.py:124 -- G88/G87's form.
            cands.append((f"mix.py {{min_n={min_n},choice}}",
                          json.dumps({"min_n": min_n, "choice": tbl}, sort_keys=True)))
        cands.append(("bare sort_keys", json.dumps(tbl, sort_keys=True)))
        for reason, blob in cands:
            if hashlib.sha256(blob.encode()).hexdigest() == digest:
                return reason, size
    return None, None


def main() -> int:
    arts = sorted(glob.glob(os.path.join(SPIKES, "G*", "*.json")))
    rows = []
    for p in arts:
        if os.path.basename(p) == "provenance.json":
            continue          # the certificate, not the spike's own claim
        try:
            art = json.loads(open(p, encoding="utf-8").read())
        except Exception:
            continue
        sites = [s for s in digest_sites(art) if in_population(s[0], s[1])]
        if not sites:
            continue
        tables = [(t, n, o) for (t, n, o) in containers(art, []) if table_shaped(t, n, o)]
        biggest = max([n for (_, n, _) in containers(art, [])] or [0])
        for dpath, key, digest, parent in sites:
            reason, size = try_reopen(art, dpath, digest, tables)
            if reason:
                verdict, note = "OPENABLE_VERIFIED", f"re-derives under {reason} over {size} entries"
            elif tables:
                verdict, note = ("OPENABLE_STRUCTURE_PRESENT",
                                 f"a TABLE-SHAPED container of "
                                 f"{max(n for _, n, _ in tables)} entries exists; "
                                 f"serialisation not discovered (WEAK)")
            else:
                verdict, note = ("NO_OPENING",
                                 f"no TABLE-SHAPED container (dict of string values, or "
                                 f"list of pairs, >= {MIN_TABLE} entries); largest "
                                 f"container of any kind is {biggest}")
            rows.append((os.path.relpath(p, os.path.dirname(SPIKES)), dpath, digest[:12], verdict, note))

    # CROSS-ARTIFACT OPENINGS. A digest with no opening in its OWN artifact is
    # not necessarily lost: eight spikes cite the same `pred_gate` digest, so it
    # can be published in a sibling. CORRECTED 2026-08-19 (AGENT-2, G101): this
    # comment used to end "and one of them publishes the table", naming G75. It
    # was never checked. G75's `g59_pred_gate` has THREE keys -- n_g51_on,
    # n_g51_off, sha256 -- which is a citation, and G101's F2 hashed 1326 JSONs
    # under every serialisation and found ZERO publications of that object. The
    # sentence was an assumption written as a measurement, and it propagated into
    # the WORK_QUEUE row, CHANNEL and a journal NEXT item that planned a
    # re-run-free "pointer" to a table that did not exist. So every table found
    # anywhere in the G-series
    # is hashed under every serialisation seen, and NO_OPENING sites are looked
    # up in that index. This is the difference between "unopenable" and
    # "unopenable from where it is published", and reporting the first when the
    # second is true would overstate the finding.
    index = {}
    for p2 in arts:
        if os.path.basename(p2) == "provenance.json":
            continue
        try:
            a2 = json.loads(open(p2, encoding="utf-8").read())
        except Exception:
            continue
        mins = []

        def fm(n):
            if isinstance(n, dict):
                for k, v in n.items():
                    if k.endswith("min_n") and isinstance(v, int):
                        mins.append(v)
                    fm(v)
            elif isinstance(n, list):
                for v in n[:50]:
                    fm(v)
        fm(a2)
        for kind, size, obj in containers(a2, []):
            # v2 (G101): EVERY container is indexed under bare sort_keys, not
            # only table-shaped ones. A repaired site republishes the object
            # inside the payload the digest was taken over -- a small dict --
            # and v1 could not see it. Equality with a container's own hash is
            # an opening by construction, so nothing here is heuristic.
            blobs = [("bare sort_keys", json.dumps(obj, sort_keys=True))]
            # v2 (G101): THE SELF-DESCRIBING PAYLOAD. G59, G64 and G101 all take
            # the digest over the payload MINUS the field the digest lands in,
            # so the container that opens it is never in the file verbatim --
            # it is the file's container with one key removed. Without this,
            # G64 published its own 223-entry object and this audit still called
            # it NO_OPENING, pointing at the very container it declared absent.
            if kind == "dict":
                for hk, hv in obj.items():
                    if is_hex64(hv):
                        blobs.append((f"payload minus {hk}", json.dumps(
                            {k: v for k, v in obj.items() if k != hk}, sort_keys=True)))
            if table_shaped(kind, size, obj):
                for mn in dict.fromkeys(mins):
                    blobs.append((f"{{min_n={mn},choice}}",
                                  json.dumps({"min_n": mn, "choice": obj}, sort_keys=True)))
            for reason, blob in blobs:
                index.setdefault(hashlib.sha256(blob.encode()).hexdigest(),
                                 (os.path.relpath(p2, os.path.dirname(SPIKES)),
                                  reason, size))

    for i, (f, dp, dg, v, note) in enumerate(rows):
        # v2 (G101): the WEAK verdict is looked up too. v1 skipped it, so a site
        # whose own artifact merely CONTAINS a same-size table stayed WEAK even
        # when another artifact opens the digest outright -- the strictly better
        # answer was in the index and never read.
        if v not in ("NO_OPENING", "OPENABLE_STRUCTURE_PRESENT"):
            continue
        full = [d for d in index if d.startswith(dg)]
        if full:
            where, reason, size = index[full[0]]
            if where == f:
                # v2 (G101): a hit in the row's OWN file is not an elsewhere.
                rows[i] = (f, dp, dg, "OPENABLE_VERIFIED",
                           f"re-derives from this artifact under '{reason}' "
                           f"over {size} entries")
            else:
                rows[i] = (f, dp, dg, "OPENS_ELSEWHERE",
                           f"absent here, but re-derives from {where} "
                           f"({size} entries, {reason})")
        else:
            # v2 (G101): a surviving NO_OPENING now means MORE than "this
            # artifact has no table". The index has tried every container in the
            # population, bare and payload-minus-digest, so the note says what
            # was actually searched instead of restating the local test.
            rows[i] = (f, dp, dg, v, note + "; and no container anywhere in the "
                       "scanned population opens it under any serialisation tried")

    order = {"NO_OPENING": 0, "OPENS_ELSEWHERE": 1,
             "OPENABLE_STRUCTURE_PRESENT": 2, "OPENABLE_VERIFIED": 3}
    rows.sort(key=lambda r: (order[r[3]], r[0]))
    counts = {v: sum(1 for r in rows if r[3] == v) for v in order}

    print("G100 v2 — G-series digests that pin an in-run SELECTION STRUCTURE")
    print(f"population: {len(arts)} G-series JSON artifacts scanned, "
          f"{len(rows)} in-population digest sites")
    print("OUT OF POPULATION and NOT audited: digests over FILES "
          "(file_sha256/*, artifacts[].sha256, *_emb_sha256, diff_sha256) — their")
    print("object is a file on disk. NOT audited at all: S-, H-, M-, W-series.\n")
    for f, dp, dg, v, note in rows:
        print(f"  {v:28s} {f}{dp}  {dg}")
        print(f"  {'':28s}   {note}")
    print()
    for v in ("NO_OPENING", "OPENS_ELSEWHERE",
              "OPENABLE_STRUCTURE_PRESENT", "OPENABLE_VERIFIED"):
        print(f"  {counts[v]:3d}  {v}")
    print("\nOPENABLE_STRUCTURE_PRESENT is a WEAK verdict and is NOT counted as "
          "clean: it says an opening plausibly exists, never that the digest opens.")

    # F3, the detector's own control: the site G99 FIXED must come out verified.
    # If a detector cannot see the one repair it was written to generalise, every
    # other verdict it emits is void.
    g88 = [r for r in rows if "G88_5way_hybrid/result.json" in r[0]]
    ok = bool(g88) and all(r[3] == "OPENABLE_VERIFIED" for r in g88)
    print(f"\nF3 control — the already-fixed G88 site: "
          f"{'OPENABLE_VERIFIED, detector encodes the property' if ok else 'NOT VERIFIED — DETECTOR VOID'}")

    # F4/F5, v2's own two-sided pair (G101). A widened index needs both halves:
    # a KNOWN POSITIVE it must find, and a PERTURBATION it must not. Neither is
    # a literal -- F4 fails if the cross-artifact pass regresses, F5 fails if the
    # lookup ever matches loosely, and the perturbed digest is computed here from
    # the same published object rather than typed in.
    g59_rows = [r for r in rows if "G59_official_split/official.json/gate/sha256" in r[0] + r[1]]
    f4 = bool(g59_rows) and all(r[3] == "OPENS_ELSEWHERE" and "G101_gate_opening" in r[4]
                                for r in g59_rows)
    print(f"F4 known positive — G59's gate site resolves to G101: "
          f"{'yes' if f4 else 'NO — the cross-artifact pass has regressed'}")

    f5 = True
    try:
        g101 = json.load(open(os.path.join(SPIKES, "G101_gate_opening", "gate_open.json")))
        pay = dict(g101["payload"])
        tbl = dict(pay["use_g51"])
        victim = sorted(tbl)[0]
        tbl[victim] = not tbl[victim]
        pay["use_g51"] = tbl
        perturbed = hashlib.sha256(json.dumps(pay, sort_keys=True).encode()).hexdigest()
        f5 = not [d for d in index if d.startswith(perturbed[:12])]
        print(f"F5 negative control — a one-entry perturbation of that same object "
              f"is NOT in the index: {'yes' if f5 else 'NO — the lookup matches loosely'}")
    except (OSError, KeyError, ValueError) as e:
        print(f"F5 negative control — SKIPPED, and a skipped control is not a passed "
              f"one: {e}")
        f5 = False

    return 0 if (ok and f4 and f5) else 1


if __name__ == "__main__":
    sys.exit(main())
