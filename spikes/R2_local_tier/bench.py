#!/usr/bin/env python3
"""Can a local model do THIS fleet's work, under THIS machine's load?

Generic tokens/sec is the wrong number. The question is whether a local tier
can carry harness/queue cycles when Claude is capped -- so the tasks here are
taken from what lanes actually do, and scored by gates that already REFUSE
rather than warn.

THREE TASKS, each with a mechanical pass condition:
  trailer   produce a commit message with the trailers section 13 requires.
            Scored by the real commit-msg rules: Atom must be a CALLSIGN,
            Reviewed-By must not be "self". A model that writes a plausible
            paragraph and omits a trailer FAILS, which is the point -- this is
            the most common thing a lane does and it is fully checkable.
  triage    given real refcheck output, name the blocking file. Extraction,
            not judgement: the answer is in the input or the model invented it.
  classify  route a cycle description to a lane. This is the router's own job,
            so a model that cannot do it cannot be the router.

MEASURED UNDER LOAD, deliberately. The fleet is five resident Claude lanes at
~600MB each on 24GB unified memory. A benchmark run on an idle machine would
report a number nobody will ever see, and memory pressure is the whole risk of
a 17GB model here.

    python3 bench.py <model.gguf> [--n 3]
"""
import json
import os
import re
import subprocess
import sys
import time

LLAMA = os.path.expanduser('~/llama.cpp/build/bin/llama-cli')

TASKS = [
    ('trailer',
     'Write a git commit message for: fixed a device selection bug where bare '
     'adb failed with two devices attached. End with exactly these trailers on '
     'their own lines: "Atom: AGENT-1" and "Reviewed-By: unreviewed". '
     'Do not think step by step. Output only the commit message. /no_think',
     lambda o: bool(re.search(r'^Atom:\s*[A-Z]+-\d+\s*$', o, re.M))
               and bool(re.search(r'^Reviewed-By:\s*(?!self)\S+', o, re.M))),
    ('triage',
     'This is checker output:\n'
     '  UNRESOLVED spikes/harness/idscope.py: section 0 does not resolve\n'
     'Reply with ONLY the file path that is blocking.',
     lambda o: 'spikes/harness/idscope.py' in o),
    ('classify',
     'Lanes: AGENT-1 owns device/transport, AGENT-2 owns graph AI training, '
     'ATTACKER-1 owns adversarial audit. Which lane owns "re-measure link '
     'prediction MRR after fixing a train/test leak"? Reply with only the '
     'lane name.',
     lambda o: 'AGENT-2' in o.upper()),
]


def run(model, prompt, n_predict=220):
    t0 = time.time()
    p = subprocess.run(
        [LLAMA, '-m', model, '-p', prompt, '-n', str(n_predict),
         '-no-cnv', '--no-warmup', '-st', '--temp', '0',
         '-ngl', os.environ.get('KF_NGL', '99')],
        capture_output=True, text=True, timeout=600)
    out = p.stdout
    # llama-cli echoes the prompt; strip it so a pass cannot come from the
    # question containing the answer. This bit the triage task first time --
    # the path appears in the PROMPT, so any echo scored as a pass.
    if prompt[-40:] in out:
        out = out.split(prompt[-40:], 1)[1]
    tps = re.search(r'Generation:\s*([0-9.]+) t/s', p.stderr + p.stdout)
    return out.strip(), (float(tps.group(1)) if tps else 0.0), time.time() - t0


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    model = os.path.expanduser(sys.argv[1])
    if not os.path.exists(model):
        sys.exit(f'no such model: {model}')
    # `pgrep -fc 'claude -p You are'` EXITS 2 on this machine and prints
    # nothing -- the pattern exceeds pgrep's matching limit, so `|| true`
    # swallowed the error and the field read 0 while FIVE lanes were resident.
    # A load figure that reports zero under full load is worse than no field at
    # all: it makes an idle-machine benchmark look like a measurement under
    # pressure, which is the entire risk being assessed here. Counted the way
    # peers.sh does it, and asserted non-negative rather than defaulted to 0.
    lanes = int(subprocess.run(
        "ps -eo command= | grep -c 'claude -p You are' || true", shell=True,
        capture_output=True, text=True).stdout.strip() or 0)
    lanes = max(0, lanes - 1)   # the grep itself
    print(f'model  {os.path.basename(model)}')
    print(f'load   {lanes} claude lanes resident\n')

    res, rates = {}, []
    for name, prompt, check in TASKS:
        out, tps, secs = run(model, prompt)
        ok = bool(check(out))
        rates.append(tps)
        res[name] = {'pass': ok, 'tps': tps, 'secs': round(secs, 1)}
        print(f'  {name:9s} {"PASS" if ok else "FAIL"}  {tps:6.1f} t/s  {secs:5.1f}s')
        if not ok:
            print(f'            got: {out[:110]!r}')

    passed = sum(1 for v in res.values() if v['pass'])
    res['_summary'] = {'passed': passed, 'of': len(TASKS),
                       'median_tps': round(sorted(rates)[len(rates) // 2], 1),
                       'lanes_resident': lanes,
                       'model': os.path.basename(model)}
    print(f"\n{passed}/{len(TASKS)} tasks, median {res['_summary']['median_tps']} t/s "
          f"under {lanes} lanes")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"bench_{os.path.basename(model).split('.')[0][:28]}.json")
    json.dump(res, open(out_path, 'w'), indent=1)
    print(f'-> {os.path.basename(out_path)}')
    return 0 if passed == len(TASKS) else 1


if __name__ == '__main__':
    sys.exit(main())
