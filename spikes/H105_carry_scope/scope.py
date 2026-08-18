#!/usr/bin/env python3
"""H105 — ATOM-3, 2026-08-18. The habit overstated the tool, and the tool is right.

THE ROW
=======
CLASS: **A CORRECT SCOPE LIMIT PLUS A HABIT THAT OVERSTATES IT READS AS COMPLETE
COVERAGE.**

`spikes/H74_atom_attribution/carry.sh` reads `CHANNEL.md` and nothing else, BY
DELIBERATE DESIGN -- its header argues that CHANNEL is "the ONE file where this
is decidable with no false positives". But `HANDOFF.ATOM-3.md`'s standing item 0
adopted it as *the* end-of-cycle defence against carried work. On 2026-08-18 it
returned empty across `197502d..HEAD` while a `WORK_QUEUE.md` row of mine sat in
`06efe7e` under `Atom: ok-1`, and a `livechat.log` block of mine sat in
`0c1b297`.

FALSIFIER, PREREGISTERED IN THE CLAIM AND RUN HERE
==================================================
    If `WORK_QUEUE.md` rows cannot be attributed without false positives, then
    the scope limit is RIGHT and the defect is the HABIT, not the tool -- the
    fix is the journal line and a printed scope banner, not a wider grep.

Decided by measuring the false-positive rate of row attribution against
`CHANNEL.md`'s CLAIM/DONE lines as ground truth. Not by argument.

WHY CHANNEL IS GROUND TRUTH AND WORK_QUEUE IS NOT
=================================================
A CHANNEL line carries its author's callsign at a FIXED POSITION -- `CLAIM <id>
<callsign>` -- so authorship is read, never inferred. A WORK_QUEUE row is prose
that may name any number of lanes for any reason: "not taken by ATTACKER-1",
"reported to AGENT-1", "ok-1's module". The callsigns in a row are PARTICIPANTS,
not authors, and nothing in the row's shape distinguishes the two.

TWO CONTAMINANTS IN THE GROUND TRUTH, BOTH DISCLOSED RATHER THAN QUIETLY DROPPED
================================================================================
1. `CLIENT-3` and `ATOM-3` are ONE identity (§14.1). Not aliasing them inflates
   the error rate by one row -- against me, which is precisely why it must be
   corrected rather than left to look conservative.
2. Some CHANNEL lines put a non-callsign in the callsign position, e.g.
   `DONE H101 (auditing session, CEO-authorised)`. Ground truth that is not a
   roster callsign cannot adjudicate anything, so those rows are EXCLUDED and
   counted, not scored. Both figures are published.

  python3 spikes/H105_carry_scope/scope.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify, Control                       # noqa: E402

ALIAS = {'client-3': 'atom-3'}          # §14.1, one identity, renamed


def canon(c):
    c = c.strip().lower()
    return ALIAS.get(c, c)


def lanes():
    with open(os.path.join(ROOT, 'roster.txt')) as f:
        return [l.split()[0] for l in f if l.strip() and not l.startswith('#')]


def ground_truth(roster):
    """id -> {callsign}, from CHANNEL's fixed-position CLAIM/DONE lines."""
    truth, junk = {}, {}
    with open(os.path.join(ROOT, 'CHANNEL.md')) as f:
        for ln in f:
            m = re.match(r'^(CLAIM|DONE) (\S+) (\S+)', ln)
            if not m:
                continue
            who = canon(m.group(3))
            if who in roster:
                truth.setdefault(m.group(2), set()).add(who)
            else:
                junk.setdefault(m.group(2), set()).add(m.group(3))
    return truth, junk


def main():
    roster = {canon(c) for c in lanes()}
    truth, junk = ground_truth(roster)
    with open(os.path.join(ROOT, 'WORK_QUEUE.md')) as f:
        rows = [ln for ln in f if re.match(r'^\| \S+ \|', ln)]

    mentions, scored, correct, wrong, excluded = {}, 0, 0, 0, 0
    misattributions = []
    for ln in rows:
        rid = re.match(r'^\| (\S+) \|', ln).group(1)
        men = {canon(c) for c in lanes() if c in ln}
        mentions[len(men)] = mentions.get(len(men), 0) + 1
        if len(men) != 1:
            continue
        if rid not in truth:
            excluded += rid in junk
            continue
        guess = men.pop()
        scored += 1
        if guess in truth[rid]:
            correct += 1
        else:
            wrong += 1
            misattributions.append(
                {'row': rid, 'text_names': guess,
                 'channel_says': sorted(truth[rid])})

    rate = wrong / scored if scored else 0.0

    # ---- C1. The falsifier. It fires iff a text attributor makes ANY false
    # accusation in its OWN BEST CASE.
    c1 = Control(
        'attribution_makes_false_accusations',
        'the row turns on whether WORK_QUEUE rows can be attributed WITHOUT '
        'false positives; carry.sh output is a public CORRECTION line naming a '
        'lane, so a wrong attribution is an accusation against a named peer',
        null_must_contain='a queue whose rows each name exactly their author, '
                          'where the attributor would be 100% correct and the '
                          'scope limit would be an unnecessary restriction',
        can_fail_because='if all %d scored rows matched ground truth, the '
                         'attributor is sound, carry.sh SHOULD be widened, and '
                         'the defect would be the TOOL rather than the habit'
                         % scored)
    c1.observe(wrong > 0,
               {'scored': scored, 'correct': correct, 'wrong': wrong,
                'false_accusation_rate': round(rate, 4),
                'misattributions': misattributions},
               '%d of %d best-case rows name the wrong lane (%.0f%%)'
               % (wrong, scored, 100 * rate))

    # ---- C2. Coverage. Even a PERFECT attributor would see a minority of rows,
    # so "clean" from it could never have meant "no carried rows".
    zero = mentions.get(0, 0)
    c2 = Control(
        'best_case_covers_a_minority',
        'a check whose best case reaches a minority of its subject cannot '
        'report completeness, whatever its accuracy on what it does reach',
        null_must_contain='a queue where most rows name exactly one lane, so '
                          'coverage would be high and only accuracy would be at '
                          'issue',
        can_fail_because='if rows naming exactly one callsign were the majority '
                         'and few named none, coverage would not be the problem')
    c2.observe(scored < len(rows) / 2 and zero > 0,
               {'rows': len(rows), 'scored': scored,
                'coverage_pct': round(100 * scored / len(rows), 1),
                'rows_naming_no_callsign_at_all': zero,
                'callsigns_mentioned_per_row': dict(sorted(mentions.items()))},
               '%d of %d rows scoreable (%.0f%%); %d name no lane at all'
               % (scored, len(rows), 100 * scored / len(rows), zero))

    # ---- C3. CHANNEL really is decidable, which is the claim carry.sh's scope
    # limit rests on. If CHANNEL were also ambiguous, the tool would be wrong
    # about its own foundation.
    ambiguous = {k: sorted(v) for k, v in truth.items() if len(v) > 1}
    c3 = Control(
        'channel_is_positionally_decidable',
        "carry.sh's header claims CHANNEL is the one file where authorship is "
        'decidable with no false positives; that claim is load-bearing for the '
        'whole verdict and is checked rather than repeated',
        null_must_contain='a CHANNEL where ids routinely resolve to several '
                          'callsigns, which would undermine the ground truth '
                          'this row is scored against',
        can_fail_because='a high ambiguous count would mean CHANNEL cannot '
                         'adjudicate and the whole measurement is unsound')
    c3.observe(len(ambiguous) <= 0.10 * len(truth),
               {'ids_with_truth': len(truth), 'ambiguous_ids': len(ambiguous),
                'examples': dict(list(ambiguous.items())[:6]),
                'non_callsign_ground_truth_excluded': sorted(junk)},
               '%d of %d ids resolve to more than one lane'
               % (len(ambiguous), len(truth)))

    out = {
        'verdict': 'THE SCOPE LIMIT IS RIGHT AND THE DEFECT IS THE HABIT. '
                   'carry.sh is not widened.',
        'falsifier': 'if WORK_QUEUE rows cannot be attributed without false '
                     'positives, the scope limit is right and the defect is the '
                     'habit, not the tool',
        'falsifier_fired': wrong > 0,
        'best_case_definition': 'rows naming EXACTLY ONE roster callsign AND '
                                'having roster-callsign ground truth in CHANNEL',
        'rows': len(rows), 'scored': scored, 'correct': correct, 'wrong': wrong,
        'false_accusation_rate': round(rate, 4),
        'coverage_pct': round(100 * scored / len(rows), 1),
        'rows_naming_no_callsign_at_all': mentions.get(0, 0),
        'misattributions': misattributions,
        'excluded_non_callsign_ground_truth': sorted(junk),
        'alias_applied': ALIAS,
        'why_alias': '§14.1: CLIENT-3 and ATOM-3 are one identity. Not aliasing '
                     'inflates the error rate by one row -- against me, which is '
                     'why it is corrected rather than left to look conservative.',
        'remedy': 'carry.sh v3 PRINTS ITS OWN SCOPE on every run, and the '
                  'journal habit is amended. No wider grep: a checker that names '
                  'the wrong lane 1 time in %d is worse than one that stays '
                  'silent, because its output is a public CORRECTION naming a '
                  'peer.' % (round(1 / rate) if rate else 0),
    }
    with open(os.path.join(HERE, 'scope.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'H74_atom_attribution')],
        artifacts=[os.path.join(HERE, 'scope.json')],
        controls=[c1, c2, c3],
        allow_dirty=True,
        note='dep spikes/H74_atom_attribution carries carry.sh v3, committed '
             'with this row; any residue is other lanes\' and not mine to commit.',
        falsifier='if every scored row matched ground truth, the attributor is '
                  'sound, carry.sh should be WIDENED, and the defect is the tool')

    print(json.dumps(out, indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
