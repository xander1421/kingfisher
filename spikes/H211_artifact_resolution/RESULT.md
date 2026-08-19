# H211 — `provenance.py` pinned the artifact it found, not the one it was given

**AGENT-1, 2026-08-19. My own row, raised from H209's certification and left OPEN
for four cycles while I filed five more. Taking it rather than filing a seventh.**

## The defect

`record()` called `os.path.exists(a)` and `sha256_file(a)` on the **declared**
name. So `certify(spike_dir=HERE, artifacts=['result.json'])` asked about
`$CWD/result.json` and never about `HERE/result.json` — **the same call correct
or void depending on where the runner stood**, silently in both directions.

**Only the harmless direction had ever fired.** Run from the repo root, H209's
certify reported `missing artifacts: ['result.json']` while the file sat in the
spike dir. That is the reason anyone saw this at all.

**The unsafe direction is the same line, and this probe fires it deliberately: a
file of that name at the CWD is found, hashed, and recorded as the spike's
artifact — the correct sha256 of the wrong file (A24), inside the module whose
entire job is family C.** A defect that has only ever failed safe is one nobody
has seen fail.

## The fix refuses; it does not re-point

The obvious repair — silently resolve against `spike_dir` — would rewrite what an
existing green record refers to **without saying so**, which is this defect
wearing a repair's clothes. `_resolve_artifact` therefore:

- **absolute** declaration → untouched (every call site hand-fixed under
  H209/H218/S92 passes absolute paths and must not change meaning);
- **relative, present in the spike** → pinned to the spike's copy; and if a
  **different** file of that name also sits at the CWD, the ambiguity becomes a
  **problem** naming both candidates;
- **relative, present only at the CWD** → recorded **MISSING**, not pinned,
  because pinning it is the original defect performed by the repair;
- `artifacts[].path` still carries the declared name and `artifacts[].resolved`
  is new, so a reader sees both.

## Evidence

`python3 spikes/H211_artifact_resolution/probe.py` — **14/14,
`checks failed: 0`.** Fixture: a spike holding its own `result.json` and a
**different** file of that name where the runner stands.

| arm | |
|---|---|
| A0 | the fixture really holds two different files of one name |
| A1 / A2 | **PRE-FIX (`efe3d81`) pins the RUNNER's file** — the correct sha256 of the wrong artifact, asserted positively because the row's size depends on this direction being reachable |
| A3 / A3b | POST-FIX pins the spike's file, recording declared name and resolved path |
| A4 / A4b | the ambiguity is a **problem**, naming both candidates |
| A5 / A5b | an absolute declaration is pinned unchanged and raises no ambiguity |
| A6 | two files of one name with **identical content** are not "ambiguous" — or every spike run from its own directory gains a spurious problem |
| A7–A7c | a name present **only** at the CWD is recorded MISSING, nothing is pinned, and the problem says the spike does not own it |

**Regression check on the one real relative caller.**
`spikes/B2_nonoracle_cutoff/certify.py` declares
`artifacts=['nonoracle.json', 'nonoracle.py', 'RUN.txt']`. Resolved from the repo
root, all three now land in its own spike directory, all exist, no ambiguity —
where before they would have read as missing from anywhere but that directory.

## One defect of my own

**A6 first went red, and the resolver was right.** I wrote the *spike's* content
into the identical-content fixture and then asserted "not ambiguous" against a
CWD file that differed — **the arm named one condition and built another**. The
fixture was corrected and the mistake recorded rather than quietly edited (§5).

## Falsifiers

Stated before the run. **F1** — every live caller already passes absolute paths,
making this latent-only: **false**, `B2_nonoracle_cutoff` declares three relative
names. **F2** — resolving against `spike_dir` silently re-points an existing green
record: **addressed by construction**, the ambiguous case is reported rather than
re-pointed and the CWD-only case is recorded missing. **F3** — `sha256_file` or
`getsize` already normalise the path somewhere: **false**, A2 shows the pre-fix
module hashing the CWD file.
