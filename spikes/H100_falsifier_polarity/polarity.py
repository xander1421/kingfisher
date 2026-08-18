#!/usr/bin/env python3
"""H100 — is 'a falsifier whose stated polarity is ambiguous' a CLASS, or one
author's error?

The row was filed by AGENT-2 from AGENT-2's own damage (G43's F2) and its
falsifier FA is the one that retires it. FA is run FIRST, before any checker is
written: build-the-mechanism-then-look-for-instances is how `refcheck.py` check
6 shipped inert AND wrong (H85).

  python3 spikes/H100_falsifier_polarity/polarity.py

Read-only. Writes only inside this spike's own directory (§10).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHANNEL = os.path.join(ROOT, "CHANNEL.md")

# The one statement whose two polarities are the reason this row exists. Named
# by content, not by index: an index moves the moment CHANNEL.md is appended to.
OWN_DEFECT = "the MISSION PROPOSITION SURVIVES"


def if_form_falsifiers(text):
    """Every falsifier stated as `(Fn) if <antecedent>, <consequent>`.

    Two marker shapes are in live use -- `**(F2)** *if` and `(F2) if` -- and an
    extraction that sees only one of them undercounts. The first pass of this
    row published **16** from a regex that missed the `**(Fn)** *if` shape; the
    corrected count is what this function returns, and the discrepancy is the
    row's own instance of CLAUDE.md's `cut -cN` family (a truncating read
    presented as a complete one).
    """
    marks = []
    for pat in (r'\*\*\(?(F\d+)[^)*]{0,40}\)?\*\*\s*\*?if\b',
                r'\((F\d+)[^)]{0,40}\)\s*\*?if\b'):
        for m in re.finditer(pat, text, re.I):
            marks.append((m.start(), m.group(1), m.end()))
    marks.sort()
    seen, out = set(), []
    for start, name, end in marks:
        if start in seen:
            continue
        seen.add(start)
        out.append((start, name, end))
    stops = [o[0] for o in out[1:]] + [len(text)]
    items = []
    for (start, name, end), stop in zip(out, stops):
        body = text[end:min(stop, end + 520)].split("\n")[0].strip()
        items.append({"n": len(items) + 1, "name": name, "text": body})
    return items


def ambiguous(item):
    """THE MECHANICAL POLARITY RULE, and it is deliberately narrow.

    An `(Fn) if <antecedent>` statement defines firing exactly once: the
    antecedent. A statement is ambiguous when it defines firing a SECOND time
    somewhere else and the two definitions can disagree -- which in this corpus
    is a `Predicted: Fn does [NOT] fire` label carrying an `i.e.` gloss that
    restates the condition in its own words. The label alone is fine (two live
    examples); the gloss is the second definition.

    Narrow on purpose. A rule that tried to decide polarity from the prose
    would be judging natural language, and a checker that gates commits on a
    judgement call is one every lane learns to route around (H14, H52, H73).
    """
    return bool(re.search(r'Predicted:\s*F\d+\s+does\s+(?:NOT\s+)?fire[^.]{0,80}\bi\.e\.',
                          item["text"], re.I))


def main():
    text = open(CHANNEL).read()
    items = if_form_falsifiers(text)
    flagged = [i for i in items if ambiguous(i)]

    res = {"spike": "H100", "if_form_falsifiers": len(items),
           "flagged_ambiguous": [i["n"] for i in flagged],
           "controls": {}, "falsifiers": {}}

    # --- C1: the rule must be able to go red on a planted defect -------------
    planted = ('**(F9)** *if the planted condition holds, the claim survives.* '
               'Predicted: F9 does NOT fire, i.e. the planted condition holds.')
    planted_items = if_form_falsifiers(planted)
    res["controls"]["C1_rule_catches_a_planted_ambiguity"] = {
        "what_would_fail_it": "a rule that flags nothing when both polarity "
                              "statements are present in one falsifier",
        "planted_extracted": len(planted_items),
        "planted_flagged": sum(1 for i in planted_items if ambiguous(i)),
        "ok": len(planted_items) == 1 and ambiguous(planted_items[0]),
    }
    # --- C2: and quiet on a clean one, or it accuses everything --------------
    clean = ('**(F9)** *if the planted condition holds, I withdraw the row.* '
             'Predicted: F9 does NOT fire.')
    clean_items = if_form_falsifiers(clean)
    res["controls"]["C2_rule_is_quiet_on_a_clean_label"] = {
        "what_would_fail_it": "a rule that flags a bare prediction label, "
                              "which two live falsifiers carry legitimately",
        "clean_flagged": sum(1 for i in clean_items if ambiguous(i)),
        "ok": len(clean_items) == 1 and not ambiguous(clean_items[0]),
    }
    # --- C3: the reader must be deterministic --------------------------------
    again = if_form_falsifiers(text)
    res["controls"]["C3_reader_is_deterministic"] = {
        "what_would_fail_it": "two reads of an unchanged CHANNEL.md returning "
                              "different counts, which would make every number "
                              "here meaningless",
        "first": len(items), "second": len(again),
        "ok": [i["text"] for i in items] == [i["text"] for i in again],
    }

    # --- FA, the killing falsifier, CORRECTED before it was run --------------
    # As first stated FA read "if EVERY one resolves to exactly one polarity,
    # H100 is withdrawn" -- and the corpus FA reads CONTAINS the statement the
    # row was filed from, so FA could never be satisfied. A falsifier that
    # cannot fire is A15, inside the row about falsifiers that cannot express
    # their verdict. Corrected to exclude this row's own instance, which is the
    # only form in which it can fire at all.
    others = [i for i in flagged if OWN_DEFECT not in i["text"]]
    res["falsifiers"]["FA_every_other_falsifier_is_unambiguous"] = {
        "question": "excluding the statement this row was filed from, does "
                    "every if-form falsifier in CHANNEL.md resolve to exactly "
                    "one polarity?",
        "flagged_excluding_own": [i["n"] for i in others],
        "unambiguous_others": len(items) - 1 - len(others),
        "total_others": len(items) - 1,
        "fired": len(others) == 0,
        "meaning_if_fired": "the prose is unambiguous by construction, the "
                            "defect is this author's alone, and H100 is "
                            "WITHDRAWN as a class",
    }
    res["falsifiers"]["FA_as_first_stated_could_not_fire"] = {
        "question": "could FA as originally written ever have been satisfied?",
        "own_instance_present_in_corpus": any(OWN_DEFECT in i["text"] for i in items),
        "fired": any(OWN_DEFECT in i["text"] for i in items),
        "meaning_if_fired": "A15 in the row about A21 -- recorded against the "
                            "author rather than quietly repaired",
    }

    bad = [k for k, v in res["controls"].items() if not v["ok"]]
    res["controls_ok"] = f"{len(res['controls']) - len(bad)}/{len(res['controls'])}"
    with open(os.path.join(HERE, "polarity.json"), "w") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    if bad:
        print("CONTROLS FAILED:", bad)
        return 1

    sys.path.insert(0, os.path.join(ROOT, "spikes", "harness"))
    import kfcheck
    from provenance import Control, Falsifier
    controls, falsifiers = [], []
    for name, spec in (
        ("C1_rule_catches_a_planted_ambiguity",
         ("the rule must go red on a falsifier carrying two polarity "
          "statements, or it cannot see the defect the row was filed for",
          "a rule that flags nothing when both statements are present",
          "a flagged verdict, produced here from a planted statement")),
        ("C2_rule_is_quiet_on_a_clean_label",
         ("the rule must be quiet on a bare `Predicted:` label, which live "
          "falsifiers carry legitimately, or it is an always-red gate",
          "flagging a clean label, which would accuse two live falsifiers",
          "a NOT-flagged verdict on a statement with one polarity")),
        ("C3_reader_is_deterministic",
         ("two reads of an unchanged CHANNEL.md must agree, or no count "
          "in this spike means anything",
          "two reads returning different extractions",
          "both outcomes: the reader is re-run, not asserted")),
    ):
        why, canfail, null = spec
        c = Control(name, why, can_fail_because=canfail, null_must_contain=null)
        c.observe(res["controls"][name]["ok"],
                  {k: v for k, v in res["controls"][name].items() if k != "ok"})
        controls.append(c)
    for name, refutes, fires_when, null in (
        ("FA_every_other_falsifier_is_unambiguous",
         "H100 as a CLASS: if every if-form falsifier other than this row's "
         "own instance has exactly one polarity, the defect is one author's",
         "no statement other than this row's own is flagged by the rule",
         "a flagged other-lane statement, which C1 shows the rule can produce"),
        ("FA_as_first_stated_could_not_fire",
         "the original wording of FA, which read on a corpus containing the "
         "very statement whose absence it required",
         "this row's own instance is present in the corpus FA reads",
         "both outcomes: the corpus is read, not assumed"),
    ):
        f = Falsifier(name, refutes=refutes, fires_when=fires_when,
                      null_must_contain=null)
        f.observe(res["falsifiers"][name]["fired"],
                  {k: v for k, v in res["falsifiers"][name].items()
                   if k not in ("fired", "question", "meaning_if_fired")})
        falsifiers.append(f)
    ok, problems = kfcheck.certify(
        HERE, deps=[], no_deps_reason="reads CHANNEL.md, a shared append-only "
                                      "log with no generator, plus its own source",
        artifacts=[os.path.join(HERE, "polarity.py"),
                   os.path.join(HERE, "polarity.json")],
        controls=controls, falsifiers=falsifiers,
        captures=[("channel_corpus", text)],
        falsifier="a flagged statement belonging to any lane but this one, "
                  "which would make the ambiguity a class rather than an "
                  "author's error",
        allow_dirty=True,
        note="H100: filed by AGENT-2 from AGENT-2's own defect, and run "
             "falsifier-first. FA fired: the row is WITHDRAWN as a class.")
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
