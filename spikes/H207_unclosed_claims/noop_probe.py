"""Does any sibling falsifier's mutation apply as a NO-OP against today's source?
A no-op mutation runs the UNMUTATED module, which exits 0, which every one of
these drivers scores as `the check is INERT` -- an accusation against the module
sourced entirely from the editing tool. Reports the FRACTION, and refuses to
publish a clean sheet it did not earn: zero mutations parsed is VOID, not 0/0."""
import importlib.util, os, sys
ROOT = os.getcwd()
DRIVERS = {
    'H114_status_decay/falsify.py':  'spikes/harness/statuscheck.py',
    'H85_check6_scope/falsify.py':   'spikes/harness/refcheck.py',
    'H94_record_loss/falsify.py':    'spikes/harness/recordloss.py',
    'H88_sentinel_branch/h98_falsify.py': None,   # asserts its anchors; listed to be seen excluded
}
total = noop = 0
for drv, target in DRIVERS.items():
    path = os.path.join(ROOT, 'spikes', drv)
    if target is None:
        print(f'{drv:36s} EXCLUDED -- asserts `V3_LOOP in src` and `text != src`')
        continue
    src = open(os.path.join(ROOT, target)).read()
    # Import the driver's FALSIFIERS table without running its main body: read
    # the module text and exec only up to the loop. Cheaper and safer: parse the
    # lambdas out by exec'ing the file with a guard env var the drivers do not set.
    text = open(path).read()
    head = text.split('\nfor ', 1)[0].split('\nrc =', 1)[0]
    ns = {'__name__': '__probe__', '__file__': path, 'os': os, 'sys': sys}
    try:
        exec(compile(head, path, 'exec'), ns)
    except SystemExit:
        pass
    except Exception as e:
        print(f'{drv:36s} VOID -- head did not exec: {type(e).__name__}: {e}')
        continue
    table = next((v for k, v in ns.items()
                  if k.isupper() and isinstance(v, (list, tuple)) and v
                  and isinstance(v[0], (list, tuple)) and any(callable(x) for x in v[0])), None)
    if not table:
        print(f'{drv:36s} VOID -- no falsifier table found in head')
        continue
    bad = []
    for row in table:
        fn = next(x for x in row if callable(x))
        name = next((x for x in row if isinstance(x, str)), '?')
        total += 1
        if fn(src) == src:
            noop += 1; bad.append(name)
    print(f'{drv:36s} {len(table)} mutations, NO-OP: {len(bad)}'
          + (' -> ' + '; '.join(b[:44] for b in bad) if bad else ''))
if total == 0:
    sys.exit('VOID: no mutation parsed, so `0 no-ops` is a statement about the probe')
print(f'\n{noop}/{total} mutations across 3 unguarded drivers are NO-OPS against today source')
