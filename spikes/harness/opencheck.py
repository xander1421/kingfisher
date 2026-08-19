#!/usr/bin/env python3
"""opencheck v1 — a digest you PUBLISH must be openable from the artifacts you publish.

  python3 spikes/harness/opencheck.py              # census over every spike
  python3 spikes/harness/opencheck.py --selfcheck  # two-sided, must exit 0
  python3 spikes/harness/opencheck.py <spike_dir>  # one spike

v1 RATIONALE (§12.7) — THE DEFECT REMOVED: **§12.10 debt, three rows deep and all
three mine.** G99 named the class — A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS
(family C) — G100 swept the G-series and found 17 sites over 7 distinct digests,
G101 opened the most-cited one by re-running its generator. §12.10 says the cycle
for a new failure mode ends at *mechanise it in `spikes/harness/` with a test that
fails before the fix*, and nothing was mechanised for three cycles. The guardrail
was meanwhile violated by its own author: **G100 v1's detector could not see a
repair of its own class**, and emitted a NO_OPENING whose note named the very
container it declared absent.

WHAT THIS ENCODES, AND WHY IT IS A DIFFERENT RULE FROM G100's
  G100 asks *can this digest be opened ANYWHERE in the tree* — the audit question,
  and it needs a cross-artifact index to answer. This module asks the SELF-
  CONTAINMENT question: *can it be opened from the artifacts this spike itself
  publishes?* That is the property a third party with one directory can check, and
  it is the one the mission's byte-compare standard actually needs. A spike that
  fails here may still be openable from a sibling — G100 reports that difference
  and this module deliberately does not.

POPULATION, STATED BECAUSE A CENSUS IS ONLY AS HONEST AS ITS DENOMINATOR
  Only digests that pin an IN-RUN STRUCTURE (a per-key table, mask, gate,
  selection) are in population. A digest of a FILE is out: it opens by reading the
  file, and republishing the corpus inside a result artifact is not the ask. The
  split is by key name, which is a heuristic, and both lists are printed by
  --selfcheck so a reader can disagree with the boundary rather than guess it.

A NESTED COPY OF THE REPO IS PRUNED, and that is ATOM-3's H223, not mine
  A materialised copy of the tree inside `spikes/` gets walked as live source by
  eight harness modules. The property is named here as *a directory that is itself
  a repo root* rather than by a name list — `constcheck.py:93` names the property
  and implements a name list, which H93 is the class for. H223 owns the general
  remedy; this is one module declining to make it worse.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)

# THE NARROW LENS. The broad population (everything a spike publishes that is
# not control evidence and not a file hash) turns out to be dominated by digests
# whose opening is a RE-RUN, not a republication -- a job result, a trace, an
# epoch commitment. Those are not this class. A name carrying one of these words
# says the digest pins an IN-RUN SELECTION STRUCTURE, which is the thing G99
# named. Both counts are printed, because reporting only the broad one would be
# alarmism and reporting only the narrow one would be flattery, and the boundary
# between them is a judgement a reader is entitled to disagree with.
STRUCTURE_WORDS = ("choice", "select", "selector", "gate", "mask", "cap",
                   "table", "assign", "seat", "quorum")
# A digest whose object is a FILE, or a commit. Out of population.
FILE_WORDS = ("file_sha256", "emb_sha256", "diff_sha256", "corpus_sha256",
              "embedding_sha256", "rules_cache_sha256", "triples_bin_sha256",
              "witness_trace_sha256", "source_sha256", "commit", "binary",
              "apk_sha256", "manifest", "blob")
# The smallest container that could plausibly BE a per-key structure.
MIN_TABLE = 20
# A directory carrying all three is a repo root, not a spike (H223).
ROOT_MARKERS = ("MISSION_LOOP.md", "CLAUDE.md", "WORK_QUEUE.md")


def is_hex64(v):
    return isinstance(v, str) and len(v) == 64 and all(
        c in "0123456789abcdef" for c in v.lower())


def is_repo_root(d):
    return all(os.path.exists(os.path.join(d, m)) for m in ROOT_MARKERS)


def containers(node, out):
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
    """A PUBLISHED CLAIM, not a recorded observation and not a file hash.

    THE FIRST POPULATION RULE WAS A KEY-NAME WHITELIST AND IT FAILED IN BOTH
    DIRECTIONS ON THE FIRST LIVE SPIKE IT SAW -- G101, mine, whose answer I
    already knew. It MISSED the two digests G101 actually publishes
    (`recomputed_sha256`, `opens/digest` -- no whitelisted word in either name)
    and it FLAGGED `controls/C3_digest_pins_the_table/mutated_sha256`, which is
    a deliberately perturbed digest recorded as EVIDENCE THAT A NEGATIVE
    CONTROL FIRED and which must never open. **A detector that reports the
    output of a working two-sided control as a defect punishes the spikes that
    did the extra work**, and it matched only because the control's NAME
    contains the word `table`.

    So the rule is structural: everything under `controls/` or `falsifiers/` is
    an observation about a check, not a claim the spike publishes; file and
    commit digests open by reading the file. Everything else is in. This is
    deliberately the UNFLATTERING direction -- it over-reports rather than
    under-reports, because a loose rule that exonerates its author's own spikes
    is A22 sitting inside the instrument (G99's lesson, in my own lane).
    """
    low = (dpath + " " + key).lower()
    if "/controls/" in low or "/falsifiers/" in low:
        return False
    if any(w in low for w in FILE_WORDS):
        return False
    return True


def is_structural(dpath, key):
    low = (dpath + " " + key).lower()
    return any(w in low for w in STRUCTURE_WORDS)


def bulk(obj, depth=0):
    """Largest container size at or below `obj` -- what makes it a candidate."""
    if depth > 6:
        return 0
    if isinstance(obj, dict):
        return max([len(obj)] + [bulk(v, depth + 1) for v in obj.values()])
    if isinstance(obj, list):
        return max([len(obj)] + [bulk(v, depth + 1) for v in obj[:50]])
    return 0


def openings(objs):
    """(blob, label) for every serialisation this repo is known to use.

    Each label names the form, so a verdict says HOW it opened rather than only
    that it did. `payload minus <k>` is the self-describing form G59, G64 and
    G101 all use: the digest is taken over the payload with the field it will
    land in removed, so the opening container is never in the file verbatim.
    """
    for kind, size, obj in objs:
        # SIZE IS NOT THE RIGHT GATE, and this cost the first two arms of
        # --selfcheck. The self-describing payload is a SMALL dict -- G59's is
        # five keys -- that CONTAINS the 223-entry table. Gating on the
        # container's own length skipped exactly the form the repair uses, so
        # the detector could not see a repair of its own class. That is G100
        # v1's defect arriving in the module written to remove it.
        if bulk(obj) < MIN_TABLE:
            continue
        yield json.dumps(obj, sort_keys=True), "bare sort_keys", size
        if kind == "dict":
            for hk, hv in obj.items():
                if is_hex64(hv):
                    yield (json.dumps({k: v for k, v in obj.items() if k != hk},
                                      sort_keys=True),
                           f"payload minus {hk}", size)
            # G87/G88's mix.py form: the table wrapped with its min_n.
            for mk, mv in obj.items():
                if mk.endswith("min_n") and isinstance(mv, int):
                    for tk, tv in obj.items():
                        if isinstance(tv, dict) and len(tv) >= MIN_TABLE:
                            yield (json.dumps({"min_n": mv, "choice": tv},
                                              sort_keys=True),
                                   f"mix.py {{min_n={mv},choice}}", len(tv))


def publish(payload, key="sha256"):
    """The cure, at the WRITE site: you cannot get the digest without the object.

        art["gate"] = opencheck.publish({"min_dev_n": 20, "use_g51": table})

    G59's `freeze_gate` RETURNED the whole payload and `official.py:282-285`
    then wrote three of its five keys, so the object was lost at publication and
    not at computation. Nine spikes cited the result and none could open it. A
    function that returns payload+digest together makes that particular edit
    unwritable; it does not make it impossible, which is why `--selfcheck` and
    the census exist as well.
    """
    if key in payload:
        raise ValueError(f"{key!r} is already in the payload; the digest must "
                         f"be taken over the object, not over itself")
    blob = json.dumps(payload, sort_keys=True).encode()
    return dict(payload, **{key: hashlib.sha256(blob).hexdigest()})


def check_spike(spike_dir):
    """[(artifact, path, digest, verdict, reason)] for one spike directory."""
    arts = [os.path.join(spike_dir, f) for f in sorted(os.listdir(spike_dir))
            if f.endswith(".json") and f != "provenance.json"]
    objs, docs = [], []
    for p in arts:
        try:
            d = json.load(open(p))
        except (OSError, ValueError):
            continue
        docs.append((p, d))
        containers(d, objs)
    index = {}
    for blob, label, size in openings(objs):
        index.setdefault(hashlib.sha256(blob.encode()).hexdigest(),
                         (label, size))
    rows = []
    for p, d in docs:
        for dpath, key, digest, parent in digest_sites(d):
            if not in_population(dpath, key):
                continue
            if digest in index:
                label, size = index[digest]
                rows.append((p, dpath, digest, "OPENABLE",
                             f"{label} over {size} entries"))
            else:
                biggest = max([s for _, s, _ in objs] or [0])
                rows.append((p, dpath, digest, "NO_OPENING",
                             f"largest container published here is {biggest}"))
    return rows


def spike_dirs():
    out = []
    for name in sorted(os.listdir(SPIKES)):
        d = os.path.join(SPIKES, name)
        if not os.path.isdir(d) or name in ("harness", "__pycache__"):
            continue
        if is_repo_root(d):
            continue
        out.append(d)
        for sub in sorted(os.listdir(d)):
            sd = os.path.join(d, sub)
            if os.path.isdir(sd) and is_repo_root(sd):
                out.pop()          # a spike holding a repo copy is not scanned
                break
    return out


def census(targets=None):
    dirs = targets or spike_dirs()
    allrows = []
    for d in dirs:
        try:
            allrows += check_spike(d)
        except OSError:
            continue
    return allrows


# --------------------------------------------------------------------------
# --selfcheck: four constructed arms (F3) and two named positions (F4).
# A detector that only ever agrees is one nobody can trust.
# --------------------------------------------------------------------------
def _fixture(tmp, name, doc):
    d = os.path.join(tmp, name)
    os.makedirs(d, exist_ok=True)
    json.dump(doc, open(os.path.join(d, "result.json"), "w"))
    return d


def selfcheck():
    import shutil
    tmp = os.path.join(ROOT, ".scratch", "opencheck_selfcheck")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    table = {str(i): (i % 3 == 0) for i in range(60)}
    payload = {"min_dev_n": 20, "use_gate": table}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    arms = []
    # A1 — the defect: the digest with only a SUMMARY of the object beside it.
    d = _fixture(tmp, "A1_dropped", {"gate": {"n_on": 20, "n_off": 40,
                                              "sha256": digest}})
    arms.append(("A1 a dropped object is FLAGGED",
                 [r[3] for r in check_spike(d)] == ["NO_OPENING"]))
    # A2 — the repair: same digest, object published, self-describing form.
    d = _fixture(tmp, "A2_published", {"gate": dict(payload, sha256=digest)})
    arms.append(("A2 the same digest with its object is NOT flagged",
                 [r[3] for r in check_spike(d)] == ["OPENABLE"]))
    # A3 — an artifact with no digests at all must produce no rows.
    d = _fixture(tmp, "A3_nodigest", {"mrr": 0.1358, "n": 223})
    arms.append(("A3 an artifact with no digest produces no rows",
                 check_spike(d) == []))
    # A4 — a FILE digest is out of population even with no object beside it.
    d = _fixture(tmp, "A4_filehash", {"inputs": {"file_sha256": digest}})
    arms.append(("A4 a file digest is out of population",
                 check_spike(d) == []))
    # A5 — one flipped entry must NOT open it: the index pins the object.
    bad = dict(table)
    bad["0"] = not bad["0"]
    d = _fixture(tmp, "A5_perturbed",
                 {"gate": {"min_dev_n": 20, "use_gate": bad, "sha256": digest}})
    arms.append(("A5 a one-entry perturbation does NOT open the digest",
                 [r[3] for r in check_spike(d)] == ["NO_OPENING"]))
    # A7 — the trap that killed the first population rule: a digest recorded
    # under `controls/` as evidence a NEGATIVE control fired must never be
    # reported. It cannot open, by construction, and that is the point of it.
    d = _fixture(tmp, "A7_control_evidence",
                 {"controls": {"C1_pins": {"mutated_sha256": digest,
                                           "fired": True}}})
    arms.append(("A7 a mutated digest recorded under controls/ is NOT reported",
                 check_spike(d) == []))
    # A8 — the cure round-trips: publish() output opens under this detector,
    # and it refuses to hash a payload that already carries the digest field.
    pub = publish({"min_dev_n": 20, "use_gate": table})
    d = _fixture(tmp, "A8_publish_helper", {"gate": pub})
    round_trips = [r[3] for r in check_spike(d)] == ["OPENABLE"]
    try:
        publish(pub)
        refuses = False
    except ValueError:
        refuses = True
    arms.append(("A8 publish() output opens, and it refuses to re-hash itself",
                 round_trips and refuses))
    # A6 — a nested repo root is pruned rather than scanned.
    nested = os.path.join(tmp, "A6_copy", "fresh")
    os.makedirs(nested, exist_ok=True)
    for m in ROOT_MARKERS:
        open(os.path.join(nested, m), "w").close()
    arms.append(("A6 a directory holding a repo root is pruned",
                 is_repo_root(nested) and not is_repo_root(tmp)))

    # F4 — named positions in the live tree. A detector is not trusted on
    # fixtures alone; these two are the ones whose answer is already known.
    g101 = os.path.join(SPIKES, "G101_gate_opening")
    g59 = os.path.join(SPIKES, "G59_official_split")
    if os.path.isdir(g101):
        v = [r[3] for r in check_spike(g101)]
        arms.append(("F4a G101 opens from its own artifacts",
                     bool(v) and set(v) == {"OPENABLE"}))
    else:
        arms.append(("F4a G101 opens from its own artifacts",
                     False))          # absent is a FAIL, not a skip
    if os.path.isdir(g59):
        v = [r[3] for r in check_spike(g59)]
        arms.append(("F4b G59 does NOT open from its own artifacts",
                     "NO_OPENING" in v))
    else:
        arms.append(("F4b G59 does NOT open from its own artifacts", False))

    bad = 0
    for name, ok in arms:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        bad += not ok
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nopencheck --selfcheck: {len(arms) - bad}/{len(arms)} arms pass")
    return 1 if bad else 0


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    targets = [a for a in argv[1:] if not a.startswith("-")]
    rows = census([os.path.abspath(t) for t in targets] if targets else None)
    narrow = [r for r in rows if is_structural(r[1], r[1].rsplit("/", 1)[-1])]
    for label, rs in (("NARROW — the digest names an in-run structure", narrow),
                      ("BROAD — every published digest that is not control "
                       "evidence or a file hash", rows)):
        n_open = sum(1 for r in rs if r[3] == "OPENABLE")
        n_shut = len(rs) - n_open
        sp = sorted({os.path.basename(os.path.dirname(r[0]))
                     for r in rs if r[3] == "NO_OPENING"})
        if rs is narrow:
            for p, dpath, digest, verdict, reason in rs:
                if verdict == "NO_OPENING":
                    print(f"  {verdict:12} {os.path.relpath(p, ROOT)}{dpath}  "
                          f"{digest[:12]}\n                 {reason}")
        print(f"\n{label}")
        print(f"  {n_open:5}  OPENABLE from the spike's own artifacts")
        print(f"  {n_shut:5}  NO_OPENING  in {len(sp)} spike(s)")
        if rs is narrow:
            print(f"         {' '.join(sp) if sp else '(none)'}")
    print("\nreport-only in v1. Whether this becomes a certify refusal is decided"
          "\nby the number above, not by preference — see WORK_QUEUE.md H226.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
