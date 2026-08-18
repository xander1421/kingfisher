#!/usr/bin/env python3
"""H98 falsifier half 2, RUN: does the fix turn any currently-green spike RED?

Stated in CHANNEL.md before the fix existed. It is not answerable by reasoning:
a directory's mtime moves on CREATE/DELETE, a file's on MODIFY, so expanding a
directory into its files can raise the floor as well as lower it, and an artifact
sitting between the two flips green -> red.

METHOD: recompute BOTH floors -- old (directory mtime, v2) and new (expanded
files, v3) -- for every dep tree, then re-run the exact comparison `record` makes
for every artifact declared in every provenance*.json on disk. No experiment is
re-executed; this reads the recorded declarations.
"""
import glob
import json
import os
import sys
sys.path.insert(0, os.path.abspath('spikes/harness'))
import provenance as P

ROOT = os.path.abspath('.')


def old_floor(path, exclude=()):
    """v2's loop, verbatim: the porcelain path is used AS A FILE."""
    excl_spec = [':(exclude)*.md', ':(exclude)provenance.json']
    for x in exclude:
        try:
            rel = os.path.relpath(os.path.realpath(x), os.path.realpath(path))
        except ValueError:
            continue
        if not rel.startswith('..'):
            excl_spec.append(f':(exclude){rel}')
    head = P._run(['git', 'log', '-1', '--format=%ct', '--', '.'] + excl_spec, cwd=path)
    newest, nf = (int(head) if head.isdigit() else 0), '<HEAD commit>'
    root = P._run(['git', 'rev-parse', '--show-toplevel'], cwd=path) or path
    dirty = [l.split(None, 1)[-1]
             for l in P._run(['git', 'status', '--porcelain', '--', '.'] + excl_spec,
                             cwd=path).splitlines() if l.split(None, 1)]
    excl = {os.path.realpath(x) for x in exclude}
    for f in dirty:
        fp = os.path.join(root, f)
        if not os.path.exists(fp) or os.path.realpath(fp) in excl:
            continue
        m = int(os.path.getmtime(fp))
        if m > newest:
            newest, nf = m, f
    return newest, nf


recs = sorted(glob.glob('spikes/**/provenance*.json', recursive=True))
flips_red, flips_green, checked, skipped, unresolved = [], [], 0, 0, []
for r in recs:
    try:
        d = json.load(open(r))
    except Exception:
        skipped += 1
        continue
    arts = d.get('artifacts') or []
    deps = [x.get('path') for x in (d.get('repos') or []) if x.get('path')]
    deps = [x for x in deps if os.path.isdir(x)]
    if not arts or not deps:
        skipped += 1
        continue
    # ARTIFACT PATHS ARE RECORDED RELATIVE TO THE SPIKE THAT WROTE THEM, and
    # v1 of this sweep resolved them against the repo root instead. Every such
    # path failed os.path.exists and was skipped, so the sweep reported
    # `RED->GREEN 0` -- a clean null from a probe that never reached a single
    # one of the records the fix is about, including its own. A29: reaching the
    # target is a precondition of the verdict. Caught by asking why the fix that
    # had demonstrably just flipped H88 did not appear in a sweep that claimed
    # to cover it.
    here = os.path.dirname(os.path.abspath(r))
    resolve = lambda ap: ap if os.path.isabs(ap) else os.path.join(here, ap)
    excl = [resolve(a['path']) for a in arts if a.get('path')] + \
           [os.path.join(here, 'provenance.json')]
    for dep in deps:
        o, of = old_floor(dep, exclude=excl)
        n, nf = P.newest_source_mtime(dep, exclude=excl)
        for a in arts:
            ap = a.get('path')
            if not ap:
                continue
            ap = resolve(ap)
            if not os.path.exists(ap):
                unresolved.append((r, a.get('path')))
                continue
            checked += 1
            ts, _ = P.artifact_time(ap)
            was_stale, now_stale = ts < o, ts < n
            if now_stale and not was_stale:
                flips_red.append((r, os.path.basename(ap), o, n, nf))
            elif was_stale and not now_stale:
                flips_green.append((r, os.path.basename(ap), o, n, of))

# THE REACH LINE. A sweep that resolves nothing prints the same two zeros as a
# sweep that found nothing, and only this number tells them apart.
print(f'records={len(recs)} usable_checks={checked} skipped_records={skipped} '
      f'unresolved_artifacts={len(unresolved)}')
if checked == 0:
    print('REACH FAILURE: no artifact resolved -- the verdict below is vacuous')
    sys.exit(2)
print(f'GREEN->RED  {len(flips_red)}   <-- the falsifier; any non-zero and the fix is a regression')
for f in flips_red:
    print('   RED ', f)
print(f'RED->GREEN  {len(flips_green)}  <-- the defect being removed')
for f in flips_green[:12]:
    print('   FIX ', f)
sys.exit(1 if flips_red else 0)
