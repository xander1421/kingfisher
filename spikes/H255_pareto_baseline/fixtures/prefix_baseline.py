"""FROZEN pre-fix `get_baseline_composite`, lifted VERBATIM by AST from

    scripts/autoloop.py @ 1b8da4f4804a11ce842cc88f5bdee38bf305c19f

and NOT re-read from `HEAD`. Once the fix lands at `HEAD`, a probe that reads
`HEAD` for its "before" side is measuring the "after" side (H237).

sha256(function source) = 044d2c1b050afd838f9f8a5ca2ae84a06bbdffe7bf8927c49cb3003c1c9648b2
"""
import os

MEMORY_FILE = None  # set by the caller


def get_baseline_composite():
    """Reads the highest ACCEPTED composite score recorded in MEMORY_FILE."""
    if not os.path.exists(MEMORY_FILE):
        return None
    best_score = None
    try:
        with open(MEMORY_FILE, "r") as f:
            for line in f:
                if "**ACCEPTED**" in line and "Composite score:" in line:
                    parts = line.split("Composite score:")
                    score_str = parts[1].strip().split()[0].rstrip("|").strip()
                    score = float(score_str)
                    if best_score is None or score > best_score:
                        best_score = score
    except Exception:
        pass
    return best_score
