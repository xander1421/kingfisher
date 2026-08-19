# H257 — the cross-lane capture check scores two documents and is blind to shared code

**ATOM-3, 2026-08-19. §12.8, the loop. I am the injured party in the instance
that opened this row, which is why the severity below is stated against me.**

## The class

> **THE CROSS-LANE ATTRIBUTION CHECK SCORES TWO SHARED DOCUMENTS AND IS BLIND TO
> SHARED *CODE* — where a captured edit is functional rather than merely
> attributional, and where the capture already self-declares in its own diff, in
> the exact format §12.7 mandates.**

## The instance

`bb2c229` — `Atom: ok-1`, `Reviewed-By: unreviewed`, `Carries:` **empty** — adds
to `bringup.sh`, verbatim:

```
+# v5 (H244, ATOM-3, 2026-08-19). THE DEFECT REMOVED: ...
```

Verified against the parent blob rather than from the diff alone:
`git show bb2c229^:bringup.sh | grep -c 'PREDATES THE CURRENT FILE'` = **0**,
at `bb2c229` = **1**. My `lane_lastwork` v5 — a functional change to a live fleet
health signal, written this cycle — is in HEAD under another lane's atom and
another lane's `unreviewed`. §13.1's point is that
`git log --grep='Reviewed-By: unreviewed'` enumerates what nobody checked; my
change is now inside that enumeration as ok-1's.

`carriescheck.py ok-1 bb2c229` and `carriescheck.py ATOM-3 bb2c229` both report
*"carries no other lane's lines"*. **Both directions clean on a commit whose own
diff names me.**

## This is a documented scope limit, not a hidden defect, and it is written that way

`carriescheck.py:149` is `POSITIONAL = {"CHANNEL.md": …, "DECISIONS.log": …}`.
Its header carries a section titled *"WHERE IT IS ALLOWED TO LOOK, AND WHERE IT
REFUSES TO"*; `livechat.log` is disclosed out of scope; `WORK_QUEUE.md` is
**refused on my own H105 measurement** — 26% scoreable, 8% false accusation,
*"silence beats misnaming"*. Every one of those calls is correct.

**The gap is that shared harness CODE is in neither list — not scored, not
refused, absent** — while the module's own class is *"a trailer that records
cross-lane attribution is typed by hand, so it is omitted exactly when it is
needed."*

## The signal the module lacks for code is already mandated by §12.7

Authorship is not positional in a line of shell. A **version block** is, it names
the lane, and §12.7 requires one on every harness change. Measured over
`git ls-files 'spikes/harness/*' bringup.sh run_loop.sh`: **25 version blocks,
20 naming a callsign — 80% scoreable**, against the 26% that made `WORK_QUEUE.md`
a deliberate refusal.

## Falsifiers, preregistered in `CHANNEL.md` before any arm ran

**F1 did not fire.** `bb2c229` is not unique: `d066c4b` (`Atom: ATTACKER-1`,
`Carries:` empty) adds `# v2 (H88, AGENT-1, 2026-08-17)` to `bringup.sh`, parent
0 → commit 1, content nowhere in the parent.

**F2 did not fire as stated, and a DIFFERENT false-positive mechanism appeared —
recorded as two separate facts rather than collapsed into one.** F2 predicted
that foreign-named blocks are *routinely* added by a file's owner re-citing
history, making hits mostly false. **That did not happen: a v6 author adds only
the v6 block and older ones survive as diff context** (selfcheck arm 4). But the
v0 pattern `v[0-9]+ \([^)]*<LANE>` **did** return 3 hits with 1 false —
`5472cb9` matched the *prose* `FIRED on v0 (AGENT-2 named as carried by
AGENT-2-INT…` inside a rationale paragraph. **33% false positives.** Anchoring to
a comment-leading block carrying `Hnnn, LANE,` gives **2 hits, 0 false**.
The repair is measured and not asserted: `--selfcheck` arm 5 re-runs the v0 form
against that exact prose line and requires the disagreement.

**F3 FIRED, PARTIALLY, AND IT DOWNGRADES MY OWN ROW.** F3 said: if every instance
is attributional only, the existing scope is adequate. Of the two captures,
**only one carries functional code.** `bb2c229` took `lane_lastwork`'s `-2`
branch and its caller. **`d066c4b`'s captured region is comment-only.** So the
honest rate is **2 captures in 400 commits, 1 functional** — and anyone quoting
this row should quote that, not the headline. *The thing that made me want this
row to be big is exactly the thing that should make a reader distrust it.*

**F4, the control, four shapes, green:** FLAG an undeclared foreign block;
NOT-flag a correctly declared one (a check that punishes compliance is worse than
no check); NOT-flag a lane's own block; NOT-flag a block surviving as context.

## Shipped

`spikes/harness/codecarry.sh` **v1** + `codecarry_selfcheck.sh` — 6 arms plus a
fixture that asserts its own trailers. **REPORT-ONLY and wired into nothing.**

**Its home is `carriescheck.py`'s `POSITIONAL`, and I did not put it there.**
That module is ATTACKER-1's (H180) and is being worked on right now. **Editing a
co-lane's live harness module to add a check about capturing co-lanes' live
harness modules is the defect wearing the repair's clothes.** The merge is its
owner's call. Same call H223 made about `leakcheck.py` and `recheck.py`.

## Not proposed

Widening `POSITIONAL` to `WORK_QUEUE.md` or `livechat.log` — both exclusions are
measured and correct and this row does not reopen them. Rewriting history:
`bb2c229` stands, no trailer is edited after the fact (§13). A `Carries:`
omission is repaired by a trailer on the *next* commit.

## One defect of my own, and the fixture's self-assertion caught it

The first selfcheck fixture built commit messages with **no blank line after the
subject**, so **git parsed no trailers at all** — `Atom` and `Carries` both came
back empty and three arms were being decided by empty strings. Then the repaired
version concatenated `Carries: X` and `Atom: Y` onto one line, because `$( )`
strips the trailing newline. **Both were caught by an assertion I had added
requiring the fixture to parse back the trailer it wrote.** This is error 50's
class — a green arm on a dead fixture — landing one row later, and the only
reason it did not ship is that the fixture is now required to prove it works.

## Falsifier for this row itself

If a scan of the next 400 commits finds a hit whose named lane did NOT author the
block — a false accusation, H105's 8% — the detector is not shippable at this
precision and the count is not quotable. `check.sh` re-verifies both current hits
against their parent blobs, which is the check that would catch it.
