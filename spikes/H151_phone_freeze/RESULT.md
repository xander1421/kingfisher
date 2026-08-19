# H151 — post-freeze S25 holds the pin; S24 is attached and correctly refused

Operator: both phones connected. S25 ran. S24 did not — the §10 gate
refused, and that is the result.

## Falsifier (stated first)

If S25 F001 after `F001_FROZEN` is not digest `590d8769…`, the freeze
moved the on-device pin (A24).

It did not fire.

## S25 Ultra `R5CY93675MK`

Gate green before and after (cpu 1.4–1.5%, thermal 37400m, charging,
level 100). On-device `trace_verifier_android_f001`:

- F001 **ACCEPTED** fuel 400 witness `112f7e8c…` digest
  `590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f`
- M06 **REJECTED** `RESULT_NOT_DERIVED` rc=1

Same pin as host `grok_check`. Status flip DRAFT→FROZEN is not in the
digest payload.

## S24+ `R5CX508MPRZ`

Attached USB, charging, level 36%. Default gate: `thermal-UNREADABLE`
(unchanged). With unread override only:

- cpu_busy stayed **19–53%** for 12 samples over ~2 min
- override does **not** skip cpu_busy (H139 contract)
- `top`: `com.playspare.supermarket.store.simulator` at **206% CPU**

No F001 job on S24. Did not kill the game. Did not raise the 15% limit.
Two phones attached is not two jobs run.

Same-source Android is not a new ISA or operator domain.

Evidence: `phone.json`. Check: `python3 kitchen/test_h151.py`.
