#!/usr/bin/env python3
"""H230 — certify the probe. ATTACKER-1, 2026-08-19.

Runs `probe.sh` and certifies from ITS printed `OBS` lines, never from a
re-statement of them. A control that printed a verdict and emitted no `OBS`
makes this EXIT rather than certify: an arm that certifies observations it
never made is the failure `provenance.py` exists for.
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

import kfcheck                                       # noqa: E402
from provenance import Control, Falsifier           # noqa: E402

p = subprocess.run(['sh', str(HERE / 'probe.sh')], cwd=ROOT,
                   capture_output=True, text=True)
out = p.stdout + p.stderr
print(out)

obs = {}
for m in re.finditer(r'^OBS (\S+) (\{.*\})$', out, re.M):
    obs[m.group(1)] = json.loads(m.group(2))

need = ['F1', 'F2', 'F2b', 'F3', 'C0', 'C1']
missing = [k for k in need if k not in obs]
if missing or p.returncode != 0:
    print(f'REFUSED — probe rc={p.returncode}, missing OBS for {missing}')
    sys.exit(1)

controls = [
    Control('C0_gate_discriminates',
            why='same repo, same file: a small staged append is green and a '
                '>1 MiB one is red, so the size gate has two reachable states',
            can_fail_because='the gate is always red or always green',
            null_must_contain='one reachable state'),
    Control('C1_only_ignores_the_index',
            why='`git commit --only` landed a line that was never staged, so '
                'the premise that the commit path skips the index is observed '
                'and not read off a man page',
            can_fail_because='--only takes the index after all',
            null_must_contain='premise wrong'),
]
controls[0].observe(obs['C0']['rc_small_staged'] == 0
                    and obs['C0']['rc_big_staged'] != 0, obs['C0'])
controls[1].observe(obs['C1']['worktree_only_line_in_commit'] == 1, obs['C1'])

falsifiers = [
    Falsifier('F1_staged_oversize_refused',
              refutes="that H229's direction is imaginary",
              fires_when='a staged >1 MiB file is refused',
              null_must_contain='not refused'),
    Falsifier('F2_unstaged_oversize_lands',
              refutes='that the size gate covers the path that commits',
              fires_when='the gate is green and `--only` lands >1 MiB anyway',
              null_must_contain='gate saw it'),
    Falsifier('F3_foreign_add_flips_my_verdict',
              refutes='that my verdict depends only on my own work',
              fires_when="another party's `git add` flips rc 0 -> 1",
              null_must_contain='verdict unchanged'),
]
falsifiers[0].observe(obs['F1']['rc'] != 0 and obs['F1']['actionable'], obs['F1'])
falsifiers[1].observe(obs['F2']['rc'] == 0 and obs['F2b']['over_1MiB'],
                      {**obs['F2'], **obs['F2b']})
falsifiers[2].observe(obs['F3']['rc_before_foreign_add'] == 0
                      and obs['F3']['rc_after_foreign_add'] != 0, obs['F3'])

(HERE / 'result.json').write_text(json.dumps({
    'spike': 'H230',
    'target': 'spikes/harness/githygiene.py + spikes/harness/commit_scoped.sh',
    'observations': obs,
    'falsifiers_fired': {f.name: bool(f.fired) for f in falsifiers},
}, indent=2) + '\n')

ok, problems = kfcheck.certify(
    str(HERE),
    artifacts=[str(HERE / 'result.json')],
    controls=controls, falsifiers=falsifiers,
    no_deps_reason='every arm builds its own scratch repo from a copy of '
                   'githygiene.py; nothing outside this spike is read at run time',
    note='H230: the size gate reads the INDEX while commit_scoped.sh commits '
         'the WORKING TREE with --only',
    falsifier='a staged >1 MiB file passing, or an unstaged one being refused, '
              'or `--only` declining to commit a line that was never staged')
print(f'certify ok={ok}')
for x in problems:
    print('   ', x)
sys.exit(0 if ok else 1)
