#!/usr/bin/env python3
"""H238 — certify the repair. ATTACKER-1, 2026-08-19.

Certifies from the `OBS` lines that `probe2.sh` PRINTS, never from a restatement
of them, and refuses if an arm produced no `OBS` at all (H230's idiom).

THREE INSTRUMENTS, AND EACH ANSWERS A QUESTION THE OTHERS CANNOT:
  probe2.sh    the SAME arms as probe.sh v1, run against v2 (from `git show
               HEAD:`) and v3 (working tree) side by side -- the before/after.
  mutants.sh   7 mutants, each deleting one part of the repair; `--selfcheck`
               must refuse every one. A green suite that has never been shown
               to go red is evidence of nothing.
  --selfcheck  the shipped check itself, which is what a future lane runs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'spikes' / 'harness'))

import kfcheck                                      # noqa: E402
from provenance import Control, Falsifier          # noqa: E402


def run(*cmd):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


rc_probe, out = run('sh', str(HERE / 'probe2.sh'))
print(out)
obs = {m.group(1): json.loads(m.group(2))
       for m in re.finditer(r'^OBS (\S+) (\{.*\})$', out, re.M)}

rc_mut, mut = run('sh', str(HERE / 'mutants.sh'))
print(mut)
m = re.search(r'mutants: (\d+) refused, (\d+) not refused', mut)
mut_refused, mut_missed = (int(m.group(1)), int(m.group(2))) if m else (0, -1)
# A mutant that never applied is scored as NOT refused by mutants.sh itself
# (H217: verify the intended edit APPLIED, never merely that the copy differs).
mut_anchor_miss = mut.count('ANCHOR-MISS')

rc_self, selfout = run('sh', str(ROOT / 'spikes/harness/stranded.sh'), '--selfcheck')
print(selfout)

need = ['C0', 'C1', 'A1_owner_live', 'A2_owner_retired', 'A3_beat_stale',
        'A4_no_fleet_apparatus', 'A5_control_stranded', 'F2', 'F3']
missing = [k for k in need if k not in obs]
if missing or rc_probe != 0:
    print(f'REFUSED — probe2 rc={rc_probe}, missing OBS for {missing}')
    sys.exit(1)

controls = [
    Control('C1_baseline_really_is_v2',
            why='the baseline is resolved by walking this file s history for the '
                'newest blob whose OWN HEADER says v2, and both versions are '
                'read back from their headers. The first draft compared sha256s '
                'only: once the repair LANDED, `git show HEAD:` returned v3, the '
                '"before" column became v3 and A2 printed a verdict v2 cannot '
                'produce -- a NECESSARY condition read as a SUFFICIENT one',
            can_fail_because='no commit carries a v2 header, or the candidate '
                             'still does; probe2 exits 2 and publishes no delta',
            null_must_contain='not v2'),
    Control('C2_live_branch_is_reachable',
            why="a real running process renamed via `exec -a` so `ps -o "
                "command=` reads a run_loop.sh -- without it v3's LIVE branch "
                'is unreachable in the fixture and every other arm proves '
                'nothing (A15 inside the fix for A15)',
            can_fail_because='`exec -a` is unavailable or the spin-wait times '
                             'out, in which case probe2 exits 2',
            null_must_contain='not reachable'),
    Control('C3_stranded_and_noowner_still_reachable',
            why='the repair added a verdict; the other three must still fire, '
                'or the vocabulary lost a branch while gaining one',
            can_fail_because='v3 collapsed a branch into UNATTENDED',
            null_must_contain='branch lost'),
    Control('C4_suite_can_go_red',
            why='8 mutants each delete one part of the repair and --selfcheck '
                'must refuse each; a check nobody has seen fail is not a check. '
                'M8 (v3.1/H243) is the source line for the shared predicate: '
                'drop it and LIVE becomes unreachable',
            can_fail_because='a mutant stays green, naming an inert assertion',
            null_must_contain='stayed green'),
]
controls[0].observe(obs['C1']['baseline_version'] == 'v2'
                    and obs['C1']['candidate_version'] != 'v2'
                    and obs['C1']['v2_sha256'] != obs['C1']['v3_sha256'], obs['C1'])
controls[1].observe(obs['A1_owner_live']['v3'] == 'IN-FLIGHT', obs['A1_owner_live'])
controls[2].observe(obs['A5_control_stranded']['v3'] == 'STRANDED'
                    and obs['F3']['noowner_under_v3'] == 'NO-OWNER',
                    {**obs['A5_control_stranded'], **obs['F3']})
controls[3].observe(mut_missed == 0 and mut_anchor_miss == 0 and mut_refused == 8,
                    {'refused': mut_refused, 'not_refused': mut_missed,
                     'anchor_miss': mut_anchor_miss, 'rc': rc_mut})

falsifiers = [
    Falsifier('F1_verdict_now_varies_with_liveness',
              refutes='that v3 is as blind as v2',
              fires_when='one arm, identical in every input but owner '
                         'liveness, changes verdict IN-FLIGHT -> UNATTENDED',
              null_must_contain='verdict unchanged'),
    Falsifier('F2_in_flight_no_longer_absorbing',
              refutes="that IN-FLIGHT is still a dead lane's permanent answer",
              fires_when='v2 reads IN-FLIGHT at 1m/1h/1d/30d and v3 reads none '
                         'of them IN-FLIGHT',
              null_must_contain='still absorbing'),
    Falsifier('F3_stale_beat_still_defers',
              refutes='that the repair calls a rate-limited live lane dead -- '
                      'the direction that would tell a lane to touch live work',
              fires_when='the stale-beat arm stays IN-FLIGHT under v3',
              null_must_contain='escalated'),
    Falsifier('F4_disarms_without_apparatus',
              refutes='that UNATTENDED fires where no lane produces liveness '
                      'artifacts at all (a fresh clone, a non-fleet machine)',
              fires_when='the no-third-party arm stays IN-FLIGHT under v3',
              null_must_contain='fired anyway'),
]
falsifiers[0].observe(obs['A2_owner_retired']['v2'] == 'IN-FLIGHT'
                      and obs['A2_owner_retired']['v3'] == 'UNATTENDED',
                      obs['A2_owner_retired'])
falsifiers[1].observe(obs['F2']['v2_absorbing'] and not obs['F2']['v3_absorbing'],
                      obs['F2'])
falsifiers[2].observe(obs['A3_beat_stale']['v3'] == 'IN-FLIGHT', obs['A3_beat_stale'])
falsifiers[3].observe(obs['A4_no_fleet_apparatus']['v3'] == 'IN-FLIGHT',
                      obs['A4_no_fleet_apparatus'])

(HERE / 'result.json').write_text(json.dumps({
    'spike': 'H238',
    'target': 'spikes/harness/stranded.sh (v2 -> v3)',
    'observations': obs,
    'mutants': {'refused': mut_refused, 'not_refused': mut_missed,
                'anchor_miss': mut_anchor_miss},
    'selfcheck_rc': rc_self,
    'falsifiers_fired': {f.name: bool(f.fired) for f in falsifiers},
}, indent=2) + '\n')

ok, problems = kfcheck.certify(
    str(HERE),
    # DIRECTORY, not a file: `repo_state` refuses a file path outright, and its
    # own message says naming one *silently produced a fake dirty verdict* in an
    # earlier generation. allow_dirty because the module under repair is the
    # uncommitted change this spike exists to certify -- acknowledged, not hidden.
    deps=[str(ROOT / 'spikes' / 'harness')],
    artifacts=[str(HERE / 'result.json')],
    controls=controls, falsifiers=falsifiers,
    allow_dirty=True,
    note='H238: stranded.sh v2 decided whether a file had a LIVE EDITOR without '
         'reading any liveness input, and IN-FLIGHT -- the verdict that tells '
         'the fleet to stand off -- was the absorbing state for a dead lane. '
         'v3 reads .loop_lock/.heartbeat and adds UNATTENDED. THE REPAIR IS '
         'SILENT ON TODAY\'S TREE (UNATTENDED 0, every rostered lane beating), '
         'which is exactly why the defect survived unmeasured.',
    falsifier='the retired-owner arm staying IN-FLIGHT under v3, or the '
              'stale-beat arm escalating, or a mutant of the repair passing '
              '--selfcheck')
print(f'certify ok={ok}')
for x in problems:
    print('   ', x)
sys.exit(0 if ok else 1)
