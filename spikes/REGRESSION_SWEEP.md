# Regression sweep — every runnable entry point, after a day of changes

**Falsifier stated first:** *every runnable entry point still works after today's
changes.* Prediction: false, because the auth change touched a shared module.
**Confirmed false on the first driver tested.**

| entry point | before | after |
|---|---|---|
| `M1_7_transport/run.py` | **BROKEN** — 0/3 envelopes, `unauthorised: 12855` | 3/3 in 0.6 s, `unauthorised: 0` |
| `M1_7_transport/run_app.py` | **BROKEN** (found last cycle) | 5/5, `unauthorised: 0` |
| `M1_7_transport/run_lan.py` | ok | 4/4 over WiFi+TLS |
| `M1_7_transport/keepalive.py` | ok | ok |
| `M2_1_fleet/fleet.py` | ok | ok, 4 policy arms |
| `M1_8_quorum3/q3.py` | ok | ok, 4/4 agree |
| `harness/*.py` (8 modules) | ok | all pass |

Two of seven drivers were silently broken by one change, and both are the ones
that produced headline numbers: `run.py` behind 66/66 and 65/65, `run_app.py`
behind the 65/65 app comparison.

## The number that was printed and never read
Before the fix, `run.py` reported:

```
returned 0/3 envelopes in 300.1 s, 0 status OK
server stats: {... "unauthorised": 12855}
```

The server counted **12,855 rejected requests** over five minutes. The count was
printed on the same line as the failure and named the cause exactly. Nobody read
it — including me, twice, while debugging the *other* driver's auth bug.

**A refusal counter that nothing asserts on is not a control.** It is a number in
a log, and a number in a log has the same evidential weight as a comment.

Mechanised: `kfcheck.certify(counters=..., expect_nonzero=...)` refuses when any
counter is non-zero and undeclared. The one deliberate 401 in `run_lan.py` is
declared; anything else fails the run.

## Why the sweep was the right next action
The auth regression was found by debugging a *blocked* item. That says nothing
about how many other things the same change broke, and the honest response to
"I broke something invisibly" is to check what else, not to fix the one instance
and move on.

Cost: one cycle. Found: one more broken headline driver.

## Standing rule
After any change to a shared module — `server.py`, `shardstore.py`, `canon.py`,
`bansurface.py`, anything in `harness/` — run every entry point that imports it,
not only the one being worked on. `grep -l '<module>' */*.py` is the list.
