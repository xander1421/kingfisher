#!/usr/bin/env python3
"""whois — which callsign is this pid, answered TWICE from independent sources.

ATOM-3, on the cross-lane bus, named the gap this closes:

    "the only link between a pid and a callsign is the literal prompt string
    `You are <X>.`, and run_loop.sh:297 documents that the watchdog's `pkill -f`
    depends on that same string. One string, load-bearing for both identity and
    termination, with nothing asserting it holds."

There are in fact two links, and nothing had ever compared them. They are
independent in WHAT THEY ENCODE and correlated in HOW THEY FAIL -- see the note
below the table, because "confirmed by two independent sources" was doing
load-bearing work in the verdict column and it is overstated:

  ARGV     `You are <X>.` in the command line. Written by run_loop.sh into the
           launch prompt. This is what the watchdog's pkill matches, so it is
           load-bearing for TERMINATION.
  ENVIRON  `CALLSIGN=<X>` in the process environment, read via `ps eww`. This is
           what loop_gate.sh reads to keep per-lane state separate, so it is
           load-bearing for the LOOP CONTRACT.

They are set at the same moment by the same launcher and can drift: a lane
relaunched from an older run_loop generation carries one and not the other
(H21 — a fix on disk is not a fix in the running process). Comparing them is
free and turns a believed map into a checked one.

WHY A THIRD ANSWER EXISTS, AND WHY IT IS THE DANGEROUS ONE. A session can also
SIGN a callsign — in CHANNEL.md, in livechat, in a commit trailer — while
carrying neither marker. That is self-declaration with nothing behind it (A22),
and it is not hypothetical: on 2026-08-17 two interactive sessions signed
AGENT-1 and AGENT-2 while the environment-carrying lanes for those callsigns
were different processes. This script reports SIGNED-ONLY sessions as exactly
that, because "claims a callsign" and "is that lane" are different facts and the
whole G25 collision came from conflating them.

THE DETECTION FLOOR, and it is the reason this is not a lane-liveness tool.
AGENT-2's lane measured it over every live launcher pid: THE LAUNCHER EXPOSES NO
CALLSIGN; ONLY THE `claude -p` TURN DOES. Verified here independently --
`ps eww` on the twelve `bash ./run_loop.sh` pids returns no CALLSIGN for any of
them, while the five claude pids all return one.

So an environment probe answers only WHILE A TURN IS IN FLIGHT. Between turns a
held callsign reads as FREE, and that window is exactly where `ok-1` was
launched onto a callsign nothing refused. ABSENCE HERE MEANS UNKNOWN, NEVER
CLEAR -- the same distinction ok-1 drew for heartbeats: stale and absent are
different failures and only one of them has a timestamp.

ARGV AND ENVIRON SHARE A FAILURE MODE, which ATOM-3 pointed out and which the
verdict column overstates. Both are read off a live process, so both vanish
between turns and both are missing for the same reason at the same moment.
Agreement between them rules out drift; it does NOT give two chances of seeing a
lane. `.loop_lock` is the only source with a DIFFERENT failure mode -- which is
exactly why the lock section could see ATOM-3 when the table could not. Three
sources, two of them correlated, is closer to two.

`.loop_lock.<CALLSIGN>` (run_loop.sh v6) is the source that does NOT have this
floor, because a file persists between turns. It is read here as a third source
where it exists. Caveat measured with `ls .loop_lock.*`: only ATOM-3 has one,
because the other spans started before v6 -- done on disk, live at next
relaunch.

CENSUS RULE: enumerate every pid, print the TOTAL beside the enumeration, never
end in `head`. A reviewer's pid census ended in a bare `head` after `sort -rn`,
cut the four lowest pids, and concluded no process carried a CALLSIGN — all
three that did were in the part it dropped.

Exit 0 agree, 1 disagreement or unverifiable lane, 2 could not run.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lanelive import launcher_alive          # pid + command, never pid alone (H243)

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True).stdout.strip() or "."


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def pids():
    """SNAPSHOT with `ps`, then search it. NOT `pgrep`.

    `man pgrep`, flag -a: "the current pgrep or pkill process and all of its
    ancestors are excluded." Not just the caller -- EVERY ANCESTOR. When a lane
    runs this script the chain is `claude -p` -> bash -> python3 -> pgrep, so
    the excluded process is THE LANE'S OWN TURN: exactly the process this tool
    exists to map.

    MEASURED by ATOM-3 running the pgrep version from inside ATOM-3: the table
    printed 4 lanes and omitted pid 44527, which carries `You are ATOM-3.` in
    argv AND `CALLSIGN=ATOM-3` in its environment -- while the LOCK FILES
    section eight lines below listed ATOM-3. The contradiction was on one screen
    and nothing flagged it. Worse, the header asserted "total printed; nothing
    truncated", which was true of the printing and false of the input.

    The answer depended on WHO RAN IT, which is the one property a census must
    not have. That is H6's class: A CENSUS THAT CANNOT SEE ITS OWN OBSERVER.
    Three sibling sites were fixed in bringup.sh the same cycle; the sharpest is
    the undeclared-lane audit, where an off-roster lane auditing the fleet
    reports itself absent -- an audit that exists BECAUSE a lane ran undeclared.

    pgrep's ancestor rule is not a bug in pgrep. It stops `pkill sshd` over ssh
    killing your own session. The defect is using a self-protecting tool as a
    census. run_loop.sh's watchdog `pkill -f "You are $CALLSIGN."` is FINE and
    untouched: its target is a sibling subshell, never an ancestor.
    """
    out = sh("ps", "-eww", "-o", "pid=,command=")
    return [l.split()[0] for l in out.splitlines()
            if "claude" in l and l.split() and l.split()[0].isdigit()]


def from_argv(pid):
    cmd = sh("ps", "-p", pid, "-o", "command=")
    m = re.search(r"You are ([A-Za-z0-9._-]+)\.", cmd)
    return m.group(1) if m else None


def from_lock(callsign):
    """`.loop_lock.<CALLSIGN>` holds the live launcher pid. Survives between
    turns, so it is the only source without the in-flight detection floor."""
    try:
        with open(os.path.join(ROOT, f".loop_lock.{callsign}")) as f:
            v = f.read().strip()
        return v if v.isdigit() else None
    except OSError:
        return None


def from_environ(pid):
    # `ps eww` prints the environment after the command. Split on whitespace and
    # look for the assignment rather than regexing the whole blob, because a
    # brief containing the string "CALLSIGN=" in prose would otherwise match.
    blob = sh("ps", "eww", "-p", pid)
    for tok in blob.split():
        if tok.startswith("CALLSIGN="):
            return tok.split("=", 1)[1]
    return None


def main():
    ps = pids()
    if not ps:
        print("whois: no claude processes found")
        return 2

    rows = []
    for p in sorted(ps, key=int):
        rows.append((p, from_argv(p), from_environ(p)))

    print(f"CENSUS: {len(rows)} claude processes (total printed; nothing "
          f"truncated)\n")
    print(f"{'pid':>8}  {'argv':<14}{'environ':<14}verdict")
    lanes = disagree = 0
    for p, a, e in rows:
        if a is None and e is None:
            verdict = "interactive — carries no callsign"
        elif a == e:
            lanes += 1
            verdict = "AGREE — argv and environ concur (correlated sources)"
        elif a is None:
            disagree += 1
            verdict = ("DISAGREE — environ only. loop_gate gates it; the "
                       "watchdog's pkill CANNOT match it")
        elif e is None:
            disagree += 1
            verdict = ("DISAGREE — argv only. pkill can kill it; loop_gate "
                       "gives it no per-lane state")
        else:
            disagree += 1
            verdict = f"DISAGREE — argv says {a}, environ says {e}"
        print(f"{p:>8}  {str(a or '-'):<14}{str(e or '-'):<14}{verdict}")

    # Duplicates: two processes answering to one callsign, on either source.
    seen = {}
    for p, a, e in rows:
        for c in {x for x in (a, e) if x}:
            seen.setdefault(c, []).append(p)
    dups = {c: v for c, v in seen.items() if len(v) > 1}

    print(f"\n{lanes} lane(s) confirmed by BOTH sources, {disagree} "
          f"disagreement(s)")
    if dups:
        print("\nDUPLICATE CALLSIGNS — two processes answer to one name:")
        for c, v in dups.items():
            print(f"   {c}: pids {', '.join(v)}")
            print(f"      They share .loop_signal.{c} and both sign CHANNEL.md "
                  f"as one atom.")

    # Third source: the lock file, which persists BETWEEN turns.
    locks = [f for f in os.listdir(ROOT) if f.startswith(".loop_lock.")]
    print(f"\nLOCK FILES ({len(locks)}) — the only source without the "
          f"in-flight floor:")
    if not locks:
        print("   none. Every callsign currently reads FREE between turns,")
        print("   which is not the same as being free. This is the window a")
        print("   second lane can be launched onto a held callsign.")
    for f in sorted(locks):
        cs = f[len(".loop_lock."):]
        held = from_lock(cs)
        # H243: `ps -p` alone says a process exists, not that it is a LAUNCHER,
        # and this line printed "live" for a lock naming any recycled pid.
        alive = launcher_alive(held)
        print(f"   {cs:<14} launcher pid {held or '?'}"
              f"  {'live' if alive else 'STALE — holder is gone'}")

    print("\nNOT ANSWERED BY THIS SCRIPT, and it is the third answer:")
    print("  a session that SIGNS a callsign in CHANNEL.md / livechat / a commit")
    print("  trailer while carrying neither marker. That is self-declaration")
    print("  (A22) and it is what produced two AGENT-2s and two spikes numbered")
    print("  G25. `grep -c '^CLAIM' CHANNEL.md` cannot distinguish it from a")
    print("  lane, so the roster is the only place that distinction can live.")

    return 1 if (disagree or dups) else 0


if __name__ == "__main__":
    sys.exit(main())
