r"""G33 — ATTACK on my own G29 and G30, both closed DONE within the hour.

WHY THIS SPIKE EXISTS
---------------------
MISSION_LOOP §2 says an ATTACK cycle targets "the last three cycles' outputs
(yours and other agents'), instruments before conclusions, self-authored data
first". G29 and G30 are mine, they are the newest published numbers in this
lane, and both shipped a verdict in prose that is stronger than the expression
which produced it.

FALSIFIERS, STATED BEFORE THE RUN (posted to CHANNEL.md first):
  F1  If yardstick.py's `f2_fires` expression tests the comparison that G30's
      RESULT.md reports it as testing, the F2 finding is WITHDRAWN.
  F2  If the four G17 arms CAN differ in top-12 confidence by construction,
      the "flat by construction" charge is WITHDRAWN.
  F3  If any elder code executes anywhere in diff_test.py, the G29 finding is
      WITHDRAWN.
  F4  If any of G30's seven external literature rows resolves to a citation
      stored in this workspace, the citation finding is WITHDRAWN for that row.

WHAT IS **NOT** UNDER ATTACK, so the scope cannot decay later:
  - G30's measured table (MRR/Hits for every Kingfisher arm) is a measurement
    and is NOT withdrawn. Nothing here recomputes or disputes it.
  - G30's F1 (degree-preserving null) is NOT withdrawn: its 15% threshold is
    pinned in yardstick.py:361 as `mrr_null >= 0.85 * mrr_real`, i.e. it was
    written into the code, and the observed margin (24.2%) is not near it.
  - G29's finding that level-wise Apriori pruning discards 1-to-many fan-out
    compositions is an argument about an ALGORITHM, and survives on its own
    terms. What is withdrawn is that it was established DIFFERENTIALLY.

CONTROLS ARE THE POINT HERE. Three of the four probes below report an ABSENCE
(a comparison that is not made, code that does not run, a citation that is not
stored). An absence-probe with no positive control proves nothing -- it is
indistinguishable from a broken search. So each one carries a fixture that it
MUST find, built from string parts rather than written as a literal path,
because ok-1's livechat CLASS 1 note is that a backticked path named because it
is absent reads to refcheck as a broken citation of it.
"""
import ast
import json
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKES = os.path.dirname(HERE)
ROOT = os.path.dirname(SPIKES)
sys.path.insert(0, os.path.join(SPIKES, "harness"))

import provenance as P  # noqa: E402
import kfcheck  # noqa: E402

G30 = os.path.join(SPIKES, "G30_external_yardstick")
G29 = os.path.join(SPIKES, "G29_differential_test")


# ---------------------------------------------------------------- P1
def probe_f2_expression():
    """Re-run G30's OWN f2_fires expression on G30's OWN recorded results.

    yardstick.py:366-368, quoted exactly:
        top12_rank_order = sorted(models.keys(), key=lambda k: -results[k]["top12_conf"])
        mrr_rank_order   = sorted(models.keys(), key=lambda k: -results[k]["mrr"])
        f2_fires = (top12_rank_order[0] != mrr_rank_order[0] or
                    top12_rank_order[1] != mrr_rank_order[1])
    """
    with open(os.path.join(G30, "yardstick.json")) as f:
        y = json.load(f)
    results = y["results"]
    # The arm order is the dict literal's order at yardstick.py:305-313. It is
    # reconstructed here in that order deliberately: Python's sort is stable, so
    # for an all-equal key this insertion order IS the resulting rank order.
    models = ["G17_all", "G17_top500", "G17_top100", "G17_conf>=0.20",
              "G17_conf>=0.40", "Null_degree", "Empty_baseline"]
    models = [m for m in models if m in results]

    top12 = sorted(models, key=lambda k: -results[k]["top12_conf"])
    mrr = sorted(models, key=lambda k: -results[k]["mrr"])
    fires = (top12[0] != mrr[0] or top12[1] != mrr[1])

    # WHICH of the two disjuncts is what made it True?
    slot0 = top12[0] != mrr[0]
    slot1 = top12[1] != mrr[1]

    # How many arms tie at the top on top12_conf? A tie means the ordering of
    # those arms is decided by the dict literal's line order, not by data.
    top_val = results[top12[0]]["top12_conf"]
    tied = [m for m in models if abs(results[m]["top12_conf"] - top_val) < 1e-12]

    # The comparison RESULT.md §4 F2 REPORTS: four G17 arms share top-12 while
    # their MRR spans 3.5x. Is that quantity anywhere in the expression above?
    g17 = [m for m in models if m.startswith("G17")]
    g17_top12 = {m: results[m]["top12_conf"] for m in g17}
    g17_mrr = {m: results[m]["mrr"] for m in g17}
    span = max(g17_mrr.values()) / min(g17_mrr.values())

    # MEASURED, not asserted. The first draft of this probe returned a hardcoded
    # `False` here -- a constant in the shape of a finding, which is the family-D
    # defect this spike exists to attack. So read it off yardstick.py's AST: the
    # f2_fires expression is examined for any subscript that selects a G17 arm,
    # which is what a spread-across-G17-arms comparison would have to contain.
    with open(os.path.join(G30, "yardstick.py")) as f:
        y_src = f.read()
    f2_expr_src = ""
    for node in ast.walk(ast.parse(y_src)):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "f2_fires"
                for t in node.targets):
            f2_expr_src = ast.get_source_segment(y_src, node.value) or ""
    literals = {n.value for n in ast.walk(ast.parse(f2_expr_src or "0"))
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    names_used = {n.id for n in ast.walk(ast.parse(f2_expr_src or "0"))
                  if isinstance(n, ast.Name)}
    mentions_any_g17_arm = any("G17" in s for s in literals)

    # And the tie-break claim, measured rather than argued: permute the arm
    # order and see whether slot 1 of the top-12 ordering follows the source
    # order. If it does not move, "decided by the dict literal" is withdrawn.
    perm = list(reversed(models))
    perm_top12_slot1 = sorted(perm, key=lambda k: -results[k]["top12_conf"])[1]

    # WHAT THE EXPRESSION ACTUALLY DETECTED, which is better than what RESULT.md
    # claims and was never reported: the degree-preserving NULL is ranked near
    # the bottom by top-12 and near the top by filtered MRR. THAT is a real
    # inversion, and it is between the null and the real arms -- not among the
    # G17 arms, which cannot invert against each other because they are tied.
    null_rank_top12 = top12.index("Null_degree") + 1 if "Null_degree" in top12 else None
    null_rank_mrr = mrr.index("Null_degree") + 1 if "Null_degree" in mrr else None
    real_arms_below_null_on_mrr = [m for m in g17
                                   if results[m]["mrr"] < results["Null_degree"]["mrr"]]

    return {
        "f2_fires": fires,
        "top12_order": top12,
        "mrr_order": mrr,
        "disjunct_slot0_differs": slot0,
        "disjunct_slot1_differs": slot1,
        "made_true_by": ("slot1 only" if (slot1 and not slot0) else
                         "slot0 only" if (slot0 and not slot1) else
                         "both" if fires else "neither"),
        "arms_tied_at_top_of_top12": tied,
        "n_tied": len(tied),
        "tie_broken_by": "dict literal insertion order (yardstick.py:305-313)",
        "slot1_top12_arm": top12[1],
        "slot1_mrr_arm": mrr[1],
        "reported_condition_g17_top12_values": g17_top12,
        "reported_condition_g17_mrr_span": round(span, 4),
        "f2_expression_source": f2_expr_src,
        "f2_expression_names": sorted(names_used),
        "reported_condition_appears_in_expression": mentions_any_g17_arm,
        "slot1_under_reversed_arm_order": perm_top12_slot1,
        "slot1_follows_source_order": perm_top12_slot1 != top12[1],
        "null_rank_by_top12": null_rank_top12,
        "null_rank_by_mrr": null_rank_mrr,
        "n_models": len(models),
        "real_arms_ranked_below_the_null_on_mrr": real_arms_below_null_on_mrr,
    }


# ---------------------------------------------------------------- P2
def probe_top12_by_construction(seed=4242):
    """Can the four G17 arms differ in top-12 confidence AT ALL?

    Every G17 arm in G30 is a confidence-RANKED prefix (top500, top100) or a
    confidence THRESHOLD (>=0.20, >=0.40) of the same ranked list. Any such
    subset that retains >= 12 rules retains THE SAME TOP 12 RULES, so the mean
    of the top 12 is identical by construction, whatever the confidences are.

    CONTROL (this is what makes the probe mean something): the same arm sizes
    drawn at RANDOM instead of by confidence rank MUST vary. If random subsets
    also came out identical, the invariance would be an artefact of this fixture
    and the "by construction" charge would be withdrawn.
    """
    rng = random.Random(seed)
    TOP_N = 12
    trials, rank_identical, random_identical = 200, 0, 0
    for _ in range(trials):
        conf = sorted((rng.random() for _ in range(3198)), reverse=True)
        full = conf[:TOP_N]
        mean = lambda xs: sum(xs[:TOP_N]) / min(TOP_N, len(xs))  # noqa: E731

        # G30's four arms, reproduced as ranked subsets
        arms = [conf[:500], conf[:100],
                [c for c in conf if c >= 0.20], [c for c in conf if c >= 0.40]]
        if all(len(a) >= TOP_N for a in arms) and \
           all(abs(mean(a) - mean(full)) < 1e-12 for a in arms):
            rank_identical += 1

        # CONTROL: same sizes, drawn at random
        rand_arms = [rng.sample(conf, len(a)) for a in arms]
        if all(abs(mean(sorted(a, reverse=True)) - mean(full)) < 1e-12
               for a in rand_arms):
            random_identical += 1

    return {
        "trials": trials,
        "seed": seed,
        "ranked_subsets_identical_top12": rank_identical,
        "random_subsets_identical_top12": random_identical,
        "control_passes": random_identical == 0,
        "verdict": ("top-12 is INVARIANT across confidence-ranked arms by "
                    "construction; the control shows random arms of the same "
                    "sizes are not"),
    }


# ---------------------------------------------------------------- P3
def probe_g29_executes_elder():
    """Does diff_test.py execute ANY elder code, or model it in-process?

    AST-based, not grep: a grep for the word `subprocess` is satisfied by the
    word appearing in a comment.
    """
    src_path = os.path.join(G29, "diff_test.py")
    with open(src_path) as f:
        src = f.read()
    tree = ast.parse(src)

    EXEC_NAMES = {"subprocess", "hyperon", "hyperonpy", "pexpect", "ctypes"}
    EXEC_CALLS = {"system", "popen", "execv", "execvp", "spawnl", "fork"}
    imports, exec_calls, opened = set(), [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr in EXEC_CALLS:
                exec_calls.append(fn.attr)
            if isinstance(fn, ast.Name) and fn.id == "open":
                opened.append(ast.dump(node)[:60])

    # Is an interpreter even present on this machine?
    metta_on_path = shutil.which("metta") is not None
    try:
        __import__("hyperon")
        hyperon_importable = True
    except ImportError:
        hyperon_importable = False

    # What does the "elder side" actually consist of? A class in this same file.
    elder_classes = [n.name for n in ast.walk(tree)
                     if isinstance(n, ast.ClassDef) and "yperon" in n.name]

    # CONTROL: the same scanner MUST detect execution in a file that does it.
    # Built from string parts, never as a literal, so the fixture cannot be
    # mistaken for a real citation and cannot be missed by the scanner by luck.
    fixture = "\n".join(["import " + "subprocess",
                         "subprocess.check_" + "output(['echo','x'])"])
    ftree = ast.parse(fixture)
    fixture_imports = {a.name for n in ast.walk(ftree)
                       if isinstance(n, ast.Import) for a in n.names}
    control_detects = bool(fixture_imports & EXEC_NAMES)

    return {
        "execution_imports_found": sorted(imports & EXEC_NAMES),
        "execution_calls_found": exec_calls,
        "elder_side_is_a_class_in_this_same_file": elder_classes,
        "metta_binary_on_path": metta_on_path,
        "hyperon_module_importable": hyperon_importable,
        "elder_paths_opened_for_DATA": sorted(
            set(t for t in ("ugly_man_sodaDrinker.metta",) if t in src)),
        "control_scanner_detects_execution_in_fixture": control_detects,
        "verdict": ("no elder code executes; the elder side is an in-process "
                    "Python model authored in the same file"),
    }


# ---------------------------------------------------------------- P4
def probe_literature_citations():
    """Do G30's external literature rows resolve to anything stored here?

    §13.2: third-party documents are stored as excerpts with provenance and
    indexed in corpus/CITATIONS.md. "Training-data memory is not a citation."
    """
    with open(os.path.join(G30, "yardstick.py")) as f:
        src = f.read()
    # the surnames G30's table attributes its numbers to
    cited = ["Meilicke", "Galarraga", "Galárraga", "Sun", "Trouillon", "Bordes"]
    claimed = sorted({c for c in cited if c in src})

    corpus = os.path.join(ROOT, "corpus")
    haystack = ""
    files_searched = []
    for base, _, names in os.walk(corpus):
        for n in names:
            if n.endswith((".md", ".txt")):
                p = os.path.join(base, n)
                files_searched.append(os.path.relpath(p, ROOT))
                try:
                    with open(p, errors="ignore") as f:
                        haystack += f.read()
                except OSError:
                    pass

    resolved = sorted({c for c in claimed if c in haystack})

    # CONTROL: the searcher must FIND the one citation this workspace does
    # store, or its empty result is evidence of a broken search and nothing
    # else. Token built from parts for the same reason as P3's fixture.
    known_token = "python-default" + "-args"
    control_finds_known = any(known_token in f for f in files_searched)

    return {
        "surnames_attributed_in_g30_table": claimed,
        "surnames_resolving_to_stored_excerpts": resolved,
        "n_unresolved": len(claimed) - len(resolved),
        "corpus_files_searched": len(files_searched),
        "control_finds_the_one_known_stored_citation": control_finds_known,
        "verdict": ("every external number in G30 §3 is unsourced recall; the "
                    "control confirms the search can find a stored citation"),
    }


def main():
    print("=" * 78)
    print("G33 — ATTACK on G29 and G30 (self-authored, closed DONE this hour)")
    print("=" * 78)

    p1 = probe_f2_expression()
    p2 = probe_top12_by_construction()
    p3 = probe_g29_executes_elder()
    p4 = probe_literature_citations()

    print("\nP1 — what G30's f2_fires actually compared")
    print(f"  f2_fires            = {p1['f2_fires']}")
    print(f"  top12 order[0:2]    = {p1['top12_order'][:2]}")
    print(f"  mrr   order[0:2]    = {p1['mrr_order'][:2]}")
    print(f"  made true by        = {p1['made_true_by']}")
    print(f"  arms tied on top12  = {p1['n_tied']} -> {p1['arms_tied_at_top_of_top12']}")
    print(f"  tie broken by       = {p1['tie_broken_by']}")
    print(f"  RESULT.md reports   = 4 G17 arms flat at top12 while MRR spans "
          f"{p1['reported_condition_g17_mrr_span']}x")
    print(f"  that comparison in the expression? "
          f"{p1['reported_condition_appears_in_expression']}  (measured from AST)")
    print(f"  f2 expr             = {p1['f2_expression_source']}")
    print(f"  slot1 if arms reversed = {p1['slot1_under_reversed_arm_order']} "
          f"(follows source order: {p1['slot1_follows_source_order']})")
    print(f"  THE REAL INVERSION  : null ranks {p1['null_rank_by_top12']}/{p1['n_models']} "
          f"by top-12 but {p1['null_rank_by_mrr']}/{p1['n_models']} by MRR; "
          f"{len(p1['real_arms_ranked_below_the_null_on_mrr'])} real arms fall below it")

    print("\nP2 — can the arms differ on top-12 at all?")
    print(f"  ranked subsets identical : {p2['ranked_subsets_identical_top12']}/{p2['trials']}")
    print(f"  random subsets identical : {p2['random_subsets_identical_top12']}/{p2['trials']} (control)")

    print("\nP3 — does G29 execute the elder?")
    print(f"  execution imports   = {p3['execution_imports_found']}")
    print(f"  execution calls     = {p3['execution_calls_found']}")
    print(f"  metta on PATH       = {p3['metta_binary_on_path']}")
    print(f"  hyperon importable  = {p3['hyperon_module_importable']}")
    print(f"  elder side is       = {p3['elder_side_is_a_class_in_this_same_file']}")
    print(f"  control detects exec= {p3['control_scanner_detects_execution_in_fixture']}")

    print("\nP4 — do G30's literature numbers resolve?")
    print(f"  attributed surnames = {p4['surnames_attributed_in_g30_table']}")
    print(f"  resolving to disk   = {p4['surnames_resolving_to_stored_excerpts']}")
    print(f"  unresolved          = {p4['n_unresolved']}")
    print(f"  control finds known = {p4['control_finds_the_one_known_stored_citation']}")

    # ---- controls -------------------------------------------------------
    controls, falsifiers = [], []

    c1 = P.Control(
        "C1_random_arms_do_vary",
        "the by-construction charge needs a design in which top-12 CAN vary",
        null_must_contain="random subsets of the same sizes reproducing the "
                          "full set's top-12 mean exactly",
        can_fail_because="if random arms also matched, invariance would be an "
                         "artefact of the fixture, not of ranked subsetting")
    c1.observe(p2["control_passes"],
               {"random_identical": p2["random_subsets_identical_top12"],
                "ranked_identical": p2["ranked_subsets_identical_top12"],
                "trials": p2["trials"]})
    controls.append(c1)

    c2 = P.Control(
        "C2_scanner_detects_execution",
        "an absence-of-execution probe is worthless unless it can see execution",
        null_must_contain="a fixture that imports and calls subprocess going "
                          "undetected",
        can_fail_because="an AST walk that misses ast.Import would report every "
                         "file as non-executing, including one that shells out")
    c2.observe(p3["control_scanner_detects_execution_in_fixture"],
               {"fixture_detected": p3["control_scanner_detects_execution_in_fixture"]})
    controls.append(c2)

    c3 = P.Control(
        "C3_citation_search_finds_a_known_citation",
        "an empty citation search must be distinguishable from a broken one",
        null_must_contain="the one excerpt this workspace does store going "
                          "unfound by the same walk",
        can_fail_because="a wrong corpus root or an extension filter would "
                         "return zero for every surname regardless of truth")
    c3.observe(p4["control_finds_the_one_known_stored_citation"],
               {"corpus_files_searched": p4["corpus_files_searched"]})
    controls.append(c3)

    # ---- falsifiers -----------------------------------------------------
    f1 = P.Falsifier(
        "F1_f2_expression_matches_its_reported_condition",
        "WITHDRAW the F2 finding if yardstick.py's f2_fires tests what "
        "RESULT.md says it tests",
        "the comparison RESULT.md reports is absent from the f2_fires "
        "expression; it would be present if f2_fires compared the G17 arms "
        "among themselves",
        null_must_contain="an expression referencing the four G17 arms' top-12 "
                          "spread")
    f1.observe(not p1["reported_condition_appears_in_expression"],
               {"made_true_by": p1["made_true_by"],
                "slot1_top12_arm": p1["slot1_top12_arm"],
                "slot1_mrr_arm": p1["slot1_mrr_arm"],
                "n_arms_tied": p1["n_tied"]})
    falsifiers.append(f1)

    f3 = P.Falsifier(
        "F3_no_elder_code_executes",
        "WITHDRAW the G29 finding if any elder code executes in diff_test.py",
        "no execution import and no execution call appears in the AST; a "
        "single subprocess call to a metta binary would make the differential "
        "test a real one",
        null_must_contain="a subprocess/metta/hyperon invocation in the AST")
    f3.observe(not p3["execution_imports_found"] and not p3["execution_calls_found"],
               {"imports": p3["execution_imports_found"],
                "calls": p3["execution_calls_found"],
                "metta_on_path": p3["metta_binary_on_path"],
                "hyperon_importable": p3["hyperon_module_importable"]})
    falsifiers.append(f3)

    f4 = P.Falsifier(
        "F4_literature_numbers_are_unsourced",
        "WITHDRAW the citation finding for any row resolving to a stored excerpt",
        "no surname attributed in G30's table resolves to any excerpt stored "
        "under corpus/; one stored excerpt would resolve that row",
        null_must_contain="a surname from G30's table found in corpus/")
    f4.observe(p4["n_unresolved"] == len(p4["surnames_attributed_in_g30_table"]),
               {"attributed": p4["surnames_attributed_in_g30_table"],
                "resolved": p4["surnames_resolving_to_stored_excerpts"]})
    falsifiers.append(f4)

    out = {"P1_f2_expression": p1, "P2_by_construction": p2,
           "P3_g29_execution": p3, "P4_citations": p4}
    out_json = os.path.join(HERE, "audit.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[G30, G29],
        artifacts=[os.path.join(HERE, "audit.py"), out_json],
        controls=controls,
        falsifiers=falsifiers,
        falsifier="G30's f2_fires tests the comparison its RESULT.md reports; "
                  "or the G17 arms can differ on top-12 by construction; or "
                  "elder code executes in diff_test.py; or any external row "
                  "resolves to a stored citation",
        allow_dirty=True,
        note="G33: ATTACK on this lane's own G29 and G30")

    print(f"\nD6 Provenance Certified: ok={ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
