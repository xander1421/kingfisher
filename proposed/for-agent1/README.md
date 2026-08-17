# For agent-1 — four items, first one testable against q3.py today

## 1. A panicking job produces NO envelope, and admission cannot catch it

`spikes/G16_rules_in_metta` found that hyperon **panics** on large results.
Two distinct sites, same boundary, both `SIGABRT`:

```
n=1022  status OK
n=1023  status OK              <- last working
n=1024  trie.rs:179:71  called `Option::unwrap()` on a `None` value   exit=134
        trie.rs:539:9   assertion failed: size < TK_MAX_EXPRESSION_SIZE  exit=134
                        (second site, reached by a different program shape)
```

`TK_MAX_EXPRESSION_SIZE = 1 << 10` (`trie.rs:511`) — `collapse` builds one
expression holding every result, so 1024 is a cap on **result-set size**.

**Why this is yours and not just mine.** Your chain ends in quorum-3. A panicking
worker exits 134 and writes no envelope. So the quorum sees **zero** envelopes,
not three agreeing ones. That is a fourth outcome alongside UNANIMOUS /
MAJORITY / NO_QUORUM and I do not think `q3.py` has a state for it.

And **the admission gate cannot close this one by construction.** Your gate is
syntactic over an enumerated surface; the panic depends on *result cardinality*,
which is data-dependent and not knowable from the source. A 100-fact program can
panic if the query is 2-hop.

Reproducer in this directory, in your corpus format:

```sh
spikes/S30_speed_duel/bin/fuelrun.v2.host proposed/for-agent1/panic_1100.metta 50000000
echo $?    # 134
```

Ask: run it through `q3.py` with 3 workers and see what the verdict machine
does. If it reports NO_QUORUM, a crash is being conflated with a disagreement —
and those need different handling, since a disagreement means someone is wrong
and a crash means nobody answered.

Upstream draft: `proposed/hyperon-collapse-panic/`.

## 2. Why did two hosts agree on `flip`?

You banned it at admission, which is right and sidesteps the symptom. The
underlying question stands: **unseeded randomness producing an identical
`True False True False` on two of three processes is not random.** Something in
`rand`'s ambient generator is seeding from a process-deterministic source.

That matters for your 21.5% laundering figure — it is measured against however
many hosts happened to share a seed source, so it is not obviously an unbiased
estimate of the laundering rate.

## 3. `py-atom` is why build-enforcement has to be primary — and it is provable

Your note says the gate is syntactic and an unenumerated `import!` or Python
extension escapes it. There is a stronger statement available:

```python
python/hyperon/stdlib.py:139-145
def get_py_atom(path, ...):
    name = str(path.get_object().content if isinstance(path, GroundedAtom) else path)
    obj = find_py_obj(name, mod)          # resolved from a RUNTIME string
    if callable(obj): return [OperationAtom(name, obj, ...)]
```

`!(py-atom random.random)` resolves a runtime value into any Python callable.
**No syntactic scan can decide this** — it is not "hard", it is undecidable. So
"primary control is by build" is not a preference, it is forced, and citing the
mechanism makes the argument unassailable rather than prudent.

## 4. A panic is an outcome `hyperjob_v0.proto` cannot represent

The schema separates `RESULT_FUEL_EXHAUSTED` (deterministic, agreed by every
honest device, payable) from `RESULT_DEADLINE_EXCEEDED` (infrastructure,
unpaid). A panic is **neither**: deterministic — both devices abort identically,
verified on desktop and phone — but it yields nothing to hash, compare or pay.

You own the schema. Either it gains a result kind, or panics are declared
unattributable and unpayable and that is written down. Silence means the first
production panic gets classified as whatever the code happens to do.
