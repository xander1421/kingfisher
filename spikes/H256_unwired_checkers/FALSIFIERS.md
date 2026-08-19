# H256 — preregistered falsifiers

`ok-1`, cycle 35, 2026-08-19. **Committed with the CLAIM, before any fix is written.**
The survey that motivated the row is already run (it is what produced the id); these attack
the *conclusion* I am about to draw from it.

| # | falsifier | prediction |
|---|---|---|
| **F1** | The unwired checkers are unwired **because they are operator entry points** — `bringup.sh`, `send.sh`, `fleetcensus.sh`, `autoloop_local.sh` are meant to be typed by a human, and a checker with no caller is normal here | **FIRES for some, not all** — I predict a residue of modules that gate nothing and were plainly built to gate something. If the residue is empty the row dies |
| **F2** | `trackcheck.py` is reachable by some route my scan does not model — a launchd plist, a crontab, `.claude/settings.json`, a `Makefile` | **does NOT fire** |
| **F3** | The condition is harmless: nothing an unwired checker would have caught has actually escaped | **does NOT fire** — `trackcheck.py` exits **1** on this tree right now, and H243 shipped a DONE row over an untracked module in the same session |
| **F4** | A `Invoked-By:`-style self-declaration is an A22 hole: a lane could silence the new check by declaring a gate operator-invoked | **FIRES as stated, and the design must answer it** — the declaration may change the CATEGORY and must never change whether the checker itself runs |
| **F5** | Wiring `trackcheck.py` into the commit path would refuse every lane's commit today, for another lane's debt | **FIRES** — 3 NEW untracked citations belong to other lanes, which is why this row ships a census and not that wiring |

**What each outcome obliges.** F1's residue is the row's actual population; if it is empty the
row is withdrawn. F5 firing is why the deliverable is a checker that *names* the condition
rather than a gate that *enforces* it this cycle — enforcing it would be H229's permanently-red
shape, imported deliberately.
