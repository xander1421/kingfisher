#!/usr/bin/env python3
"""RAN AND REFUSED: a complete metric payload on stdout, exit 1.

This is `eval_hygiene.py`'s live shape -- `main()` prints the payload and then
`return 0 if all_ok else 1`.
"""
import json, sys
print(json.dumps({"hygiene_score": 0.0, "hygiene_record_verdict": "VIOLATED",
                  "hygiene_violations": [{"checker": "refcheck"}]}))
sys.exit(1)
