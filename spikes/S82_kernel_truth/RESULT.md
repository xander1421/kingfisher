# S82 — the prefilter kernel is correct, not merely repeatable; and here is the D at which it silently stops being either

**ATTACKER-1, 2026-08-17.** Second consecutive target picked by grepping
`out/LEDGER.md` for a falsifier written down and marked **not yet run**.

## The open finding this closes

> `Determinism across core types` | **B, with an open finding against it** |
> `S52_attack_s50` scored: *digest proves repeatability, not correctness*; the
> kernel was **rewritten** for S50 so a regression would be invisible. v1 cited
> the confirming attacker, omitted the scoring one. **Fix = one assertion:
> S45's 12-row ground truth through the new kernel.**

S52 was right about the *gap* and wrong about one premise, and the difference
matters:

**The kernel was not rewritten.** `S50 remeasure.c:44-58` and
`S45 prefilter.c:105-117` are the same arithmetic, instruction for instruction,
differing only in the accumulator's name (`v` vs `vsum`). What S50 rewrote is
the **harness** — pinning, amortisation, null control, digest coverage. So the
risk S52 named ("a regression would be invisible") was real as a *class*, but no
regression was introduced.

**The gap S52 named is real and was still open.** Neither spike ever compared
the vector kernel to an *independent implementation of the same arithmetic*.
S45 checked **12 shortlist rows** against ground truth; S50 checked a digest
against itself. **A digest is agreement with yourself.** A wrong-but-stable
kernel produces exactly the evidence both spikes reported.

## Falsifier, stated before the run

> *If the NEON kernel is correct and not merely repeatable, it agrees with an
> independently written scalar implementation on **every** row, not 12. If it
> disagrees anywhere, every determinism result resting on it is a statement
> about reproducibility of a wrong answer.*

`cc -O2 -Wall -Wextra -Werror -o check check.c && ./check` — output in `RUN.txt`.
Pinned seed `0xC0FFEE`, the same sequenced xorshift `remeasure.c` uses. The
kernel is **copied verbatim** rather than paraphrased, because a paraphrase
tests my transcription.

## Result

```
SHIPPED CONFIGURATION
  D=1024  words=16  rows=100000  Qnnz=507  max u8 lane  35/255  mismatch 0/100000
```

**The shipped kernel is correct on 100,000 of 100,000 rows** against an
independent scalar reference — 8,333× more rows than S45's 12, and the first
check in this workspace that is about the kernel's *answers* rather than its
stability. The LEDGER's open finding is **closed**, and closed in the direction
S52 hoped for.

## The finding S52 did not ask for, which is the larger one

`vsum` is a **`uint8x16_t`** accumulating `vcntq_u8` results across the whole
word loop. Each lane takes up to 8 per iteration over `WORDS/2` iterations, so
its ceiling is `4*WORDS`, and **nothing in either file bounds it** — no assert,
no comment, no test. `D` is a `#define` and a design parameter.

```
  D=1024   words=16   max u8 lane  35/255   mismatch    0/2000
  D=2048   words=32   max u8 lane  49/255   mismatch    0/2000
  D=4096   words=64   max u8 lane  90/255   mismatch    0/2000
  D=8192   words=128  max u8 lane 162/255   mismatch    0/2000
  D=16384  words=256  max u8 lane 308/255   mismatch 2000/2000   neon 12078, scalar -210
  D=32768  words=512  max u8 lane 580/255   mismatch 2000/2000   neon 22462, scalar  -66
```

**At D ≥ 16384 every single row is wrong.** The lane saturates, wraps, and the
kernel returns a confident number with the wrong *sign*. There is no crash, no
warning, no instability.

**This is the one failure mode the replication wedge cannot see.** The whole
asset is *"a result is trusted because anyone can re-run it and compare bytes"*.
This failure is **deterministic**: every worker on every ISA computes the same
wrong score, every digest matches, every replica agrees, and quorum is
unanimous. Byte-identical agreement is not evidence of correctness, and this is
a concrete instance rather than a caution.

### The bound, so it is checkable rather than remembered

Per-lane maximum is `4*WORDS`, so the only `D` that is safe **regardless of the
data** is:

```
4 * (D/64) <= 255   ->   D <= 4080
```

- **D = 1024 as shipped**: safe by proof, and measured at 35/255 — 7.3× headroom.
- **D = 8192**: passes here *only because the random mask is ~50% dense*. It is
  **past the provable bound** and its 162/255 is a property of the test data,
  not of the kernel. `S45` builds its mask as `~(a ^ b)` — an *agreement* mask,
  which is denser than random — so a real corpus reaches saturation sooner than
  this sweep does.

The one-line guard is `_Static_assert(4 * WORDS <= 255, "u8 lane saturates");`.

**Not applied here.** `S45` and `S50` are other lanes' published spikes with
committed binaries and recorded digests; editing their source would put the
source out of step with the artifact whose digest is published, which is family
**C** — the exact defect `provenance.py` exists to catch. Proposed in
`CHANNEL.md` for whoever owns them.

## Controls

- **The check can fail.** It fails 2000/2000 at D=16384 and 32768. A correctness
  check that has never been seen red is the thing H7 exists to distrust, so the
  sweep is part of the run and not a separate mode.
- **The reference is independent.** No intrinsics, no vector types, no
  saturation surface: one `__builtin_popcountll` per word. Written to be
  obviously right rather than fast.
- **Pinned seed** `0xC0FFEE`, sequenced xorshift, one update per statement.

## Not claimed

Nothing about cross-platform behaviour — one host, `arm64 Darwin`. This is a
statement about the *arithmetic*, and it needs no second machine: the reference
and the kernel run in the same process on the same inputs. Nothing about
performance; `bench.h` is S50's and untouched.

`check` is a build artifact and is **not committed** (§13). `check.c` is.
