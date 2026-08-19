#!/usr/bin/env python3
"""H223 probe — a materialised copy of the repo, inside the tree the instruments walk.

Measures, in this order, and NOTHING here re-derives a rule another module owns:

  BEFORE  each disk-walking harness module is run and its output SIZE is asserted
          before its hit count is read (error 42: the first sweep for this row
          printed `stray_hits=0` for all seven modules because macOS has no
          `timeout`, every run exited 127 with zero output, and only the size
          column said so).
  F1      `git check-ignore` on the stray tree -- if it is IGNORED, the three
          modules simply are not consulting .gitignore and there is no class.
  F2      census: every untracked directory in the workspace, scored by how many
          of its files have a path SUFFIX that is a tracked repo path. That is
          the predicate for "a copy of part of this tree", and it is prefix-blind
          on purpose -- the observed copy sits one level down, under `fresh/`,
          so a root-filename test would have missed it.
  F3      blast radius: does any tracked document quote a count from one of the
          three contaminated modules?
  AFTER   the stray tree is deleted and the three modules are re-run. Absence of
          hits means nothing unless the instrument still speaks: the size guard
          runs again on every AFTER measurement.

repro: python3 spikes/H223_copy_of_the_tree/probe.py
"""
import json, os, subprocess, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STRAY = 'spikes/H210_refutation_outlives_target'
# Modules that walk the disk rather than `git ls-files`, from a source census:
#   grep -lE 'os.walk|rglob|glob.glob' spikes/harness/*.py
WALKERS = ['constcheck', 'leakcheck', 'recheck', 'cite', 'prosecite', 'versioncheck', 'stalecheck']


def run(cmd, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def measure_walkers(label):
    """Run each walker. SIZE FIRST, then hits -- a silent instrument has no verdict."""
    out = {}
    for m in WALKERS:
        path = os.path.join(ROOT, 'spikes', 'harness', m + '.py')
        if not os.path.exists(path):
            out[m] = {'ran': False, 'why': 'no such module'}
            continue
        rc, text = run([sys.executable, path])
        lines = text.count('\n')
        out[m] = {
            'ran': lines > 0,                      # the guard, not the finding
            'rc': rc,
            'output_lines': lines,
            'stray_hits': sum(1 for L in text.splitlines() if STRAY in L),
        }
        print(f'  {label:7} {m:<13} rc={rc:<4} output_lines={lines:<6} '
              f'stray_hits={out[m]["stray_hits"]}'
              + ('' if out[m]['ran'] else '   <-- SILENT: this run has NO verdict'))
    return out


def tracked_paths():
    rc, text = run(['git', 'ls-files'])
    assert rc == 0, f'git ls-files exited {rc}'      # error 42, mechanised
    return set(text.splitlines())


def untracked_dirs():
    rc, text = run(['git', 'status', '--porcelain', '--untracked-files=normal'])
    assert rc == 0, f'git status exited {rc}'
    return [L[3:] for L in text.splitlines() if L.startswith('?? ') and L.rstrip().endswith('/')]


def copy_score(d, tracked):
    """How many files under `d` have a path SUFFIX that is a tracked repo path.

    Prefix-blind by construction: the observed copy is at `<d>/fresh/<repo path>`,
    so anything anchored at `d` or at a root filename cannot see it.
    """
    n = 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, d)):
        dirnames[:] = [x for x in dirnames if x != '.git']
        for fn in filenames:
            total += 1
            rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).split(os.sep)
            for i in range(len(rel)):
                if '/'.join(rel[i:]) in tracked:
                    n += 1
                    break
    return n, total


def main():
    os.chdir(ROOT)
    res = {'stray': STRAY}

    stray_abs = os.path.join(ROOT, STRAY)
    res['stray_present_at_start'] = os.path.isdir(stray_abs)
    if res['stray_present_at_start']:
        nf = sum(len(f) for _, _, f in os.walk(stray_abs))
        res['stray_files'] = nf
        res['stray_bytes'] = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(stray_abs) for f in fs
            if os.path.exists(os.path.join(dp, f)))

    print('== BEFORE: the seven disk-walking modules, size asserted before hits ==')
    res['before'] = measure_walkers('BEFORE')

    print('== F1: is the stray tree gitignored? ==')
    rc, _ = run(['git', 'check-ignore', '-q', STRAY])
    res['f1_check_ignore_rc'] = rc          # 0 = ignored, 1 = not ignored
    res['f1_fired'] = (rc == 0)
    print(f'  git check-ignore rc={rc}  ->  ' +
          ('IGNORED (F1 FIRES: the modules just are not consulting .gitignore)'
           if rc == 0 else 'NOT ignored (F1 does not fire: .gitignore could not have saved this)'))

    print('== F2: census of every untracked directory, scored as a copy of this tree ==')
    tracked = tracked_paths()
    res['tracked_files'] = len(tracked)
    census = []
    for d in untracked_dirs():
        n, total = copy_score(d, tracked)
        census.append({'dir': d, 'files': total, 'tracked_path_suffixes': n})
        print(f'  {d:<50} files={total:<6} tracked-path suffixes={n}')
    res['census'] = census
    copies = [c for c in census if c['tracked_path_suffixes'] >= 20]
    res['copies'] = copies
    res['f2_fired'] = len([c for c in copies if not c['dir'].startswith(STRAY)]) == 0
    print(f'  copies (>=20 tracked-path suffixes): {[c["dir"] for c in copies]}')
    print('  F2 ' + ('FIRES: mine is the only one -- the rate is the deliverable, no module ships'
                     if res['f2_fired'] else 'does not fire: a second copy exists'))

    print('== F3: does any tracked document quote a count from a contaminated module? ==')
    rc, text = run(['git', 'grep', '-n', '-iE',
                    r'constcheck|leakcheck|recheck\.py', '--', '*.md'])
    quotes = [L for L in text.splitlines() if any(ch.isdigit() for ch in L.split(':', 2)[-1])]
    res['f3_doc_mentions'] = len(text.splitlines())
    res['f3_numeric_mentions'] = len(quotes)
    res['f3_fired'] = len(quotes) == 0
    print(f'  {len(text.splitlines())} document mentions, {len(quotes)} carrying a number')
    print('  F3 ' + ('FIRES: nothing quotes them, blast radius zero'
                     if res['f3_fired'] else 'does not fire: read the numeric mentions'))
    res['f3_numeric_lines'] = quotes[:40]

    if res['stray_present_at_start']:
        print('== REMEDY: deleting the stray tree ==')
        shutil.rmtree(stray_abs)
        res['stray_deleted'] = True
        print('== AFTER: the same seven modules, size asserted again ==')
        res['after'] = measure_walkers('AFTER')

    with open(os.path.join(HERE, 'probe.json'), 'w') as fh:
        json.dump(res, fh, indent=2, sort_keys=True)
    print(f'wrote {os.path.join(HERE, "probe.json")}')
    return res


if __name__ == '__main__':
    main()
