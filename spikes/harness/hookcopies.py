#!/usr/bin/env python3
"""hookcopies.py v1 — H258. Every REGISTERED Stop hook on this disk, against the
one the harness checks.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **the harness has three checks on the Stop hook and all three read
the same single path.** `test_loop_gate.sh` copies `.claude/hooks/loop_gate.sh`,
its H23 block reads that file twice, and `vocabcheck.py` (H252, one cycle old)
compares it against the contract. Nothing asked whether that is the file a session
runs.

H1 -- the row that started class H -- was a Stop hook registered in a directory no
session used, inert for an entire session. **The mirror case is a hook that IS
used and is not the one every check reads**, and it was live when this was
written: `.codex/hooks.json` registers a Stop command at `.codex/hooks/
loop_gate.sh`, a 173-line copy whose banner says `v8`, beside a 205-line live hook
at `v9`. Pre-H219: no per-lane `STOP.$CALLSIGN`, so a lane running under that
registration cannot be retired except by the watchdog.

WHAT IT DOES NOT DO. It does not sync, copy or delete anything. A registration
outside `.claude/` belongs to another harness, and an artefact that is the
evidence for an open row is not the finder's to tidy (A23). It reports, and it
refuses when a registered hook differs from the reference.

SCOPE, stated because the population is the part that goes wrong (A22/family D --
earned this hour, in this lane, by a census that measured a hand-typed list):
every `*.json` under the workspace whose object graph contains a `Stop` hook
entry, excluding `.git/`, `elders/` (untrusted, read-only) and `.scratch/`
(sandboxes built BY the checks, which legitimately hold old copies). The
exclusions are PRINTED with their counts, never silently applied.

usage:
  python3 spikes/harness/hookcopies.py              # report + verdict
  python3 spikes/harness/hookcopies.py --selfcheck
"""
import hashlib
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REFERENCE = os.path.join(ROOT, ".claude", "hooks", "loop_gate.sh")
SKIP_DIRS = (".git", "elders", ".scratch", "node_modules")
VERSION = re.compile(r"^#\s*v(\d+)\b", re.M)


def digest(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return None


def version_of(path):
    """The HIGHEST `# vN` in the file, not the last.

    Read out of H219's own write-up: this hook's rationale blocks are in file
    order and v9's note sits above v3/v5/v6's, so `tail -1` reported v6 for a v9
    file and a banner that misidentifies its own subject is how a probe measured
    the repaired hook under the pre-fix label.
    """
    try:
        nums = [int(n) for n in VERSION.findall(open(path, encoding="utf-8", errors="replace").read())]
    except OSError:
        return None
    return max(nums) if nums else None


def registrations(root=ROOT):
    """[(settings_path, command_string, resolved_path_or_None)] for Stop hooks."""
    out, skipped = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".json"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                doc = json.load(open(p))
            except Exception:
                skipped += 1
                continue
            hooks = doc.get("hooks") if isinstance(doc, dict) else None
            if not isinstance(hooks, dict):
                continue
            for entry in hooks.get("Stop", []) or []:
                for hk in entry.get("hooks", []) or []:
                    cmd = str(hk.get("command", ""))
                    # The command may be quoted, and may be `python3 <path> --flag`.
                    cand = [t.strip("'\"") for t in cmd.split()]
                    resolved = None
                    for t in cand:
                        t = t.strip("'\"")
                        if t.endswith(".sh") or t.endswith(".py"):
                            resolved = t if os.path.isabs(t) else os.path.join(root, t)
                            break
                    out.append((os.path.relpath(p, root), cmd, resolved))
    return out, skipped


def check(root=ROOT, reference=REFERENCE, quiet=False):
    say = (lambda *a: None) if quiet else print
    regs, skipped = registrations(root)
    ref_d, ref_v = digest(reference), version_of(reference)
    say(f"reference {os.path.relpath(reference, root)}  v{ref_v}  {ref_d}")
    if ref_d is None:
        say("REFUSE: the reference hook does not exist")
        return 1
    # AN EMPTY POPULATION IS NOT AGREEMENT. Walk breakage, a renamed settings key
    # or a moved workspace all produce zero registrations, which compares equal to
    # "every registration matches" (H178's shape, and the shape the other ok-1
    # turn caught in my census an hour before this file was written).
    if not regs:
        say("REFUSE: no Stop-hook registration found at all; the walk found nothing to check")
        return 1
    bad = 0
    for rel, cmd, path in sorted(regs):
        if path is None:
            say(f"  {rel}: UNRESOLVED command {cmd[:60]!r}")
            bad += 1
            continue
        d, v = digest(path), version_of(path)
        same = d == ref_d
        mark = "same" if same else ("MISSING" if d is None else "DRIFTED")
        say(f"  {rel}: {os.path.relpath(path, root)}  v{v}  {d or '-'}  {mark}")
        if not same:
            bad += 1
    say(f"  ({skipped} unparseable .json skipped; {', '.join(SKIP_DIRS)} not walked)")
    if bad:
        say(f"REFUSE: {bad} of {len(regs)} registered Stop hook(s) are not the checked hook. "
            "Every check in this harness reads the reference; a session running the other "
            "copy is running a contract nothing tests.")
        return 1
    say(f"hookcopies: {len(regs)} registration(s), all the same object as the reference")
    return 0


def selfcheck():
    ok = fail = 0

    def ck(name, cond):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  PASS  {name}")
        else:
            fail += 1
            print(f"  FAIL  {name}")

    with tempfile.TemporaryDirectory() as d:
        hooks = os.path.join(d, ".claude", "hooks")
        os.makedirs(hooks)
        ref = os.path.join(hooks, "loop_gate.sh")
        open(ref, "w").write("#!/bin/sh\n# v9\nexit 0\n")
        def register(where, target):
            os.makedirs(os.path.dirname(where), exist_ok=True)
            json.dump({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": target}]}]}},
                      open(where, "w"))
        register(os.path.join(d, ".claude", "settings.json"), ref)
        ck("green when the only registration is the reference",
           check(root=d, reference=ref, quiet=True) == 0)

        other = os.path.join(d, ".codex", "hooks", "loop_gate.sh")
        os.makedirs(os.path.dirname(other))
        open(other, "w").write("#!/bin/sh\n# v8\nexit 0\n")
        register(os.path.join(d, ".codex", "hooks.json"), other)
        ck("RED when a second registration points at a drifted copy",
           check(root=d, reference=ref, quiet=True) == 1)

        open(other, "w").write("#!/bin/sh\n# v9\nexit 0\n")
        ck("green again once the second copy matches byte for byte",
           check(root=d, reference=ref, quiet=True) == 0)

        os.remove(other)
        ck("RED when a registration points at a file that is not there",
           check(root=d, reference=ref, quiet=True) == 1)

        # the empty-population guard
        e = tempfile.mkdtemp()
        ck("REFUSES on zero registrations rather than reporting agreement",
           check(root=e, reference=ref, quiet=True) == 1)

        # the version reader, which is the one piece of logic here that is not a hash
        multi = os.path.join(d, "multi.sh")
        open(multi, "w").write("# v9 note\n# v3 older note below\n# v5 note\n")
        ck("version is the HIGHEST `# vN`, not the last one in the file",
           version_of(multi) == 9)
    print(f"hookcopies selfcheck: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else check())
