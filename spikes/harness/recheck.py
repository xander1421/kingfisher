#!/usr/bin/env python3
"""recheck.py v1 — H69. Does a `provenance.json` still describe the tree?

THE DEFECT THIS REMOVES
-----------------------
`kfcheck.certify` refuses at the **END** of a run. So it cannot refuse for a run
that never reaches it, and nothing in this harness ever re-reads a record that is
already on disk. A record is written once, `ok=true`, and is thereafter believed
forever — by every agent that walks into the directory and reads it.

Earned 2026-08-17 in `spikes/G38_evolved_on_yardstick/` (AGENT-2, C13). That run
crashed on a summary line one edit after a green run, so the directory sat at
`provenance.json ok=true` recording `evolved.py` at sha256 `51c78697…`/13967
bytes while the file on disk was `d9ed8e81…`/17093 bytes. The certificate
described a generator that no longer existed, and everything about the directory
read CERTIFIED.

SWEPT BEFORE IT WAS CALLED A CLASS, which is the part worth copying: one instance
is a bug. At the time of writing, **13 of 45 records under `spikes/` no longer
describe the tree and 11 of those read `ok=true`** — 5 by artifact-hash drift
(G25, G30, G34, G38, M2_1_fleet), 8 by a recorded path that is not on disk.

SCOPE, STATED HERE BECAUSE THE LOUD READING IS THE WRONG ONE
------------------------------------------------------------
This says the RECORD is unverified. It does **not** say any published number is
wrong, and it must never be quoted as though it did. G30's and G34's figures were
independently byte-reproduced by G36, so their drift is a later edit to a
generator, not a bad measurement. "Correct numbers pointing at the wrong cause"
is the second of `CLAUDE.md`'s three unmechanisable failures and this module is
exactly the shape that invites it.

REPORTS, DOES NOT GATE (H33/H54)
--------------------------------
Exit status is 0 whatever it finds, and that is deliberate rather than timid. The
party who trips this is a *reader* of someone else's spike; the only party who
can clear it is the author, by re-running the spike. A gate a non-author trips
and cannot clear is the gate H14 records everyone learning to bypass, and the
bypass then covers the cases that were real. `--strict` exists for a caller who
has *just written* a record and wants a non-zero exit on its own directory.

WHAT IT CANNOT SEE, so nobody reads a green run as more than it is:
  * a record whose artifact list never covered the file that mattered — an empty
    `artifacts=[]` re-hashes cleanly and says nothing (A28's shape one level up);
  * a drifted artifact whose *content* is equivalent — a comment-only edit reads
    identically to a rewritten algorithm here;
  * whether the recorded numbers were ever right. This is a byte check.
"""
import hashlib
import json
import os
import sys

VERSION = 1

OK, DRIFTED, MISSING, UNREADABLE, NO_ARTIFACTS = (
    "OK", "DRIFTED", "MISSING", "UNREADABLE", "NO_ARTIFACTS")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_records(root):
    """Every `provenance.json` under `root`, skipping dot-directories.

    Dot-directories are skipped so this module's own `--selfcheck` fixture
    cannot be picked up by a real scan. H64 is the general form of that hazard:
    test fixtures living in the same namespace as real entries, reserved by
    convention and by nothing else.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if "provenance.json" in filenames:
            out.append(os.path.join(dirpath, "provenance.json"))
    return sorted(out)


def check_record(rec_path):
    """Re-hash one record's artifacts against disk.

    Returns `{'record', 'ok', 'status', 'artifacts': [(status, path, why)]}`.
    `ok` is what the RECORD claims about itself; `status` is what the tree says.
    The interesting combination is `ok=True` with a status that is not OK.
    """
    try:
        with open(rec_path) as f:
            rec = json.load(f)
    except (OSError, ValueError) as e:
        return {"record": rec_path, "ok": None, "status": UNREADABLE,
                "artifacts": [(UNREADABLE, rec_path, str(e))]}

    arts = rec.get("artifacts") or []
    if not arts:
        return {"record": rec_path, "ok": rec.get("ok"),
                "status": NO_ARTIFACTS, "artifacts": []}

    rec_dir = os.path.dirname(os.path.abspath(rec_path))
    rows, worst = [], OK
    for a in arts:
        path, recorded = a.get("path"), a.get("sha256")
        if not path or not recorded:
            rows.append((UNREADABLE, str(path), "record has no path or sha256"))
            worst = UNREADABLE
            continue
        # A RELATIVE `path` IS RELATIVE TO THE RECORD, NOT TO THE CALLER'S CWD.
        # v1's first live run resolved these against CWD and reported all 8
        # relative-path records under `spikes/` as MISSING -- every one of them
        # false, and every file present beside its own record. Family B, the
        # instrument reporting fiction, inside the module written to catch a
        # family-C fiction, and the wrong count reached livechat.log, CHANNEL.md
        # and the H69 row before it was checked. Asserted in `selfcheck`.
        if not os.path.isabs(path):
            path = os.path.join(rec_dir, path)
        if not os.path.exists(path):
            rows.append((MISSING, path, "recorded path is not on disk"))
            if worst != UNREADABLE:
                worst = MISSING
            continue
        actual = _sha256(path)
        if actual != recorded:
            rows.append((DRIFTED, path,
                         f"recorded {recorded[:16]}… "
                         f"({a.get('bytes')} B), disk {actual[:16]}… "
                         f"({os.path.getsize(path)} B)"))
            if worst not in (UNREADABLE, MISSING):
                worst = DRIFTED
        else:
            rows.append((OK, path, ""))
    return {"record": rec_path, "ok": rec.get("ok"), "status": worst,
            "artifacts": rows}


def report(results, out=sys.stdout):
    bad = [r for r in results if r["status"] not in (OK,)]
    green = [r for r in results if r["status"] == OK]
    print(f"recheck v{VERSION} — {len(results)} provenance record(s) re-hashed "
          f"against the tree", file=out)
    print(f"  {len(green)} still describe it, {len(bad)} do not\n", file=out)
    for r in bad:
        claims = ("ok=%s" % r["ok"]) if r["ok"] is not None else "ok=?"
        flag = "  <-- CLAIMS ok=true" if r["ok"] is True else ""
        print(f"  {r['status']:<12} {claims:<8} {r['record']}{flag}", file=out)
        for st, path, why in r["artifacts"]:
            if st != OK:
                print(f"      {st:<10} {path}", file=out)
                if why:
                    print(f"                 {why}", file=out)
    lying = [r for r in bad if r["ok"] is True]
    if bad:
        print(f"\n  {len(lying)} of the {len(bad)} read `ok=true`.", file=out)
        print("  This says the RECORD is unverified. It does NOT say a "
              "published number is wrong —", file=out)
        print("  a drifted generator is usually a later edit. Re-run the spike "
              "to clear it.", file=out)
    else:
        print("  every recorded artifact re-hashes to its recorded sha256.",
              file=out)
    return bad


def selfcheck():
    """Fails when this module breaks. §12.3.

    Two fixtures, deliberately: a POSITIVE that must report exactly one drift and
    one missing, and a NEGATIVE that must report nothing. Without the negative,
    a checker that reported every record as broken would pass — `CLAUDE.md`'s
    "a control that cannot fail is not a control", applied to the checker itself.
    """
    import shutil
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        ".recheck_selfcheck")   # dot-dir: invisible to a real scan
    shutil.rmtree(base, ignore_errors=True)
    try:
        def fixture(name, drift, drop, relative=False):
            d = os.path.join(base, name)
            os.makedirs(d)
            arts = []
            for i, tag in enumerate(("kept", "edited", "deleted")):
                p = os.path.join(d, f"{tag}.txt")
                with open(p, "w") as f:
                    f.write(f"original {i}\n")
                arts.append({"path": os.path.basename(p) if relative else p,
                             "sha256": _sha256(p),
                             "bytes": os.path.getsize(p)})
            if drift:
                with open(os.path.join(d, "edited.txt"), "w") as f:
                    f.write("rewritten, and the record does not know\n")
            if drop:
                os.remove(os.path.join(d, "deleted.txt"))
            with open(os.path.join(d, "provenance.json"), "w") as f:
                json.dump({"ok": True, "artifacts": arts}, f)
            return d

        fixture("positive", drift=True, drop=True)
        fixture("negative", drift=False, drop=False)
        # the case v1 got wrong on its first live run: a record whose paths are
        # RELATIVE, checked from a CWD that is not the record's directory. It
        # must come back clean. Without this the fix is untested and regresses.
        fixture("relative_clean", drift=False, drop=False, relative=True)

        recs = find_records(base)
        assert len(recs) == 3, f"expected 3 records, walked {len(recs)}"
        by = {os.path.basename(os.path.dirname(r)): check_record(r)
              for r in recs}

        pos = by["positive"]
        sts = [s for s, _, _ in pos["artifacts"]]
        assert sts.count(DRIFTED) == 1, f"positive: drift {sts}"
        assert sts.count(MISSING) == 1, f"positive: missing {sts}"
        assert sts.count(OK) == 1, f"positive: ok {sts}"
        assert pos["status"] == MISSING, f"positive worst: {pos['status']}"

        neg = by["negative"]
        assert neg["status"] == OK, f"negative reported {neg['status']}"
        assert all(s == OK for s, _, _ in neg["artifacts"]), neg["artifacts"]

        rel = by["relative_clean"]
        assert rel["status"] == OK, \
            f"relative paths resolved against CWD, not the record: {rel}"
        # and it must still SEE a drift through a relative path, or the fix
        # above would have been "call everything relative fine"
        with open(os.path.join(base, "relative_clean", "edited.txt"), "w") as f:
            f.write("rewritten behind a relative path\n")
        rel2 = check_record(os.path.join(base, "relative_clean",
                                         "provenance.json"))
        assert rel2["status"] == DRIFTED, \
            f"relative path hid a real drift: {rel2}"

        # a record with no artifacts re-hashes cleanly and says nothing: the
        # module's own documented blind spot, asserted so it stays documented
        empty = os.path.join(base, "empty")
        os.makedirs(empty)
        with open(os.path.join(empty, "provenance.json"), "w") as f:
            json.dump({"ok": True, "artifacts": []}, f)
        assert check_record(os.path.join(empty, "provenance.json"))["status"] \
            == NO_ARTIFACTS

        # the fixture must be invisible to a scan rooted above it (H64)
        parent = os.path.dirname(base)
        assert not [r for r in find_records(parent) if base in r], \
            "dot-dir fixture leaked into a real scan"

        print(f"recheck v{VERSION} selfcheck: PASS "
              "(positive 1 drift + 1 missing + 1 ok; negative clean; "
              "empty-artifacts blind spot held; fixture invisible to a real scan)")
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    strict = "--strict" in argv
    roots = [a for a in argv[1:] if not a.startswith("-")] or ["spikes"]
    results = []
    for root in roots:
        results.extend(check_record(r) for r in find_records(root))
    bad = report(results)
    return 1 if (strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
