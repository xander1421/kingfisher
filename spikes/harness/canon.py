#!/usr/bin/env python3
"""Canonicalise MeTTa output before hashing.

M1.1c mechanism (2): `VariableAtom::name()` embeds the process-global
`NEXT_VARIABLE_ID`, and `Display` calls it, so a result carrying a data-origin
variable prints `$x#24605`. The number depends on how many variables the
process created earlier, so two honest devices disagree and result-hash
comparison -- the project's whole verification mechanism -- fails.

Fix at the comparison boundary rather than upstream: renumber variables by
FIRST APPEARANCE within the result.

Why not just strip the id: `($x#1 $x#2)` and `($x#1 $x#1)` are different
answers -- one has two distinct variables, the other one variable twice.
Stripping maps both to `($x $x)` and would make a wrong result compare equal to
a right one. In a verification system that is the worst possible failure, so
renumbering is used instead: it is injective on structure and invariant to
process history.
"""
import re

VARID = re.compile(r'\$([^\s()#]+)#(\d+)')


def canon(text: str) -> str:
    mapping, n = {}, [0]

    def sub(m):
        key = (m.group(1), m.group(2))
        if key not in mapping:
            n[0] += 1
            mapping[key] = n[0]
        return f'${m.group(1)}#{mapping[key]}'

    return VARID.sub(sub, text)


VARANY = re.compile(r'\$[^\s()]+')


def is_ground(text: str) -> bool:
    """True when a result set carries no free variables.

    This is the exact condition under which `canon_alpha` is LOSSLESS. Alpha
    discards which of the requester's variables landed where; that is vacuous
    while the variables are unbound and never read again, but it stops being
    vacuous the moment a result carrying free variables is fed into another
    query -- the match/add-atom/match shape of a self-modifying pass.

    Checkable per result at runtime, and cheaper than a static analysis of the
    program, so it is enforced rather than trusted.
    """
    return not VARANY.search(text)


class AlphaLossy(Exception):
    """Raised when alpha-canonicalisation would discard real information."""


def canon_alpha_strict(text: str) -> str:
    """`canon_alpha`, but refuses on a non-ground result instead of silently
    weakening the comparison. The failure this guards is silent, so it raises."""
    if not is_ground(text):
        raise AlphaLossy(
            'result carries free variables; alpha-canonicalisation is lossy here '
            '(it equates ($x $y) with ($y $x), which matters once a free '
            'variable is carried into another query)')
    return canon_alpha(text)


def canon_alpha(text: str) -> str:
    """Alpha-canonicalise: rename EVERY variable by first appearance.

    Mechanism 1 makes `(pair $z $z)` matched by `(pair $x $y)` return `($x $x)`
    or `($y $y)` depending on process history. Those two are **alpha-
    equivalent** -- the same term up to renaming -- so for result comparison
    they should be equal.

    Measured on device: every mechanism-1 case collapses to a single hash
    (A1 2->1, A2 3->1, A3/A4/D3/E2 all ->1) while the heap-address control
    stays at 40/40.

    OPT-IN, NOT DEFAULT. It is strictly stronger than `canon` and strictly
    riskier, because it changes the notion of equality rather than removing
    noise:
      - it discards the requester's own variable names;
      - it equates `($x $y)` with `($y $x)` -- alpha-equivalent as terms, but a
        different statement about which of the requester's variables landed
        where. Vacuous while both are unbound, which is why this is judged
        acceptable, but it IS a loss.
    Structure survives: `($x $y)` never equals `($x $x)`, and `($x $y $x)`
    never equals `($x $y $y)`.

    Default to `canon`, which only removes process history. Enable `canon_alpha`
    per job class, where alpha-equivalence is the intended semantics.
    """
    mapping, n = {}, [0]

    def sub(m):
        v = m.group(0)
        if v not in mapping:
            n[0] += 1
            mapping[v] = n[0]
        return f'$v{mapping[v]}'

    return VARANY.sub(sub, text)


def demo():
    # same structure, different process history -> identical after canon
    a = "((Frog $x#24605) (Green $x#24605))"
    b = "((Frog $x#99) (Green $x#99))"
    assert canon(a) == canon(b) == "((Frog $x#1) (Green $x#1))"

    # distinctness is PRESERVED -- this is the property stripping would destroy
    two = canon("($x#7 $x#9)")
    one = canon("($x#7 $x#7)")
    assert two == "($x#1 $x#2)" and one == "($x#1 $x#1)"
    assert two != one, 'two distinct variables must not collapse onto one'

    # order of first appearance defines the numbering
    assert canon("($b#5 $a#2 $b#5)") == "($b#1 $a#2 $b#1)"

    # different NAMES with the same id stay distinct
    assert canon("($a#3 $b#3)") == "($a#1 $b#2)"

    # ids absent -> untouched; non-variable '#' untouched
    assert canon("(pair A B)") == "(pair A B)"
    assert canon("($x $y)") == "($x $y)"
    assert canon("(tag #42)") == "(tag #42)"

    # a heap address is NOT a variable id and must survive: it is a real
    # divergence we still want a hash to expose
    addr = "GroundingSpace-0xb40000763c2352e8"
    assert canon(addr) == addr

    # idempotent
    assert canon(canon(a)) == canon(a)
    # --- alpha-canonicalisation, mechanism 1
    # the two divergent outcomes of an aliased match are alpha-equivalent
    assert canon_alpha("($x $x)") == canon_alpha("($y $y)") == "($v1 $v1)"
    # ...and the 3-way case
    assert canon_alpha("($w $w $w)") == canon_alpha("($x $x $x)")

    # NEGATIVE CONTROLS -- these must NOT collapse
    assert canon_alpha("($x $y)") != canon_alpha("($x $x)"), \
        'distinct variables must not equal a repeated variable'
    assert canon_alpha("($x $y)") == "($v1 $v2)"
    assert canon_alpha("(f $x $y)") != canon_alpha("(g $x $y)"), \
        'different functors must stay different'
    assert canon_alpha("($x A)") != canon_alpha("($x B)"), \
        'different ground terms must stay different'
    assert canon_alpha("($x $y $x)") != canon_alpha("($x $y $y)"), \
        'different repeat PATTERNS must stay different'
    # ordering of first appearance is what carries the structure
    assert canon_alpha("($b $a $b)") == "($v1 $v2 $v1)"
    # a heap address is still not a variable
    assert canon_alpha("GroundingSpace-0xdeadbeef") == "GroundingSpace-0xdeadbeef"
    # subsumes canon for id-bearing variables
    assert canon_alpha("((Frog $x#24605) (Green $x#24605))") == "((Frog $v1) (Green $v1))"
    assert canon_alpha(canon_alpha("($x $y)")) == canon_alpha("($x $y)")

    # --- DOCUMENTED INFORMATION LOSS, not a correctness claim.
    # alpha collapses a permutation of unbound variables. As terms these ARE
    # alpha-equivalent, but the requester distinguishes them positionally: a
    # device answering ($y $x) made a different statement about which of the
    # requester's variables landed where. Both are vacuous while unbound, so
    # this is judged acceptable -- but it is a real loss and it is why alpha is
    # OPT-IN per job class rather than the default.
    assert canon_alpha("($x $y)") == canon_alpha("($y $x)")

    # --- the losslessness condition, enforced
    assert is_ground("(at-risk B1 W1)")
    assert is_ground("((Frog A) (Green A))")
    assert not is_ground("($x $x)")
    assert not is_ground("((Frog $x#24605) (Green $x#24605))")
    assert not is_ground("(at-risk $x $y)")

    # ground results: alpha is a no-op, so it cannot lose anything
    for g in ("(at-risk B1 W1)", "(pair A B)", "3", "()"):
        assert canon_alpha(g) == g, g
        assert canon_alpha_strict(g) == g

    # non-ground: strict refuses rather than silently weakening
    for ng in ("($x $y)", "($x $x)", "((Frog $x#1))"):
        try:
            canon_alpha_strict(ng)
            raise AssertionError(f'should have refused: {ng}')
        except AlphaLossy:
            pass

    print('canon: 37 assertions pass '
          '(12 canon, 11 alpha, 1 documented loss, 13 ground-gate)')


if __name__ == '__main__':
    demo()
