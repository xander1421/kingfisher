#!/usr/bin/env python3
"""Shard admission -- REFUTED AS A GATE. Kept as a linter, not an admission rule.

STATUS: the predicate below rejects **51% of hyperon's own 67-program corpus**,
and 21 of the 34 rejections are inside `(= ...)` rule bodies that were MEASURED
STABLE (C1/C2). Worse, the E-series showed a second mechanism this rule does not
touch at all. Do not gate on it. See M1.1c SOAK_RESULT.md.

Two distinct mechanisms produce non-reproducibility, and they need different
fixes:

  (1) REPRESENTATIVE SELECTION -- a query aliasing two distinct pattern
      variables onto one data variable returns `($x $x)` or `($y $y)`.
      Outcomes = number of aliased variables. This rule catches it.

  (2) THE COUNTER IS PRINTED -- `VariableAtom::name()` embeds `#{id}` and
      `Display` calls it, so ANY result containing a data-origin variable emits
      the process-global counter. `(implies (Frog $x) (Green $x))` queried with
      a NON-aliasing `(implies $p $q)` gives 40 distinct outputs in 40 runs.
      This rule does not catch it, and no data-side syntactic rule can: it
      depends on what the query projects.

Mechanism (2) is the more severe and is a small upstream fix. Mechanism (1)
needs either a per-runner id space or an ordered binding map.

Original docstring follows.

Shard admission: reject atoms that would make a job non-reproducible.

M1.1c measured the class. Same program, fresh runner, one process:
`(pair $z $z)` matched by `(pair $x $y)` returns `($x $x)` or `($y $y)`
depending on how many variables the process created earlier
(`NEXT_VARIABLE_ID` is a process-global counter and `VariableAtom.id`
participates in the derived Hash).

The predicate is per-atom and syntactic:

    REJECT any stored data atom containing the same variable more than once.

Scope, established by the 16-program sweep and not assumed:
  - repetition in the QUERY pattern is safe          (B3 STABLE)
  - the same variable name in DIFFERENT atoms is safe (D4 STABLE -- they become
    distinct after make_variables_unique)
  - aliasing produced by a RULE is safe               (C1/C2 STABLE)
  - a single variable, or several DISTINCT variables, in one atom is safe
    (D1/D2 STABLE) -- so "shards must be ground" is the wrong, stricter rule
"""
import re, sys

VAR = re.compile(r'\$[^\s()]+')


def strip_comments(text):
    out = []
    for line in text.splitlines():
        q = False
        for i, ch in enumerate(line):
            if ch == '"':
                q = not q
            elif ch == ';' and not q:
                line = line[:i]
                break
        out.append(line)
    return '\n'.join(out)


def top_level_forms(text):
    """Yield (form_text, is_query, line_no). A `!` prefix marks a query, which
    is evaluated rather than stored, and queries are NOT subject to the rule."""
    text = strip_comments(text)
    depth, buf, start_line, line_no, bang, q = 0, [], 1, 1, False, False
    for ch in text:
        if ch == '\n':
            line_no += 1
        if ch == '"':
            q = not q
        if not q:
            if ch == '(':
                if depth == 0:
                    start_line = line_no
                depth += 1
            elif ch == ')':
                depth -= 1
        buf.append(ch)
        if depth == 0 and not q:
            s = ''.join(buf).strip()
            if s.endswith(')'):
                body = s.lstrip()
                is_q = body.startswith('!')
                yield body.lstrip('!').strip(), is_q, start_line
                buf, bang = [], False
    # trailing junk is not a form


def repeated_vars(form):
    seen, dup = set(), []
    for v in VAR.findall(form):
        if v in seen and v not in dup:
            dup.append(v)
        seen.add(v)
    return dup


def check_text(text):
    """Return a list of violations: (line, var, form_excerpt)."""
    bad = []
    for form, is_query, line in top_level_forms(text):
        if is_query:
            continue                      # queries are safe (B3)
        for v in repeated_vars(form):
            bad.append((line, v, form[:70]))
    return bad


def admit(data: bytes):
    """(ok, violations) for a candidate shard."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return False, [(0, '<non-utf8>', '')]
    v = check_text(text)
    return not v, v


def demo():
    ok, _ = admit(b'(pair $z $w)\n')
    assert ok, 'two distinct vars in one atom is safe (D2)'
    ok, v = admit(b'(pair $z $z)\n')
    assert not ok and v[0][1] == '$z', v
    ok, _ = admit(b'(pair $z A)\n')
    assert ok, 'one var is safe (D1)'
    ok, _ = admit(b'(one $z)\n(two $z)\n')
    assert ok, 'same name across atoms is safe (D4)'
    ok, _ = admit(b'!(match &self (pair $x $x) $x)\n')
    assert ok, 'repetition in a QUERY is safe (B3)'
    ok, _ = admit(b'(= (f $x) (g $x $x))\n')
    assert not ok, 'a rule atom repeating $x is caught by the syntactic rule'
    ok, _ = admit(b'(tri $z $z $z)\n')
    assert not ok
    ok, _ = admit(b'; (pair $z $z)\n(ok $a)\n')
    assert ok, 'commented-out text must not trigger'
    ok, _ = admit(b'(say "$z $z")\n')
    assert ok, 'a string literal is not two variables'
    ok, _ = admit(b'(pair A A)\n')
    assert ok, 'repeated SYMBOL is safe (B2)'
    ok, _ = admit(b'(o (i $z $z))\n')
    assert not ok, 'nested repetition still counts (A4)'
    print('admission: 11 assertions pass')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            ok, v = admit(open(p, 'rb').read())
            print(f'{"ADMIT " if ok else "REJECT"} {p}'
                  + ('' if ok else f'  {len(v)} violation(s), first: line {v[0][0]} {v[0][1]}'))
    else:
        demo()
