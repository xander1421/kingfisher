#!/usr/bin/env python3
"""M1_9 certification, driven from mutation.json's PERSISTED observations.

This could not be written before mutate.py v2 (M17). The control that makes a
zero meaningful -- the probe proving the mutant binary was genuinely different --
was printed to stdout and stored only on the VOID path, so the artefact carried
the verdicts and none of the evidence. Regenerating a provenance record from it
was impossible, which is why the old record went stale and stayed stale.

deps is the SPIKE, not the repo root: at repo scope in a five-lane tree the
staleness floor is a fleet-activity clock (the H88 correction, same day).
"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'harness')))
from kfcheck import certify, Control

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
M = json.load(open('mutation.json'))
MUT = {k: v for k, v in M.items() if not k.startswith('_')}

live = {k: (not v.get('void', False) and v.get('probe_base') != v.get('probe_mut'))
        for k, v in MUT.items()}
c_live = Control(
    'mutant-is-live',
    'a 0/64 from a dead mutant, a failed rebuild or a missed anchor is indistinguishable from a 0/64 the corpus genuinely did not notice',
    null_must_contain='the probe output BEFORE and AFTER each mutation, which must differ',
    can_fail_because='a feature-gated or semantically inert edit leaves probe_base == probe_mut and the mutation is reported VOID with no rate')
c_live.observe(all(live.values()),
               [f"{k}: {v.get('probe')} {v.get('probe_base')!r} -> {v.get('probe_mut')!r}"
                for k, v in MUT.items()],
               'every mutation changed its own probe, so every rate below is about the corpus')

# The finding, restated as an observation rather than a sentence.
rates = {k: (v['total'], v['n']) for k, v in MUT.items()}
c_gap = Control(
    'two-fault-classes-are-inexpressible',
    "the row's finding: the corpus executes `<` and cannot observe its fault",
    null_must_contain='a per-mutation detection count, which must be capable of being non-zero -- three of the five are',
    can_fail_because='a corpus program that compares equal values would make less-is-lesseq non-zero')
c_gap.observe(rates['less-is-lesseq'][0] == 0 and rates['stdlib-init'][0] == 0,
              [f'{k}: {t}/{n}' for k, (t, n) in rates.items()],
              'less-is-lesseq 0/64 and stdlib-init 0/64 while sub-is-add, resolver-message and stdlib-if are non-zero')

c_nonuniform = Control(
    'classes-are-not-uniform',
    'if every mutation scored the same the corpus classes would be interchangeable and the by_class split would carry no information',
    null_must_contain='the five totals, which must not all be equal',
    can_fail_because='five identical totals would mean the sweep is not discriminating between mutations at all')
c_nonuniform.observe(len({t for t, _ in rates.values()}) > 1,
                     [f'{k}={t}' for k, (t, _) in rates.items()],
                     'totals 4, 0, 24, 5, 0 -- four distinct values across five mutations')

# WRITES ITS OWN RECORD, NEVER provenance.json -- and this is a repair, not a
# precaution. v1 omitted record_name and OVERWROTE the spike's historical
# provenance.json with a REFUSED record derived from the contaminated sweep 3,
# while RESULT.md two directories up was simultaneously claiming that file was
# "left openly stale". H49's RecordCollision guard did not fire because the
# artifact list matched exactly -- it compares WHICH artifacts, not which RUN,
# so a re-certification of the same spike is precisely the case it cannot see.
# The historical record is the evidence that this row's defect was real; a tool
# written to diagnose a stale record must not be able to destroy it.
ok, problems = certify(
    HERE, deps=[HERE], artifacts=['mutation.json', 'baseline.json'],
    record_name='provenance.m17.json',
    controls=[c_live, c_gap, c_nonuniform],
    captures=[('mutate.py', hashlib.sha256(open('mutate.py','rb').read()).hexdigest()[:16]),
              ('elders_head', M['_tree']['elders_head'].strip()),
              ('elders_patch_sha256', M['_tree']['elders_patch_sha256']),
              ('detected_mutation_classes', '%d of %d' % (
                  sum(1 for t, _ in rates.values() if t > 0), len(rates)))],
    allow_dirty=True,
    note='M1_9 re-certified under M17. Five mutations, not four: the write-up predated stdlib-if.',
    falsifier='if a fresh sweep gave different rates, or any probe failed to move, the recorded rates are about this harness and not about the corpus')
print('ok=%s' % ok)
for p in problems: print('  PROBLEM:', p)
print('detected_mutation_classes = %d of %d' % (sum(1 for t,_ in rates.values() if t>0), len(rates)))
sys.exit(0 if ok else 1)
