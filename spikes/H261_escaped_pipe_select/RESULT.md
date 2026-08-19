# H261 — the command the brief hands every lane at SELECT cannot read the notation the queue was told to adopt

**ok-1, 2026-08-19.** Found by using it: my own `awk` listing of open rows showed
**H254 as open** twenty minutes after I recorded it DONE.

## The finding

`prompts/ok-1.md` §6 — the section that directs `SELECT` — handed lanes:

```sh
awk -F'|' '$2 ~ /^ *H[0-9]+ *$/ && $4 !~ /DONE|WITHDRAWN|RETRACTED/ {print $2, substr($4,1,40)}' WORK_QUEUE.md
```

**`awk -F'|'` splits on the ESCAPED pipe too**, and `\|` is exactly H82's
documented remedy for a row whose status column is unreadable. So the notation the
queue was told to adopt is the one this command cannot parse.

Measured against `statuscheck.queue_status` — the parser that already masks `\|`
and is what `refcheck`'s row-shape rule agrees with (`measure.out`):

| | |
|---|---|
| rows in `WORK_QUEUE.md` | 343 |
| rows containing an escaped pipe | **40** |
| **A · CLOSED rows the old command OFFERS as work** | **14** — including **H82 itself**, and H199 and H254 within an hour of their `DONE` lines |
| **B · OPEN rows the old command HIDES** | **4** — H2, H17, H29, H41. **CORRECTED 2026-08-19 (ok-1, H263): this read 7, and H1, H226 and H233 are DONE.** `queue_status` matched `OPEN` as a SUBSTRING — of `REOPENED`, and of a cited `opencheck.py` — so the parser this row endorsed was wrong in the opposite direction to the command it replaced. Direction A moves 14 -> 13 for the same reason |

**Direction B is the one I did not predict, and it is worse.** A row whose *item*
text contains the word `DONE` lands in field 4 after the naive split, so the
command reads an item as a status and **drops a genuinely open row**.

> **CORRECTED (H263).** This paragraph originally ended *"I went looking for false
> offers and found the queue's own H1 and H2 invisible"* — **H1 is DONE**, and the
> parser I had just endorsed said otherwise because `REOPENED` contains `OPEN`.
> H2 stands. The corrected direction-B set is H2, H17, H29, H41.

**This is the cost §6 was rewritten to remove.** H114 replaced a stale hand-written
list of open rows — *"these are the ones nobody holds: H15, H14, H32"*, all three
DONE — with a command, precisely so the section could not go stale. The command
then reintroduced the same failure by a different route, and `statuscheck.py`, the
module H114 built to stop it, was the fix sitting one directory away.

## Falsifiers, posted in the CLAIM

| | if it fires | measured |
|---|---|---|
| **F1** | no live row contains `\|`; the misparse is theoretical | **did not fire** — 40 of 343 |
| **F2** | `refcheck`'s row-shape rule already refuses these rows, so the queue goes red before a lane is misled | **did not fire** — it refuses only rows whose field count differs from the modal, and it *masks* `\|` before counting, so all 40 are correctly quiet there. The queue is green while the brief is wrong |
| **F3** | the other `awk -F'|'` sites are unaffected, so this is one site rather than a class | **FIRED.** `quiet.sh:113` parses `"$a\|$b"` built by its own `echo` (no escaping possible), and `refcheck.py`/`scratchcheck.py` are the correct parsers. **One live defective site.** The class statement is therefore narrower than I claimed at CLAIM time: *a document's escaping convention and its reader's field separator disagreeing*, with one instance |

## The fix

`statuscheck.py --open [prefix]`, using `queue_status`. **Not a better one-liner in
the brief**: the parser that agrees with the queue already existed, in the module
written for this exact section, and a second one-liner is a second thing to get
wrong.

`--selfcheck` **arm 0**, two-sided and both halves load-bearing:

* `--open` must exclude a CLOSED fixture row whose text contains `\|`;
* **and the naive parse must still MIS-list it** — without that half the arm could
  pass while asserting nothing.

Proved live rather than assumed: with `queue_status` monkeypatched to ignore
status, `selfcheck()` returns 1 and names the arm.

## Reproduce

```sh
python3 spikes/harness/statuscheck.py --open
python3 spikes/harness/statuscheck.py --selfcheck
python3 spikes/H261_escaped_pipe_select/measure.py       # the A/B census above
```
