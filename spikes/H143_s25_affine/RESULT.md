# H143 — S25 F001 verify is a rate

On-device loop, one adb call per N. `units.fit_or_refuse` (1 decade, 50→800)
and `check_affine` (tol 25%). Falsifier did not fire.

| N | wall s | ms/verify |
|---:|---:|---:|
| 50 | 0.455 | 9.09 |
| 100 | 0.841 | 8.41 |
| 200 | 1.576 | 7.88 |
| 400 | 3.159 | 7.90 |
| 800 | 6.506 | 8.13 |

Fit: intercept **4.1 ms**, slope **8.075 ms/verify**. Affine holds (adj. slopes
within 14%). Operating point: `R5CY93675MK` charging, thermal 42°C, usb.

S24+ was unplugged; this is one phone. Two-phone H141 still OPEN.

Check: `python3 kitchen/test_h143.py`
