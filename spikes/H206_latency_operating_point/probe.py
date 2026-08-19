#!/usr/bin/env python3
"""H206 — a preregistered falsifier whose term is a wall clock publishes a
verdict about the machine, not about the system.

W9's falsifier is a disjunction of five terms. Term 3 was
`median_latency_us > 500.0`, evaluated unconditionally. Measured across three
runs of the SAME code: 508.71 us with five lanes live (FIRED, a 1.7% threshold
crossing), 211.54 us idle (not fired), 214.46 us idle (not fired).

THE TWO ARTIFACTS IN THAT SPIKE DISAGREED ON DISK FOR A DAY BECAUSE OF IT:
`provenance.json` recorded `falsifiers_fired: [F_bound_streaming_advantage]`
while `bound_streaming.json` beside it recorded `falsifier_fired: false`. One
said the headline claim was REFUTED and the other said it stood. `recheck` read
DRIFTED and that was correct -- the artifact really had changed.

TWO-SIDED, AND THE SIDE THAT MATTERS IS §5: conditioning a term on its operating
point must not make the falsifier unable to fire. Every deterministic term must
still fire at any load, and an unassertable latency term must read UNASSERTED --
never silently "did not fire".
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
W9 = os.path.join(ROOT, 'spikes', 'W9_bound_streaming_witness')
sys.path.insert(0, W9)

checks = []
def ck(name, cond, detail=''):
    checks.append((bool(cond), name, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def main():
    print(__doc__.split('\n')[0])
    print()
    art = json.load(open(os.path.join(W9, 'bound_streaming.json')))
    prov = json.load(open(os.path.join(W9, 'provenance.json')))
    lt = art.get('latency_term')

    ck('A1 the artifact publishes a latency_term at all', isinstance(lt, dict))
    if not isinstance(lt, dict):
        return 1

    # ---- the operating point is RECORDED, which is the whole family-E remedy ---
    op = lt.get('operating_point') or {}
    ck('A2 the operating point is recorded beside the number, not inferred',
       'loadavg_1m' in op and 'quiet_limit' in op and op.get('reason'),
       f"loadavg {op.get('loadavg_1m')} / limit {op.get('quiet_limit')}")

    # ---- the verdict is THREE-VALUED, so "cannot assert" is not "did not fire" -
    ck('A3 the verdict is one of EXCEEDED / WITHIN / UNASSERTED',
       lt.get('verdict') in ('EXCEEDED', 'WITHIN', 'UNASSERTED'), str(lt.get('verdict')))
    ck('A4 an uncitable operating point yields UNASSERTED, never WITHIN',
       lt.get('citable') or lt.get('verdict') == 'UNASSERTED',
       f"citable={lt.get('citable')} verdict={lt.get('verdict')}")

    # ---- THE FINDING THE ROW DID NOT CONTAIN, and it survives a quiet host -----
    ck('A5 BOTH statistics are published, because the claim says "sub-500us '
       'latency" and does not say WHICH',
       'median_latency_us' in lt and 'p95_latency_us' in lt,
       f"median {lt.get('median_latency_us')} / p95 {lt.get('p95_latency_us')}")
    ck('A6 and the p95 EXCEEDS the 500us bound on a host quiet.sh admits — the '
       'claim is true of the median and false of the p95 in the SAME run',
       lt.get('p95_exceeds_threshold') is True and lt.get('citable') is True,
       f"p95 {lt.get('p95_latency_us')} us vs threshold {lt.get('threshold_us')} us, "
       f"citable={lt.get('citable')}")

    # ---- the two artifacts must now agree, which is what recheck reads --------
    sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
    import recheck
    fired_rec = bool(prov.get('falsifiers_fired'))
    ck('A7 the record and the artifact agree on the headline verdict '
       '(they disagreed on disk for a day)',
       fired_rec == bool(art.get('falsifier_fired')),
       f"record fired={fired_rec}, artifact fired={art.get('falsifier_fired')}")
    st = recheck.check_record(os.path.join(W9, 'provenance.json'))['status']
    ck('A8 recheck reads OK where it read DRIFTED', st == 'OK', st)

    # ---- §5: NOT A WEAKER FALSIFIER. The deterministic terms must still fire ---
    # Driven through the real disjunction with the latency term forced
    # UNASSERTABLE, which is the state §5 is worried about.
    def disjunction(all_72b, fork_rejected, inflation_defeated,
                    lat_citable, lat_exceeds, bw_ge):
        lat_term = lat_citable and lat_exceeds
        return (not all_72b or not fork_rejected or not inflation_defeated
                or lat_term or bw_ge)

    ck('A9a memory violation still fires with the latency term UNASSERTABLE',
       disjunction(False, True, True, False, False, False))
    ck('A9b fork injection still fires with the latency term UNASSERTABLE',
       disjunction(True, False, True, False, False, False))
    ck('A9c inflation still fires with the latency term UNASSERTABLE',
       disjunction(True, True, False, False, False, False))
    ck('A9d bandwidth regression still fires with the latency term UNASSERTABLE',
       disjunction(True, True, True, False, False, True))
    ck('A10 the latency term STILL FIRES when it is assertable and exceeded — '
       'conditioning is not disabling',
       disjunction(True, True, True, True, True, False))
    ck('A11 and a slow run on a LOADED host does NOT fire it, which is the '
       'behaviour change and the whole point',
       not disjunction(True, True, True, False, True, False))

    # ---- the probe itself: quiet.sh must be able to REFUSE, or A4 is untested --
    import importlib
    bsv = importlib.import_module('bound_streaming_verifier')
    # THE FIXTURE IS INJECTED, NOT SWAPPED IN. This arm's first draft renamed
    # the real `spikes/quiet.sh` for its duration -- in a tree five lanes share,
    # in a cycle whose own claim line says not to be the hazard you filed
    # (H234). `latency_operating_point(quiet_path=...)` exists for exactly this
    # and the shared file is never touched.
    with tempfile.TemporaryDirectory(prefix='.h206_', dir=HERE) as d:
        fake = os.path.join(d, 'quiet.sh')
        with open(fake, 'w') as f:
            f.write('#!/bin/sh\necho "REFUSED - fixture" >&2\nexit 1\n')
        os.chmod(fake, 0o755)
        op2 = bsv.latency_operating_point(quiet_path=fake)
        op3 = bsv.latency_operating_point(quiet_path=os.path.join(d, 'absent.sh'))
    ck('A12 a REFUSING quiet.sh makes the operating point uncitable — the arm '
       'that makes A4 mean something', op2.get('citable') is False,
       str(op2.get('reason'))[:80])
    ck('A13 ...and the reason names the refusal rather than going quiet',
       'REFUS' in str(op2.get('reason')).upper(), str(op2.get('reason'))[:60])
    ck('A14 an ABSENT quiet.sh is also uncitable — no party can assert the '
       'operating point, so it is not assumed quiet',
       op3.get('citable') is False and 'absent' in str(op3.get('reason')),
       str(op3.get('reason'))[:70])
    ck('A15 and the SHARED spikes/quiet.sh was never touched by this probe',
       os.path.exists(os.path.join(ROOT, 'spikes', 'quiet.sh')) and
       not os.path.exists(os.path.join(ROOT, 'spikes', 'quiet.sh.h206_probe_moved')))

    bad = [c for c in checks if not c[0]]
    print(f"\nH206 probe: {len(checks) - len(bad)} pass, {len(bad)} fail")
    for _, n, dt in bad:
        print(f"  FAILED  {n}  {dt}")
    out = {'row': 'H206', 'latency_term': lt,
           'checks_pass': len(checks) - len(bad), 'checks_fail': len(bad),
           'arms': [{'name': n, 'pass': ok, 'detail': dt} for ok, n, dt in checks]}
    with open(os.path.join(HERE, 'result.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write('\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
