# H150 — D1+ draw exists; R4 redraws restore duty capture

Coordinator-emulated R1–R4. No chain, no slash constants (D3). Concession
recorded: the coordinator holds `REG_e` and `beacon_e` and can bias every
draw. R3/F5 scoped out (W1 still live for non-aligned classes).

## Falsifiers (stated first)

| id | claim if fired | result |
|---|---|---|
| F1 | first-offer share ≉ stake | **did not fire** (0.203 vs stake 0.200) |
| F2 | decliner raises accepted share | **did not fire** (decliner accepted 0) |
| F2b | always-on accepted share > stake | **FIRED** |
| F3 | a device moves `seed` | **did not fire** |
| F4 | mid-epoch stake change moves this epoch | **did not fire** |

## Operating point

16 honest + 4 adversary, equal stake (adv = 20%). 4000 jobs, k=3.
Honest duty Bernoulli; adversary duty 1.0. Null: draw from the online set
(S69 shape).

| honest duty | first-offer adv | accepted adv | online-set null |
|---:|---:|---:|---:|
| 0.05 | 0.203 | **0.856** | 0.856 |
| 0.10 | 0.203 | **0.744** | 0.752 |
| 0.25 | 0.203 | **0.525** | 0.526 |

R2 (first offers, no replacement) tracks stake and beats the online-set
null. R4 redraw-until-ack then makes **accepted** seats match the online
set. Staying online *is* the attack again, at the ack layer.

§8 item 4 stays **UNPROVEN**. The mechanism runs; it does not satisfy D1's
own F2b. Fixing that is a spec change (e.g. original-k offers only, silence
→ reduced quorum), not a silent R4 rewrite.

Evidence: `draw.json`. Check: `python3 kitchen/test_h150.py`.
F001 pin unmoved `590d8769…`.
