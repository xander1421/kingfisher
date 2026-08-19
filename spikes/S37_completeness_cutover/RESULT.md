# S37 — the completeness verifier now binds the proof to the query

`repro: python3 spikes/S37_completeness_cutover/cutover.py`
`consumers: sh spikes/S37_completeness_cutover/consumers.sh <out.tsv>`
`resolution: python3 spikes/S37_completeness_cutover/which_module.py`
`check: python3 kitchen/test_s37.py`

**`certify ok=True`, 3 controls all fired, 3 preregistered falsifiers RAN and
NONE fired.** `trie_witness.verify_completeness` is **v3**.

## THE GATE THIS ROW SAT BEHIND HAD LIFTED, AND ONE COMMAND SAID SO

The row's stated blocker was *"`trie_witness.py` carries **145 uncommitted lines
from another lane**"* — correctly refusing to run into H19/H66.
`git status --porcelain spikes/W2_witnessed_trie/` is now **empty**; those lines
are in `330df18` with `903f5c6` (H51) on top. §3 says gates are respected and
never waited on, and W5's DONE line last cycle was the same shape — *the gate
expired without anyone saying so*. **Nothing in this repo tells a lane when one
lifts; checking cost one command.**

## WHAT WAS WRONG, AND IT IS A SOUNDNESS HOLE

The COVER branch authenticated the answer against the **root** and never bound it
to the **query**, while `verify_membership` and `verify_non_membership` both
re-walk unconditionally — with the reason in their own source, *"so a proof of a
different key cannot be replayed for this one."*

So a prover asked for prefix `q` could return the **complete, unforged,
byte-identical honest proof** for a deeper prefix `q2` it held, and it verified:
the keys start with `q` because they start with `q2`, they are canonical, and the
subtrie folds to the root **because it is a real subtrie**.

S36's three tamper controls — omit / add / alter, 37/37 each — could not see it.
All three rewrite `pf['keys']` and keep the honest path, so they are one attack
shape tested three ways.

## F3 — THE EXHIBIT, against the EXACT module replaced

| | honest proofs accepted | replay proofs accepted |
|---|---:|---:|
| **pre-S37** (`git show HEAD:.../trie_witness.py`) | 37 / 37 | **37 / 37** |
| **v3, lifted** | 37 / 37 | **0 / 37** |

Worst job, and it is not a corner case:

```
q               0000000200000004
q2              0000000200000004000000
true answer     394 keys
claimed         12 keys          (382 OMITTED)
proof unforged  true             (byte-identical to prove_completeness(root,q2))
pre-S37         ACCEPTS
v3              REJECTS
```

**The comparison is against the module this cutover replaced, read out of git,
not against `S20_verify_kinds/w2_head/trie_witness.py`.** That pin is an *older*
frozen HEAD with a different sha256, and using it as "the old version" would be a
citation to the wrong artifact — family C.

## F1 — the cutover is not free, and the tightening is not a blanket reject

**Honest 37/37 still accepted through the LIVE module.** A verifier that rejects
everything scores perfectly on every attack in S36's file, which is why this arm
exists and why it is stated as an acceptance count and not a rejection rate.

## F2 — every consumer re-run, and the green is PARTLY VACUOUS

**All 12 consumers identical before and after** (`consumers_before.tsv` vs
`consumers_after.tsv`, rc + `certify ok=` + problem counts; deliberately not a
stdout hash, because these scripts print timings that move for reasons unrelated
to this change).

**The queue row says "the nine importers". That number is stale.** Resolved
mechanically (§12.4): `grep -rl verify_completeness spikes --include=*.py`
returns **12** consumers plus the module.

**AND THE MEASUREMENT THAT MAKES F2's GREEN HONEST — 5 OF THE 12 CANNOT SEE THIS
CHANGE AT ALL.** `which_module.py` runs each consumer and reads
`sys.modules['trie_witness'].__file__` rather than trusting the import line:

```
live 7 | pinned copy 5 | unresolved 0

S20_verify_kinds/verify_kinds.py          -> w2_head/trie_witness.py   (PIN)
S24_range_crossover/range_crossover.py    -> w2_head/trie_witness.py   (PIN)
S27_verify_floor/verify_floor.py          -> w2_head/trie_witness.py   (PIN)
S36_witnessed_job/witnessed_job.py        -> w2_head/trie_witness.py   (PIN)
S36_witnessed_job/attack.py               -> w2_head/trie_witness.py   (PIN)
```

`verify_kinds` installs S20's frozen HEAD copy on `sys.path` **under the bare
name `trie_witness`**, so every module importing `verify_kinds` first gets the
pin for the rest of the process. **A consumer that never resolves to the live
module cannot change when the live module changes**, so for those five F2's
"identical" is a tautology and is labelled one here rather than counted as
evidence.

**THE LIVE CONSEQUENCE, AND IT IS CLAIM DECAY IN THE MAKING: `S36/attack.py` WILL
GO ON PRINTING `witnessed_accepts_replay: true` AFTER THIS FIX.** It is reading
the pin. The hole is closed in the live module and open in S20's frozen artifact,
which is what a pin is *for* — but a reader who runs S36's attack tomorrow will
conclude the fix never landed. Filed as an OPEN row rather than fixed here:
repointing five spikes' `sys.path` is a separate change with its own blast
radius, and §12.1 says a defect is a row, not a side fix.

**S36's finding is unaffected either way**: the hole is present in *both* the pin
and the pre-S37 HEAD (37/37 replay accepted, measured here against HEAD).

## MY OWN DEFECTS THIS CYCLE, ALL THREE CAUGHT BY THE ARMS THEMSELVES

1. **`consumers.sh` wrote to a RELATIVE outfile while `cd`-ing into each
   consumer's directory**, so the "after" run produced an **empty file** and the
   diff read as *all 12 consumers changed*. The loudest possible way to be wrong
   quietly. `OUT` is now absolutised before the first `cd`.
2. **`which_module.py` v1 compared raw path strings** and reported `live 3` while
   five consumers were plainly resolving to the live file — their `sys.path`
   entries carry `..` segments, so equal paths were unequal strings. A comparison
   wrong only for the *passing* case reads as a finding. `realpath` both sides.
3. **`which_module.py` v1 also swallowed the reason** with
   `except BaseException: pass` and printed `UNRESOLVED` for all 12 — a
   clean-looking answer with the diagnosis discarded, family B. The exception is
   now reported.

And one that bit this file before it bit anything else: **`import attack`
resolved to W2's `attack.py`**, not S36's, because W2 is first on `sys.path` —
two spikes both named their attack module `attack`. Loaded by path instead. That
is the same shadowing class as the five pinned consumers above, met twice in one
cycle from opposite directions.

## W2's OWN ARTIFACTS ARE DELIBERATELY NOT REGENERATED

`trie_witness.py` changed, so `W2_witnessed_trie/*.json` would normally be
re-derived beside it. They are restored to HEAD instead, and the reason is a
finding this cycle turned up: **those artifacts do not reproduce byte-for-byte
across runs of unchanged code.** `W7_streaming_witness` publishes a different
`final_chain_head` on every run — three runs, three heads — and
`PYTHONHASHSEED=0` makes it stable, so CPython's per-process string-hash
randomisation is reaching a commitment. Regenerating here would replace one
unreproducible value with another and record it under my `Atom:` as though it
were the consequence of the cutover. **Filed as H197**, measured before claiming.
The same re-runs also moved `S85`'s crossover fuel figures and `W6`/`W7`'s
`mean_us`, which are timings and expected to move; the chain head is not.

## SCOPE

`prove_completeness` is unchanged; only the verifier tightened, so existing
proofs on disk remain valid inputs. The non-COVER branch is untouched — it
already re-walked. This says nothing about membership or non-membership proofs,
which were already query-bound.
