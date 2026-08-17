#!/usr/bin/env python3
"""Admission gate for the nondeterministic op surface.

M1.8b measured why this is a SAFETY control and not hygiene: quorum-of-3
accepts a genuinely nondeterministic job **21.5% of the time**, because two
honest devices coincide by chance and an arbitrary answer is recorded as
canonical. Replication cannot detect a job with no single right answer, so the
only place to stop it is admission.

The surface is enumerated from the shipped build, not guessed
(`lib/src/metta/runner/builtin_mods/random.rs:99-132`):

    flip  random-int  random-float
    new-random-generator  set-random-seed  reset-random-generator
    &rng                                    <- the AMBIENT generator token

The ban is NOT blanket. LEDGER carries a grade-A row that a job with a
correctly-bound SEEDED generator is bit-identical across two ISAs, and S58's
rule is "seeded or removed", not "removed". So:

    REJECT   use of the ambient `&rng`, or `flip`, which has no seed argument
    ADMIT    a generator explicitly constructed with `new-random-generator <seed>`
             and threaded through the random ops
"""
import re, sys

AMBIENT = re.compile(r'&rng\b')
FLIP = re.compile(r'\(\s*flip\b')
RANDOM_OP = re.compile(r'\(\s*(random-int|random-float)\b')
SEEDED_GEN = re.compile(r'\(\s*new-random-generator\s+(-?\d+)\s*\)')
RESET = re.compile(r'\(\s*(reset-random-generator|set-random-seed)\b')
IMPORT_RANDOM = re.compile(r'\(\s*import!\s+\S+\s+random\s*\)')

# Filesystem surface, enumerated from builtin_mods/fileio.rs `register_function`
# calls. These resolve RELATIVE paths against the runner's working directory, so
# the same program returns different results on an agent and its verifier when
# the two have different working dirs -- measured: `mkdocs.metta` calls
# `(file-open! "./docs/generated/corelib.md" ...)` and was the last of 66
# programs to disagree between the Android app and the host, after feature sets
# were matched and an escaping bug in our own transport was fixed.
#
# This is not nondeterminism: each runtime is internally deterministic. It is an
# environment dependency, and replication cannot detect it because both sides
# are honestly reporting their own filesystem.
# no \b after the trailing `!`: `!` and the following space are both
# non-word characters, so there is no word boundary there and the pattern
# never matched. Caught by the assertion below, which is why it exists.
# Modules whose EXISTENCE depends on a Cargo feature, from
# builtin_mods/mod.rs `#[cfg(feature = ...)]` gates:
#   pkg_mgmt -> catalog        das -> das
# A program importing one of these behaves differently on two honest workers
# built with different feature sets -- measured: `integration_tests__das__test`
# gives fuel 580 with `das` and fuel 107 without, and both are correct answers
# from their own runtime.
#
# This is the price of INDEPENDENCE, not a defect. Two workers built from
# different manifests are two failure domains, which is what the quorum needs;
# admitting feature-dependent programs is what stops them agreeing. Banning
# these buys `manifest = 2` at a cost of one program in 65.
FEATURE_MODULES = ('das', 'catalog')
IMPORT_FEATURE = re.compile(
    r'\(\s*import!\s+\S+\s+(' + '|'.join(FEATURE_MODULES) + r')\s*\)')

FILEIO = re.compile(r'\(\s*(file-open!|file-read-exact!|file-read-to-string!'
                    r'|file-write!|file-seek!|file-get-size!)(?=[\s)])')


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


def scan(text):
    """Return a list of (kind, detail) violations."""
    t = strip_comments(text)
    bad = []
    if FLIP.search(t):
        bad.append(('flip', 'flip takes no generator, so it cannot be seeded'))
    if AMBIENT.search(t):
        bad.append(('ambient-rng', '&rng is the module-level generator, '
                                   'not seeded by the job'))
    if RESET.search(t):
        bad.append(('reseed', 'reset-random-generator/set-random-seed mutate '
                              'generator state mid-job; the result then depends '
                              'on evaluation order'))
    m = IMPORT_FEATURE.search(t)
    if m:
        bad.append(('feature-gated-module',
                    f'module `{m.group(1)}` exists only under a Cargo feature, so '
                    f'two honest workers built differently give different results'))
    m = FILEIO.search(t)
    if m:
        bad.append(('filesystem', f'{m.group(1)} resolves paths against the '
                                  f'runner working directory, which differs '
                                  f'between an agent and its verifier'))
    # random-int/float are fine ONLY if every generator in the job is seeded
    if RANDOM_OP.search(t) and not SEEDED_GEN.search(t):
        bad.append(('unseeded-random', 'random-int/random-float used with no '
                                       '(new-random-generator <seed>) in the job'))
    return bad


def admit(data: bytes):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return False, [('non-utf8', '')]
    v = scan(text)
    return not v, v


def demo():
    # the program M1.8b measured at 21.5% laundering MUST be rejected
    ok, v = admit(b'!(import! &self random)\n!(xor (flip) (flip))\n')
    assert not ok and v[0][0] == 'flip', v

    ok, v = admit(b'!(random-int &rng 0 10)\n')
    assert not ok, v
    kinds = {k for k, _ in v}
    assert 'ambient-rng' in kinds and 'unseeded-random' in kinds, kinds

    # a correctly seeded generator is ADMITTED -- LEDGER grade A says it is
    # bit-identical across two ISAs, so banning it would be wrong
    ok, v = admit(b'!(let $g (new-random-generator 42) (random-int $g 0 10))\n')
    assert ok, v

    # reseeding mid-job is rejected even though a seed is present
    ok, v = admit(b'!(let $g (new-random-generator 42) (reset-random-generator $g))\n')
    assert not ok and v[0][0] == 'reseed'

    # ordinary programs are untouched
    for good in (b'!(+ 1 2)\n', b'(= (f $x) (g $x))\n!(f A)\n',
                 b'!(match &self (pair $x $y) ($x $y))\n'):
        ok, _ = admit(good)
        assert ok, good

    # a comment must not trigger the gate
    ok, _ = admit(b'; !(flip)\n!(+ 1 2)\n')
    assert ok

    # filesystem ops are environment-dependent, not nondeterministic -- both
    # runtimes answer honestly about their own filesystem, so quorum cannot see it
    ok, v = admit(b'!(file-open! "./docs/x.md" "w")\n')
    assert not ok and v[0][0] == 'filesystem', v
    for op in (b'file-read-to-string!', b'file-write!', b'file-get-size!'):
        ok, _ = admit(b'!(' + op + b' "x")\n')
        assert not ok, op
    ok, _ = admit(b'; !(file-open! "x" "w")\n!(+ 1 2)\n')
    assert ok, 'a commented-out fileio call must not trigger'

    # feature-gated modules: the program is fine, the runtime differs
    ok, v = admit(b'!(import! &self das)\n')
    assert not ok and v[0][0] == 'feature-gated-module', v
    ok, v = admit(b'!(import! &self catalog)\n')
    assert not ok, v
    # a module that is NOT feature-gated must still be admitted
    ok, _ = admit(b'!(import! &self json)\n')
    assert ok, 'json is unconditional -- must not be banned'
    ok, _ = admit(b'; !(import! &self das)\n!(+ 1 2)\n')
    assert ok, 'commented-out import must not trigger'
    print('bansurface: 20 assertions pass')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            ok, v = admit(open(p, 'rb').read())
            if not ok:
                print(f'REJECT {p}: ' + '; '.join(k for k, _ in v))
    else:
        demo()
