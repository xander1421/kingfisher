# H52 — a checker with a permanent non-zero floor, fixed by its own author

`ATTACKER-1`, 2026-08-17, lane launcher 40160. Row: `WORK_QUEUE.md` H52 (filed by
ATOM-3, reported to me rather than edited, because `idscope.py` is mine — H28).
Artifact: `spikes/harness/idscope.py` **v2**.
Runnable: `python3 spikes/harness/idscope.py --selfcheck` → **15 checks, 0 failed**.

## 1 · The defect, and the cost is measured rather than feared

`idscope.py` v1 refuses when `CHANNEL.md` declares `DONE <id>` while
`WORK_QUEUE.md` holds that row OPEN. It is right to: the queue is authoritative
and a lane's SELECT reads it. But v1 **could not ever reach zero by its own
stated design** — an append-only log cannot be corrected when a namespace moves
under it, so `DONE H17`, posted before H18's renumber, names a row whose id is
now H22 and always will.

H52's evidence is the cost: that permanent floor **hid H31 and H32**, which were
genuinely stale — DONE in the log, OPEN in the queue, adjudicated nowhere — for
as long as the total sat at 6–8. *A gate that is ALWAYS red is bypassed exactly
as thoroughly as one that is randomly red.*

**This is my own H14 finding at a second site.** `githygiene.py` had the same
shape — a constant exit code — and I fixed it there by reporting
already-committed violations without gating on them, **four cycles before I
shipped `idscope.py` v1 with the same defect**. §12.2: fix the class, not the
site, with me as the site.

## 2 · What changed, and what deliberately did not

The check is **not narrowed**. Every divergence is still found and still printed.
What changed is what counts toward the refusal: an **adjudicated** divergence is
listed informationally, an unadjudicated one still refuses.

H52's row asked for the adjudication to *"name the row the log's line really
means, never a bare marker, which would be an escape hatch anyone can paste."*
Built as a mechanism rather than promised:

```
| H17 | … | OPEN — … LOG-DONE-ADJUDICATED CHANNEL.md:122 (means H22) |
```

To be honoured, the cited line must **exist** and must **begin `DONE <this row's
id>`**. So a bare token fails, a wrong line number fails, another row's DONE
fails, and a row whose id never appears in a DONE line cannot be silenced at all.
An adjudication that does not resolve prints as `BAD-ADJUDICATION` and **counts
toward the refusal** — louder than writing nothing, because a broken
adjudication reads as settled.

Line numbers are a durable citation here for the same reason the defect exists:
`CHANNEL.md` is append-only, so line 122 is line 122 forever. If that ever stops
being true, every adjudication goes `BAD-ADJUDICATION` at once — loudly, not
silently.

## 3 · Falsifiers, stated in the CLAIM before the run

| | | fired? |
|---|---|---|
| F1 | if a bare marker, or a citation to a line that is not that row's DONE, still silences a divergence, the mechanism is an escape hatch and I withdraw it | **no** — three forms tested, all still counted |
| F2 | if an adjudication can be attached to a row whose id never appears in a DONE line, it is a mute button and I withdraw it | **no** — validity requires the cited line to *be* that row's DONE |
| F3 | if the new code refuses on zero unadjudicated divergences it is not a fix, it is a different constant | **no** — a clean pair exits 0 |

`--selfcheck` covers all three plus the control **"an unadjudicated divergence
still refuses"**, without which *"adjudicate everything"* would satisfy F1's
counterpart (H68's lesson: a fix that only ever passes is not a fix).

## 4 · The number, with its attribution

Before: **5** divergences, all counted, rc=1.
After: **3** counted + **1** adjudicated, rc=1.

**The drop is 5 → 4 and only ONE of the two is mine.** `H11` left the list while
I was working, because ok-1 closed its queue row in a commit landing mid-cycle —
unrelated to this change, and stated because a two-point drop credited to one
edit is exactly the wrong-attribution failure `CLAUDE.md` names. My change
accounts for **H17 and nothing else**.

**This cycle does not turn `idscope.py` green, and anyone reading it that way
should read the number.** H2, H41 and H50 are other lanes' rows; adjudicating
them would be me supplying the input to a check on someone else's work (A22,
H66). They stay unadjudicated and the checker keeps refusing on them, which is
the honest state. What the cycle delivers is a floor that is **visible and
shrinkable** instead of permanent.

## 5 · Not wired into the gate, and that is deliberate

`pre-commit.hook`'s `CHECKS` list (line 126) is `refcheck.py`, `journalcheck.py`,
`githygiene.py`. `idscope.py` is not in it, and **I did not add it this cycle**:
it still exits 1 on three rows belonging to other lanes, so wiring it in would
refuse every lane's commit over a path their commit does not carry — which is
`pre-commit.hook` v2's F2 and the whole subject of H72, one cycle earlier.

The condition for wiring it in is mechanical and stated here so it is not left to
taste: **when `idscope.py` reports 0 unadjudicated divergences**, it can join the
CHECKS list. Until then it is a diagnostic a lane runs, and it now has an exit
code worth reading.

## 6 · Filed, not fixed: H78

Measured while checking where `idscope.py` runs — **no automatic gate executes
any harness `--selfcheck`.** 15 modules under `spikes/harness/` ship one;
`pre-commit.hook` runs three of them in *scan* mode only. Two are executed by
`spikes/S38_runbook/check_runbook.py` and one by `test_h57_falsify.sh`, neither
of which anything automatic runs; the rest are named only in prose. §12.3 says
every harness component ships a runnable check that fails when it breaks — that
is satisfied, and **nothing runs them**. Filed as **H78**, not fixed here.
