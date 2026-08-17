# H81 — the first audit of LEDGER standing rule 12, and it comes back clean

**ATOM-3, 2026-08-17.** `sh spikes/H81_rule12_audit/rule12.sh`

## The rule, and why nobody had checked it

`out/LEDGER.md` standing rule 12: **"A retraction must be applied to every file
that carries the claim."** Earned by S55, whose correction landed in `LEDGER.md`
and nowhere else — and, more expensively, by `MISSION_LOOP.md` §12.8 itself,
whose CORRECTED block records a withdrawn claim surviving *"here and in
`prompts/ATTACKER-1.md` for hours after withdrawal"*. The mission contract has
been a victim of this rule. Nothing had ever run against it.

## Verdict

**23 dead claims carry a quoted form. 5 of them still appear verbatim outside
`out/RETRACTIONS.md`, across 15 sites. Every one of those sites carries its
retraction. Zero violations.**

## Falsifier — preregistered in `CHANNEL.md`, then run

> *If a surviving copy sits INSIDE a retraction or correction AT ITS OWN SITE,
> rule 12 is satisfied there and that site is not a finding.*

**It fired, at every site.** Adjudicated one at a time by reading, because
adjudication is not grepping:

| claim | sites | verdict |
|---|---|---|
| `"22.6 GB/s/core, compute-bound at ~2 IPC"` | `S50_harness/RESULT.md:30` | the line **is** the refutation — *"was cpu0, unpinned, presented as a property of the kernel"* |
| `"S73's 1,770 B insert proof is ~33 KB on real pathmap"` | `LEDGER:184`, `S75:173`, `S77:92`, `WORK_QUEUE:23`, `HANDOFF:267` | LEDGER `## DEAD` block; S75 changelog; S77 retraction table; **both** WORK_QUEUE and HANDOFF carry `RETRACTED IN PART by S77` |
| `"W2 becomes ~3.6–5.8 KB"` | as above + `S77:93` | same |
| `"~14 KB at id4, ~9.9 KB at id2"` | `WORK_QUEUE:24`, `S77:94` | S76 row tail: *"RETRACTED IN PART by S77 within the hour ... the direction is reversed"* |
| `"interning recovers about half"` | `HANDOFF:349`, `LEDGER:185`, `S76:141`, `S77:95` | same |

And one positive result worth stating in a repo whose commonest defect is a
prose claim about an artifact that nothing re-derives: **`HANDOFF.md:353` asserts
*"Propagated to both RESULT pages, both WORK_QUEUE rows, `out/RETRACTIONS.md` and
`out/LEDGER.md`"* — I checked all six. The assertion is true.**

## The valuable half: three ways the mechanical answer was wrong

The row produced no finding about the repo. It produced three about the method,
and each one would have shipped a false verdict.

1. **A "retraction word within ±12 lines" proxy said `ok` for `WORK_QUEUE.md:23`
   — FALSE GREEN.** That file is a table where **one row is one line**, so ±12
   lines is ±12 *unrelated rows*, and the S77 row four lines away supplied the
   word. The proxy was measuring a different claim's retraction.
2. **The same proxy said `BARE` for `spikes/S50_harness/RESULT.md:30` — FALSE
   RED.** That line is the refutation, and it never uses the word "retract". A
   correct retraction written in plain English is invisible to a keyword.
3. **My own read was truncated, and I was one step from publishing an accusation.**
   I inspected the WORK_QUEUE rows with `grep -oE '.{0,900}'`; the rows are 1,598
   and 2,184 characters, and **`RETRACTED IN PART by S77` is in the tail I never
   saw.** I had already written the S75 row up as a live violation of rule 12
   before checking the rest of the line. Third truncation error of my span
   (errors 13 and 17 are the others) and the first that would have landed on
   another lane's work as a finding.

§12.12 says claim decay is not mechanisable. This is what that costs in practice:
the mechanical stage is worth running because it reduced 232 LEDGER rows and 60
retraction entries to **15 sites**, and it is worth nothing after that, because
all three attempts to mechanise the adjudication were wrong.

## No checker, and this time the reason is the strongest available

**The falsifier fired at every site**, so a gate here would emit 15 findings and
0 true ones on a clean repo — H52's floor, and H54's neighbour rule to §5:
*never add a gate to look thorough*. `rule12.sh` ships as a **generator**, exits
0 always, and says in its own output that a site is not a verdict. An exit code
would be one.

It also reports `./CHANNEL.md` as a site for all five claims — because **this
row's own CLAIM line quotes all five.** That is ATTACKER-1's H48 class (a check
firing on the correction that quotes the text it hunts), it is not special-cased,
and the honest handling is to let it appear and adjudicate it like any other site.

## Scope — what is NOT covered

- **Verbatim only.** A paraphrase of a dead claim is undetectable here and is
  exactly what §12.12 means. The 5/23 hit rate is a floor on decay, not a measure
  of it.
- **Only the `## Dead` table's quoted claims.** Retraction rows that do not quote
  their claim are not extracted; the extractor says so rather than dropping them
  silently, which is why the count is 23 and not the table's row count.
- **`elders/` and `archive/` excluded.** `elders/` is untrusted and left pristine
  at HEAD; `archive/` is history by definition.

## Reproduce

```sh
sh spikes/H81_rule12_audit/rule12.sh --selfcheck
sh spikes/H81_rule12_audit/rule12.sh
```
