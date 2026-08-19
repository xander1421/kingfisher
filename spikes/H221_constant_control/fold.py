#!/usr/bin/env python3
"""fold.py v2 — H221. A one-assignment-deep constant folder for control verdicts.

==== v2 — A MUTABLE CONSTANT IS NOT A CONSTANT ==============================
DEFECT REMOVED, found by hand-verifying 4 of v1's own 24 hits and not by any
check: `spikes/S26_cheat_attribution/cheat_attr.py:283` is
`c.observe(wt_keys == pinned_keys, …)` where both names are bound to `[]` at the
top of the function and then FILLED by `.append()` in a loop. v1 bound them to
the empty list and folded `[] == []` to True — a FALSE ACCUSATION against
another lane's spike, which this module's own docstring calls the expensive
error here. `wt_keys.append(x)` stores nothing: the name is LOADED and the
object is mutated, so a store-counting rule cannot see it.

THE FIX IS NOT "ALSO COUNT `.append`" — that is a denylist of every mutating
method. v2 binds a name only when its folded value is IMMUTABLE (str, bytes,
int, float, bool, None, or a tuple of those, recursively). A `[]` or `{}`
binding is exactly the case where a later mutation is invisible to a folder
that does not track objects, so it is refused at the binding rather than
patched at each mutation site.

Check that fails when this breaks (§12.3): selfcheck 9 constructs the S26 shape.

WHY THIS EXISTS AND WHY IT IS NOT A PATCH TO `constcheck.py`:
`constcheck.py` v2 (ATOM-3, H201) reads the CALL SITE — it flags
`c.observe(True, ...)`, a literal written where the verdict goes. Every real
spike in this tree instead writes

    c3_pins = (PIN_F001 == "590d876..." and PIN_F002 == "c43b1ea...")
    controls[2].observe(c3_pins, {...})

and the call site now holds a Name, so v2 is quiet. This module folds the
verdict expression against the module-level and linear function-level bindings
that are themselves constant, and reports the ones that reduce to a value.

CONSERVATIVE BY CONSTRUCTION — false negatives are accepted, false positives are
not, because a false accusation against another lane's spike is the expensive
error here (H41, H33):
  * a name stored more than once ANYWHERE in the module (or in the function) is
    never bound — that covers `global`, augmented assignment, loop targets and
    `with ... as`;
  * bindings are taken only from the LINEAR top-level statements of a module or
    a function body. A name first bound inside an `if`/`for`/`try` is skipped,
    because statement order across branches is not decidable here;
  * any node this folder does not understand — every Call, every subscript,
    every attribute load — makes the whole expression NOT constant.

Check that fails when this breaks (§12.3):
    python3 spikes/H221_constant_control/fold.py --selfcheck
"""
from __future__ import annotations

import ast
import sys
from collections import Counter

_CMP = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Is: lambda a, b: a is b,
    ast.IsNot: lambda a, b: a is not b,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_BIN = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
}

FIXTURE_FUNCS = ('demo', 'selfcheck', '_selfcheck', 'main_selfcheck')


def fold(node, env):
    """(is_constant, value). Anything not understood is NOT constant."""
    if isinstance(node, ast.Constant):
        return True, node.value
    if isinstance(node, ast.Name):
        return (True, env[node.id]) if node.id in env else (False, None)
    if isinstance(node, ast.BoolOp):
        vals = []
        for v in node.values:
            ok, val = fold(v, env)
            if not ok:
                return False, None
            vals.append(val)
        if isinstance(node.op, ast.And):
            for v in vals:
                if not v:
                    return True, v
        else:
            for v in vals:
                if v:
                    return True, v
        return True, vals[-1]
    if isinstance(node, ast.UnaryOp):
        ok, v = fold(node.operand, env)
        if not ok:
            return False, None
        if isinstance(node.op, ast.Not):
            return True, not v
        if isinstance(node.op, ast.USub):
            return True, -v
        if isinstance(node.op, ast.UAdd):
            return True, +v
        return False, None
    if isinstance(node, ast.Compare):
        ok, cur = fold(node.left, env)
        if not ok:
            return False, None
        for op, comp in zip(node.ops, node.comparators):
            ok, right = fold(comp, env)
            if not ok:
                return False, None
            f = _CMP.get(type(op))
            if f is None:
                return False, None
            try:
                if not f(cur, right):
                    return True, False
            except Exception:
                return False, None
            cur = right
        return True, True
    if isinstance(node, ast.BinOp):
        f = _BIN.get(type(node.op))
        if f is None:
            return False, None
        ok1, a = fold(node.left, env)
        ok2, b = fold(node.right, env)
        if not (ok1 and ok2):
            return False, None
        try:
            return True, f(a, b)
        except Exception:
            return False, None
    if isinstance(node, ast.IfExp):
        ok, t = fold(node.test, env)
        if not ok:
            return False, None
        return fold(node.body if t else node.orelse, env)
    if isinstance(node, (ast.Tuple, ast.List)):
        out = []
        for e in node.elts:
            ok, v = fold(e, env)
            if not ok:
                return False, None
            out.append(v)
        return True, tuple(out) if isinstance(node, ast.Tuple) else out
    return False, None


def _store_counts(node):
    """Every name STORED anywhere under `node` — assignment, augmented
    assignment, loop target, `with ... as`, comprehension target, `del`."""
    c = Counter()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            c[n.id] += 1
        elif isinstance(n, ast.arg):
            c[n.arg] += 1
        elif isinstance(n, ast.Global):
            for nm in n.names:
                c[nm] += 2          # a global declaration alone disqualifies
    return c


def _immutable(v):
    """A mutable constant is not a constant: `xs = []` then `xs.append(y)`
    stores nothing, so no store-counting rule can see the mutation."""
    if isinstance(v, (str, bytes, int, float, bool, type(None))):
        return True
    if isinstance(v, tuple):
        return all(_immutable(x) for x in v)
    return False


def _bind_linear(body, env, counts):
    """Bind names from the LINEAR statements of `body` only, in order."""
    for stmt in body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                and isinstance(stmt.targets[0], ast.Name):
            name = stmt.targets[0].id
            if counts[name] != 1:
                continue
            ok, val = fold(stmt.value, env)
            if ok and _immutable(val):
                env[name] = val
    return env


def scan_source(src, path='<str>'):
    """[{path, line, func, verdict, shape, fixture}] for every `.observe(x, …)`
    whose first argument folds to a constant."""
    tree = ast.parse(src)
    mcounts = _store_counts(tree)
    genv = _bind_linear(tree.body, {}, mcounts)

    hits = []

    def visit_scope(node, env, func_name):
        # `mcounts` is already module-wide and includes this function's own
        # stores. Re-counting them here made every local name read as stored
        # twice and bound nothing -- caught by selfcheck 1, 6 and 7.
        local = _bind_linear(node.body, dict(env), mcounts)
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and n.func.attr == 'observe' and n.args:
                arg = n.args[0]
                ok, val = fold(arg, local)
                if not ok:
                    continue
                hits.append({
                    'path': path,
                    'line': n.lineno,
                    'func': func_name,
                    'verdict': val,
                    # constcheck v2 already reaches a bare literal at the call
                    # site; a Name that FOLDS is this row's delta.
                    'shape': 'literal' if isinstance(arg, ast.Constant) else 'folded',
                    'name': arg.id if isinstance(arg, ast.Name) else None,
                    'fixture': func_name.split('/')[-1].startswith(FIXTURE_FUNCS),
                })

    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        visit_scope(fn, genv, fn.name)

    # module-level observe() calls, outside any function
    class _Top(ast.NodeVisitor):
        def visit_FunctionDef(self, n):
            pass
        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, n):
            if isinstance(n.func, ast.Attribute) and n.func.attr == 'observe' and n.args:
                ok, val = fold(n.args[0], genv)
                if ok:
                    hits.append({'path': path, 'line': n.lineno, 'func': '<module>',
                                 'verdict': val,
                                 'shape': 'literal' if isinstance(n.args[0], ast.Constant) else 'folded',
                                 'name': n.args[0].id if isinstance(n.args[0], ast.Name) else None,
                                 'fixture': False})
            self.generic_visit(n)
    _Top().visit(tree)
    return hits


def selfcheck():
    """Both directions. A folder that only ever says CONSTANT is not a folder."""
    bad = []

    def want(src, n, why, pred=lambda h: True):
        hits = [h for h in scan_source(src) if pred(h)]
        if len(hits) != n:
            bad.append(f'{why}: expected {n}, got {len(hits)} {hits}')
        return hits

    # 1 · the H161 shape: two module literals compared to their own twins
    h = want('''
PIN = "abc"
def main():
    ok = (PIN == "abc")
    c.observe(ok, {})
''', 1, 'folded verdict through a local binding')
    if h and h[0]['verdict'] is not True:
        bad.append(f'folded verdict value wrong: {h[0]}')
    if h and h[0]['shape'] != 'folded':
        bad.append('shape must be `folded`, not `literal`')

    # 2 · QUIET when the verdict actually depends on the world
    want('''
def main():
    ok = (open("x").read() == "abc")
    c.observe(ok, {})
''', 0, 'a verdict reading a file is NOT constant')

    # 3 · QUIET when the name is rebound — order is not decidable
    want('''
PIN = "abc"
def main():
    ok = (PIN == "abc")
    ok = probe()
    c.observe(ok, {})
''', 0, 'a name stored twice is never bound')

    # 4 · QUIET when the binding comes from a parameter
    want('''
def main(ok):
    c.observe(ok, {})
''', 0, 'a parameter is not a constant')

    # 5 · a bare literal is still caught, and marked as constcheck`s reach
    h = want('c.observe(True, {})\n', 1, 'bare literal at module level')
    if h and h[0]['shape'] != 'literal':
        bad.append('bare literal must be marked `literal`')

    # 6 · the false verdict folds too — this is not a True-detector
    h = want('''
PIN = "abc"
def main():
    ok = (PIN == "zzz")
    c.observe(ok, {})
''', 1, 'a constant FALSE verdict is also constant')
    if h and h[0]['verdict'] is not False:
        bad.append(f'constant False not detected: {h[0]}')

    # 7 · `and` returns the operand, not a bool — semantics must match Python
    h = want('''
A = 0
def main():
    ok = (A and 5)
    c.observe(ok, {})
''', 1, 'and-chain folds')
    if h and h[0]['verdict'] != 0:
        bad.append(f'`and` semantics wrong: {h[0]["verdict"]!r} != 0')

    # 9 · THE S26 SHAPE: a name bound to a mutable constant and then filled
    #     by a method call. v1 called this constant and accused another lane.
    want("""
def main():
    xs = []
    ys = []
    for k in stuff():
        xs.append(k)
    c.observe(xs == ys, {})
""", 0, 'a mutable constant is never bound (v2, the S26 false positive)')

    # 8 · a verdict that calls anything is NOT constant, even on constants
    want('''
A = "abc"
def main():
    ok = len(A) == 3
    c.observe(ok, {})
''', 0, 'a Call makes the expression non-constant')

    for b in bad:
        print('  FAIL', b)
    print(f'fold selfcheck: {"FAILED" if bad else "9 checks, both directions"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else 0)
