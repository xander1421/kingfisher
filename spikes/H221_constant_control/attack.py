#!/usr/bin/env python3
"""H221 — ATTACK on H161's controls. ATTACKER-1, 2026-08-19.

CLASS: A CONTROL WHOSE VERDICT IS A CONSTANT ONE ASSIGNMENT AWAY FROM THE CALL
SITE. `constcheck.py` v2 (ATOM-3, H201) flags `c.observe(True, …)` — a literal
written where the verdict goes. Move the same literal one line up into a
variable and the call site holds a Name, so v2 is quiet, and that is the shape
every real spike in this tree uses.

TARGET: `spikes/H161_heterogeneous_device_consensus/run.py`, the run behind the
headline scoreboard claim *"100% bit parity across 5 heterogeneous live
execution endpoints"*. It has no `WORK_QUEUE.md` row.

FALSIFIERS — F1..F5 PREREGISTERED IN `CHANNEL.md` BEFORE THIS FILE EXISTED, with
the prediction recorded for each. F6 was added when this file was written, AFTER
the CLAIM, and is labelled as such rather than backdated.

  F1  C3_pins_intact can fail through its stated cause ("pin drift"). If
      corrupting `fixtures/F001/F001.accepted_digest` — what "pins intact" must
      mean — moves the verdict, F1 FIRES and the C3 finding is WITHDRAWN.
      predicted: does not fire.
  F2  C1_device_health refuses an absent device. If a stubbed `adb` returning
      the real `device not found` makes C1 False, F2 FIRES and the C1 finding
      is WITHDRAWN.  predicted: does not fire.
  F3  this is a duplicate of H201. If `constcheck.py` names H161 anywhere, F3
      FIRES and this row closes as ALREADY DONE.  predicted: does not fire.
  F4  the blast radius is one spike. If the fold finds a folded-constant
      verdict ONLY in H161, this is one bug and not a class.
      predicted: FIRES.
  F5  the parity NUMBER is bad. If the two committed local binaries do not
      reproduce the pinned digests, this stops being a controls attack and
      becomes a retraction of the digests.  predicted: does not fire, and the
      attack kills the CONTROLS, not the NUMBER.
  F6  (added after the CLAIM) `kitchen/test_h161.py`, the only standing check
      on the claim, can see a fabricated digest. If it fails on a result.json
      whose digests are `0`*64 with `match: true`, F6 FIRES and the tautology
      finding is WITHDRAWN.  predicted: does not fire.

Every arm prints `OBS <arm> <json>` with the values it compared, so a control
cannot be certified against an observation it never made.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'spikes' / 'harness'))
sys.path.insert(0, str(HERE))

from fold import scan_source                                    # noqa: E402
from provenance import Control, Falsifier                       # noqa: E402
import kfcheck                                                  # noqa: E402

H161 = ROOT / 'spikes' / 'H161_heterogeneous_device_consensus'
RUN_PY = H161 / 'run.py'
SCRATCH = ROOT / '.scratch' / 'h221'
PIN_F001 = '590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f'
PIN_F002 = 'c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9'

OBS = {}


def obs(arm, **kw):
    OBS.setdefault(arm, []).append(kw)
    print(f'OBS {arm} {json.dumps(kw, sort_keys=True)}')


def fresh(name):
    d = SCRATCH / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def c3_verdict(src):
    """The folded value of the FIRST folded verdict in a copy of run.py."""
    hits = [h for h in scan_source(src, 'run.py') if h['shape'] == 'folded']
    return hits[0]['verdict'] if hits else None


# ── A1 / F1 ─ C3_pins_intact compares each pin to a hand-typed twin ───────────
def arm_c3():
    src = RUN_PY.read_text()
    base = c3_verdict(src)

    # THE INTERVENTION, AND ITS SIZE IS PRINTED. An isolated copy of the whole
    # spike + the whole fixture tree, with the external referent the control's
    # `why` describes -- `F001.accepted_digest`, which really does carry the
    # pinned value -- replaced by garbage.
    iso = fresh('iso_f1')
    shutil.copy(RUN_PY, iso / 'run.py')
    shutil.copytree(ROOT / 'fixtures' / 'F001', iso / 'F001')
    dig = iso / 'F001' / 'F001.accepted_digest'
    before = dig.read_text().strip()
    dig.write_text('0' * 64 + '\n')
    after_corrupt = c3_verdict((iso / 'run.py').read_text())

    # POSITIVE CONTROL: the ONLY thing that moves this verdict is editing one of
    # the two twins. If this does not flip, the folder is a stub.
    mutated = src.replace(f'PIN_F001 = "{PIN_F001}"', 'PIN_F001 = "drifted"', 1)
    assert mutated != src, 'anchor absent: PIN_F001 definition not found'
    after_pin_edit = c3_verdict(mutated)

    obs('A1_c3',
        verdict_as_shipped=base,
        referent_on_disk=before,
        referent_equals_pin=(before == PIN_F001),
        verdict_after_referent_corrupted=after_corrupt,
        verdict_after_pin_definition_edited=after_pin_edit,
        intervention='whole fixture referent replaced with 0*64')
    return {
        'constant': base is True,
        'f1_fired': after_corrupt is not True,
        'control_live': after_pin_edit is False,
    }


# ── A2 / F2 ─ C1_device_health passes when the device is gone ────────────────
ADB_ABSENT = """#!/bin/sh
echo "error: device '$2' not found" >&2
exit 1
"""
ADB_HOT = """#!/bin/sh
cat <<'EOT'
Current Battery Service state:
  level: 100
  status: 5
  temperature: 450
EOT
exit 0
"""


def _battery_under(stub_src, tag):
    """Run H161's OWN get_phone_battery() and its OWN C1 expression, with `adb`
    replaced on PATH. The code under test is imported, never re-typed."""
    import importlib.util
    binx = fresh('bin_' + tag)
    adb = binx / 'adb'
    adb.write_text(stub_src)
    adb.chmod(0o755)
    old = os.environ['PATH']
    os.environ['PATH'] = f'{binx}:{old}'
    try:
        spec = importlib.util.spec_from_file_location(f'h161run_{tag}', RUN_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        battery = mod.get_phone_battery()
    finally:
        os.environ['PATH'] = old
    # run.py:206-208, copied verbatim, and that is the point
    temp_after = battery.get('temperature_c', 0.0) or 0.0
    return battery, temp_after, (temp_after <= 38.0)


def arm_c1():
    gone, t_gone, c1_gone = _battery_under(ADB_ABSENT, 'absent')
    hot, t_hot, c1_hot = _battery_under(ADB_HOT, 'hot')
    obs('A2_c1',
        battery_when_device_absent=gone,
        temp_used_when_absent=t_gone,
        c1_passes_when_absent=c1_gone,
        battery_when_45C=hot,
        temp_used_when_hot=t_hot,
        c1_passes_when_hot=c1_hot,
        mechanism='`.get(...,0.0)` never fires; `or 0.0` converts None to 0.0')
    return {'passes_absent': c1_gone, 'f2_fired': not c1_gone,
            'control_live': c1_hot is False}


# ── A3 / F4 ─ how many spikes carry a folded-constant verdict ────────────────
SKIP_TREES = ('spikes/H210_refutation_outlives_target/fresh',)


def arm_sweep():
    files, skipped, unparseable = 0, 0, 0
    folded, literal = [], []
    for p in sorted((ROOT / 'spikes').rglob('*.py')):
        rel = str(p.relative_to(ROOT))
        if any(rel.startswith(s) for s in SKIP_TREES):
            skipped += 1
            continue
        files += 1
        try:
            hits = scan_source(p.read_text(encoding='utf-8'), rel)
        except (SyntaxError, UnicodeDecodeError):
            unparseable += 1
            continue
        lines = p.read_text(encoding='utf-8').splitlines()
        for h in hits:
            # The BINDING line, not just the call site -- a reader must be able
            # to check every accusation by eye without opening 21 files.
            h['binding'] = ''
            if h['name']:
                for i, l in enumerate(lines, 1):
                    t = l.strip()
                    if t.startswith(h['name'] + ' =') or t.startswith(h['name'] + '='):
                        h['binding'] = f'{i}: {t[:120]}'
                        break
            (literal if h['shape'] == 'literal' else folded).append(h)
    live = [h for h in folded if not h['fixture']]
    obs('A3_sweep', files=files, skipped_trees=list(SKIP_TREES),
        skipped_files=skipped, unparseable=unparseable,
        folded_total=len(folded), folded_live=len(live),
        literal_total=len(literal),
        sites=[{'site': f'{h["path"]}:{h["line"]}', 'verdict': repr(h['verdict']),
                'binding': h['binding']} for h in live])
    return {'live': live, 'literal': len(literal), 'files': files,
            'f4_fired': len({h['path'] for h in live}) <= 1}


# ── A4 / F3 ─ is this already H201's? ────────────────────────────────────────
def arm_constcheck():
    p = subprocess.run([sys.executable, 'spikes/harness/constcheck.py'],
                       cwd=ROOT, capture_output=True, text=True)
    out = p.stdout + p.stderr
    names_h161 = 'H161' in out
    obs('A4_constcheck', rc=p.returncode, names_h161=names_h161,
        live_literal_verdicts=int((re.search(r'(\d+) LIVE literal verdict', out)
                                   or re.match(r'(0)', '0')).group(1)))
    return {'f3_fired': names_h161}


# ── A5 / F5 ─ does the NUMBER reproduce on the two endpoints I can run? ──────
DIG_RE = re.compile(r'Consensus Digest:\s+([0-9a-fA-F]{64})')


def _verify(binary, fixture):
    p = subprocess.run([str(binary), str(fixture)], cwd=ROOT,
                       capture_output=True, text=True)
    m = DIG_RE.search(p.stdout + p.stderr)
    return p.returncode, (m.group(1).lower() if m else '')


def arm_reproduce():
    out = {}
    for tag, binary in (('macos_host_arm64', H161 / 'trace_verifier_host'),
                        ('macos_rosetta_x86', H161 / 'trace_verifier_x86')):
        rc1, d1 = _verify(binary, ROOT / 'fixtures' / 'F001')
        rc2, d2 = _verify(binary, ROOT / 'fixtures' / 'F002_specv1')
        out[tag] = {'f001_rc': rc1, 'f001_digest': d1, 'f002_rc': rc2,
                    'f002_digest': d2,
                    'match': d1 == PIN_F001 and d2 == PIN_F002}

    # CONTROL: the verifier must actually READ its input. A digest that does not
    # move under a corrupted corpus is a disconnected wire, not a measurement.
    iso = fresh('iso_f5')
    shutil.copytree(ROOT / 'fixtures' / 'F001', iso / 'F001')
    corpus = iso / 'F001' / 'F001.corpus.bin'
    raw = bytearray(corpus.read_bytes())
    flipped = len(raw) // 2
    raw[flipped] ^= 0xFF
    corpus.write_bytes(bytes(raw))
    rc_c, d_c = _verify(H161 / 'trace_verifier_host', iso / 'F001')

    obs('A5_reproduce', endpoints=out, pins={'F001': PIN_F001, 'F002': PIN_F002},
        control_corrupt_byte=flipped, control_rc=rc_c, control_digest=d_c,
        control_moved=(d_c != PIN_F001))
    return {'both_match': all(v['match'] for v in out.values()),
            'f5_fired': not all(v['match'] for v in out.values()),
            'control_live': d_c != PIN_F001, 'endpoints': out}


# ── A6 / F6 ─ the only standing check re-reads the claim's own output ────────
def arm_kitchen():
    src_test = ROOT / 'kitchen' / 'test_h161.py'
    live = json.loads((H161 / 'result.json').read_text())

    def run_iso(tag, mutate):
        iso = fresh('iso_kitchen_' + tag)
        (iso / 'kitchen').mkdir()
        (iso / 'spikes' / H161.name).mkdir(parents=True)
        shutil.copy(src_test, iso / 'kitchen' / 'test_h161.py')
        d = json.loads(json.dumps(live))
        mutate(d)
        (iso / 'spikes' / H161.name / 'result.json').write_text(
            json.dumps(d, indent=2) + '\n')
        p = subprocess.run([sys.executable, str(iso / 'kitchen' / 'test_h161.py')],
                           capture_output=True, text=True)
        return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1][:110]

    def fabricate(d):
        for ep in d['endpoints'].values():
            ep['f001_digest'] = '0' * 64
            ep['f002_digest'] = '0' * 64      # `match` LEFT TRUE

    rc_base, o_base = run_iso('base', lambda d: None)
    rc_fake, o_fake = run_iso('fake', fabricate)
    rc_flag, o_flag = run_iso(
        'flag', lambda d: d['endpoints']['samsung_s25_ultra'].update(match=False))

    obs('A6_kitchen', rc_unmutated=rc_base, out_unmutated=o_base,
        rc_fabricated_digests=rc_fake, out_fabricated=o_fake,
        rc_match_flag_cleared=rc_flag, out_flag=o_flag,
        intervention='every digest in every endpoint -> 0*64, `match` left true')
    return {'tautology': rc_fake == 0, 'f6_fired': rc_fake != 0,
            'control_live': rc_flag != 0 and rc_base == 0}


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    a1, a2 = arm_c3(), arm_c1()
    a3, a4 = arm_sweep(), arm_constcheck()
    a5, a6 = arm_reproduce(), arm_kitchen()

    controls = [
        Control('C0_folder_is_live',
                why='editing PIN_F001 flips the folded verdict to False, so the '
                    'folder evaluates rather than asserts',
                can_fail_because='the folder is a stub that always reports True',
                null_must_contain='verdict did not move'),
        Control('C1_thermal_arm_is_live',
                why='a stub adb reporting 45.0C makes H161 C1 False, so the '
                    'stub is really consulted',
                can_fail_because='PATH interception does not reach the subprocess',
                null_must_contain='stub ignored'),
        Control('C2_verifier_reads_its_input',
                why='one flipped byte in F001.corpus.bin moves the digest, so a '
                    'reproduction is a measurement and not a constant',
                can_fail_because='the verifier ignores the corpus',
                null_must_contain='digest did not move'),
        Control('C3_kitchen_check_is_not_dead',
                why='clearing one `match` flag makes kitchen/test_h161.py fail '
                    'while the unmutated copy passes',
                can_fail_because='the test passes on everything',
                null_must_contain='test never fails'),
    ]
    controls[0].observe(a1['control_live'], OBS['A1_c3'][0])
    controls[1].observe(a2['control_live'], OBS['A2_c1'][0])
    controls[2].observe(a5['control_live'], OBS['A5_reproduce'][0])
    controls[3].observe(a6['control_live'], OBS['A6_kitchen'][0])

    falsifiers = [
        Falsifier('F1_c3_can_fail',
                  refutes='that C3_pins_intact cannot fail through pin drift',
                  fires_when='corrupting F001.accepted_digest moves the verdict',
                  null_must_contain='verdict moved'),
        Falsifier('F2_c1_refuses_absent_device',
                  refutes='that C1_device_health passes with the device gone',
                  fires_when='C1 is False under a device-not-found adb',
                  null_must_contain='C1 refused'),
        Falsifier('F3_duplicate_of_H201',
                  refutes='that constcheck v2 is blind to these two controls',
                  fires_when='constcheck names H161',
                  null_must_contain='H161 named'),
        Falsifier('F4_single_site',
                  refutes='that this is a class rather than one bug',
                  fires_when='the fold finds folded verdicts in <=1 file',
                  null_must_contain='one file only'),
        Falsifier('F5_number_does_not_reproduce',
                  refutes='that H161 parity evidence stands',
                  fires_when='a committed local binary misses a pinned digest',
                  null_must_contain='digest mismatch'),
        Falsifier('F6_kitchen_sees_fabrication',
                  refutes='that the only standing check is a tautology',
                  fires_when='the test fails on fabricated digests',
                  null_must_contain='fabrication caught'),
    ]
    fired = [a1['f1_fired'], a2['f2_fired'], a4['f3_fired'], a3['f4_fired'],
             a5['f5_fired'], a6['f6_fired']]
    for f, v, key in zip(falsifiers, fired,
                         ('A1_c3', 'A2_c1', 'A4_constcheck', 'A3_sweep',
                          'A5_reproduce', 'A6_kitchen')):
        f.observe(v, OBS[key][0])

    result = {
        'spike': 'H221',
        'target': 'spikes/H161_heterogeneous_device_consensus/run.py',
        'c3_pins_intact_is_constant': a1['constant'],
        'c1_device_health_passes_with_device_absent': a2['passes_absent'],
        'kitchen_test_is_tautology': a6['tautology'],
        'reproduced_endpoints': a5['endpoints'],
        'sweep': {'files': a3['files'], 'folded_live_sites': len(a3['live']),
                  'distinct_files': len({h['path'] for h in a3['live']}),
                  'literal_sites_constcheck_already_sees': a3['literal'],
                  'sites': [{'site': f'{h["path"]}:{h["line"]}',
                             'verdict': repr(h['verdict']),
                             'binding': h['binding']} for h in a3['live']]},
        'falsifiers': {f.name: bool(v) for f, v in zip(falsifiers, fired)},
        'observations': OBS,
    }
    (HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    ok, problems = kfcheck.certify(
        str(HERE),
        artifacts=[str(HERE / 'result.json')],
        controls=controls, falsifiers=falsifiers,
        no_deps_reason='reads H161 and fixtures/ read-only; the folder is in '
                       'this spike dir and is hashed as the artifact set',
        note='H221: H161 C3 compares each pin to a hand-typed twin of itself '
             'and C1 passes at 0.0C when the phone is gone',
        falsifier='C3 moving under a corrupted F001.accepted_digest, or C1 '
                  'refusing a device-not-found adb, or the two committed local '
                  'binaries missing the pinned digests')
    print(f'\ncertify ok={ok}')
    for p in problems:
        print('   ', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
