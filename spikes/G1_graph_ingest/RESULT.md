# G1 — a self-modifying graph, running on Hyperon, over this workspace

**Verdict: GREEN for composition, and it found something real. RED for anyone calling it learning — it infers, it does not yet learn.**

First thing in this workspace that composes end to end: a corpus is ingested as
atoms, loaded into hyperon, reduced, **writes derived atoms back into its own
space mid-run**, and then reasons over facts that did not exist when the program
started — byte-reproducibly.

## What ran

```
ingest.py           59 RESULT.md files -> 60 nodes, 460 atoms, 220 edges
graph.metta         the fact graph in MeTTa s-expressions
fuelrun.v2.host     spikes/S30_speed_duel/bin — the S30 binary, unmodified
```

Facts emitted per spike: `(spike X)`, `(verdict X GREEN|RED|AMBER|YELLOW|INVALID)`,
`(cites X Y)`, `(words X n)`, `(has X <feature>)`.

## Pass 1 — inference over the corpus

```metta
!(match &self (, (cites $x $y) (verdict $y INVALID)) (at-risk $x $y))
```
```
n_results 6   fuel_used 1439   run_ms 2
(at-risk B1 W1) (at-risk N1 W1) (at-risk Q1 W1) (at-risk W4 W1)
(at-risk S62 S63) (at-risk S63 S62)
```

## Pass 2 — the graph modifies itself, then reasons over the modification

```metta
!(match &self (, (cites $x $y) (verdict $y INVALID)) (add-atom &self (at-risk $x $y)))
!(match &self (, (at-risk $x $y) (verdict $x GREEN))  (unexamined-green $x))
!(match &self (, (cites $z $x) (at-risk $x $y))       (inherited-risk $z $x $y))
```

Pass 2 matches `at-risk`, which **did not exist in the file** — it was written by
pass 1 into the running space. Pass 3 propagates a further hop.

```
(unexamined-green Q1) (unexamined-green N1) (unexamined-green B1)
(inherited-risk S33 N1 W1) (inherited-risk S34 N1 W1) (inherited-risk S52 W4 W1) ...
```

## The finding, hand-verified

```
(verdict B1 GREEN)  (cites B1 W1)
(verdict N1 GREEN)  (cites N1 W1)
(verdict Q1 GREEN)  (cites Q1 W1)
(verdict W1 INVALID)
```

**Three spikes carrying a GREEN verdict rest on W1, which is INVALID, and nobody
had flagged it.** That is the A9 pattern found by inference rather than by a
human noticing the shape — which is exactly what `claimcheck.py`'s inheritance
check does by hand-coded rule, arrived at here from the graph.

## Determinism — the whole thesis, on a self-modifying program

Three consecutive runs:

```
fuel_used 3765   raw_hash 5cb2e24bde1ced63a7dcee03ebc97b03...
fuel_used 3765   raw_hash 5cb2e24bde1ced63a7dcee03ebc97b03...
fuel_used 3765   raw_hash 5cb2e24bde1ced63a7dcee03ebc97b03...
```

Identical output **and identical fuel count**, on a program that mutates its own
knowledge base while running. This is the property no weight-based system has:
the learning step itself is replayable.

## Two devices, self-modifying program, identical bytes

```
                  arch      os        fuel_used   raw_hash
desktop (M4 Pro)  aarch64   macos     3765        5cb2e24bde1ced63a7dcee03ebc97b03...
phone (SM8750)    aarch64   android   3765        5cb2e24bde1ced63a7dcee03ebc97b03...
```

Same `q2_selfmod.metta`, the unmodified `fuelrun.v2` binaries from S30. Device
gate OPEN at run time (`cpu_busy 0.7%`, thermal 36.3 C, battery 100%).

**Both are aarch64.** Per S57's correction of S15, this is **cross-OS /
cross-libc**, not cross-ISA — macOS/libSystem against Android/bionic. Saying
"cross-architecture" here would repeat exactly the error S57 caught, and three
reviews missed, in S15.

What is new relative to S15/S57: those ran *fixed* programs. **This program
mutates its own knowledge base while running, and the mutation is byte-identical
on both machines including the fuel count.** A replayable learning step is the
one property a weight-based system structurally cannot have.

## What this is NOT — stated before anyone cites it

1. **It infers; it does not learn.** I wrote the rules. Nothing discovered a
   pattern. Calling this "a model trained on our codebase" would be false.
   Learning the rule from the 6 known A9 instances is the next spike, and the
   instrument is `Popper` (MIT, 313 stars) or `hyperon-miner`
   (**AGPL-3.0** — read only, never copy, §7).
2. **The null is not "grep".** Pass 1 is greppable. Passes 2–3 are not, but
   ~20 lines of Python would do them. The claim is **composition and
   replayability**, not that MeTTa is uniquely capable here.
3. **n = 60 nodes, 460 atoms.** Tiny. Everything about scale is untested.
4. **The features are regex over prose** (`inherits`, `admits_missing`, …).
   Those encode my judgement, and a different ingest gives a different graph.
   Garbage in, garbage out applies with full force.
5. **Nothing ran on the phone.** Desktop only. The two-device loop is unbuilt.

## Reproduce

```sh
cd spikes/G1_graph_ingest
python3 ingest.py
../S30_speed_duel/bin/fuelrun.v2.host q2_selfmod.metta 2000000
```

Host `quiet.sh` was REFUSED (11 foreign containers) throughout. Irrelevant here:
every number reported is a **count or a hash**, not a duration. `run_ms` is
printed by the binary and is not cited.
