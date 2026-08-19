#!/usr/bin/env python3
"""vocabcheck.py v1 — H252. The Stop hook's accepted vocabulary against the
CONTRACT's, read out of two different documents.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **every check on the loop's exit vocabulary read both of its sets
out of ONE FILE.** `test_loop_gate.sh`'s H23 block compares the hook's refusal
MESSAGE against the hook's ACCEPT BRANCH -- both in `.claude/hooks/loop_gate.sh` --
so a rename applied to the pair together reports `equal`, and the hook can drift
away from `MISSION_LOOP.md` §7 with every check green. ok-1 recorded that limit in
cycle 28 and carried it as a NEXT item for four cycles for one honest reason: it
was unmeasured whether §7's vocabulary is EXTRACTABLE at all. If it were not, the
only "cross-document" check buildable would compare the hook against a THIRD
hand-written copy of the same list -- which is not a second source, it is the same
assertion wearing a different filename.

MEASURED FIRST (`spikes/H252_two_documents/`): it is extractable, from one
sentence in §7 -- *"A legal exit requires writing exactly one of `LOOP-DONE`,
`LOOP-HALT`, `LOOP-IDLE`"* -- and the hook's accept set is extractable from its
`case` pattern. So the check compares a CONTRACT sentence with an IMPLEMENTATION
branch, and a rename in either one alone goes red.

WHAT THIS DOES NOT CLAIM. A rename applied CONSISTENTLY to both documents stays
green, and that is correct: this check asserts that the implementation matches the
contract, not that the contract is wise. Nothing here can catch a fleet that
renames its own exit signal in both places -- that is a review question.

`LOOP-FUSE` IS EXCLUDED BY CONSTRUCTION, and the reason is the row it comes from:
§7 says it "is written by the hook itself, not by the agent", so it belongs to the
hook's WRITE vocabulary and not to the set an agent may write into
`.loop_signal.$CALLSIGN`. A check that folded it in would demand the hook accept a
marker the contract forbids the agent to send.

usage:
  python3 spikes/harness/vocabcheck.py [--contract PATH] [--hook PATH]
  python3 spikes/harness/vocabcheck.py --selfcheck
"""
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTRACT = os.path.join(ROOT, "MISSION_LOOP.md")
HOOK = os.path.join(ROOT, ".claude", "hooks", "loop_gate.sh")

MARKER = re.compile(r"LOOP-[A-Z]+")


def contract_markers(path):
    """The set an AGENT may write, from §7's own sentence.

    Anchored on "exactly one of", which is the contract's normative phrasing, not
    on the section number: renumbering a section is routine here (§13 was a second
    §9 until 2026-08-17) and a check keyed to the number would go red on a
    renumber, which is the noisy failure that gets a check deleted.
    """
    text = open(path).read()
    m = re.search(r"exactly one of(.{0,200})", text, re.S)
    if not m:
        return set(), "no 'exactly one of' sentence found"
    line = text[: m.start()].count("\n") + 1
    return set(MARKER.findall(m.group(1))), f"{os.path.basename(path)}:{line}"


def hook_markers(path):
    """The set the HOOK accepts, from its `case` pattern.

    A case pattern is `LOOP-A|LOOP-B|LOOP-C)` at the start of a branch. Comments
    are skipped: this hook's header quotes the same three markers in prose, and a
    check that read the prose would be reading one file's comment against another
    file's sentence -- two documents, still no implementation in the comparison.
    """
    out, where = set(), None
    for i, ln in enumerate(open(path), 1):
        s = ln.strip()
        if s.startswith("#"):
            continue
        if re.match(r"^\(?\s*LOOP-[A-Z]+(\s*\|\s*LOOP-[A-Z]+)*\s*\)", s):
            out |= set(MARKER.findall(s))
            where = f"{os.path.basename(path)}:{i}"
    return out, where or f"{os.path.basename(path)}:none"


def check(contract=CONTRACT, hook=HOOK, quiet=False):
    cset, cwhere = contract_markers(contract)
    hset, hwhere = hook_markers(hook)
    say = (lambda *a: None) if quiet else print
    say(f"contract {cwhere}: {sorted(cset) or 'NONE'}")
    say(f"hook     {hwhere}: {sorted(hset) or 'NONE'}")
    # AN EMPTY SET IS NOT AGREEMENT. Two empty sets compare equal, and that is
    # exactly what a refactor that moves either construct would produce: a green
    # check that has stopped reading anything (H178's shape).
    if len(cset) < 2 or len(hset) < 2:
        say("REFUSE: a vocabulary of fewer than two markers means the extraction "
            "stopped working, not that the loop grew simpler.")
        return 1
    if cset != hset:
        say(f"REFUSE: contract-only {sorted(cset - hset)}, hook-only {sorted(hset - cset)}")
        return 1
    say(f"vocabcheck: {len(cset)} markers, contract and hook agree")
    return 0


def selfcheck():
    """Two-sided, and each mutation asserts THAT IT APPLIED (H217)."""
    ok = fail = 0

    def ck(name, cond):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  PASS  {name}")
        else:
            fail += 1
            print(f"  FAIL  {name}")

    ck("green on the shipped pair", check(quiet=True) == 0)
    with tempfile.TemporaryDirectory() as d:
        # rename in the HOOK only -- the case v1 of the H23 guard could not see
        hook_txt = open(HOOK).read()
        mutant = os.path.join(d, "hook_renamed.sh")
        new = hook_txt.replace("LOOP-IDLE", "LOOP-QUIET")
        ck("the hook mutation applied", new != hook_txt)
        open(mutant, "w").write(new)
        ck("a hook that renames a marker the contract still promises is RED",
           check(hook=mutant, quiet=True) == 1)
        # rename in the CONTRACT only -- the mirror case
        c_txt = open(CONTRACT).read()
        cmut = os.path.join(d, "contract_renamed.md")
        cnew = c_txt.replace("`LOOP-IDLE`", "`LOOP-QUIET`", 1)
        ck("the contract mutation applied", cnew != c_txt)
        open(cmut, "w").write(cnew)
        ck("a contract that renames a marker the hook still accepts is RED",
           check(contract=cmut, quiet=True) == 1)
        # the empty-extraction guard: a hook with no case pattern at all
        gutted = os.path.join(d, "hook_gutted.sh")
        gnew = re.sub(r"(?m)^(\s*)LOOP-[A-Z]+(\|LOOP-[A-Z]+)*\)", r"\1esac_removed)", hook_txt)
        ck("the gutting applied", gnew != hook_txt)
        open(gutted, "w").write(gnew)
        ck("an extraction that finds nothing REFUSES rather than reporting agreement",
           check(hook=gutted, quiet=True) == 1)
        # THE ANCHOR'S OWN FAILURE MODE. This check keys on the contract's phrase
        # "exactly one of"; reword that sentence and the extraction stops working.
        # It must REFUSE loudly rather than compare an empty set -- the risk F1
        # named, mitigated rather than argued away.
        reworded = os.path.join(d, "contract_reworded.md")
        rnew = c_txt.replace("exactly one of", "precisely one among", 1)
        ck("the rewording applied", rnew != c_txt)
        open(reworded, "w").write(rnew)
        ck("a contract whose anchor sentence is reworded REFUSES, not passes",
           check(contract=reworded, quiet=True) == 1)
    print(f"vocabcheck selfcheck: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    a = sys.argv
    kw = {}
    if "--contract" in a:
        kw["contract"] = a[a.index("--contract") + 1]
    if "--hook" in a:
        kw["hook"] = a[a.index("--hook") + 1]
    sys.exit(check(**kw))
