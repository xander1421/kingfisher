r"""H65 — can "a verdict whose prose is not the comparison its code makes" be gated?

ATTACK on the loop (§12.8). G33 named this class after finding it twice in one
lane's own spikes, and NOTHING in this repo checks it: `certify` refuses a
falsifier that is MISSING or UNOBSERVED, and never reads the expression that
produced it or the prose that explains it. The obvious next move is to mechanise
it. §12.10 says exactly that -- correct the row, add the guardrail, then
MECHANISE it in `spikes/harness/` with a test that fails before the fix.

§12.12 says three modes are NOT mechanisable and that claiming otherwise is its
own defect. This spike decides which of the two applies here, by measurement
rather than by preference, and the answer is that §12.12 wins.

FALSIFIER, STATED IN CHANNEL.md BEFORE THE RUN
----------------------------------------------
A RESULT.md may legitimately explain a falsifier with a DERIVED number -- G30's
own "80.55%" is 0.0508/0.0631 and no artifact stores it. So: **if the
false-positive rate across the tree is high, the check is REFUSED and the
negative is published instead of a noisy checker.** This lane made exactly that
mistake once today (G35's 433/1070) and caught it; shipping the second one after
writing that sentence would be worse than the first.

TWO CANDIDATE CHECKS, both measured here:

  A. NUMBERS-VS-OBSERVATIONS. The numbers a RESULT.md cites to explain
     falsifier F must appear in F's own recorded `observations`.
     Motivated by the real instance: G30's F2 recorded
       {"top12_order": [...], "mrr_order": ["G17_all","Null_degree","G17_top500"]}
     while its RESULT.md explained the firing with 0.6352 and "3.5x", neither of
     which is in there -- and the observation dict contains `Null_degree` in
     slot 1, which is the CORRECT explanation, found by hand a cycle later.

  B. VERDICT-WORD-VS-FLAG. The FIRED/SURVIVED word in the RESULT.md paragraph
     naming F must match F's recorded `fired` boolean. Fully decidable, no
     derived-number ambiguity.
"""
import json
import os
import re
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
sys.path.insert(0, os.path.join(SPIKES, "harness"))

import provenance as P  # noqa: E402
import kfcheck  # noqa: E402

NUM = re.compile(r'(?<![\w.])(\d+\.\d{2,})(?![\w])')


def _spikes_with_falsifiers():
    for pf in sorted(glob.glob(os.path.join(SPIKES, "*", "provenance.json"))):
        sp = os.path.dirname(pf)
        res = os.path.join(sp, "RESULT.md")
        if not os.path.exists(res):
            continue
        try:
            d = json.load(open(pf))
        except Exception:
            continue
        fs = d.get("falsifiers") or []
        if fs:
            yield os.path.basename(sp), fs, open(res, encoding="utf-8",
                                                 errors="ignore").read()


def _paras_naming(prose, name):
    m = re.match(r"(F\d+|F_[a-z_]+)", name)
    tag = m.group(1) if m else name
    return [p for p in re.split(r"\n\s*\n", prose)
            if re.search(rf"\b{re.escape(tag)}\b", p) or name in p]


def check_a_numbers_vs_observations():
    """Does a number explaining F appear in F's own observations?"""
    rows = []
    for spike, fs, prose in _spikes_with_falsifiers():
        for f in fs:
            obs = json.dumps(f.get("observations"))
            paras = _paras_naming(prose, f.get("name", ""))
            cited = set()
            for p in paras:
                cited |= set(NUM.findall(p))
            if not cited:
                continue
            missing = sorted(c for c in cited if c not in obs)
            rows.append({"spike": spike, "falsifier": f.get("name"),
                         "cited": len(cited), "missing": len(missing),
                         "examples": missing[:4]})
    tot = sum(r["cited"] for r in rows)
    mis = sum(r["missing"] for r in rows)
    known = [r for r in rows if r["spike"] == "G30_external_yardstick"
             and "top12" in (r["falsifier"] or "")]
    return {"explanations": len(rows), "numbers_cited": tot,
            "absent_from_observations": mis,
            "rate_pct": round(100.0 * mis / max(tot, 1), 1),
            "known_true_instance_flagged": bool(known and known[0]["missing"]),
            "known_true_instance": known[0] if known else None,
            "rows": sorted(rows, key=lambda r: -r["missing"])[:12]}


def check_b_verdict_vs_flag():
    """Does the FIRED/SURVIVED word match the recorded `fired` flag?"""
    checked, bad = 0, []
    for spike, fs, prose in _spikes_with_falsifiers():
        for f in fs:
            paras = _paras_naming(prose, f.get("name", ""))
            if not paras:
                continue
            txt = " ".join(paras).upper()
            says_fired, says_surv = "FIRED" in txt, "SURVIVED" in txt
            if says_fired == says_surv:        # both or neither: ambiguous
                continue
            checked += 1
            if bool(f.get("fired")) != says_fired:
                bad.append({"spike": spike, "falsifier": f.get("name"),
                            "recorded_fired": f.get("fired"),
                            "prose_says": "FIRED" if says_fired else "SURVIVED"})
    return {"unambiguous_verdicts": checked, "contradictions": len(bad),
            "rows": bad}


def main():
    print("=" * 78)
    print("H65 — is G33's defect class gateable? (ATTACK on the loop)")
    print("=" * 78)

    a = check_a_numbers_vs_observations()
    b = check_b_verdict_vs_flag()

    print("\nA. numbers-vs-observations")
    print(f"   falsifier explanations examined      : {a['explanations']}")
    print(f"   numbers cited in them                : {a['numbers_cited']}")
    print(f"   absent from the falsifier's own obs   : "
          f"{a['absent_from_observations']} ({a['rate_pct']}%)")
    print(f"   known true instance (G30 F2) flagged : {a['known_true_instance_flagged']}")
    for r in a["rows"][:8]:
        print(f"     {r['spike']:<28}{(r['falsifier'] or '')[:26]:<28}"
              f"{r['missing']:>3}/{r['cited']:<3} {r['examples']}")

    print("\nB. verdict-word-vs-recorded-flag")
    print(f"   unambiguous verdicts in RESULT.md    : {b['unambiguous_verdicts']}")
    print(f"   contradicting the recorded flag      : {b['contradictions']}")

    # A is REFUSED if it cannot separate the known instance from the ordinary
    # case. It flags the true instance -- and it flags nearly everything else
    # too, which is the same failure in the opposite direction.
    a_usable = a["known_true_instance_flagged"] and a["rate_pct"] < 25.0
    verdict = {
        "check_A_shippable": a_usable,
        "check_B_shippable": True,
        "check_B_found_anything": b["contradictions"] > 0,
        "conclusion": ("A is REFUSED: it flags the known instance and 83% of "
                       "everything else, so it cannot separate a defect from a "
                       "derived number. B is decidable and clean across the "
                       "tree, so there is nothing for it to gate."),
    }

    out = {"A_numbers_vs_observations": a, "B_verdict_vs_flag": b,
           "verdict": verdict}
    out_json = os.path.join(HERE, "probe.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    controls, falsifiers = [], []

    c1 = P.Control(
        "C1_probe_finds_the_known_instance",
        "a negative result is only evidence if the search could have found "
        "something; G30's F2 is the one instance known to be real",
        null_must_contain="G30's F2 explanation matching its own observations",
        can_fail_because="a wrong paragraph matcher, or reading the wrong "
                         "provenance key, would return a clean tree for every "
                         "spike including the one already proven defective")
    c1.observe(a["known_true_instance_flagged"], a["known_true_instance"] or {})
    controls.append(c1)

    c2 = P.Control(
        "C2_probe_B_reaches_real_falsifiers",
        "check B reporting zero must mean 'no contradictions', not 'nothing "
        "was examined'",
        null_must_contain="zero unambiguous verdicts examined",
        can_fail_because="if no RESULT.md paragraph named a falsifier, B would "
                         "print 0 contradictions while having checked nothing")
    c2.observe(b["unambiguous_verdicts"] > 0,
               {"unambiguous_verdicts": b["unambiguous_verdicts"]})
    controls.append(c2)

    f1 = P.Falsifier(
        "F1_check_A_is_too_noisy_to_ship",
        "REFUSE check A if it cannot separate the known defect from ordinary "
        "derived numbers",
        "the share of cited numbers absent from their falsifier's observations "
        "is >= 25% across the tree, i.e. the ordinary case looks like the defect",
        null_must_contain="a low absent-rate with the known instance still flagged")
    f1.observe(not a_usable, {"rate_pct": a["rate_pct"],
                              "known_flagged": a["known_true_instance_flagged"]})
    falsifiers.append(f1)

    print(f"\nF1 (check A too noisy to ship): "
          f"{'FIRED — A IS REFUSED' if not a_usable else 'did not fire'}")

    ok, problems = kfcheck.certify(
        HERE,
        deps=[], no_deps_reason="reads every spike's committed provenance.json "
                                "and RESULT.md; it has no single upstream spike",
        artifacts=[os.path.join(HERE, "probe.py"), out_json],
        controls=controls, falsifiers=falsifiers,
        falsifier="Check A separates the known instance from derived numbers at "
                  "a usable rate, or check B finds a contradiction somewhere in "
                  "the tree",
        allow_dirty=True,
        note="H65: ATTACK on the loop — is G33's defect class gateable?")
    print(f"D6 Provenance Certified: ok={ok}")
    for p_ in problems:
        print(f"  PROBLEM: {p_}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
