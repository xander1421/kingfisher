# H153 — F001 on 3 adb endpoints

S25 Ultra + S24+ + `emulator-5554`. Three **serials**, not three phones
and not three operators. Emulator is the same Mac (H147). Unread-thermal
override on S24 and emu only.

Falsifier: 3-way steal of 400 not faster than S25 k=2, or any serial
fails pin `590d8769…`.

It did not fire.

| endpoint | one verify | role |
|---|---|---|
| S25 | ACCEPT `590d8769…` | phone, Snapdragon |
| S24 | ACCEPT same | phone, Exynos; unread override |
| emu | ACCEPT same | **not a phone**, same host as this Darwin |

Live 400 F001, chunk 50, 3 rounds on the triple:

| config | wall | jobs/s | taken S25/S24/emu |
|---|---:|---:|---|
| S25 k=2 | 1.747s | 229 | 400 / 0 / 0 |
| 2 phones k=2+2 | 1.396s | 287 | 300 / 100 / 0 |
| 3 serials best | **1.236s** | **324** | 100 / 100 / 200 |

3 / S25 k=2 = **0.708**. 3 / 2-phone = **0.885**.

The 100/100/200 split is first-come 50-job grabs, not a third phone
being fastest. Emulator took half the chunks on this Mac. That is extra
host compute in an Android userspace, **not** a third physical device
and **not** `host=3` or `operator=3`. §8 item 1 stays UNPROVEN.

Evidence: `three.json`. Check: `python3 kitchen/test_h153.py`.
