#!/usr/bin/env python3
"""H94 probe — MEASURE BEFORE BUILDING. What would a key-loss rule refuse?

Walks every committed revision of every journal and of CHANNEL.md, extracts the
two candidate key families, and reports every revision where a key present in the
parent revision is absent in the child. This is F2: the H14 gate. A rule that
refuses on revisions that are legitimate is a checker everyone learns to ignore,
so the refusals it produces here are read one by one BEFORE the rule ships.

  python3 probe.py            # every candidate rule, every revision
"""
import re, subprocess, sys, os

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

CYCLE = re.compile(r'^#{2,}\s*Cycle\s+(\d+)', re.M)
# verb-agnostic: `<id> <lane>`, so a CLAIM edited in place into a DONE is one key
LOG_VERB = re.compile(r'^(CLAIM|DONE)\s+(\S+)\s+(\S+)', re.M)


def keys(text, kind):
    if kind == 'cycle':
        return {'Cycle ' + m for m in CYCLE.findall(text)}
    if kind == 'log_verb':          # CLAIM/DONE kept distinct
        return {f'{v} {i} {l}' for v, i, l in LOG_VERB.findall(text)}
    if kind == 'log_pair':          # verb-agnostic
        return {f'{i} {l}' for v, i, l in LOG_VERB.findall(text)}
    if kind == 'log_done':          # completed work only
        return {f'{i} {l}' for v, i, l in LOG_VERB.findall(text) if v == 'DONE'}
    raise SystemExit('bad kind')


def show(rev, path):
    r = subprocess.run(['git', 'show', f'{rev}:{path}'],
                       capture_output=True, text=True, cwd=ROOT)
    return r.stdout if r.returncode == 0 else None


def revisions(path):
    r = subprocess.run(['git', 'rev-list', '--reverse', 'HEAD', '--', path],
                       capture_output=True, text=True, cwd=ROOT)
    return [x for x in r.stdout.split() if x]


def subject(rev):
    return subprocess.run(['git', 'log', '-1', '--format=%h %s', rev],
                          capture_output=True, text=True, cwd=ROOT).stdout.strip()


def main():
    docs = subprocess.run(['git', 'ls-files'], capture_output=True, text=True,
                          cwd=ROOT).stdout.split()
    journals = [d for d in docs if re.fullmatch(r'HANDOFF(\.[\w.-]+)?\.md', d)]
    targets = [(j, 'cycle') for j in sorted(journals)]
    for kind in ('log_verb', 'log_pair', 'log_done'):
        targets.append(('CHANNEL.md', kind))

    total = {}
    for path, kind in targets:
        revs = revisions(path)
        losses = 0
        for i in range(1, len(revs)):
            a, b = show(revs[i - 1], path), show(revs[i], path)
            if a is None or b is None:
                continue
            lost = keys(a, kind) - keys(b, kind)
            if lost:
                losses += 1
                print(f'{kind:9s} {path:24s} {subject(revs[i])}')
                for k in sorted(lost):
                    print(f'            LOST  {k}')
        total[(path, kind)] = (len(revs), losses)

    print()
    for (path, kind), (n, l) in sorted(total.items()):
        print(f'{kind:9s} {path:24s} {n:3d} revisions, {l} with a lost key')


main()
