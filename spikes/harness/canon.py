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
    print('canon: 12 assertions pass')


if __name__ == '__main__':
    demo()
