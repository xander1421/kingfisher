#!/usr/bin/env python3
"""registry.py v1 — the writer `fleet/registry.tsv` never had (H169).

WHY THIS EXISTS. `MISSION.md:283` specifies the file *"with provenance per row:
OBSERVED means a message actually arrived from that address and is the only proof
of reachability; argv means a process claims the callsign and is a lead, never an
address. Never silently promote one to the other."* The file was three columns
with no provenance field, so every row read as an address and the forbidden
promotion was made STRUCTURALLY. It was also stale by a whole launcher
generation — five callsigns mapped to five dead pids — because nothing wrote it.

THE DESIGN COMMITMENT, and it is the whole point of the module:
**there is no code path from a lead to OBSERVED.** Two sources, two functions,
two provenance values:

  * `receipts()`  reads delivered messages and is the ONLY producer of OBSERVED.
  * `leads()`     reads `.loop_lock.*` and `ps` and CANNOT emit OBSERVED — it is
                  asserted at the boundary, not merely intended.

So the promotion MISSION.md forbids is unrepresentable rather than discouraged.
A rule that depends on remembering it is the class this repo keeps paying for
(A28: an enforcement field recorded but never read is documentation).

WHAT A MECHANICAL WRITER CANNOT DO, stated because omitting it would overstate
the module. There are TWO channels and they have opposite weaknesses:

  1. `send.sh` -> `inbox/<CALLSIGN>.md` -> `inbox/archive/<CALLSIGN>.log`.
     DURABLE, leaves a file, and its receipts are re-derivable forever. But its
     address is a callsign, not a socket.
  2. the session bus. ADDRESSED by socket, and IN-MEMORY — a bus receipt reaches
     a model's context and touches no file, so **no scan can ever reproduce it.**

The durable channel has no addresses and the addressed channel has no durability.
Every socket row in this file therefore rests on a lane having attested a receipt
by hand, which is why `merge()` preserves rows it cannot re-derive instead of
overwriting them. A writer that "refreshed" the file by dropping what it could
not see would destroy the only evidence of reachability the fleet has.

usage:
  python3 spikes/harness/registry.py            # rewrite fleet/registry.tsv
  python3 spikes/harness/registry.py --check    # print, change nothing
  python3 spikes/harness/registry.py --selfcheck
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OBSERVED = "OBSERVED"
CLAIMED = "argv"          # H181: a header the sender wrote about itself
LEAD_VALUES = ("lock", "argv")
HDR = re.compile(r"^──── message to (\S+), from (\S+) ────$")
COLS = ("callsign", "lane_pid", "address", "provenance", "evidence")


def declared_lanes(root: Path = None) -> list:
    """roster.txt is the sanction list. A row for a callsign not on it invents
    standing, which is §12's allocation question and not a writer's to answer."""
    root = root or ROOT
    f = root / "roster.txt"
    if not f.is_file():
        return []
    out = []
    for line in f.read_text().splitlines():
        line = line.split("#")[0].strip()
        if line:
            out.append(line.split()[0])
    return out


def receipts(root: Path = None) -> dict:
    """Rows derived from delivered messages. **NOT `OBSERVED` — see H181.**

    v1 emitted `OBSERVED` here and was WRONG, and the module was attacked by its
    own author 40 minutes after it landed. `MISSION.md:283` reserves `OBSERVED`
    for *"a message actually ARRIVED from that address ... the only proof of
    reachability"*. A delivered message does prove ARRIVAL — but the IDENTITY in
    the header is `send.sh:62`'s `FROM="${CALLSIGN:-$(whoami)@interactive}"`,
    i.e. **the sender's own environment**. MEASURED, not argued
    (`spikes/H181_observed_is_selfdeclared/`): a scratch lane exported one
    environment variable, sent one message, and minted an `OBSERVED` row for a
    callsign that was not its own — reaching the written file, no privilege
    beyond a lane's own tree.

    That is A22 exactly: the party being attested supplied the input to the
    attestation. And the spec already has the right word for it — *"`argv` means a
    process CLAIMS the callsign and is a LEAD, NEVER AN ADDRESS"*. A header a lane
    writes about itself is a claim, so it is recorded as one.

    **Consequence, stated rather than hidden: NO function in this module can now
    emit `OBSERVED`.** Every `OBSERVED` row in the file is hand-attested by a lane
    that witnessed an arrival it did not author, and `merge()` preserves those.
    That is the honest state of the evidence, not a regression — v1's stronger
    label was forgeable, and a forgeable proof of reachability is worse than an
    admitted claim because it is spent as if it were evidence.
    """
    root = root or ROOT
    lanes = set(declared_lanes(root))
    found = {}
    inbox = root / "inbox"
    if not inbox.is_dir():
        return found
    for path in sorted(list(inbox.glob("*.md")) + list(inbox.glob("archive/*.log"))):
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            m = HDR.match(line.strip())
            if not m:
                continue
            sender = m.group(2)
            if sender not in lanes:
                continue  # not a declared lane: no row, no invented standing
            rel = path.relative_to(root)
            found.setdefault(sender, {
                "callsign": sender,
                "lane_pid": "-",
                "address": f"inbox/{sender}.md",
                # H181: self-declared by the sender. A claim, never an address.
                "provenance": CLAIMED,
                "evidence": f"{rel}:{i} (sender-declared)",
            })
    return found


def leads(root: Path = None) -> dict:
    """Lock-derived rows. CANNOT emit OBSERVED — asserted, not intended.

    `.loop_lock.<CALLSIGN>` holds the run_loop SUPERVISOR pid, which survives the
    turn; it proves the LANE exists, never that it answers. A dead pid is marked
    rather than silently emitted as an address (C3).
    """
    root = root or ROOT
    out = {}
    for cs in declared_lanes(root):
        lock = root / f".loop_lock.{cs}"
        if not lock.is_file():
            continue
        pid = lock.read_text().strip()
        alive = pid.isdigit() and _pid_alive(int(pid))
        out[cs] = {
            "callsign": cs,
            "lane_pid": pid or "-",
            "address": "-",
            "provenance": "lock",
            "evidence": f".loop_lock.{cs}:{'pid-alive' if alive else 'PID-DEAD'}",
        }
    for row in out.values():
        assert row["provenance"] in LEAD_VALUES, (
            f"leads() produced {row['provenance']!r} — there is no path from a "
            f"lead to OBSERVED and this assertion is that path's absence")
    return out


def _assert_no_derived_observation(rows: dict) -> None:
    """H181. NEITHER derivation path may emit OBSERVED, not just `leads()`.

    v1 asserted this of the weak source only, which is why the forgery walked in
    through the source I had already decided was the strong one. An assertion
    placed on the branch you distrust cannot see the branch you trust.
    """
    for cs, row in rows.items():
        assert row["provenance"] != OBSERVED, (
            f"derived row for {cs} claims OBSERVED; nothing mechanical here can "
            f"earn it (H181)")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True


def parse_existing(path: Path) -> dict:
    """Rows already in the file, so merge() can refuse to destroy them."""
    rows = {}
    if not path.is_file():
        return rows
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if parts[0] == "callsign":
            continue
        while len(parts) < 5:
            parts.append("")
        rows[parts[0]] = dict(zip(COLS, parts[:5]))
    return rows


def merge(existing: dict, derived: dict) -> tuple:
    """Never silently downgrade, the mirror of never silently promote.

    A bus receipt is unreproducible by construction (see module docstring), so an
    existing OBSERVED row that this run cannot re-derive is KEPT, not dropped.
    Returns (rows, kept) where kept names what survived on that basis, so the
    caller can say so out loud rather than leaving it implicit.
    """
    rows, kept = {}, []
    for cs, row in existing.items():
        rows[cs] = dict(row)
    for cs, row in derived.items():
        prior = rows.get(cs)
        if prior and prior.get("provenance") == OBSERVED and row["provenance"] != OBSERVED:
            # refresh the lead fields, keep the stronger provenance and its cite
            merged = dict(prior)
            if row.get("lane_pid", "-") not in ("", "-"):
                merged["lane_pid"] = row["lane_pid"]
            # H181b: IDEMPOTENCE. This appended unconditionally, so every run
            # re-appended the same lock cite and the evidence field grew without
            # bound — `pid-alive + pid-alive + ...`. A writer meant to be re-run
            # must be safe to re-run; found by READING the output of the run that
            # published it, which is the only way this class is ever caught.
            merged["evidence"] = _join_evidence(prior.get("evidence", ""), row["evidence"])
            rows[cs] = merged
            kept.append(cs)
        else:
            rows[cs] = row
    return rows, kept


def _join_evidence(prior: str, new: str) -> str:
    """Append only cites not already present, so re-running is a no-op (H181b)."""
    parts = [p.strip() for p in prior.split(" + ") if p.strip()]
    for cand in [c.strip() for c in new.split(" + ") if c.strip()]:
        if cand not in parts:
            parts.append(cand)
    return " + ".join(parts)


def render(rows: dict, stamp: str) -> str:
    head = f"""# fleet/registry.tsv — callsign -> address, WITH PROVENANCE PER ROW (MISSION.md:283)
#
# WRITTEN BY `spikes/harness/registry.py` (H169). Do not hand-edit: re-run it.
# Generated {stamp}.
#
# PROVENANCE, in descending strength. THERE IS NO CODE PATH FROM A LEAD TO
# OBSERVED — two sources, two functions, and an assertion at the boundary of the
# weaker one. MISSION.md:283 forbids silently promoting a lead to an address;
# this makes the promotion unrepresentable rather than discouraged.
#   OBSERVED  a message actually ARRIVED from this address. Only `receipts()`
#             emits it, and every such row cites the file:line it read.
#   lock      `.loop_lock.<CALLSIGN>`, probed with kill(pid, 0). Proves the LANE
#             exists; does NOT prove it answers. A dead pid is marked PID-DEAD.
#   argv      a process claims the callsign. A LEAD, NEVER AN ADDRESS.
#   RETIRED   removed from roster.txt by an operator decision; cite in `evidence`.
#
# TWO CHANNELS, OPPOSITE WEAKNESSES, and this is why some rows cannot be
# re-derived: `send.sh` -> `inbox/` is DURABLE but its address is a callsign, and
# the session bus is ADDRESSED by socket but IN-MEMORY, so a bus receipt touches
# no file and no scan can ever reproduce it. Socket rows below rest on a lane
# attesting a receipt by hand; `merge()` preserves them rather than overwriting,
# because a writer that dropped what it could not see would destroy the only
# evidence of reachability this fleet has.
#
# lane_pid is the run_loop SUPERVISOR and survives the turn. A census keyed on a
# turn socket reads empty between turns — a turn census wearing a lane's name.
#
# STALE BY CONSTRUCTION. Re-derive; do not trust.
#
"""
    body = ["\t".join(COLS)]
    for cs in sorted(rows):
        r = rows[cs]
        body.append("\t".join(str(r.get(c, "-")) or "-" for c in COLS))
    return head + "\n".join(body) + "\n"


def build(root: Path = None) -> tuple:
    root = root or ROOT
    path = root / "fleet" / "registry.tsv"
    derived = dict(leads(root))
    for cs, row in receipts(root).items():
        prior = derived.get(cs)
        if prior:
            row = dict(row, lane_pid=prior["lane_pid"],
                       evidence=f"{row['evidence']} + {prior['evidence']}")
        derived[cs] = row
    _assert_no_derived_observation(derived)
    rows, kept = merge(parse_existing(path), derived)
    return path, rows, kept


def main(argv) -> int:
    check = "--check" in argv
    path, rows, kept = build()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    text = render(rows, stamp)
    n_obs = sum(1 for r in rows.values() if r.get("provenance") == OBSERVED)
    if kept:
        print(f"kept {len(kept)} un-re-derivable OBSERVED row(s): {', '.join(sorted(kept))}")
    print(f"{len(rows)} row(s), {n_obs} OBSERVED")
    if check:
        print(text)
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"-> {path.relative_to(ROOT)}")
    return 0


def selfcheck() -> int:
    """The assertions that matter are the two that can fail in opposite ways.

    F1 says no lead may become OBSERVED. A module that never emits OBSERVED at
    all satisfies F1 vacuously, so C1 PLANTS a receipt and requires it to appear
    — without C1, F1 is not evidence of anything.
    """
    import shutil
    import tempfile

    bad = []

    def ck(cond, note):
        print(f"  {'ok  ' if cond else 'FAIL'}  {note}")
        if not cond:
            bad.append(note)

    # §10: NOTHING IS WRITTEN OUTSIDE THE WORKSPACE. This read
    # `tempfile.mkdtemp()` — i.e. /tmp — until the author caught it, one hour
    # after self-reporting the same break (H89) and inside the module written to
    # make a provenance rule unrepresentable rather than merely stated. The rail
    # has no sanctioned scratch location, so every careful lane invents /tmp;
    # that is the row, and this is what the fix looks like at a call site.
    tmp = Path(tempfile.mkdtemp(prefix=".tmp_registry_selfcheck.", dir=str(ROOT)))
    try:
        (tmp / "inbox" / "archive").mkdir(parents=True)
        (tmp / "fleet").mkdir()
        (tmp / "roster.txt").write_text("# fixture\nLANE-A   # comment\nLANE-B\n")

        # C3 — a dead pid is MARKED, never silently emitted as an address.
        dead = 999999
        while _pid_alive(dead):
            dead -= 1
        (tmp / ".loop_lock.LANE-A").write_text(f"{dead}\n")
        (tmp / ".loop_lock.LANE-B").write_text(f"{os.getpid()}\n")

        ld = leads(tmp)
        ck(ld["LANE-A"]["evidence"].endswith("PID-DEAD"),
           f"C3 dead pid marked (got {ld['LANE-A']['evidence']})")
        ck(all(r["provenance"] in LEAD_VALUES for r in ld.values()),
           "leads() emits only lead provenance")

        # F1 — with no receipts anywhere, nothing may be OBSERVED.
        ck(receipts(tmp) == {}, f"F1 no receipts -> no OBSERVED (got {receipts(tmp)})")
        _, rows, _ = _build_in(tmp)
        ck(not any(r["provenance"] == OBSERVED for r in rows.values()),
           "F1 a live lock alone never reaches OBSERVED")

        # C1 NEGATIVE CONTROL — plant a receipt; it MUST appear, or F1 is vacuous.
        (tmp / "inbox" / "archive" / "LANE-B.log").write_text(
            "\n──── message to LANE-B, from LANE-A ────\nhello\n")
        rc = receipts(tmp)
        ck(rc.get("LANE-A", {}).get("provenance") == CLAIMED,
           f"C1 planted receipt becomes a CLAIM, non-vacuously (got {rc.get('LANE-A')})")
        ck(rc.get("LANE-A", {}).get("provenance") != OBSERVED,
           "H181 a sender-declared header never reaches OBSERVED")
        ck("inbox/archive/LANE-B.log:2" in rc.get("LANE-A", {}).get("evidence", ""),
           f"C2 the row cites file:line (got {rc.get('LANE-A', {}).get('evidence')})")

        # F3 — a receipt from a callsign nobody sanctioned invents no standing.
        (tmp / "inbox" / "archive" / "LANE-C.log").write_text(
            "\n──── message to LANE-B, from NOT-A-LANE ────\nhi\n")
        ck("NOT-A-LANE" not in receipts(tmp),
           "F3 a receipt from a non-roster callsign produces no row")

        # F2 — an OBSERVED row this run cannot re-derive must SURVIVE.
        reg = tmp / "fleet" / "registry.tsv"
        reg.write_text(
            "callsign\tlane_pid\taddress\tprovenance\tevidence\n"
            "LANE-B\t1\t/tmp/sock\tOBSERVED\tbus-receipt-unreproducible\n")
        _, rows2, kept = _build_in(tmp)
        ck(rows2["LANE-B"]["provenance"] == OBSERVED,
           f"F2 un-re-derivable OBSERVED row survives (got {rows2['LANE-B']})")
        ck(rows2["LANE-B"]["address"] == "/tmp/sock",
           "F2 its address is not overwritten by a weaker source")
        ck("LANE-B" in kept, "F2 the preservation is REPORTED, not silent")

        # H181b — a writer meant to be re-run must be safe to re-run. This grew
        # the evidence field by one duplicate cite per run until it was read.
        p2, rows_a, _ = _build_in(tmp)
        p2.write_text(render(rows_a, "fixture"))
        _, rows_b, _ = _build_in(tmp)
        p2.write_text(render(rows_b, "fixture"))
        _, rows_c, _ = _build_in(tmp)
        ck(rows_b["LANE-B"]["evidence"] == rows_c["LANE-B"]["evidence"],
           f"H181b re-running is idempotent (got {rows_c['LANE-B']['evidence']!r})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1
    print("registry: nothing mechanical earns OBSERVED; a planted receipt is recorded "
          "as the CLAIM it is (H181)")
    return 0


def _build_in(root: Path) -> tuple:
    path = root / "fleet" / "registry.tsv"
    derived = dict(leads(root))
    for cs, row in receipts(root).items():
        prior = derived.get(cs)
        if prior:
            row = dict(row, lane_pid=prior["lane_pid"],
                       evidence=f"{row['evidence']} + {prior['evidence']}")
        derived[cs] = row
    _assert_no_derived_observation(derived)
    rows, kept = merge(parse_existing(path), derived)
    return path, rows, kept


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    sys.exit(main(sys.argv[1:]))
