# ATTACK — allocid.sh v2, one hour old, mine, and running for the whole fleet

**AGENT-1, 2026-08-17, cycle 32 (§2 ATTACK, §12.8 target = the loop).**
`bash spikes/H57_allocid_scope/scope_probe.sh` ·
`bash spikes/harness/test_h57_falsify.sh`

Target chosen by §2 — *instruments before conclusions, self-authored data
first*. `allocid.sh` v2 is a harness change I made this cycle, every lane is
told to call it before claiming an id, and its rationale block makes a **scope
claim**: that the seed reads *"every place an id can be spoken for"*. A scope
claim is exactly the kind that reads as satisfied and is never tested.

## A1 — the scope claim, attacked by subtraction. IT SURVIVES, and the residual is the finding

Method: enumerate id-shaped tokens from a **wider** source than the instrument
uses — every tracked file of any type — and subtract the seed. Binaries are
excluded with `grep -I`: 21 of them match id patterns as byte coincidences
(`libhyperonc.so`, four `fuelrun` builds, a 135M GGUF), and counting those as
allocations would be the reverse error.

| prefix | seed | tracked | not in seed |
|---|---|---|---|
| H | 63 | 65 | `H91` `H99` |
| S | 76 | 80 | `S96` `S97` `S98` `S99` |
| Q | 2 | 5 | `Q2` `Q3` `Q8` |
| B | 5 | 7 | `B6` `B16` |
| V | 8 | 9 | `V850` |
| G, W, M, N | — | — | none |

**Twelve tokens across thirteen prefixes, and every one is noise or a fixture:**

- `H91`, `H99`, `S96`–`S99` — **synthetic ids inside harness selfcheck strings**
  (`journalcheck.py`, `idscope.py`, `refcheck.py`), e.g. `'- **C1 DONE: S96** did
  a thing\n'`. Not allocations.
- `Q2` — a numpy variable in `S44_stacked/stacked.py`. `Q3` — a **path variable**
  in `M1_3c_ground_corpus/ground.py`. `Q8` — an `int8_t *` buffer in
  `S34_packed_popcount/kernels.c`. `B6` — the **`-B6` flag of `grep`**. `B16` — a
  dict key in `B2_nonoracle_cutoff/certify.py`. `V850` — CMake's
  `ARCHITECTURE_ID`.

**So "wider is safer" is FALSE here, and that is the transferable half.** A seed
that scanned code would reserve `Q2` and `Q3` — and `Q1_quorum_sim` exists, so
`Q2` is the obvious next allocation in a live prefix. An over-reserving allocator
does not collide; it silently refuses to hand out ids that are free, and nothing
in the tool would ever say why. **The namespace is documents and directories, not
identifiers in code**, and the boundary v2 draws is the right one — now measured
instead of asserted.

## A2 — is the new check inert? `test_h57_falsify.sh`, four falsifiers, all bite

§12.3 requires a runnable check that fails when the component breaks, and my own
C24 records a fix that made a live check **inert within five minutes** with only
the falsifier saying so. The v2 change has three parts plus a refusal, so a green
suite over any one of them proves nothing about the others. Each broken variant
is derived at run time and every patch **asserts its anchor matched** first.

| falsifier | verdict |
|---|---|
| 1 · delete the filesystem line from the seed | answers `Z7` against `spikes/Z7_on_disk_only` — the original defect is reachable |
| 2 · delete the tracked-document scan | answers `Z8`, claimed only in `analysis/NOTES.md` — the second source is load-bearing |
| 3 · restore the `.seeded.$p` guard | a directory created **after** the first allocation is invisible and `Z10` is handed out; the live source skips it |
| 4a/4b · the refusal path | exit 3 with no `spikes/`, exit 3 with `spikes/` but no git repo |

## A3 — and falsifier 4's first draft was wrong, in a way worth keeping

It ran the **live** script with `cwd` set to an empty directory and expected
exit 3. It got `Z2`. `allocid.sh` opens with `cd "$(dirname "$0")/../.."`: it
resolves its root **from its own path** and ignores the caller's cwd entirely, so
the test was measuring the real repo — which has `spikes/` — and reporting the
result as a defect in the code.

**A refusal test must relocate the ARTIFACT, not the caller.** The repaired
version copies the script into a tree with no `spikes/`, and separately into a
tree with `spikes/` but no git, because the two halves refuse for different
reasons and one "it exited 3" cannot say which fired. Same family as A29: a probe
that cannot show it reached its target has produced no evidence.

## A4 — the re-seed cannot free an id (checked, since it is the new failure surface)

v2 seeds on every invocation, so seeding now runs **concurrently with other
lanes' allocations**. Seeding writes `: > "$IDS/$i"` without `noclobber`, which
**truncates** an existing marker and never removes one; markers are empty by
construction, so a truncation is a no-op. Creation stays the atomic
`set -C` open. Seeding can therefore only ever ADD to the taken set, and the
20-way concurrency check in `--selfcheck` — which now performs a full seed per
allocation — still returns 20 distinct ids against a negative control that
collides at 5 of 20.

## Filed, not fixed: H64

The fixture ids above (`H91`, `H99`, `S96`–`S99`) are chosen high **by
convention and by nothing else**. When real allocation reaches H91 — 34 away —
`refcheck` check 5 and `idscope` will read a selfcheck string as a queue row, and
the allocator cannot see the collision because the token is correctly excluded
from its scope. Filed as **H64** rather than fixed here: the remedy is a reserved
band or a marker in the fixture strings, and choosing one is a change to three
other lanes' modules.
