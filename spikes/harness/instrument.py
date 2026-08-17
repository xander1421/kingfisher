#!/usr/bin/env python3
"""Family B — the instrument is reporting fiction.

Confident, well-formed, wrong. No exception, no malformed value, nothing to
notice. Instances:
  - frozen override: `dumpsys battery` printing `UPDATES STOPPED`, every field
    stale. Produced an entire false defect report about a phone that WAS charging.
  - empty capture read as data: `da39a3ee…` (sha256 of ''), `curl -s` writing a
    404 body to the cache, an unpopulated JS dashboard reading as "0 providers".
  - gate testing the wrong condition: `status=5` means the battery is FULL, not
    that the device is plugged in.
"""
import hashlib
import re

# sha256 and md5 of the empty string. These appear whenever a capture silently
# produced nothing and the pipeline hashed it anyway.
EMPTY_HASHES = {
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'da39a3ee5e6b4b0d3255bfef95601890afd80709',          # sha1('')
    'd41d8cd98f00b204e9800998ecf8427e',                  # md5('')
}

FROZEN_MARKERS = (
    'UPDATES STOPPED',          # dumpsys battery set/unplug
    'IsStatusOverride: true',   # thermalservice override
    '(overridden)',
)


class InstrumentFault(Exception):
    """The instrument is not reporting the world."""


def check_not_frozen(text, markers=FROZEN_MARKERS, name='instrument'):
    """(ok, detail). A frozen service reports pinned values with no other signal."""
    for m in markers:
        if m in text:
            return False, (f'{name} is OVERRIDDEN ({m!r}): every field it reports '
                           f'is stale. Reset it before reading.')
    return True, 'not frozen'


def check_nonempty(capture, name='capture'):
    """(ok, detail). Refuse an empty capture, and refuse the hash of one.

    Both forms have appeared: an empty string hashed downstream, and the
    well-known empty-hash constant arriving as if it were a result.
    """
    if capture is None:
        return False, f'{name} is None'
    if isinstance(capture, (bytes, bytearray)):
        capture = capture.decode('utf-8', 'replace')
    s = str(capture).strip()
    if not s:
        return False, f'{name} is EMPTY -- an empty capture is not a measurement'
    if s.lower() in EMPTY_HASHES:
        return False, (f'{name} is the hash of the empty string ({s[:12]}...): '
                       f'something upstream captured nothing and hashed it')
    return True, f'{name} non-empty ({len(s)} chars)'


def check_semantics(field, value, means, tested_for):
    """(ok, detail). Force the question 'does this field mean what I am using
    it for?' to be answered in code rather than assumed.

    `status=5` means BATTERY_STATUS_FULL. It was used to test 'is plugged in'.
    An unplugged phone at 100% reports FULL, so the test could not have been
    right in the direction that mattered.
    """
    if means.strip().lower() == tested_for.strip().lower():
        return True, f'{field} means {means!r}, tested for {tested_for!r}'
    return False, (f'{field}={value!r} MEANS {means!r} but is being used to test '
                   f'{tested_for!r}. State why those coincide, or test the right field.')


def sha256_of(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def demo():
    real = "Current Battery Service state:\n  AC powered: true\n  status: 2\n"
    frozen = ("Current Battery Service state:\n"
              "  (UPDATES STOPPED -- use 'reset' to restart)\n"
              "  AC powered: false\n  status: 5\n")
    assert check_not_frozen(real)[0]
    ok, why = check_not_frozen(frozen, name='dumpsys battery')
    assert not ok and 'OVERRIDDEN' in why, why

    assert check_nonempty('hello')[0]
    for bad in ('', '   ', None, b''):
        assert not check_nonempty(bad)[0], bad
    ok, why = check_nonempty(sha256_of(''), 'result_hash')
    assert not ok and 'empty string' in why, why
    assert check_nonempty(sha256_of('x'), 'result_hash')[0]

    ok, why = check_semantics('status', 5, means='battery is FULL',
                              tested_for='device is plugged in')
    assert not ok and 'MEANS' in why, why
    assert check_semantics('powered', True, means='device is plugged in',
                           tested_for='device is plugged in')[0]
    print('instrument: 12 assertions pass')


if __name__ == '__main__':
    demo()
