#!/usr/bin/env python3
"""A silent no-op edit is a bug that leaves no trace.

`s.replace(old, new)` returns the string unchanged when `old` is absent. A
`global ALPHA` insert was shipped this way and was only discovered because the
resulting flag was inert -- the patch script printed success, the file was
written, and nothing was different.
"""


class AnchorMissing(Exception):
    pass


def anchored_replace(s, old, new, count=1):
    """Replace, asserting the anchor appears exactly `count` times."""
    n = s.count(old)
    if n != count:
        raise AnchorMissing(
            f'anchor appears {n} time(s), expected {count}: {old[:70]!r}')
    return s.replace(old, new)


def patch_file(path, pairs, count=1):
    """Apply [(old, new), ...] to a file, all-or-nothing."""
    s = orig = open(path).read()
    for old, new in pairs:
        s = anchored_replace(s, old, new, count)
    if s == orig:
        raise AnchorMissing(f'{path}: every replacement was a no-op')
    open(path, 'w').write(s)
    return len(pairs)


def demo():
    assert anchored_replace('a b a', 'b', 'X') == 'a X a'
    for bad in ('zzz', 'a'):          # absent, and present twice
        try:
            anchored_replace('a b a', bad, 'X')
            raise AssertionError(f'accepted {bad!r}')
        except AnchorMissing:
            pass
    assert anchored_replace('a b a', 'a', 'X', count=2) == 'X b X'
    import tempfile, os
    p = os.path.join(tempfile.mkdtemp(), 'f.txt')
    open(p, 'w').write('hello world')
    assert patch_file(p, [('world', 'there')]) == 1
    assert open(p).read() == 'hello there'
    try:
        patch_file(p, [('absent', 'x')]); raise AssertionError('accepted no-op')
    except AnchorMissing:
        pass
    print('edits: 7 assertions pass')


if __name__ == '__main__':
    demo()
