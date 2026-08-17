# Citation corpus

Excerpts kept so a claim can be checked without a network call, and so
`spikes/harness/cite.py` can verify a `Cites:` trailer resolves.

**Excerpts only.** Third-party documents are not ours to redistribute (§7), the
same reason `elders/` is gitignored. Each file records its source URL, the
retrieval date, the licence position, and why it was needed.

| ref | source | why |
|---|---|---|
| `refs/python-default-args.txt` | docs.python.org 4.9.1 (sha256 adbd692cf5c3aab3…) | default args bind at DEF time; a monkeypatched global does not reach them |

Verify: `python3 spikes/harness/cite.py 40`
