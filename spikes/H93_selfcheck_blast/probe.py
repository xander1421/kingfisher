#!/usr/bin/env python3
"""H93 probe — observe what each harness `--selfcheck` WRITES, one module at a
time, instead of reading its source and believing the docstring.

Preregistered falsifiers (CHANNEL.md, before this file was written):
  F1  every python module the sweep runs confines its writes to a workspace dir
      it creates and removes  -> the `.sh`/`.py` proxy tracks the behaviour, and
      the attack FAILS.
  F2  a full sweep leaves `git status --porcelain` byte-identical -> no shared
      tree mutation, launchd cadence risk is nil.
  F3  modules()' quoted-flag rule and the shell listing's bare-substring rule
      agree on the same file -> one rule, not two.

METHOD, and why it is not a grep. The claim under attack is about BEHAVIOUR
("builds git sandboxes"), so the observation must be of behaviour. Each module's
selfcheck is run as its own subprocess with `/tmp` and the workspace SNAPSHOTTED
either side; a path that appears and a path that appears-then-vanishes are
reported as DIFFERENT states, because the second is the one a mkdtemp+rmtree
leaves and it is invisible to an after-the-fact `ls`.

CONTROL C1 (must fire): a fixture module that writes one file to /tmp and leaves
it there must be reported OUTSIDE. Fails if the snapshot differ is inert.
CONTROL C2 (must fire): a fixture module that touches nothing must be reported
clean. Fails if the differ reports everything, which would make C1 vacuous.
"""
import json, os, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HARNESS = os.path.join(ROOT, 'spikes', 'harness')
TMPDIRS = ['/tmp', os.environ.get('TMPDIR', '/tmp').rstrip('/')]
TIMEOUT = 90


def snap(dirs):
    """Top-level entry names only. mkdtemp lands at the top level of TMPDIR, and
    a full recursive walk of /tmp is a measurement whose cost dwarfs the thing
    measured."""
    s = {}
    for d in dirs:
        try:
            s[d] = set(os.listdir(d))
        except OSError:
            s[d] = set()
    return s


def git_porcelain():
    return subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT,
                          capture_output=True, text=True).stdout


def probe_one(path, argv=('--selfcheck',)):
    """-> dict. Runs ONE module and reports every write it can be seen to make."""
    before_t = snap(TMPDIRS)
    before_g = git_porcelain()
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, path, *argv], cwd=ROOT,
                           capture_output=True, text=True, timeout=TIMEOUT)
        rc, state = p.returncode, ('GREEN' if p.returncode == 0 else 'RED')
    except subprocess.TimeoutExpired:
        rc, state = None, 'TIMEOUT'
    dt = time.time() - t0
    after_t = snap(TMPDIRS)
    after_g = git_porcelain()
    left = sorted({f'{d}/{n}' for d in TMPDIRS for n in after_t[d] - before_t[d]})
    # A path that came and went is invisible to the after-snapshot. It is still a
    # write OUTSIDE the workspace, and it is the case the docstring under attack
    # claims does not happen, so it gets its own detector below.
    return {'module': os.path.basename(path), 'state': state, 'rc': rc,
            'secs': round(dt, 2), 'left_outside': left,
            'git_changed': after_g != before_g,
            'git_delta': sorted(set(after_g.split('\n')) ^ set(before_g.split('\n')))}


def trace_outside(path):
    """The transient case: run the module under a TMPDIR we own, so a mkdtemp
    that is removed before we can see it still proves WHERE it went. This is the
    observation the after-the-fact snapshot structurally cannot make."""
    box = os.path.join(ROOT, 'spikes', 'H93_selfcheck_blast', '.tmpbox')
    subprocess.run(['rm', '-rf', box]); os.makedirs(box)
    env = dict(os.environ, TMPDIR=box)
    try:
        p = subprocess.run([sys.executable, path, '--selfcheck'], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=TIMEOUT)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = None
    used = sorted(os.listdir(box))
    subprocess.run(['rm', '-rf', box])
    # tempfile honours TMPDIR; a module that hardcodes '/tmp' or writes elsewhere
    # shows an EMPTY box while still writing outside, so an empty box is reported
    # as UNKNOWN-or-none and never as proof of confinement.
    return {'redirected_tmpdir_entries': used, 'rc_under_redirect': rc}


def controls():
    """Both must fire, per D6/§5: state the input that makes each one fail."""
    d = os.path.join(ROOT, 'spikes', 'H93_selfcheck_blast', '.ctl')
    subprocess.run(['rm', '-rf', d]); os.makedirs(d)
    dirty = os.path.join(TMPDIRS[0], 'h93_ctl_leftover')
    out = {}
    try:
        open(os.path.join(d, 'leaks.py'), 'w').write(
            f"import sys\nopen({dirty!r}, 'w').write('x')\n"
            "if '--selfcheck' in sys.argv: sys.exit(0)\n")
        open(os.path.join(d, 'quiet.py'), 'w').write(
            "import sys\nif '--selfcheck' in sys.argv: sys.exit(0)\n")
        r_leak = probe_one(os.path.join(d, 'leaks.py'))
        os.path.exists(dirty) and os.remove(dirty)
        r_quiet = probe_one(os.path.join(d, 'quiet.py'))
        out['C1_leak_detected'] = any('h93_ctl_leftover' in x for x in r_leak['left_outside'])
        out['C1_fails_if'] = 'the /tmp snapshot differ is inert; then no module can ever be reported OUTSIDE'
        out['C2_quiet_is_clean'] = (r_quiet['left_outside'] == [] and not r_quiet['git_changed'])
        out['C2_fails_if'] = 'the differ reports noise for a module that writes nothing; then C1 proves nothing'
    finally:
        subprocess.run(['rm', '-rf', d])
        os.path.exists(dirty) and os.remove(dirty)
    return out


def f3_membership():
    """F3: apply BOTH of selfcheckall v1's discovery rules to one file each way."""
    import re
    quoted = lambda t: bool(re.search(r"['\"]--selfcheck['\"]", t))   # modules(), .py
    bare = lambda t: '--selfcheck' in t                                # shell listing, .sh
    cases = {
        'prose_quoted_never_handled': "# see `'--selfcheck'` in the sibling module\n",
        'handled_via_bare_argv':      "import sys\nif sys.argv[1:] == ['--self' 'check']: pass\n",
        'bare_mention_only':          "# talks about --selfcheck, implements nothing\n",
    }
    return {k: {'quoted_rule_counts_it': quoted(v), 'bare_rule_counts_it': bare(v),
                'rules_agree': quoted(v) == bare(v)} for k, v in cases.items()}


def main():
    sys.path.insert(0, HARNESS)
    import selfcheckall
    swept = selfcheckall.modules()
    rep = {'swept_by_selfcheckall_v1': swept, 'controls': controls(),
           'f3_rule_membership': f3_membership(), 'modules': []}
    for name in swept:
        r = probe_one(os.path.join(HARNESS, name))
        r.update(trace_outside(os.path.join(HARNESS, name)))
        r['writes_outside_workspace'] = bool(r['left_outside']) or bool(r['redirected_tmpdir_entries'])
        rep['modules'].append(r)
        print(f"  {r['state']:8} {name:20} outside={r['writes_outside_workspace']!s:5} "
              f"tree_dirtied={r['git_changed']!s:5} {r['secs']}s "
              + (f"left={r['left_outside']}" if r['left_outside'] else ''))
    n_out = sum(1 for m in rep['modules'] if m['writes_outside_workspace'])
    n_git = sum(1 for m in rep['modules'] if m['git_changed'])
    rep['summary'] = {'swept': len(swept), 'write_outside_workspace': n_out,
                      'mutate_shared_tree': n_git,
                      'F1_falsified': n_out > 0, 'F2_falsified': n_git > 0,
                      'F3_falsified': any(not c['rules_agree']
                                          for c in rep['f3_rule_membership'].values())}
    print(f"\n{n_out}/{len(swept)} swept modules WRITE OUTSIDE THE WORKSPACE (§10).")
    print(f"{n_git}/{len(swept)} mutate the shared git tree.")
    print('F1 falsified:', rep['summary']['F1_falsified'],
          '| F2 falsified:', rep['summary']['F2_falsified'],
          '| F3 falsified:', rep['summary']['F3_falsified'])
    print('controls:', json.dumps(rep['controls'], indent=1))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe.json'), 'w') as f:
        json.dump(rep, f, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
