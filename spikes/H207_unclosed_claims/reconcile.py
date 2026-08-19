"""reconcile.py — H207, ATTACKER-1, 2026-08-19.

The CLAIM line for this row preregistered a hand count: **32 of 235 CLAIM lines
(14%) have no DONE/RETRACTED/WITHDRAWN line anywhere in CHANNEL.md**, with a
per-lane breakdown. The shipped module reports 3 + 14 + 12 = 29 unclosed
subjects of 245. Those are different numbers and the difference is the finding,
not a rounding: **the hand count's closer vocabulary was incomplete.**

Recomputes both, in one pass, over the same file. A reconciliation whose two
sides are computed by different programs is not one.
run: python3 spikes/H207_unclosed_claims/reconcile.py
"""
import os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ID = re.compile(r'^(?:[A-Z]+\d+(?:\.\d+)?|M1\.\d+)$')
lines = open(os.path.join(ROOT, 'CHANNEL.md')).read().splitlines()

def subjects(prefix):
    out = collections.defaultdict(set)          # subject -> set(lines)
    for i, ln in enumerate(lines, 1):
        w = ln.split()
        if len(w) >= 2 and w[0] == prefix:
            out[w[1].strip('*`,.')].add(i)
    return out

claims = subjects('CLAIM')
HAND    = ['DONE', 'RETRACTED', 'WITHDRAWN']            # what the CLAIM line used
SHIPPED = HAND + ['RELEASE', 'RELEASED']                # v5's CLOSERS, exactly
# CORRECTED is deliberately NOT a closer and is scored SEPARATELY below. The
# first draft of this probe folded it into SHIPPED, "rescued" H69 -- and the
# module names H69 DECIDABLE-STALE in the same run. A reconciliation that
# disagrees with the module it reconciles is measuring a third thing. The module
# is right: it reports CORRECTED under its own DRIFT arm precisely because
# whether that prefix closes a claim is a VOCABULARY DECISION nobody has made,
# and a probe must not make it silently on the module's behalf.
closed_hand    = set().union(*(subjects(p) for p in HAND))
closed_shipped = set().union(*(subjects(p) for p in SHIPPED))
closed_corrected = set(subjects('CORRECTED'))
# RELEASE closes every id-shaped token in its leading run, not only its subject.
for i, ln in enumerate(lines, 1):
    w = ln.split()
    if w and w[0] in ('RELEASE', 'RELEASED'):
        head = re.split(r'—|--', ln)[0]
        closed_shipped |= {t.strip('*`,.') for t in head.split()[1:]
                           if ID.match(t.strip('*`,.'))}

n_lines = sum(len(v) for v in claims.values())
stale_hand    = sorted(s for s in claims if s not in closed_hand)
stale_shipped = sorted(s for s in claims if s not in closed_shipped)
if not claims:
    sys.exit('VOID: no CLAIM parsed, so any stale count is a statement about this probe')

print(f'CLAIM lines: {n_lines}   distinct CLAIM subjects: {len(claims)}')
print(f'  unclosed under the HAND vocabulary    {HAND}: {len(stale_hand)}')
print(f'  unclosed under the SHIPPED vocabulary {SHIPPED}: {len(stale_shipped)}')
rescued = sorted(set(stale_hand) - set(stale_shipped))
print(f'\nRESCUED by treating RELEASE as a closer: {len(rescued)}')
print('  ' + ', '.join(rescued) if rescued else '  (none)')
extra = sorted(set(stale_shipped) - set(stale_hand))
print(f'ACCUSED only by the shipped vocabulary: {len(extra)}  {extra}')
drift = sorted(s for s in stale_shipped if s in closed_corrected)
print(f'\nSTILL ACCUSED but named by a CORRECTED line -- the module DRIFT arm: '
      f'{len(drift)}  {drift}')
print('  These decide a vocabulary question and this probe does not decide it.')

# The control, and it is the one that decides whether this reconciliation means
# anything: a vocabulary that closed EVERYTHING would also "explain" the gap.
if not stale_shipped:
    sys.exit('CONTROL FAILED: the shipped vocabulary closes every claim, so it '
             'is not a closer list, it is a mute button')
if len(closed_shipped) <= len(closed_hand):
    sys.exit('CONTROL FAILED: the shipped vocabulary is not a superset -- the '
             'comparison is not measuring what it says')
print(f'\ncontrol: the shipped vocabulary still leaves {len(stale_shipped)} accused '
      f'(it is not a mute button) and closes {len(closed_shipped) - len(closed_hand)} '
      f'more subjects than the hand list (it is a superset)')
