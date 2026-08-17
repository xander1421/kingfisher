# The app as a q3 quorum member: written, does not work, time-boxed

**`worker_app.py` is complete and the app fails against it with an okhttp error
I could not isolate. `run_app.py` drives the same app, over the same server
module, on the same port, successfully. Reverted `q3.py` to the adb-driven
verifier so the pipeline keeps working.**

## Symptom
```
KFNET  : poll failed: java.io.IOException: unexpected end of stream
         on com.android.okhttp.Address@...      (x9, instantly)
KFWORKER: giving up after 9 transport errors
KFWORKER: FLEET RUN: 0 jobs in 30046 ms, exited on idle
```

## What was ruled out, each by measurement
| hypothesis | test | result |
|---|---|---|
| wrong port | app defaults to 18080; shim was on 18090 | **was true**, fixed, did not resolve it |
| 204 response breaks okhttp | replaced with an empty 200 | did not resolve |
| `Content-Length` on 204 | removed | did not resolve |
| keep-alive / stale pooled socket | `Connection: close` on **both** sides | did not resolve |
| app not launched | verified `KFPREFLIGHT` enqueue lines | app launches fine |
| stale APK | verified installed sha == built sha (A24) | matched |
| jobs queued after launch | shim reordered to preload, like `run_app.py` | did not resolve |
| stale listener on the port | `lsof` | none |
| transport itself broken | `curl` from the device: `/stats` 200, `/job` empty 200 | **transport is fine** |

`curl` on the device drives the same endpoints correctly. So the fault is
specific to `HttpURLConnection` under whatever differs between the two drivers,
and I have not found what differs.

## Round 2 — one real bug found and fixed, the fault itself still unexplained

**FOUND AND FIXED: the app sent no `Authorization` header.** A bearer token was
added to the coordinator and to the shell agent (`agent.sh`), and
`Transport.java` — the third client — was missed at all three call sites. So
every app request got a 401.

Validated the fix against the known-good driver: `run_app.py` went from broken
to **5/5 envelopes, `unauthorised: 0`**. That result also means `run_app.py`'s
earlier 65/65 predates the token and any post-token run would have failed —
the regression existed and was invisible until now.

**A security requirement added to N-1 of N clients fails in the one place, with
an error that names neither auth nor the 401 behind it** (`okhttp: unexpected
end of stream`). That is the transferable lesson and it is worth more than the
fix.

### The shim fault survives the fix, and is now better bounded
With the token threaded through identically, `run_app.py` works and
`worker_app.py` still sees **zero requests reach the server**, while `curl` from
the same device at the same moment gets 401 without a token and 200 with one.
So the tunnel, the port, the server and the token are all fine.

Additionally eliminated this round:
| hypothesis | test | result |
|---|---|---|
| missing auth header | added at 3 sites | **was real**, fixed, insufficient |
| stale WorkManager state | `pm clear` instead of `am force-stop` | no change |
| tunnel down | `adb reverse --list` + curl during a live run | tunnel fine, 200 |
| server not listening | `lsof` during a live run | listening |
| server never parsing | `STATS['unauthorised']` increments for curl, not for the app | **server sees curl, not the app** |

The last row is the whole remaining mystery: same device, same port, same
second — curl's request is parsed by the server and the app's is not.

## Why it is being left
`run_app.py` already demonstrates the substantive claim — the app is a real
fleet member, pulling shards by CID over a dial-out transport and evaluating
in-process, **65/65 byte-identical to host on the admitted corpus**. Folding it
into `q3.py` would raise the `binary` and `manifest` domain axes, but both are
already capped at 1 by `operator`, so it changes no verdict today.

Time-boxed twice now, ~15 cycles total. Round 2 was justified by finding a real
regression (the missing auth header, which was breaking the WORKING driver too).
Round 3 is not: the remaining fault blocks nothing, since `operator` caps the
domain vector at 1 regardless.

## What this costs, stated
- `q3.py`'s phone worker remains `fuelrun.android`, so the quorum contains a
  copy of the **verifier** rather than the **product**. `binary=3` and
  `manifest=1` both understate what a real fleet would have.
- The next person should start from the one asymmetry I never explained:
  the same app, same server module, same port, same preloaded queue — one
  driver works and the other does not.
