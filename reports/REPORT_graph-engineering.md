# REPORT — codejunkie99/graph-engineering

**Assessed 2026-08-18. Verdict: SPEC, worth reading, worth zero as evidence.**
Adopt the vocabulary and the checklist; cite nothing from it as a number.

## 1. Identity

| | |
|---|---|
| URL | https://github.com/codejunkie99/graph-engineering |
| Licence | **MIT** — PORT allowed under §7's gate, with attribution + a NOTICE entry |
| Stars / forks | 421 / 58 |
| History | **1 commit on master** |
| Shape | Markdown + a packaged `graph-engineering.skill`. **No executable code.** |

Origin: a translation of Southeast University's graduate Knowledge Graph course
into a Claude Code skill.

> 421 stars against 1 commit. Popularity is not evidence and is not a licence
> to skip the read — noted because in this tree an unchecked citation is worse
> than none (§12.4).

## 2. What it is

A 9-stage knowledge-graph pipeline plus task-graph orchestration patterns:

```
scope · representation · ontology · entities · relations · events
      · quality gate · fusion · serve to LLMs
```

Its thesis, and it is a good one: *"Prompt engineers steered the model's words.
Loop engineers steered its iterations. Graph engineers steer its topology."*
And: *"A knowledge graph is a product with a schema, not a pile of triples."*

## 3. The three parts with real content

Read `references/fusion-and-llm.md` if you read nothing else.

**Fusion in three layers**, which is a genuine technique and not a slogan:
- *string* — normalised / alias / acronym match
- *attribute* — compatible attributes (same founding year, same email domain)
- *structure* — *"two 'J. Smith' nodes sharing 3 coauthors and an affiliation
  are the same person"*

**Adjudication policy**: *"auto-merge only above high confidence; auto-reject
below low; queue the middle for LLM adjudication."*

**Serving a graph to an LLM**, the most directly usable paragraph:
*"entity-link the query → expand k hops (k=1-2; beyond 2 is noise without
re-ranking) → serialize the subgraph as compact triples/paths with provenance"*,
formatted `(head)-[REL {time, source}]->(tail)`, grouped by head entity.

## 4. What it does not have, and why that is decisive here

**No F1, precision, recall or MRR. No confidence thresholds. No benchmark
datasets. No complexity bounds. No evaluation protocol.** The adjudication
policy names "high" and "low" confidence and supplies neither number.

That is fine for a course synthesis and disqualifying as evidence in this tree:

- `CLAUDE.md` opens with *"before you believe a number, run the checks"*, and
  `certify` **refuses** rather than warns. There is nothing here to certify.
- Its named failure — **claim decay across documents**, "404s" → "deleted" →
  "the project failed" — is exactly what happens to a well-written framework
  with no numbers: the stage names become vocabulary, the vocabulary gets cited,
  and three documents later a citation reads as a measurement.
- `k=1-2; beyond 2 is noise` is an *assertion*. It is plausible, it is
  probably right, and it has no measurement behind it. On this graph, at this D,
  with this prefilter, nobody knows.

## 5. Where it lands in the mission

**The data pipeline is the one role `MISSIONS.md` names as unowned** — `corpus/`,
`graph.tsv`, the citation excerpts and FB15k-237 ingestion are "mine by accident,
not by allocation". This is a checklist for exactly that lane, and its 9 stages
are a better skeleton than the one we have, which is none.

It is **complementary to G30, not a substitute**: G30 supplies filtered MRR /
Hits@k against AMIE, RuleN and AnyBURL — the numbers this document lacks — while
this supplies the stage names G30 has no reason to invent. Take the ordering,
measure everything.

Cross-checks against work already done here, which is the useful comparison:

| its stage | what this tree already has, measured |
|---|---|
| quality gate | `certify`, `refcheck`, `journalcheck`, `githygiene` — gates that refuse |
| fusion | nothing. **The clearest gap it names.** |
| serve to LLMs | the MeTTa path; S40 now prices the deployable cutoff |
| entities / relations | the G-series on FB15k-237, with real MRR |

## 6. Recommendation

1. **Read `fusion-and-llm.md` and `modeling.md`.** The three-layer fusion split
   and the k-hop serving recipe are worth having as a starting shape.
2. **Do not install the skill into a lane's context.** It is prompt text that
   would be read every turn by an agent that already carries a brief; §12's
   whole problem this week has been superseded wording with wide readership.
   Read it, cite it, do not load it.
3. **If any of its assertions is used, measure it first** and record it as ours.
   `k≤2` is the obvious first candidate and is cheap to test on FB15k-237.
4. Licence is MIT, so a NOTICE entry is owed if anything is lifted verbatim.
   Nothing has been.

**Nothing from this repository has been cloned, copied or installed.**
