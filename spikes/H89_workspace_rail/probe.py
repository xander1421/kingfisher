#!/usr/bin/env python3
"""H89 — §10 "nothing is written outside the workspace" has no mechanism.

Runs the five falsifiers preregistered in CHANNEL.md before anything was built,
and writes falsifiers.json. Nothing here is retyped from prose: every count is
computed from the tree at run time.

  python3 spikes/H89_workspace_rail/probe.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import scratchcheck as sc  # noqa: E402

# The 8 §10 instances this fleet has on record, each with the citation that is
# the ONLY evidence it happened. `in_source` is the claim under test in F4: is
# there a tracked file a scanner could have read?
RECORDED = [
    ('/tmp/kfmsg.txt', 'CHANNEL.md:726 (ATOM-3)', False),
    ('/tmp/config.json.bak', 'CHANNEL.md:726 (ATOM-3)', False),
    ('/tmp/eh.bak', 'CHANNEL.md:726 (ATOM-3)', False),
    ('/tmp/ROSTER.bak', 'CHANNEL.md:726 (ATOM-3)', False),
    ('/tmp/kf_id.txt', 'CHANNEL.md:726 (ATOM-3)', False),
    ('/tmp/kf_sid.txt', 'CHANNEL.md:726 (ATOM-3)', False),
    ('/tmp/<commit msg file>', 'WORK_QUEUE.md:325 (AGENT-1, d717518)', False),
    ('/tmp/_cm.$$', 'spikes/harness/test_commit_msg.sh:7', True),
]


def tracked_sources():
    out = subprocess.run(['git', 'ls-files', '*.sh', '*.py', '*.hook'],
                         cwd=ROOT, capture_output=True, text=True).stdout.split()
    return [os.path.join(ROOT, t) for t in out if not t.startswith('elders/')]


def main():
    src = tracked_sources()
    rows = sc.scan_source(src)
    r = {}

    # C0 · the scan reached the tree at all. A census over zero files reports
    # "no violations" and looks exactly like compliance.
    r['C0_files_scanned'] = len(src)
    assert len(src) > 100, 'C0: scan corpus is too small to be the tree'

    # F1 · fires when every out-of-workspace path in committed source is
    # READ-ONLY. Then the source half is a non-finding.
    writes = [x for x in rows if x[2] != 'mktemp']
    r['F1'] = {'fires': len(rows) == 0,
               'source_write_positions': len(rows),
               'non_mktemp_writes': len(writes),
               'live_worst': [f'{os.path.relpath(f, ROOT)}:{l} {k} {t}'
                              for f, l, k, t in rows if 'LaunchAgents' in t]}

    # F2 · fires when >50% of hits are Android device paths §10 permits.
    dev = [x for x in rows if x[3].startswith(('/data/local/tmp', '/sdcard'))]
    r['F2'] = {'fires': len(rows) > 0 and len(dev) * 2 > len(rows),
               'device_path_hits': len(dev), 'total_hits': len(rows)}

    # F3 · fires when a PLANTED out-of-workspace writer is NOT flagged. Both
    # mouths are planted against: the source scan and the live hook.
    plant = os.path.join(HERE, 'planted_writer.sh')
    with open(plant, 'w') as f:
        f.write('#!/bin/sh\n# F3. Planted deliberately; this file is evidence.\n'
                'echo pwned > /tmp/h89_planted.txt\n')
    seen_scan = bool(sc.scan_source([plant]))
    import io
    ev = json.dumps({'tool_name': 'Bash',
                     'tool_input': {'command': 'echo pwned > /tmp/h89_planted.txt'}})
    seen_hook = sc.hook(io.StringIO(ev)) == 2
    # The plant must not actually have run. Nothing here writes outside the tree.
    r['F3'] = {'fires': not (seen_scan and seen_hook),
               'flagged_by_scan': seen_scan, 'refused_by_hook': seen_hook,
               'planted_file_was_never_executed': not os.path.exists('/tmp/h89_planted.txt')}

    # F4 · fires when a source-level detector flags >=4 of the 8 recorded
    # instances. PREDICTED IN THE CLAIM: it flags 1, so F4 does not fire.
    hit_paths = {t for _, _, _, t in rows}
    caught = [p for p, cite, in_src in RECORDED if p in hit_paths]
    r['F4'] = {'fires': len(caught) >= 4, 'recorded_instances': len(RECORDED),
               'visible_to_a_source_scan': len(caught), 'which': caught,
               'predicted_in_claim': 1}

    # F5 · fires when the sanctioned location cannot serve a real converted
    # site. Run against the REAL suite, not a fixture.
    conv = subprocess.run(['sh', 'spikes/harness/test_carriescheck.sh'],
                          cwd=ROOT, capture_output=True, text=True)
    tail = (conv.stdout or '').strip().splitlines()[-1:] or ['']
    r['F5'] = {'fires': conv.returncode != 0,
               'converted_site': 'spikes/harness/test_carriescheck.sh:22',
               'suite_result': tail[0].strip(), 'rc': conv.returncode,
               'site_now_scans_clean':
                   not sc.scan_source([os.path.join(ROOT, 'spikes/harness/test_carriescheck.sh')])}

    # The census, published as rows rather than as a total, because a total is
    # what decays into prose (§7: cite the artifact, not its size).
    r['census'] = [f'{os.path.relpath(f, ROOT)}:{l}: {k} {t}' for f, l, k, t in rows]
    r['census_by_kind'] = {}
    for _, _, k, _ in rows:
        r['census_by_kind'][k] = r['census_by_kind'].get(k, 0) + 1

    with open(os.path.join(HERE, 'falsifiers.json'), 'w') as f:
        json.dump(r, f, indent=2, sort_keys=True)

    for k in ('F1', 'F2', 'F3', 'F4', 'F5'):
        print('%s  %s  %s' % (k, 'FIRED' if r[k]['fires'] else 'quiet',
                              {x: y for x, y in r[k].items() if x != 'fires'}))
    print('census: %d write position(s), by kind %s' % (len(rows), r['census_by_kind']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
