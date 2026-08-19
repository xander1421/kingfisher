#!/usr/bin/env python3
"""CLASS SWEEP for H188 (MISSION_LOOP §12.2 — fix the CLASS, never the site).

CLASS: a per-seat function that takes a seat/agent/node/device identity and
never reads it, so N seats are one computation replicated by assignment.

AST, not grep: a name can appear in a docstring or a comment and not be read.
`.venv/` is excluded and the exclusion is REPORTED, not silent — vendored
third-party code is not this fleet's claim surface, and 80 of the 83 raw hits
were pip/scipy/urllib3 keyword arguments.

KNOWN FALSE-POSITIVE SHAPE, stated so the count is not read as 3 defects: a
parameter shadowed by a closure that captures the same name from an enclosing
scope reads as unused here. `G2_rule_learning/learn.py:77` is exactly that.
"""
import ast
import os
import sys

SEAT = ('agent', 'seat', 'node', 'device', 'worker', 'member', 'host',
        'replica', 'target', 'peer')
SKIP = {'.git', '__pycache__', 'target', 'node_modules', '.venv', 'elders'}


def sweep(base='spikes'):
    hits, skipped = [], []
    for root, dirs, files in os.walk(base):
        # COUNT WHERE THE PRUNING HAPPENS. The first version incremented a
        # counter in a branch the pruning made unreachable, so it printed
        # "0 vendored tree(s) skipped" while excluding 80 hits -- family B, in
        # the tool written to report a family-B defect. The counter now IS the
        # pruned list, so it cannot disagree with what was pruned.
        pruned = [d for d in dirs if d in SKIP]
        skipped += [os.path.join(root, d) for d in pruned]
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if not f.endswith('.py'):
                continue
            p = os.path.join(root, f)
            try:
                tree = ast.parse(open(p, encoding='utf-8', errors='replace').read())
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                args = [a.arg for a in n.args.args]
                seats = [a for a in args if any(s in a.lower() for s in SEAT)]
                if not seats:
                    continue
                used = {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}
                dead = [a for a in seats if a not in used]
                if dead:
                    hits.append((p, n.lineno, n.name, dead))
    return sorted(hits), sorted(skipped)


if __name__ == '__main__':
    hits, skipped = sweep()
    for p, ln, name, dead in hits:
        print(f"{p}:{ln} {name}()  UNREAD: {','.join(dead)}")
    print(f"\n{len(hits)} site(s), {len(skipped)} excluded tree(s):")
    for d in skipped:
        print(f"  excluded: {d}")
