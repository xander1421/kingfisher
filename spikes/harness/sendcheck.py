#!/usr/bin/env python3
"""sendcheck.py v1 — H186. Does `send.sh` actually READ its roster?

WHY THIS IS A `.py` AND NOT THE `.sh` IT REPLACES. H184 shipped this check as a SHELL
script beside `send.sh`, 6 assertions, in the cycle that repaired the fleet's
only durable channel — and **nothing ran it.** (The path is described rather
than written: naming a file in order to say it was removed is indistinguishable
from citing one that is missing, which is the trap `refcheck` catches and which
caught this very sentence.) The single automatic path
in this repo is `bringup.sh:373` -> `selfcheckall.py`, on the launchd
`com.kingfisher.bringup` cadence (`StartInterval 600`), and `selfcheckall.py`
discovers by `if not name.endswith('.py')` plus a `--selfcheck` flag. A shell
test is not merely EXCLUDED there — it is INVISIBLE, absent even from the sweep's
own "N shell module(s) ... excluded here" line, because that line counts shell
files that carry `--selfcheck` and a plain test script carries none. So the check
proving the channel works ran exactly when a lane remembered, which is H15's
class (*a check nobody is routed to is prose with extra steps*) committed by the
lane that had just cited it.

Not fixed by teaching `selfcheckall.py` to run shell: that is H93 (ATTACKER-1,
open) and editing it under them is the A22 shape. §3 says gates are respected and
never waited on, so this check moves onto the path that exists.

THE DEFECT IT HOLDS SHUT (H184). `f6f923d` dropped one space:

    sed 's/#.*//'"$_ROSTER"      <- ONE argument, not two

sed read the path as part of its script, printed nothing, `LANES` went EMPTY, and
every consumer read "not in LANES" as "not a declared lane". `send.sh` refused
every callsign in the fleet for ~2 hours while `--list` printed "(nothing
pending)" over 205 pending lines.

TWO NEGATIVE CONTROLS, because without them this file is decorative:
  * the fixture's roster names a callsign the no-roster FALLBACK LITERAL does not
    contain, so acceptance proves the file was READ rather than the literal hit;
  * `--mutate`: `send.sh` is copied, the space is REMOVED again, and this check
    must go RED against it. A check that cannot fail against the exact defect it
    was written for is not evidence that the defect is gone.

usage:  python3 spikes/harness/sendcheck.py [--selfcheck]
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEND = ROOT / "spikes" / "harness" / "send.sh"

# Absent from send.sh's no-roster fallback literal, so accepting it proves the
# roster file was read. If this name is ever added to that literal, the control
# dies silently -- which is why the check asserts its absence below.
ROSTER_ONLY = "ZZ-ONLY-IN-ROSTER"


def _fleet(tmp: Path, send_text: str, roster: str) -> None:
    (tmp / "spikes" / "harness").mkdir(parents=True, exist_ok=True)
    (tmp / "prompts").mkdir(exist_ok=True)
    (tmp / "inbox" / "archive").mkdir(parents=True, exist_ok=True)
    (tmp / "roster.txt").write_text(roster)
    (tmp / "prompts" / f"{ROSTER_ONLY}.md").write_text("# brief\n")
    p = tmp / "spikes" / "harness" / "send.sh"
    p.write_text(send_text)
    p.chmod(0o755)


def _run(tmp: Path, *args: str):
    return subprocess.run(["sh", "spikes/harness/send.sh", *args],
                          cwd=str(tmp), capture_output=True, text=True)


def probe(send_text: str) -> dict:
    """Drive one send.sh text through the fixture. Returns what the checks judge."""
    # §10: the fixture lives INSIDE the workspace.
    tmp = Path(tempfile.mkdtemp(prefix=".tmp_sendcheck.", dir=str(ROOT)))
    try:
        _fleet(tmp, send_text, f"# scratch\n{ROSTER_ONLY}\n")
        sent = _run(tmp, ROSTER_ONLY, "hello")
        queued = (tmp / "inbox" / f"{ROSTER_ONLY}.md").is_file()

        _fleet(tmp, send_text, "")          # roster present but EMPTY
        listed = _run(tmp, "--list")
        return {
            "accepted": sent.returncode == 0,
            "queued": queued,
            "sed_ok": "bad flag in substitute" not in (sent.stdout + sent.stderr),
            "empty_refuses": listed.returncode != 0,
            "empty_quiet": "nothing pending" in (listed.stdout + listed.stderr),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def break_send(text: str) -> str:
    """Re-introduce H184's defect: remove the space before the filename."""
    broken = text.replace("""sed 's/#.*//' "$_ROSTER\"""",
                          """sed 's/#.*//'"$_ROSTER\"""")
    assert broken != text, "could not re-break send.sh — the mutation target moved"
    # the v2 refusal guard would mask the defect, so the mutant is the pre-v2 shape
    return broken.replace('if [ -z "$(printf \'%s\' "$LANES" | tr -d \'[:space:]\')" ]; then',
                          'if false; then')


def selfcheck() -> int:
    bad = []

    def ck(cond, note):
        print(f"  {'ok  ' if cond else 'FAIL'}  {note}")
        if not cond:
            bad.append(note)

    text = SEND.read_text()

    ck(ROSTER_ONLY not in text.split("LANES=\"AGENT-1")[-1][:200] if "LANES=\"AGENT-1" in text else True,
       f"control is live: {ROSTER_ONLY} is absent from the no-roster fallback literal")

    r = probe(text)
    ck(r["accepted"], "a roster-only callsign is accepted (proves the roster was READ)")
    ck(r["sed_ok"], "sed parsed its expression and filename as two arguments")
    ck(r["queued"], "the message was actually queued")
    ck(r["empty_refuses"], "an empty lane list REFUSES")
    ck(not r["empty_quiet"], "--list does not report quiet over an unread roster")

    # NEGATIVE CONTROL: the check must go RED against the exact defect it exists for.
    m = probe(break_send(text))
    ck(not m["accepted"] or not m["sed_ok"],
       f"MUTATION: re-breaking the sed space makes this check RED (got {m})")

    if bad:
        print("SELFCHECK FAILED:", bad)
        return 1
    print("sendcheck: the roster is READ, an unread roster refuses, and re-breaking it goes red")
    return 0


if __name__ == "__main__":
    # The flag is HANDLED, not merely mentioned in the docstring.
    # `selfcheckall.discover()` requires a quoted "--selfcheck" in the source,
    # and its comment says why: a module that only NAMES the flag "would be
    # reported GREEN forever on the strength of a `python3 x.py` that does
    # something else." v1 of this file mentioned it and did not parse it, so the
    # sweep did not discover it at all -- the sweep was right and I was sloppy.
    if len(sys.argv) > 1 and sys.argv[1] not in ("--selfcheck",):
        sys.stderr.write(f"usage: {os.path.basename(__file__)} [--selfcheck]\n")
        sys.exit(2)
    sys.exit(selfcheck())
