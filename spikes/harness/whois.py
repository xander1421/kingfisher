#!/usr/bin/env python3
"""whois — which callsign is this pid, answered TWICE from independent sources.

ATOM-3, on the cross-lane bus, named the gap this closes:

    "the only link between a pid and a callsign is the literal prompt string
    `You are <X>.`, and run_loop.sh:297 documents that the watchdog's `pkill -f`
    depends on that same string. One string, load-bearing for both identity and
    termination, with nothing asserting it holds."

There are in fact TWO independent links, and nothing had ever compared them:

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

CENSUS RULE: enumerate every pid, print the TOTAL beside the enumeration, never
end in `head`. A reviewer's pid census ended in a bare `head` after `sort -rn`,
cut the four lowest pids, and concluded no process carried a CALLSIGN — all
three that did were in the part it dropped.

Exit 0 agree, 1 disagreement or unverifiable lane, 2 could not run.
"""

import re
import subprocess
import sys


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


def pids():
    out = sh("pgrep", "-f", "claude")
    return [p for p in out.split() if p.isdigit()]


def from_argv(pid):
    cmd = sh("ps", "-p", pid, "-o", "command=")
    m = re.search(r"You are ([A-Za-z0-9._-]+)\.", cmd)
    return m.group(1) if m else None


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
            verdict = "AGREE — lane confirmed by two sources"
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

    print("\nNOT ANSWERED BY THIS SCRIPT, and it is the third answer:")
    print("  a session that SIGNS a callsign in CHANNEL.md / livechat / a commit")
    print("  trailer while carrying neither marker. That is self-declaration")
    print("  (A22) and it is what produced two AGENT-2s and two spikes numbered")
    print("  G25. `grep -c '^CLAIM' CHANNEL.md` cannot distinguish it from a")
    print("  lane, so the roster is the only place that distinction can live.")

    return 1 if (disagree or dups) else 0


if __name__ == "__main__":
    sys.exit(main())
