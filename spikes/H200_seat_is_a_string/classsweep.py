#!/usr/bin/env python3
"""H200 class sweep — the defect is mechanical, so look for it mechanically.

  CLASS: a function takes the axis of independence as a PARAMETER and never
         reads it, so N parties produce one computation repeated N times.

S91's `execute_job_on_agent(agent, job)` never references `agent`. That is not a
judgement about the code, it is an `ast` fact, so the whole tree can be asked.
§12.2: name the class, grep the tree, post it -- the rule only works if the
other lanes know what to grep for.

Reported in two tiers, because precision matters more than the total here:
  * INDEPENDENCE-SHAPED -- the unused parameter is named for a party whose
    distinctness is what a result would be claiming (agent, node, seat, worker,
    host, device, operator, peer, replica, validator, witness, verifier);
  * OTHER -- an unused parameter that carries no such claim. Reported as a count
    only, because an unused argument is ordinary and flagging every one would
    make this instrument the boy who cried wolf.

  python3 spikes/H200_seat_is_a_string/classsweep.py
"""
import ast
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

INDEPENDENCE = ('agent', 'node', 'seat', 'worker', 'host', 'device', 'operator',
                'peer', 'replica', 'validator', 'witness', 'verifier', 'party',
                'member', 'domain')
# `self`/`cls` are bound by the language, and `_`-prefixed names are the
# conventional way to SAY a parameter is unused -- flagging either would be
# measuring style rather than the defect.
EXEMPT = ('self', 'cls')


def unused_params(tree):
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        a = fn.args
        names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
        if a.vararg:
            names.append(a.vararg.arg)
        if a.kwarg:
            names.append(a.kwarg.arg)
        used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        used |= {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        # a nested def may close over the parameter; count those uses too
        for p in names:
            if p in EXEMPT or p.startswith('_'):
                continue
            if p not in used:
                out.append((fn.name, p, fn.lineno))
    return out


def main():
    files = [t for t in subprocess.run(
        ['git', 'ls-files', '*.py'], cwd=ROOT, capture_output=True,
        text=True).stdout.split() if not t.startswith('elders/')]
    # S91 is UNTRACKED (git ls-files returns 0 for it), so a sweep over tracked
    # files alone would miss the very instance that motivated the sweep. Adding
    # it explicitly and saying so, because a corpus that silently excludes the
    # known positive is a check that cannot find what it was built for.
    extra = 'spikes/S91_multi_agent_quorum/run.py'
    if extra not in files and os.path.exists(os.path.join(ROOT, extra)):
        files.append(extra)

    shaped, other = [], 0
    for t in files:
        try:
            tree = ast.parse(open(os.path.join(ROOT, t), errors='replace').read())
        except (SyntaxError, OSError):
            continue
        for fname, param, line in unused_params(tree):
            if any(k in param.lower() for k in INDEPENDENCE):
                shaped.append({'file': t, 'line': line, 'function': fname,
                               'unused_parameter': param})
            else:
                other += 1

    # ---- RECALL, because H194 was one cycle ago and its whole finding was a
    # precision fix measured only in the direction it was made. An unused
    # PARAMETER is one shape of this defect and not the shape itself. Two
    # variants that collapse independence exactly as S91 does and that this
    # detector CANNOT see, constructed rather than imagined:
    MISSED = {
        'label_only': (
            'def execute(agent, job):' + chr(10) +
            '    return {"seat": agent["agent_id"], "digest": sha256(job)}'),
        'no_parameter_at_all': (
            'def run(jobs, roster):' + chr(10) +
            '    for a in roster:' + chr(10) +
            '        votes.append(compute(job))'),
    }
    missed = {}
    for name, src in MISSED.items():
        hits = unused_params(ast.parse(src))
        missed[name] = [h for h in hits
                        if any(k in h[1].lower() for k in INDEPENDENCE)]
    # In `label_only` the seat IS read -- for a label -- while the digest does
    # not depend on it. In `no_parameter_at_all` there is no parameter to be
    # unused. Both produce N identical votes from one computation.
    assert not any(missed.values()), \
        'the recall arm is wrong: these were supposed to be MISSED'

    res = {'files_scanned': len(files),
           'independence_shaped': shaped,
           'other_unused_params': other,
           'recall_limit_constructed_and_missed': sorted(MISSED),
           'recall_note': 'an unused PARAMETER is one shape of the defect, not '
                          'the defect. A seat read only for a LABEL, or a loop '
                          'with no seat parameter at all, collapses independence '
                          'identically and is invisible here. The count below is '
                          'a FLOOR and the two variants above are the proof.',
           'known_positive_present': any(
               s['file'] == extra and s['function'] == 'execute_job_on_agent'
               for s in shaped)}
    # C0. A sweep that cannot find the instance it was written for is inert, and
    # this repo has shipped one of those before (H85). Refuse rather than report.
    assert res['known_positive_present'], \
        'C0 FAILED: the sweep does not find S91 execute_job_on_agent(agent) -- ' \
        'it is inert and its zero would mean nothing'

    with open(os.path.join(HERE, 'classsweep.json'), 'w') as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print('scanned %d python file(s); %d other unused parameter(s) not shown'
          % (res['files_scanned'], other))
    print('INDEPENDENCE-SHAPED unused parameters: %d (a FLOOR -- 2 constructed '
          'variants that collapse independence identically are invisible to '
          'this detector: %s)' % (len(shaped), ', '.join(sorted(MISSED))))
    for s in shaped:
        print('   %s:%d  %s(%s)  <- never read'
              % (s['file'], s['line'], s['function'], s['unused_parameter']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
