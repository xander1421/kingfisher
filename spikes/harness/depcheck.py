#!/usr/bin/env python3
"""depcheck.py v1 -- H210. A TRACKED file whose DEPENDENCY is not tracked.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **a refutation ships while the artefact it refutes does not.**
`spikes/H188_seats_are_one_computation/` is 18 tracked files whose `attack.py`
loads `spikes/S91_multi_agent_quorum/run.py` by path, and
`git ls-files spikes/S91_multi_agent_quorum/` is **0**. ATTACKER-1's
`H200_seat_is_a_string/attack.py` loads the same untracked file. So two
committed attacks refute a claim a fresh clone cannot read, using a program a
fresh clone cannot run, and §13 -- *"an uncommitted result is indistinguishable
from one that was never run"* -- is violated from the DEPENDENT side.

Measured against `git archive HEAD` rather than argued: the tracked tree
materialises, `attack.py` runs, and it dies at

    FileNotFoundError: .../spikes/S91_multi_agent_quorum/run.py

WHY EVERY EXISTING GATE IS BLIND TO IT
--------------------------------------
* `trackcheck.py` (H182, same author) reads `Check:` citations out of
  `WORK_QUEUE.md`. S91's row cites none, so S91 is absent from trackcheck's
  89-item floor AND from its live refusal. **Third time a checker of this
  lane's could not see its own motivating case** (H26b; errors 36 and 40).
* `refcheck.py:473` resolves a citation with `os.path.exists` -- the WORKING
  TREE, where every one of these resolves (H35).
* `stranded.sh` asks who OWNS an uncommitted edit, never who DEPENDS on one.
* `githygiene.py` judges what a commit ADDS, never what it leaves behind.

TWO EXTRACTION MODES, AND THE SECOND IS WHY THIS IS NOT A GREP
---------------------------------------------------------------
TEXT  a slash-bearing path token anywhere in the bytes -- docstrings, comments,
      shell, markdown. A MENTION.
AST   `.py` only: folds `X / "a" / "b"` Div-chains, `os.path.join(...)` and
      `Path(...)`/`open(...)` of constants, propagating module-level
      assignments, so `S91_DIR / "run.py"` resolves through
      `S91_DIR = ROOT / "spikes" / "S91_multi_agent_quorum"`. An EXECUTABLE
      dependency: that path will actually be opened.

Reported separately ON PURPOSE. A TEXT-only detector flags H188 -- via its
docstring -- and could then be SATISFIED BY DELETING THE DOCSTRING, leaving
`load_s91()` exactly as broken. That is family B, an instrument reporting
fiction. **AST mode is the one whose fix is the fix.**

THREE-VALUED, BECAUSE "NOT TRACKED" IS THREE DIFFERENT FACTS
------------------------------------------------------------
IGNORED    a DECLARED absence -- `.gitignore` records that someone decided.
SUBMODULE  content under a gitlink; tracked by another repo, not this one.
UNTRACKED  an UNDECLARED absence. Nobody decided; it just never got committed.
           This is the only one that is a defect.

WHAT IS NOT CLAIMED
-------------------
AST folding is module-level and constant-only. A path built inside a function
from a runtime value is invisible to it. That gap is **stated, not defended**
(error 36: a detector whose header argues why it does not look where the
motivating case is); `selfcheck` measures that the covered set contains the
motivating shape rather than assuming it.

REPORT ONLY. It gates nothing. 1621 hits on day one would be a gate every lane
learns to bypass (H14), the paths belong to six lanes, and 85.9 MB of the 87.3
MB it names CANNOT be committed at all -- `githygiene` refuses oversized
additions and §13 says commit the maker, not the artefact. The remedy differs
by size and that decision is the owner's, not this module's.

    python3 depcheck.py [--selfcheck] [--ast-only]      exit 0 always
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = 'depcheck.py v1'
ROOT = Path(__file__).resolve().parents[2]

# A slash-bearing path token. A bare basename is not a path reference, and
# matching one would flag every English word that happens to be a filename.
PATH_RE = re.compile(r'(?<![\w./-])((?:[A-Za-z0-9_.+-]+/)+[A-Za-z0-9_.+-]+)')
SKIP_PREFIX = ('http:', 'https:', 'git@', '.git/', 'refs/')


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, text=True,
                          capture_output=True).stdout


def tracked_set(root):
    """Files AND their ancestor directories.

    **git tracks FILES, so no directory is ever in `git ls-files`** -- and the
    first version of this scan therefore reported every reference to an
    existing directory as an untracked dependency, `spikes/harness` and `.`
    included: 3145 hits in which the real ones were invisible. The four-sided
    `selfcheck` below exists because the two-sided one passed over exactly that.
    """
    files = {p for p in git(root, 'ls-files').split('\n') if p}
    dirs = {'.'}
    for p in files:
        parts = p.split('/')
        for i in range(1, len(parts)):
            dirs.add('/'.join(parts[:i]))
    return files, dirs


def submodule_roots(root):
    """Gitlink entries (mode 160000). Mechanical -- no directory NAME LIST."""
    return {ln.split('\t', 1)[1] for ln in git(root, 'ls-files', '-s').split('\n')
            if ln.startswith('160000 ') and '\t' in ln}


def _check_ignore(root, paths):
    p = subprocess.run(['git', 'check-ignore', '--stdin'], cwd=root, text=True,
                       input='\n'.join(sorted(paths)), capture_output=True)
    return {x for x in p.stdout.split('\n') if x}, p.returncode


def ignored_set(root, paths):
    """-> (ignored, in_submodule, meta).

    DEFECT REMOVED, found on this scan's own first run and before any number
    was read off it: **`git check-ignore --stdin` ABORTS THE WHOLE STREAM on
    the first fatal** -- here `Pathspec '.../mork-server/.git' is in submodule`
    -- exits 128, and prints only what it reached. The first version read
    `p.stdout` and never looked at the return code, so over 1286 deps it
    emitted 826 ignored paths and stopped: **43 deps that ARE ignored were
    reported UNTRACKED and 19 submodule paths got no verdict at all.**

    CLASS: **a subprocess whose non-zero exit is not read, so a TRUNCATED
    output is consumed as a complete one.** Fifth instance in this lane's
    record, in a new mechanism each time -- pipe `head`, a `{0,N}` regex bound,
    `-1`/HEAD, a `sed` range terminator, and now a stream abort. Which is why
    "be careful with truncation" has never worked as a remedy; what works is
    checking the SIZE of what you read against the size of what you expected.

    Submodule paths are excluded FIRST, mechanically, from `ls-files -s` mode
    160000. The remaining call must exit 0 or 1 and RAISES otherwise, so this
    can never again fail quietly. The pre-fix form is re-run beside it and its
    disagreement reported, so the repair is measured rather than asserted.
    """
    paths = set(paths)
    if not paths:
        return set(), set(), {'batch_rc': None, 'v1_rc': None, 'v1_missed': 0,
                              'v1_extra': 0, 'n_paths': 0, 'n_submodule': 0}
    subs = submodule_roots(root)
    inside = {p for p in paths
              if any(p == s or p.startswith(s + '/') for s in subs)}
    clean = paths - inside
    ign, rc = _check_ignore(root, clean) if clean else (set(), 1)
    if rc not in (0, 1):
        raise RuntimeError(
            f'git check-ignore exited {rc} over {len(clean)} paths: the stream '
            f'aborted and the classification is TRUNCATED, not clean')
    v1_ign, v1_rc = _check_ignore(root, paths)
    return ign, inside, {'batch_rc': rc, 'v1_rc': v1_rc,
                         'v1_missed': len(ign - v1_ign),
                         'v1_extra': len(v1_ign - ign),
                         'n_paths': len(paths), 'n_submodule': len(inside)}


# ---------------------------------------------------------------- extraction
def text_paths(src):
    out = set()
    for m in PATH_RE.finditer(src):
        tok = m.group(1)
        if tok.startswith(SKIP_PREFIX) or '://' in tok:
            continue
        out.add(tok.rstrip('/'))
    return out


def _fold(node, env):
    """-> list of path components, or None if the node is not path-shaped.

    An unknown base (a Name not in env, an Attribute, a Call) folds to `[]`:
    ROOT-anchored. Permissive by design -- what makes the result sound is the
    `exists on disk` filter in `scan`, not the folding.
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return list(env.get(node.id, []))
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return []
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = _fold(node.left, env), _fold(node.right, env)
        if left is None or right is None:
            return None
        return left + right
    if isinstance(node, ast.Call):
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else \
            (fn.id if isinstance(fn, ast.Name) else '')
        if name == 'join':
            parts = [_fold(a, env) for a in node.args]
            if parts and all(p is not None for p in parts):
                return [c for p in parts for c in p]
            return None
        if name in ('Path', 'open'):
            return _fold(node.args[0], env) if len(node.args) == 1 else None
        return []          # unknown call: ROOT-anchored base
    return None


def ast_paths(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    env, out = {}, set()
    for stmt in tree.body:                       # module-level env only
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                and isinstance(stmt.targets[0], ast.Name):
            folded = _fold(stmt.value, env)
            if folded is not None:
                env[stmt.targets[0].id] = folded
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            folded = _fold(node, env)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else \
                (fn.id if isinstance(fn, ast.Name) else '')
            folded = _fold(node, env) if name in ('join', 'Path', 'open') else None
        else:
            continue
        if folded and len(folded) >= 2:
            out.add('/'.join(str(c) for c in folded))
    return out


# ------------------------------------------------------------------- sweeping
def scan(root):
    """-> (hits, ignore_classifier_meta). Every hit carries its own mode set."""
    root = Path(root)
    tracked, tracked_dirs = tracked_set(root)
    hits, deps = [], set()
    for rel in sorted(tracked):
        f = root / rel
        if not f.is_file():
            continue
        try:
            src = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        found = {}
        for cand in text_paths(src):
            found.setdefault(cand, set()).add('TEXT')
        if rel.endswith('.py'):
            for cand in ast_paths(src):
                found.setdefault(cand, set()).add('AST')
        for cand, modes in found.items():
            for anchor in (root, f.parent):
                dep = anchor / cand
                try:
                    relp = dep.resolve().relative_to(root.resolve()).as_posix()
                except ValueError:
                    continue
                if not dep.exists() or relp in tracked or relp == rel:
                    continue
                if relp in tracked_dirs:      # git tracks files, not directories
                    continue
                hits.append({'file': rel, 'dep': relp, 'modes': sorted(modes),
                             'dep_is_dir': dep.is_dir()})
                deps.add(relp)
                break
    ign, inside, meta = ignored_set(root, deps)
    for h in hits:
        h['dep_status'] = ('SUBMODULE' if h['dep'] in inside
                           else 'IGNORED' if h['dep'] in ign else 'UNTRACKED')
    return hits, meta


def summarise(hits):
    live = [h for h in hits if h['dep_status'] == 'UNTRACKED']
    ast_live = [h for h in live if 'AST' in h['modes']]
    return {
        'hits_total': len(hits),
        'untracked': len(live),
        'ignored': sum(1 for h in hits if h['dep_status'] == 'IGNORED'),
        'submodule': sum(1 for h in hits if h['dep_status'] == 'SUBMODULE'),
        'untracked_ast': len(ast_live),
        'untracked_text_only': len(live) - len(ast_live),
        'files_with_untracked_dep': len({h['file'] for h in live}),
        'distinct_untracked_deps': len({h['dep'] for h in live}),
        'ast_pairs': sorted({(h['file'], h['dep']) for h in ast_live}),
    }


def du(path):
    if os.path.isdir(path):
        t = 0
        for r, _, fs in os.walk(path):
            for f in fs:
                try:
                    t += os.path.getsize(os.path.join(r, f))
                except OSError:
                    pass
        return t
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


# ------------------------------------------------------------------ selfcheck
def selfcheck(root=None):
    """FOUR-sided, in a throwaway git repo. Fails if the scan breaks.

    An inert sweep and a clean tree are indistinguishable (H124), so the
    fixture must produce BOTH verdicts -- in the FILE shape AND the DIRECTORY
    shape. The first fixture here covered files only and passed while every
    existing directory was being reported untracked. **A two-sided control in
    one shape is a one-sided control** (A15), and that is this arm's own origin.
    """
    d = Path(root or (ROOT / '.scratch' / 'depcheck_selfcheck'))
    if d.exists():
        shutil.rmtree(d)
    (d / 'pkg' / 'lib').mkdir(parents=True)
    (d / 'pkg' / 'ghost').mkdir(parents=True)
    (d / 'pkg' / 'lib' / 'present.py').write_text('X = 1\n')
    (d / 'pkg' / 'lib' / 'absent.py').write_text('Y = 2\n')
    (d / 'pkg' / 'ghost' / 'x.py').write_text('Z = 3\n')
    head = ('from pathlib import Path\n'
            'ROOT = Path(__file__).resolve().parent\n')
    (d / 'bad.py').write_text(head + 'D = ROOT / "pkg" / "lib"\np = D / "absent.py"\n')
    (d / 'good.py').write_text(head + 'D = ROOT / "pkg" / "lib"\np = D / "present.py"\n')
    (d / 'dirref.py').write_text(head + 'D = ROOT / "pkg" / "lib"\n')
    (d / 'ghostref.py').write_text(head + 'D = ROOT / "pkg" / "ghost"\n')
    (d / '.gitignore').write_text('declared/\n')
    (d / 'declared').mkdir()
    (d / 'declared' / 'thing.py').write_text('W = 4\n')
    (d / 'decref.py').write_text(head + 'D = ROOT / "declared" / "thing.py"\n')
    for a in (['init', '-q'],
              ['add', 'bad.py', 'good.py', 'dirref.py', 'ghostref.py',
               'decref.py', '.gitignore', 'pkg/lib/present.py'],
              ['-c', 'user.email=f@x', '-c', 'user.name=f',
               'commit', '-q', '-m', 'fixture', '--no-verify']):
        subprocess.run(['git', *a], cwd=d, capture_output=True)
    hits, _ = scan(d)
    ast_pairs = {(h['file'], h['dep']) for h in hits if 'AST' in h['modes']}
    live = {(h['file'], h['dep']) for h in hits
            if 'AST' in h['modes'] and h['dep_status'] == 'UNTRACKED'}
    checks = [
        ('flags an untracked FILE dependency', ('bad.py', 'pkg/lib/absent.py') in live),
        ('does NOT flag a tracked file', ('good.py', 'pkg/lib/present.py') not in ast_pairs),
        ('does NOT flag a tracked DIRECTORY', ('dirref.py', 'pkg/lib') not in ast_pairs),
        ('flags a wholly untracked directory', ('ghostref.py', 'pkg/ghost') in live),
        ('classifies a gitignored dep as DECLARED, not a defect',
         ('decref.py', 'declared/thing.py') in ast_pairs
         and ('decref.py', 'declared/thing.py') not in live),
    ]
    for n, okc in checks:
        print(f'  {"ok  " if okc else "FAIL"} {n}')
    print(f'{VERSION} selfcheck: '
          f'{sum(1 for _, o in checks if o)}/{len(checks)}')
    return dict(checks)


def main(argv):
    if '--selfcheck' in argv:
        return 0 if all(selfcheck().values()) else 1
    hits, meta = scan(ROOT)
    s = summarise(hits)
    ast_only = '--ast-only' in argv
    print(f'{VERSION}: {s["hits_total"]} referenced-but-not-tracked paths  '
          f'[{s["untracked"]} UNTRACKED · {s["ignored"]} IGNORED (declared) · '
          f'{s["submodule"]} SUBMODULE]')
    print(f'  EXECUTABLE (AST) untracked deps: {s["untracked_ast"]} hits · '
          f'{len(set(p[1] for p in s["ast_pairs"]))} distinct paths · '
          f'{len(set(p[0] for p in s["ast_pairs"]))} tracked files depend on them')
    deps = sorted({p[1] for p in s['ast_pairs']}, key=lambda p: -du(ROOT / p))
    big = [p for p in deps if du(ROOT / p) > 1_000_000]
    print(f'  of those, {len(big)} exceed 1 MB and CANNOT be committed '
          f'(§13 "commit the maker, not the artefact"); the remaining '
          f'{len(deps) - len(big)} total '
          f'{sum(du(ROOT / p) for p in deps if p not in big) / 1e3:.0f} kB')
    for p in deps:
        users = sorted({f for f, dp in s['ast_pairs'] if dp == p})
        print(f'    {du(ROOT / p) / 1e3:10.1f} kB  {p}   <- {len(users)} file(s)'
              + ('' if len(users) > 3 else '  ' + ', '.join(users)))
    if not ast_only:
        print(f'  MENTION-only (TEXT) untracked refs: {s["untracked_text_only"]} '
              f'-- reported apart because deleting the mention would silence '
              f'them without fixing anything')
    print(f'  ignore classifier: batch_rc={meta["batch_rc"]} '
          f'(pre-fix form rc={meta["v1_rc"]}, missed {meta["v1_missed"]})')
    return 0                       # REPORT ONLY: never gates


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
