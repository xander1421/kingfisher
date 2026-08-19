#!/usr/bin/env python3
"""constcheck.py v2 — H201. A control whose VERDICT is a literal cannot fail.

THE DEFECT MEASURED
-------------------
`provenance.Control` refuses a control with no `can_fail_because` prose, and
`record()` refuses a control that did not fire. Neither can see the case where
the verdict handed to `observe()` is a CONSTANT WRITTEN IN THE SOURCE:

    c3_ok = True                                   # S91/run.py:242
    ...
    controls[2].observe(c3_ok, {"f001": PIN_F001, "f002": PIN_F002})

on a Control declaring `can_fail_because="pin drift"`. No input to that program
makes `c3_ok` anything but `True`. It fired, `certify` recorded `ok=True`, and
the claim it stands behind is *"F001 and F002 pins remain invariant"*.

AND THE GUARD THAT EXISTS FOR THIS DOES NOT REACH IT
-----------------------------------------------------
`Control.observe` already flags constant observations -- *"a control whose
observations are all identical distinguished nothing"* -- but only when
`len(values) > 1` and every value is equal. Measured:

    observe(True, {"f001": ..., "f002": ...})  ->  constant = False
    observe(True, [True])                      ->  constant = False
    observe(True, [1, 1, 1])                   ->  constant = True

So a dead control with a rich-looking observation dict reads as a healthy one.
The flag inspects the OBSERVATIONS; the defect is in the VERDICT.

AST OVER SOURCE, NOT A VALUE HEURISTIC, AND THAT IS THE WHOLE DESIGN
---------------------------------------------------------------------
This flags a `.observe(` call whose FIRST POSITIONAL ARGUMENT is a literal
constant. That is decidable with zero false positives by construction: a literal
is a literal. It is deliberately narrower than "the value looked constant at
runtime", because

    c1.observe(len(ROSTER) == 5, {"n_seats": len(ROSTER)})

is DERIVED -- it would have come out False on a different roster -- and flagging
it would make this checker the thing it is auditing.

v2 ALSO resolves a NAME bound exactly once, in the same scope, to a literal --
which is S91's actual form (`c3_ok = True`) and which v1 could not see. The bound
is what keeps it free of false positives: one binding, constant right-hand side,
and any other binding of that name disqualifies it. See the v2 block below; that
gap is the defect v2 removes.

EXCLUSIONS ARE PRINTED, NEVER IMPLIED
--------------------------------------
H188's `class_sweep.py` v1 printed `0 vendored tree(s) skipped` while excluding
80 hits -- family B in the tool written about family B. Every skipped tree is
named in the output and counted.

REPORTS, DOES NOT GATE. Changing `certify` to REFUSE this would retro-refuse
records already on disk across six lanes, which is H14's shape: a gate a
non-author trips and cannot clear is the one everybody learns to bypass.

    python3 constcheck.py              report; exit 1 if any LIVE literal verdict
    python3 constcheck.py --selfcheck  both directions, on synthetic source

==== v2, 2026-08-19, ATOM-3 — TWO DEFECTS, BOTH IN v1, BOTH FOUND BY RUNNING IT

**D1 — v1 COULD NOT SEE THE INSTANCE THAT MOTIVATED THE ROW.** v1 flagged a
`.observe(` whose first argument is a `Constant`. S91 writes

    c3_ok = True
    controls[2].observe(c3_ok, {...})

so the argument is a `Name` and v1's tree-wide sweep returned 23 hits with **S91
not among them**. A detector that misses its own motivating case is the class it
was written to report, and v1's own header argued the gap was a design virtue --
which is how a scope narrows itself green (H26b). v2 resolves a name bound
EXACTLY ONCE in the scope to a literal, and nothing more.

**D2 — 11 OF v1's 23 HITS WERE FIXTURES AND IT COUNTED THEM AS DEFECTS.**
`provenance.py`'s own `demo()` builds `c_dead.observe(False, ...)` deliberately,
to prove `record()` refuses a control that did not fire. Reporting that as a
defect is this module reporting the test written for the thing it reports, and
a checker red on its own fixtures is one everybody learns to ignore (H14). v2
splits on the ENCLOSING FUNCTION CHAIN -- `demo` / `selfcheck` -- which is
mechanical and about where the code sits, not a file name list. Only LIVE hits
set the exit code; fixtures are printed and counted separately, never hidden.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

# Trees that are not this fleet's evidence. NAMED, and the count is printed.
SKIP_DIRS = ('elders', '.venv', '__pycache__', 'target', 'node_modules', '.git',
             '.scratch')   # gitignored scratch is not this fleet's evidence (H89)


def _scopes(tree):
    """[(scope_node, chain_of_enclosing_function_names)] — module first."""
    out = [(tree, [])]

    def rec(node, chain):
        for c in ast.iter_child_nodes(node):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ch = chain + [c.name]
                out.append((c, ch))
                rec(c, ch)
            else:
                rec(c, chain)
    rec(tree, [])
    return out


def _single_constant_bindings(scope):
    """{name: literal} for names bound EXACTLY ONCE in this scope, to a constant.

    This is the S91 form and it is why v1 missed its own motivating case:

        c3_ok = True
        controls[2].observe(c3_ok, {...})

    `c3_ok` is a Name, so a first-argument-is-Constant test does not see it.
    BOUNDED ON PURPOSE, and the bound is the whole reason it has no false
    positives: ONE binding, whose right-hand side is a literal, and any other
    binding of that name in the scope (augmented assignment, loop target, `with
    ... as`, walrus, `global`) disqualifies it. That is not dataflow analysis --
    it is "this name is a constant in this scope, by construction". A verdict
    assembled from two literals, or rebound in a branch, is deliberately OUT of
    scope: a half-done dataflow that misses the interesting cases while
    reporting a number is the shape this module exists to report.
    """
    stores, assigned = {}, {}
    for n in ast.walk(scope):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not scope:
            continue
        if isinstance(n, ast.Global) or isinstance(n, ast.Nonlocal):
            for nm in n.names:
                stores[nm] = stores.get(nm, 0) + 99
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            stores[n.id] = stores.get(n.id, 0) + 1
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.Constant):
            assigned[n.targets[0].id] = n.value.value
    return {k: v for k, v in assigned.items() if stores.get(k) == 1}


def literal_verdicts(src, path=None):
    """[(line, receiver, literal, chain)] for `.observe(<literal>, ...)`.

    `chain` is the enclosing function names, so a control DELIBERATELY built
    dead inside a `demo()` or `selfcheck()` is separable from one in a live run
    path. That distinction is mechanical -- where the code sits -- not a file
    name list, because a name list narrows itself green the next time somebody
    adds a module (H26b).
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None                      # unparseable is its own state, not clean
    out = []
    for scope, chain in _scopes(tree):
        consts = _single_constant_bindings(scope)
        for node in ast.walk(scope):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if not (isinstance(f, ast.Attribute) and f.attr == 'observe'):
                continue
            if not node.args:
                continue
            a0 = node.args[0]
            lit = None
            if isinstance(a0, ast.Constant):
                lit = repr(a0.value)
            elif isinstance(a0, ast.Name) and a0.id in consts:
                lit = f'{a0.id}={consts[a0.id]!r}'
            if lit is None:
                continue
            recv = ast.unparse(f.value) if hasattr(ast, 'unparse') else '?'
            rec = (node.lineno, recv, lit, tuple(chain))
            if rec not in out:
                out.append(rec)
    # one scope may be walked by an outer scope too; keep the DEEPEST chain
    best = {}
    for line, recv, lit, chain in out:
        k = (line, recv, lit)
        if k not in best or len(chain) > len(best[k]):
            best[k] = chain
    return sorted((l, r, v, best[(l, r, v)]) for (l, r, v) in best)


FIXTURE_FUNCS = ('demo', 'selfcheck')


def is_fixture(chain):
    """A control built dead ON PURPOSE inside a demo/selfcheck is not a defect.

    `provenance.py`'s own `demo()` constructs `c_dead.observe(False, ...)` to
    prove `record()` refuses it -- flagging that would make this module report
    the test written for the thing it reports.
    """
    return any(c in FIXTURE_FUNCS for c in chain)


def scan(root):
    live, fixture, skipped, unparseable, files = [], [], set(), [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        for d in list(dirnames):
            if d in SKIP_DIRS:
                skipped.add(os.path.relpath(os.path.join(dirpath, d), root))
                dirnames.remove(d)
        for fn in filenames:
            if not fn.endswith('.py'):
                continue
            p = os.path.join(dirpath, fn)
            files += 1
            try:
                src = open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            if '.observe(' not in src:
                continue
            res = literal_verdicts(src)
            if res is None:
                unparseable.append(os.path.relpath(p, root))
                continue
            rel = os.path.relpath(p, root)
            for line, recv, lit, chain in res:
                row = (rel, line, recv, lit, '/'.join(chain) or '<module>')
                (fixture if is_fixture(chain) else live).append(row)
    return live, fixture, sorted(skipped), unparseable, files


def main():
    live, fixture, skipped, unparseable, files = scan(ROOT)
    for path, line, recv, lit, where in sorted(live):
        print(f'  LITERAL VERDICT  {path}:{line}  {recv}.observe({lit}, ...)  in {where}')
    for path, line, recv, lit, where in sorted(fixture):
        print(f'  fixture          {path}:{line}  {recv}.observe({lit}, ...)  in {where}')
    for p in unparseable:
        print(f'  UNPARSEABLE      {p} -- not scanned, and not scored clean')
    print(f'\nconstcheck: {files} .py file(s) scanned · {len(live)} LIVE literal '
          f'verdict(s) · {len(fixture)} fixture(s) in demo/selfcheck · '
          f'{len(unparseable)} unparseable · {len(skipped)} tree(s) skipped')
    if skipped:
        print(f'  skipped trees are NAMED, never implied — run with --list-skipped '
              f'for all {len(skipped)}')
        if '--list-skipped' in sys.argv:
            for x in skipped:
                print(f'    {x}')
    if not files:
        print('REFUSE: no .py files scanned at all -- reporting 0 from an empty '
              'scan is the H30 shape.')
        return 2
    if live:
        print('\nA control whose verdict is a literal cannot fail, whatever its\n'
              '`can_fail_because` says (A15). Owners, not me. REPORT ONLY: making\n'
              '`certify` refuse this would retro-refuse records already on disk.\n'
              'Fixtures above are controls built dead ON PURPOSE inside demo() or\n'
              'selfcheck() and are NOT defects; they are printed, never hidden.')
        return 1
    return 0


def selfcheck():
    """Both directions on synthetic source: a literal verdict is caught, and a
    DERIVED one that merely evaluates to a constant is NOT."""
    ok = True

    def one(src, want, why):
        nonlocal ok
        got = literal_verdicts(src)
        if (len(got) if got else 0) != want:
            print(f'SELFCHECK FAILED: {why} -- want {want}, got {got}')
            ok = False
        return got

    one('c.observe(True, {"a": 1})\n', 1, 'a literal verdict must be caught')

    # THE ARM THAT MATTERS. `len(R) == 5` is derived: a different roster gives
    # False. Flagging it would make this module the thing it audits, and it is
    # the arm that fails first if anyone "improves" this into a value heuristic.
    one('R = [1, 2, 3, 4, 5]\nc.observe(len(R) == 5, {"n": len(R)})\n', 0,
        'a DERIVED verdict must not be flagged')

    # A constant in a LATER argument is not a verdict. Observations are allowed
    # to be constants -- that is what `Control.observe`'s own flag is for.
    one('c.observe(x > 0, True)\n', 0, 'only the FIRST argument is the verdict')

    # S91'S ACTUAL FORM, and the one v1 missed entirely.
    got = one('def main():\n    c3_ok = True\n    ctl[2].observe(c3_ok, {"a": 1})\n',
              1, 'a name bound once to a literal is S91\'s form and must be caught')
    if got and 'c3_ok=True' not in got[0][2]:
        print(f'SELFCHECK FAILED: the resolved binding must be reported, got {got}')
        ok = False

    # REBOUND is out of scope BY DESIGN -- two bindings means the value is not a
    # constant by construction, and guessing which one wins is the dataflow this
    # deliberately does not do.
    one('def m():\n    v = True\n    if x: v = False\n    c.observe(v, {})\n', 0,
        'a REBOUND name must not be flagged')

    # Fixture separation, both directions.
    got = literal_verdicts('def demo():\n    c.observe(False, [1])\n')
    if not got or not is_fixture(got[0][3]):
        print(f'SELFCHECK FAILED: a verdict inside demo() must read as a fixture, got {got}')
        ok = False
    got = literal_verdicts('def main():\n    c.observe(False, [1])\n')
    if not got or is_fixture(got[0][3]):
        print(f'SELFCHECK FAILED: a verdict inside main() must NOT read as a fixture, got {got}')
        ok = False
    # NESTED inside demo() counts too -- provenance.py's `_c` helper is exactly this.
    got = literal_verdicts('def demo():\n    def _c():\n        c.observe(True, [1])\n')
    if not got or not is_fixture(got[0][3]):
        print(f'SELFCHECK FAILED: nested inside demo() must read as a fixture, got {got}')
        ok = False

    # Unparseable source is its own state and must never come back as "clean".
    if literal_verdicts('def (\n') is not None:
        print('SELFCHECK FAILED: unparseable source must return None, not []')
        ok = False

    # The real tree must be reachable and non-empty, or the report above is an
    # empty scan wearing a clean bill.
    _l, _f, _s, _u, files = scan(ROOT)
    if files < 50:
        print(f'SELFCHECK FAILED: only {files} .py files scanned -- the sweep is '
              f'not reaching this repo')
        ok = False

    print('constcheck --selfcheck: ok' if ok else 'constcheck --selfcheck: FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
