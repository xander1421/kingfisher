#!/usr/bin/env python3
"""H7 — do the loop-harness checks FAIL when their defect comes back?

MISSION_LOOP §5: *a control that cannot fail is not a control.* Every check in
`test_loop_gate.sh` was written in response to a defect that had already
shipped, so every one of them has a known-failing input on record: the code as
it stood before its fix. Nothing had ever driven them against that input, so
"37 checks pass" was a statement about the current tree and not about the
checks.

That gap is the one this repo keeps paying for. `test_loop_gate.sh`'s own
header records the 15-check version passing while the hook was broken, because
every check set CALLSIGN; check 3 asserted the bare-signal path WORKED and so
certified the hole it was meant to close. A green suite is evidence only if a
red one is reachable.

ISOLATION. The suite mutates `.loop_signal*` / `.loop_exit.*` / `.loop_blocks.*`
in its ROOT and drives `run_loop.sh` with a stub `claude`. Reverting a fix in
the live tree would disarm the live Stop hook for as long as the run takes,
with lanes running against it. So each falsifier is applied to a fresh COPY and
the live tree is never written. Same rule the suite states for itself: a test
that can stop production is not a test.

REVERTS USE `edits.anchored_replace`, never `str.replace`: a revert whose anchor
has drifted would silently do nothing, the check would pass, and this script
would report the check as sound on the strength of having tested nothing. That
is the exact failure mode the module exists for, and it is the one this script
is most exposed to.

usage:  python3 spikes/H7_harness_attack/falsify.py
exit 0 = every check fired on its own defect. Non-zero = a check is inert.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'spikes', 'harness'))
from edits import anchored_replace, AnchorMissing          # noqa: E402

SUITE = 'spikes/harness/test_loop_gate.sh'
GATE = '.claude/hooks/loop_gate.sh'
LAUNCHER = 'run_loop.sh'

# Files the suite reads out of ROOT. settings.json is copied because the
# registration block enumerates them with `git ls-files`.
TREE = [SUITE, GATE, LAUNCHER,
        'spikes/harness/commit-msg.hook',
        'spikes/harness/install_hooks.sh',
        '.claude/settings.json',
        'spikes/S51_multicore/.claude/settings.json']

# (id, why it is here, file, anchor, replacement, check that must go red)
FALSIFIERS = [
    ('F1',
     'the refusal message names the bare path v5 stopped accepting, so a lane '
     'obeying the hook verbatim can never exit',
     GATE,
     'into the file .loop_signal.%s ,',
     'into the file .loop_signal , (lane %s),',
     'refusal names a path the hook obeys'),

    ('F2',
     'the launcher leaves a previous span\'s terminal signal armed, so the next '
     'span exits at its first turn end having done no work',
     LAUNCHER,
     'rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK" ".loop_signal.${CALLSIGN}"',
     'rm -f ".loop_blocks.${CALLSIGN}" "$EXIT_MARK"',
     'launcher clears a stale signal'),

    ('F3',
     'the callsign is interpolated into the refusal JSON unvalidated, so a '
     'quote in it makes the block decision unparseable and the refusal is lost',
     GATE,
     'case "$LANE" in (*[!A-Za-z0-9._-]*) exit 0 ;; esac\n',
     '',
     'UNPARSEABLE decision'),

    # F4-F6 are the three defects that were OBSERVED live rather than reasoned
    # about, so they are the ones whose guards most need to be non-inert.
    ('F4',
     'v3\'s LANE default collapsed every callsign-less session into one shared '
     'lane, so a human reading the repo was gated and incremented the fleet fuse',
     GATE,
     'if [ -z "${CALLSIGN:-}" ]; then\n  exit 0\nfi\nLANE="$CALLSIGN"',
     'LANE="${CALLSIGN:-unknown}"',
     'no callsign is not gated'),

    ('F5',
     'accepting a bare signal let whichever lane\'s hook fired first consume it '
     'and exit in the place of the lane that wrote it',
     GATE,
     'for SIGFILE in ".loop_signal.${LANE}"; do',
     'for SIGFILE in ".loop_signal.${LANE}" ".loop_signal"; do',
     'bare signal is REFUSED'),

    ('F6',
     'a non-numeric fuse counter was written back unchanged, so the arithmetic '
     'errored and the hook blocked forever with a fuse that could never trip',
     GATE,
     "case \"$N\" in (''|*[!0-9]*) N=0 ;; esac\n",
     '',
     'corrupt fuse file recovers'),

    ('F7',
     'the enforcing commit gate lives in untracked .git/hooks/, so it can drift '
     'from the tracked source that gets reviewed, or be absent entirely',
     '.git/hooks/commit-msg',
     'exit 0\n',
     'exit 0\n# drifted from source\n',
     'DRIFTED from its tracked source'),

    ('F8',
     'the launcher spawns a lane on a callsign the hook silently refuses to '
     'gate, so the lane runs unsupervised with no loop contract and looks normal',
     LAUNCHER,
     'case "$CALLSIGN" in (*[!A-Za-z0-9._-]*)',
     'case "$CALLSIGN" in (thiswillnevermatch)',
     'launcher refuses what the hook will not gate'),
]


def build(dst):
    """Copy the harness under test into a scratch tree."""
    for rel in TREE:
        d = os.path.join(dst, os.path.dirname(rel))
        os.makedirs(d, exist_ok=True)
        shutil.copy2(os.path.join(REPO, rel), os.path.join(dst, rel))
    # The registration block enumerates settings.json with `git ls-files`, and
    # the commit-gate check reads .git/hooks -- so the scratch tree has to be a
    # real repo with the hooks installed the same way a fresh clone would.
    for cmd in (['git', 'init', '-q'], ['git', 'add', '-A'],
                ['sh', 'spikes/harness/install_hooks.sh']):
        subprocess.run(cmd, cwd=dst, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_suite(root):
    """Run the suite in `root`; return (pass_count, [failed check names])."""
    p = subprocess.run(['bash', SUITE], cwd=root, capture_output=True, text=True)
    out = p.stdout + p.stderr
    failed = [m.strip() for m in re.findall(r'^  FAIL  (.*)$', out, re.M)]
    passed = len(re.findall(r'^  PASS  ', out, re.M))
    return passed, failed, out


def main():
    problems = []

    # CONTROL. An unmodified copy must come back all-green. Without it a driver
    # that broke every copy -- a bad `build`, a missing file, an unset PATH --
    # would report all three falsifiers firing and read as a perfect result.
    # This is the check that tells "the defect fired" from "the copy is rubble".
    tmp = tempfile.mkdtemp(prefix='h7_control_')
    try:
        build(tmp)
        base_pass, base_fail, out = run_suite(tmp)
        if base_fail:
            problems.append(f'CONTROL: unmodified copy already fails: {base_fail}')
            print(out)
        print(f'  CONTROL  unmodified copy: {base_pass} pass, '
              f'{len(base_fail)} fail  -> {"ok" if not base_fail else "BROKEN"}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for fid, why, rel, old, new, want in FALSIFIERS:
        tmp = tempfile.mkdtemp(prefix=f'h7_{fid}_')
        try:
            build(tmp)
            path = os.path.join(tmp, rel)
            src = open(path).read()
            try:
                open(path, 'w').write(anchored_replace(src, old, new))
            except AnchorMissing as e:
                # The fix moved and this falsifier no longer describes it. Loud,
                # because the silent version is a green report over no test.
                problems.append(f'{fid}: anchor gone, revert tested NOTHING ({e})')
                print(f'  {fid}  ANCHOR MISSING in {rel} — cannot falsify')
                continue

            n_pass, failed, out = run_suite(tmp)
            hit = [f for f in failed if want in f]
            if not failed:
                problems.append(f'{fid}: defect restored, suite still all-green '
                                f'({n_pass} pass) — "{want}" is INERT')
                print(f'  {fid}  INERT   defect restored and nothing went red')
            elif not hit:
                problems.append(f'{fid}: suite went red on {failed}, but not on '
                                f'"{want}" — wrong check fired')
                print(f'  {fid}  WRONG   red on {failed}, expected "{want}"')
            else:
                print(f'  {fid}  FIRES   {hit[0]}')
                print(f'           defect: {why}')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print()
    if problems:
        print(f'H7: {len(problems)} check(s) do not fail on their own defect')
        for p in problems:
            print(f'  - {p}')
        return 1
    print(f'H7: {len(FALSIFIERS)} checks each go red on the defect they exist '
          f'for, and the unmodified control stays green')
    return 0


if __name__ == '__main__':
    sys.exit(main())
