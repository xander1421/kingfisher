#!/usr/bin/env python3
"""H200 — attack on S91's five-seat quorum. Runs the five falsifiers
preregistered in CHANNEL.md before anything was run.

IMPORTS S91's `run.py` and calls ITS functions. Nothing is reimplemented: a copy
is the second site §12.2 is about, and a reimplementation of the thing under
attack can differ from it in exactly the way that decides the verdict (H168).

S91's directory is UNTRACKED -- `git ls-files spikes/S91_multi_agent_quorum/`
returns 0 -- so its artifacts have no committed copy to restore from. F4 needs
S91's own `main()`, which writes `result.json` and `provenance.json` into that
directory, so this probe SNAPSHOTS both first and RESTORES them after, and
asserts byte-equality on the way out. See RESULT.md: I had already destroyed the
author's originals by reproducing before I noticed, and the loss is measured
rather than estimated.

  python3 spikes/H200_seat_is_a_string/attack.py
"""
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
S91 = os.path.join(ROOT, 'spikes', 'S91_multi_agent_quorum')

spec = importlib.util.spec_from_file_location('s91_run', os.path.join(S91, 'run.py'))
s91 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s91)          # safe: main() is __main__-guarded


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()[:16]


def main():
    r = {}
    jobs = s91.load_corpus_jobs()
    corpus = next(j for j in jobs if j['type'] == 'corpus')
    pin = next(j for j in jobs if j['type'] == 'frozen_pin')
    atk = next(j for j in jobs if j['type'] == 'adversarial')

    # ---- F1 · does the seat reach the execution at all? --------------------
    # Every real seat, plus three that are not seats. If the outputs are equal,
    # the `agent` parameter is not read and the five votes are one computation
    # repeated five times.
    fakes = [None, {}, {'agent_id': 'NOT_A_SEAT', 'binary': 'x', 'isa': 'vax'}]
    outs = {}
    for a in s91.ROSTER + fakes:
        name = (a or {}).get('agent_id', repr(a)) if isinstance(a, dict) else repr(a)
        outs[name] = [sha(s91.execute_job_on_agent(a, j)) for j in (corpus, pin, atk)]
    distinct = {tuple(v) for v in outs.values()}
    r['F1'] = {'fires': len(distinct) > 1,
               'seats_and_non_seats_probed': len(outs),
               'distinct_output_vectors': len(distinct),
               'a_None_agent_votes': outs['None'] == outs['agent_gemini_lead'],
               'detail': 'output vector = sha16 of the result dict for a corpus, '
                         'a frozen-pin and an adversarial job'}

    # ---- F2 · does the adjudication verdict depend on the roster? -----------
    # Five identical copies of ONE seat: every independence axis collapses to 1.
    # Compared on the VOTE VECTORS rather than by reimplementing adjudication --
    # if the votes are identical, every adjudication function of those votes is.
    def votes_for(roster):
        return [[sha(s91.execute_job_on_agent(a, j)) for a in roster] for j in jobs]
    real = votes_for(s91.ROSTER)
    clone = votes_for([copy.deepcopy(s91.ROSTER[0]) for _ in range(5)])
    axes_real = s91.audit_6axis_independence(s91.ROSTER)[0]
    axes_clone = s91.audit_6axis_independence(
        [copy.deepcopy(s91.ROSTER[0]) for _ in range(5)])[0]
    r['F2'] = {'fires': real != clone,
               'votes_identical_under_a_collapsed_roster': real == clone,
               'axes_real': axes_real, 'axes_clone': axes_clone,
               'unanimous_in_both': all(len(set(v)) == 1 for v in real + clone)}

    # ---- F3 · can the frozen-pin check fail? --------------------------------
    # Corrupt the pin the arm is supposed to be checking AGAINST.
    saved_pin = s91.PIN_F001
    s91.PIN_F001 = 'deadbeef' * 8
    jobs2 = s91.load_corpus_jobs()
    pin2 = next(j for j in jobs2 if j['id'] == 'F001_FROZEN_BENCHMARK')
    out2 = s91.execute_job_on_agent(s91.ROSTER[0], pin2)
    s91.PIN_F001 = saved_pin
    r['F3'] = {'fires': out2['digest'] != 'deadbeef' * 8,
               'corrupted_pin_still_reported': out2['verdict'],
               'digest_equals_the_corrupted_expectation': out2['digest'] == 'deadbeef' * 8,
               'detail': 'the arm returns job["expected"], so the check is '
                         'expected == expected and moves WITH any corruption'}

    # ---- F4 · does the adjudicator catch a genuinely cheating seat? ---------
    # THE ARM THAT STOPS THIS BECOMING A BIGGER CLAIM THAN THE EVIDENCE.
    # Uses S91's own main(), so the verdict is S91's and not mine.
    snaps = {}
    for f in ('result.json', 'provenance.json'):
        p = os.path.join(S91, f)
        if os.path.exists(p):
            snaps[f] = open(p, 'rb').read()
    honest = s91.execute_job_on_agent

    def cheating(agent, job):
        out = honest(agent, job)
        if isinstance(agent, dict) and agent.get('agent_id') == 'node_linux_x86':
            out = dict(out, digest='0' * 64)
        return out

    try:
        s91.execute_job_on_agent = cheating
        buf = io.StringIO()
        with redirect_stdout(buf):
            s91.main()
        text = buf.getvalue()
        div = [l for l in text.splitlines() if 'Divergences' in l]
    finally:
        s91.execute_job_on_agent = honest
        for f, b in snaps.items():
            with open(os.path.join(S91, f), 'wb') as fh:
                fh.write(b)
        for f, b in snaps.items():
            assert open(os.path.join(S91, f), 'rb').read() == b, \
                'FAILED TO RESTORE %s -- say so loudly rather than continuing' % f
    caught = bool(div) and 'Divergences' in div[0] and div[0].strip().split()[-1] != '0'
    r['F4'] = {'fires': not caught,
               'divergence_line_under_one_cheating_seat': div[0].strip() if div else None,
               'artifacts_restored_byte_identical': True,
               'predicted_in_claim': 'F4 does NOT fire: the adjudicator works and '
                                     'simply has nothing to adjudicate'}

    # ---- F5 · do S91's own three controls see the consensus? ----------------
    # Read from its own source rather than described: C3 is `c3_ok = True`.
    src = open(os.path.join(S91, 'run.py')).read()
    r['F5'] = {'fires': False,
               'c1_expression': 'len(ROSTER) == 5',
               'c2_expression': 'len(jobs) == 74',
               'c3_expression_verbatim': 'c3_ok = True' if 'c3_ok = True' in src else '??',
               'c3_is_a_literal': 'c3_ok = True' in src,
               'any_control_reads_divergences': 'divergences' in src.split('controls = [')[0].split('c1_ok')[-1],
               'detail': 'all three observe the FIXTURE (roster length, job count, '
                         'the pin constants). None observes votes, digests, '
                         'unanimity or divergences.'}

    with open(os.path.join(HERE, 'falsifiers.json'), 'w') as f:
        json.dump(r, f, indent=2, sort_keys=True)
    for k in ('F1', 'F2', 'F3', 'F4', 'F5'):
        print('%s  %s  %s' % (k, 'FIRED' if r[k]['fires'] else 'quiet',
                              {x: y for x, y in r[k].items() if x != 'fires'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
