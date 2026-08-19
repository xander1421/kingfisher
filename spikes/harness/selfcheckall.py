#!/usr/bin/env python3
"""selfcheckall.py v1 — H78. Run every harness module's `--selfcheck` on a
schedule, because §12.3 was satisfied and nothing ran the result.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **15 modules under `spikes/harness/` ship a `--selfcheck` and the
number executed by any automatic path was 0.** `pre-commit.hook`'s CHECKS list
(line 126) runs `refcheck.py`, `journalcheck.py` and `githygiene.py` in **scan**
mode — the mode that judges the TREE, never the mode that judges the CHECKER.
`githygiene --selfcheck` and `demo8 --selfcheck` are executed by
`spikes/S38_runbook/check_runbook.py`, and `allocid.sh --selfcheck` by
`test_h57_falsify.sh`; nothing automatic runs either of those. The rest are named
only in `.md` prose, and **a mention in a document is not an invocation** — that
distinction is the measurement.

The cost is not hypothetical. On the day this was written `demo8.py --selfcheck`
was **exiting 1**, and had been since `ed1a68e` committed the live spike
directory its positive control depends on. Nobody saw it because nothing looked.

WHERE IT RUNS, AND WHY NOT ANYWHERE ELSE
----------------------------------------
Answered by measurement, not by taste. The repo has exactly ONE automatic path:
`launchctl list` shows `com.kingfisher.bringup` LOADED, running the tracked root
`./bringup.sh` with `RunAtLoad` + `StartInterval 600`. So this is called from
there, as a **REPORTING** step:

  * NOT the pre-commit gate. Bolting tree-wide checks onto a gate three lanes
    share is `pre-commit.hook` v2's F2 — one lane's state refusing every other
    lane's commits (H72).
  * NOT gating inside bringup either. Bringup is the reconciler that STARTS
    lanes; a failing self-check must never stop a lane launching. Same reasoning
    the `RUNNING CODE` block already states for `check_live_launcher.sh`.

THE HANG IS THE REAL RISK, AND IT IS BOUNDED
--------------------------------------------
`bringup.sh` runs every 10 minutes under launchd. A module whose `--selfcheck`
blocks would wedge the fleet reconciler, which is worse than the gap this fills
(preregistered as falsifier F3). `timeout(1)` does not exist on this host, so the
bound is `subprocess.run(timeout=)` and a TIMEOUT is reported as its own state —
never silently as a pass, and never as a hang.

Shell modules are deliberately EXCLUDED: `test_h51_falsify.sh` and friends build
git sandboxes and copy launchers, which is not something to run every ten minutes
under launchd. Reported by name so the exclusion is visible rather than implied.

  python3 selfcheckall.py [--selfcheck]   exit 0 = every selfcheck green.
"""
import os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HARNESS = os.path.join(ROOT, 'spikes', 'harness')
PER_MODULE_TIMEOUT = 60
SELF = os.path.basename(__file__)


def modules(d=None):
    """Modules DISCOVERED, never listed. A hardcoded roster is the defect this
    repo keeps paying for -- it goes stale the next time somebody adds a module
    and reads as coverage. Itself excluded, or this recurses.
    """
    d = d or HARNESS
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith('.py') or name == SELF:
            continue
        try:
            text = open(os.path.join(d, name), encoding='utf-8').read()
        except OSError:
            continue
        # The FLAG must be handled, not merely mentioned: a module whose docstring
        # says "--selfcheck" and has no branch for it would be reported GREEN
        # forever on the strength of a `python3 x.py` that does something else.
        if re.search(r"['\"]--selfcheck['\"]", text):
            out.append(name)
    return out


def demo_only(d=None):
    """H104: modules whose runnable check is demo() on __main__, not --selfcheck.

    Discovered by the property (a demo entry point), not by the flag name.
    Listed, not executed: kfcheck.demo() writes tempfile.mkdtemp() (/tmp),
    and this runner is on a 10-minute launchd path.
    """
    d = d or HARNESS
    flagged = set(modules(d))
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith('.py') or name == SELF or name in flagged:
            continue
        try:
            text = open(os.path.join(d, name), encoding='utf-8').read()
        except OSError:
            continue
        if re.search(r'^def demo\s*\(', text, re.M) and '__main__' in text:
            out.append(name)
    return out


def demo_argv(text):
    """reprocheck's __main__ runs production main() unless --demo is passed."""
    if re.search(r"""['"]--demo['"]""", text):
        return ['--demo']
    return []


def run(d, name, timeout=PER_MODULE_TIMEOUT, extra_args=None, env=None):
    """-> (state, detail). States: GREEN, RED, TIMEOUT, ERROR."""
    args = [sys.executable, os.path.join(d, name)]
    if extra_args is None:
        args.append('--selfcheck')
    else:
        args.extend(extra_args)
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', f'no verdict in {timeout}s'
    except OSError as e:
        return 'ERROR', str(e)
    if p.returncode == 0:
        return 'GREEN', ''
    # The last non-empty line of a refusing selfcheck is its verdict, by
    # convention across every module here. Taken as DETAIL only -- the state is
    # the EXIT CODE, never the text (H72: a gate that judges stdout while
    # discarding rc reads a crash as clean).
    lines = [l for l in (p.stdout + p.stderr).strip().split('\n') if l.strip()]
    return 'RED', (lines[-1][:120] if lines else f'exit {p.returncode}, no output')


def scan(d=None, timeout=PER_MODULE_TIMEOUT):
    d = d or HARNESS
    names = modules(d)
    demos = demo_only(d)
    bad = []
    for name in names:
        state, detail = run(d, name, timeout)
        print(f'  {state:8} {name}' + (f' -- {detail}' if detail else ''))
        if state != 'GREEN':
            bad.append(name)
    # H104: the certify() stack is demo() on __main__, not --selfcheck.
    # TMPDIR under the workspace: kfcheck.demo() uses mkdtemp (/tmp otherwise).
    tmp = os.path.join(d, '.selfcheckall_demo_tmp')
    os.makedirs(tmp, exist_ok=True)
    env = os.environ.copy()
    env['TMPDIR'] = tmp
    try:
        for name in demos:
            text = open(os.path.join(d, name), encoding='utf-8').read()
            state, detail = run(d, name, timeout, extra_args=demo_argv(text), env=env)
            print(f'  {state:8} {name}' + (f' -- {detail}' if detail else ''))
            if state != 'GREEN':
                bad.append(name)
    finally:
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except OSError:
            pass
    n = len(names) + len(demos)
    shell = sorted(n for n in os.listdir(d)
                   if n.endswith('.sh') and '--selfcheck' in
                   open(os.path.join(d, n), encoding='utf-8', errors='replace').read())
    if shell:
        print(f'  NOT RUN  {len(shell)} shell module(s) carry --selfcheck and are '
              f'excluded here (they build git sandboxes): ' + ' '.join(shell))
    if bad:
        print(f'\nselfcheckall: {len(bad)} of {n} harness selfcheck(s) '
              f'are not green -- ' + ', '.join(bad))
        return 1
    print(f'selfcheckall: all {n} harness selfcheck(s) green')
    return 0


def selfcheck():
    """Both directions plus the two states a naive runner gets wrong.

    Fixtures are written under the WORKSPACE, never `/tmp` (§10, and the lane
    that wrote this broke that rail in two consecutive cycles).
    """
    import shutil
    d = os.path.join(ROOT, 'spikes', 'harness', '.selfcheckall_fixture')
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    try:
        open(os.path.join(d, 'green.py'), 'w').write(
            "import sys\nif '--selfcheck' in sys.argv: sys.exit(0)\n")
        open(os.path.join(d, 'red.py'), 'w').write(
            "import sys\nprint('fixture: 1 FAILED -- deliberate')\n"
            "if '--selfcheck' in sys.argv: sys.exit(1)\n")
        open(os.path.join(d, 'hangs.py'), 'w').write(
            "import sys, time\nif '--selfcheck' in sys.argv: time.sleep(30)\n")
        # Mentions the flag in a comment and never handles it. A discovery rule
        # that greps for the bare word calls this covered.
        open(os.path.join(d, 'mentions_only.py'), 'w').write(
            "# this module talks about --selfcheck and implements nothing\n")
        open(os.path.join(d, 'demo_only.py'), 'w').write(
            "def demo():\n    print('demo ran')\n"
            "if __name__ == '__main__':\n    demo()\n")
        open(os.path.join(d, 'demo_red.py'), 'w').write(
            "def demo():\n    print('demo failed on purpose')\n    raise SystemExit(1)\n"
            "if __name__ == '__main__':\n    demo()\n")

        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = scan(d, timeout=2)
        out = buf.getvalue()

        bad = []

        def ck(cond, note):
            print(f'  {"ok  " if cond else "FAIL"}  {note}')
            if not cond:
                bad.append(note)

        ck('GREEN    green.py' in out, 'a passing selfcheck reports GREEN')
        ck('RED      red.py' in out, 'a failing selfcheck reports RED')
        ck('deliberate' in out, "RED carries the module's own last line as detail")
        # The two a naive runner gets wrong, and the reason this file exists as a
        # module instead of three lines of shell in bringup.sh.
        ck('TIMEOUT  hangs.py' in out,
           'a HANGING selfcheck is bounded and reported TIMEOUT, not waited on')
        ck('hangs.py' not in out.split('TIMEOUT  hangs.py')[0],
           'the hang is not reported GREEN before it is reported TIMEOUT')
        ck('mentions_only' not in out,
           'a module that only MENTIONS the flag is not counted as covered')
        ck('GREEN    demo_only.py' in out,
           'H104: demo() on __main__ is executed under the timeout contract')
        ck('RED      demo_red.py' in out,
           'H104: a failing demo() reports RED, not skipped')
        ck('DEMO' not in out,
           'H104: demo() modules are no longer listed-and-skipped')
        # Anti-inversion: without this, "report RED for everything" passes above.
        ck(rc == 1, 'a set containing a red module exits 1')
        b2 = io.StringIO()
        for f in ('red.py', 'hangs.py', 'demo_red.py'):
            os.remove(os.path.join(d, f))
        with contextlib.redirect_stdout(b2):
            rc2 = scan(d, timeout=2)
        ck(rc2 == 0, 'an all-green set exits 0, so the exit code is not a constant')

        if bad:
            print(f'SELFCHECK FAILED: {bad}')
            return 1
        print('selfcheck: green/red/timeout/mention-only all distinguished, and '
              'the exit code moves in both directions')
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else scan())
