#!/usr/bin/env python3
"""G101 standing check — opens the digest from the ARTIFACT alone, no re-run.

  python3 spikes/G101_gate_opening/verify.py        (< 1 s, reads only)

This is the check MISSION_LOOP §12.3 asks for, and it is deliberately the check a
THIRD PARTY would run: it never imports G59, never touches corpus/, and never
recomputes the gate. It reads `gate_open.json`, re-derives the digest from the
published payload under the recorded serialisation, and compares it to the
digest `spikes/G59_official_split/official.json` published -- read from that file
rather than typed here, so the two records cannot drift apart silently (H39).

It also asserts the counts are DERIVABLE from the table. G99 shipped that
assertion for the same reason: five published integers and the object they
summarise must be one record, or a later reader has two sources and no way to
tell which is stale.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)


def digest_of(payload):
    body = {k: v for k, v in payload.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def main():
    art = json.load(open(os.path.join(HERE, "gate_open.json")))
    g59 = json.load(open(os.path.join(SPIKES, "G59_official_split", "official.json")))

    published = g59["gate"]["sha256"]
    reopened = digest_of(art["payload"])
    table = art["payload"]["use_g51"]
    on = sum(1 for v in table.values() if v)
    off = sum(1 for v in table.values() if not v)

    checks = [
        ("digest re-derives from the published table",
         reopened == published, f"{reopened[:12]} vs {published[:12]}"),
        ("artifact's own recorded digest agrees",
         art["recomputed_sha256"] == published, art["recomputed_sha256"][:12]),
        ("table size matches the artifact's n_entries",
         len(table) == art["n_entries"], f"{len(table)} vs {art['n_entries']}"),
        ("n_g51_on derives from the table",
         on == g59["gate"]["n_g51_on"], f"{on} vs {g59['gate']['n_g51_on']}"),
        ("n_g51_off derives from the table",
         off == g59["gate"]["n_g51_off"], f"{off} vs {g59['gate']['n_g51_off']}"),
        ("payload carries every key the digest is taken over",
         set(art["payload"]) == {"min_dev_n", "n_dev_queries", "n_g51_on",
                                 "n_g51_off", "use_g51"}, sorted(art["payload"])),
    ]

    # The two-sided half: a checker that only ever agrees is one nobody can trust.
    # Flip one entry in a COPY and the digest must move.
    victim = sorted(table)[0]
    mutated = dict(art["payload"])
    mutated["use_g51"] = dict(table)
    mutated["use_g51"][victim] = not mutated["use_g51"][victim]
    checks.append(("a one-entry mutation moves the digest",
                   digest_of(mutated) != published, f"p={victim}"))

    # SPECIFICITY, and it is not hypothetical: G64_bidirectional_topologies
    # publishes a table under the SAME name, the SAME 223 keys and the SAME
    # min_dev_n / n_dev_queries, differing in 19 entries and splitting 174/49.
    # A reader who matched on shape would read a DIFFERENT gate. The digest is
    # what tells them apart, so that separation is asserted rather than
    # described. An ABSENT G64 fails this check: a skipped control is not a
    # passed one, and silently having nothing to distinguish is the failure.
    g64_path = os.path.join(SPIKES, "G64_bidirectional_topologies",
                            "g64_results.json")
    try:
        g64 = json.load(open(g64_path))["gate"]
        other = g64["use_g51"]
        ndiff = sum(1 for k in table if other.get(k) != table[k])
        checks.append((
            "the same-shaped G64 table is a DIFFERENT object and the digest says so",
            len(other) == len(table) and ndiff > 0
            and digest_of({k: v for k, v in g64.items() if k != "sha256"}) != published,
            f"{ndiff}/{len(table)} entries differ, {g64['n_g51_on']}/{g64['n_g51_off']} vs {on}/{off}"))
    except (OSError, KeyError) as e:
        checks.append(("the same-shaped G64 table is a DIFFERENT object and the digest says so",
                       False, f"decoy unreadable, nothing was distinguished: {e!r}"))

    bad = 0
    for name, ok, detail in checks:
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}   [{detail}]")
        bad += not ok
    print(f"\nG101 verify: {len(checks) - bad}/{len(checks)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
