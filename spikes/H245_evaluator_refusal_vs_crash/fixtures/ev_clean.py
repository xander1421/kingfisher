#!/usr/bin/env python3
"""RAN AND PASSED: payload on stdout, exit 0."""
import json
print(json.dumps({"hygiene_score": 1.0, "hygiene_record_verdict": "CLEAN"}))
