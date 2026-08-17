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

## Why it is being left
`run_app.py` already demonstrates the substantive claim — the app is a real
fleet member, pulling shards by CID over a dial-out transport and evaluating
in-process, **65/65 byte-identical to host on the admitted corpus**. Folding it
into `q3.py` would raise the `binary` and `manifest` domain axes, but both are
already capped at 1 by `operator`, so it changes no verdict today.

Time-boxed after ~10 cycles. Continuing would be sunk cost against a defect
that blocks nothing.

## What this costs, stated
- `q3.py`'s phone worker remains `fuelrun.android`, so the quorum contains a
  copy of the **verifier** rather than the **product**. `binary=3` and
  `manifest=1` both understate what a real fleet would have.
- The next person should start from the one asymmetry I never explained:
  the same app, same server module, same port, same preloaded queue — one
  driver works and the other does not.
