#!/usr/bin/env python3
# sites.py v2 — H243 (v1), H243-attack (v2). ok-1, 2026-08-19.
# Version in a `#` comment as well as the docstring: versioncheck.py reads a
# comment and cannot see a docstring version (H193).
"""A1 — every liveness test applied to a pid that came out of `.loop_lock.<CS>`.

==== v2, AND IT IS AN ATTACK ON v1 BY ITS OWN AUTHOR (cycle 34, §2) ==========
DEFECT REMOVED: **THE POPULATION WAS A HAND-TYPED LIST, SO "READ BY SIX
INSTRUMENTS" WAS TRUE OF THE SIX I TYPED AND OF NOTHING ELSE.** That is family D
-- a party supplying the input to a check applied to itself -- in the instrument
whose whole job was to be the population.

MEASURED: `spikes/harness/commit-msg.hook` reads `.loop_lock.$CALLSIGN` at :149
and takes `ps -p "$_lp" -o lstart=` from it. v1's `LIVENESS` regex matches
`ps -p ` and its `CMD` regex does not match `-o lstart=`, so that site WOULD have
been reported PID ONLY -- **the detector was working and never got the file.**
The count was not wrong about what it saw; it was wrong about what it looked at.

v2 derives the population from the tree: every tracked `.sh` / `.py` / `.hook`
that mentions `loop_lock`. It REFUSES on an empty population, because a census
whose population is empty prints a clean zero (H178's shape, and this lane's
third cycle running on it). The v1 list is kept only as a COVERAGE ASSERTION:
if a file it named is no longer derived, that is a rename and the census says so
rather than quietly shrinking.

A LIVENESS TEST IS ONLY THIS ROW'S SUBJECT IF THE pid CAME FROM A LOCK. The first
version of this census counted `kill -0 "$turn"` in run_loop.sh's heartbeat -- a
TURN pid, legitimately tested by pid alone, because the launcher spawned it and
knows what it is. Scoring it would have inflated the count by one and pointed the
row at code that is correct.

The window rule is mechanical: a hit counts if `loop_lock`, `from_lock` or `$LOCK`
appears within the 12 lines above it. Excluded hits are PRINTED rather than
dropped -- a census that hides its exclusions is one whose number cannot be
checked. This file is separate from probe.sh because the same nesting that
produced H232's dead mutants (a heredoc inside a shell function) was reproduced
here in one cycle: the python for this arm lived in a heredoc inside probe.sh and
its own heredoc terminated the outer one.

usage: python3 sites.py <repo-root>       exit 0 always; the count is the output
"""
import re, sys, pathlib

SITES = [
    ("run_loop.sh",                   "acquire + per-turn re-read"),
    ("bringup.sh",                    "supervisor: decides MISSING"),
    ("spikes/harness/bringup.sh",     "preflight copy: decides stale-clear"),
    ("spikes/harness/fleetcensus.sh", "census: status word"),
    ("spikes/harness/registry.py",    "registry: lead provenance"),
    ("spikes/harness/whois.py",       "whois: 'live' vs 'STALE'"),
]
# CALL SITES COUNT, NOT ONLY INLINE TESTS. registry.py reads the lock at :142 and
# tests it at :147 with `_pid_alive(...)`, whose BODY is 30 lines away in a generic
# helper -- so a window rule keyed on inline `os.kill` found the helper (excluded,
# correctly: it is not a lock pid there) and MISSED the reader. The first count
# printed 4 with registry.py absent from it, which is the under-report that mirrors
# the over-report above.
LIVENESS = re.compile(r'kill -0|os\.kill\(|\["ps", "-p"|ps -p |_pid_alive\(|lane_lock_pid\(|launcher_alive[ (]')
# v2 · A pid that came from a lock is tracked by the VARIABLE it landed in, not
# by a magic distance. The 12-line window is kept as a fallback so nothing v1
# counted is lost, but it FAILED the first time it was tested against a real
# edit: adding this row's own rationale comment pushed `ps -p "$_lp"` thirteen
# lines below the `loop_lock` read in `commit-msg.hook`, and the site silently
# left the population -- so a reverted fix would have read as "not a site".
LOCKVAR = re.compile(r'(?:^|[^\w])(\w+)\s*=\s*\$?\(?[^\n]*loop_lock')
# CEILING, stated not fixed: LOCKVAR tracks ONE hop. `registry.py` does
# `lock = root / f".loop_lock.{cs}"` then `pid = lock.read_text()`, so `pid` is
# lock-derived transitively and this rule does not see it -- the 12-line window
# is what catches that site. A second hop is a dataflow pass and this is a
# census; the fallback covers the real cases and the gap is named so a reader
# does not read the variable rule as complete.
CMD = re.compile(r"-o command=|'command'|comm=|launcher_alive")

def _uncomment(text):
    """Drop `#` comments. Approximate on purpose: a `#` inside a string is rare
    in these files and treating one as a comment can only SHRINK a match, which
    is the safe direction for a rule that decides a line is a defect."""
    return "\n".join(l.split("#", 1)[0] for l in text.split("\n"))


root = pathlib.Path(sys.argv[1])

# v2 · DERIVED, NOT TYPED. `git ls-files` is the tracked set; anything untracked
# is not yet in the record and is reported separately rather than scored.
import subprocess
_tracked = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                          text=True).stdout.split("\n")
_known = dict(SITES)
derived = []
for rel in _tracked:
    if not rel or not rel.endswith((".sh", ".py", ".hook")) or rel.startswith("elders/"):
        continue
    if rel.endswith("H243_lock_liveness/sites.py"):
        continue          # this file matches its own prose; that is noise, not a site
    try:
        if "loop_lock" in (root / rel).read_text(encoding="utf-8", errors="replace"):
            derived.append((rel, _known.get(rel, "derived from the tree")))
    except OSError:
        continue
if not derived:
    sys.exit("sites.py REFUSES: derived population is EMPTY. A census with no "
             "population prints a clean zero and tells you nothing.")
missing = [rel for rel, _ in SITES if rel not in dict(derived)]
if missing:
    print(f"    COVERAGE: v1 named {missing}, which the tree no longer yields "
          f"-- renamed or deleted, not silently dropped")
print(f"    population: {len(derived)} tracked .sh/.py/.hook files mention "
      f"loop_lock (v1 scanned {len(SITES)}, hand-typed)")

pidonly = excluded = counted = 0
for rel, what in derived:
    lines = (root / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith('#') or not LIVENESS.search(ln):
            continue
        window = '\n'.join(lines[max(0, i - 13):i])
        # A MENTION IS NOT A USE. `registry.py:181` is
        # `def _pid_alive(pid) -> bool:   # NOT for lock pids (H243)` and the
        # word `lock` in that comment matched the lock-derived variable `lock`
        # assigned 36 lines above -- so the census counted a helper its own
        # comment says is not for lock pids. A30's class (a checker that cannot
        # tell a live construct from a mention of one), in a rule written to fix
        # a different one, in the same cycle. Comments are stripped before any
        # variable is matched, and the match is word-bounded.
        code = _uncomment('\n'.join(lines[:i]))
        lockvars = {m.group(1) for m in LOCKVAR.finditer(code)}
        ln_code = _uncomment(ln)
        from_var = any(re.search(r'\b' + re.escape(v) + r'\b', ln_code)
                       for v in lockvars if v)
        if not from_var and not any(
                k in window for k in ('loop_lock', 'from_lock', '$LOCK')):
            excluded += 1
            print(f"    {rel}:{i:<5} EXCLUDED — this pid does not come from a lock")
            print(f"        {s[:78]}")
            continue
        counted += 1
        # v2 · A PID-ONLY LINE THAT IS GUARDED UPSTREAM IS NOT THE DEFECT. The
        # census counts LINES, so after `launcher_alive "$_lp" || _lp=''` the
        # very next `ps -p "$_lp"` still reads PID ONLY -- it would report the
        # repaired code as broken, which is the same family of confident wrong
        # answer this row is about. A variable that has passed a command-identity
        # test earlier in the file is marked, and its later uses say so.
        guarded = {v for v in lockvars if v and any(
            CMD.search(prev) and re.search(r'\b' + re.escape(v) + r'\b',
                                          _uncomment(prev))
            for prev in lines[:i - 1])}
        on_guarded = any(re.search(r'\b' + re.escape(v) + r'\b', ln_code)
                         for v in guarded)
        kind = ('pid+command' if CMD.search(ln)
                else 'guarded-upstream' if on_guarded else 'PID ONLY')
        if kind == 'PID ONLY':
            pidonly += 1
        print(f"    {rel}:{i:<5} {kind:<12} {what}")
        print(f"        {s[:78]}")
print(f"    lock-pid liveness tests: {counted}, of them PID ALONE: {pidonly}"
      f"   (excluded as not lock pids: {excluded})")
# v2 · THE TOTAL IS NOT THE ANSWER, AND SAYING SO IS PART OF THE OUTPUT. A
# derived population mixes live instruments with pinned historical copies
# (`bringup.before_h88.sh`) and deliberate test fixtures (`H238/probe.sh` seeds a
# dead pid on purpose). v1 under-reported from a typed list; a total that pools
# those over-reports in the other direction, and both are the right measurement
# of the wrong question. The per-file list above is what to act on.
print("    NOTE: the population is DERIVED, so it includes pinned historical "
      "copies and test fixtures that are correct as they stand. Read the "
      "per-file lines, not the total.")
