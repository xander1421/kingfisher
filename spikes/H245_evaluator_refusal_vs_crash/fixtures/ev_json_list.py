#!/usr/bin/env python3
"""WELL-FORMED JSON THAT IS NOT A PAYLOAD: a list, exit 0.

`results.update(data)` raises on a list, so the pre-fix runner hands the
scoring loop something it cannot consume. Must be an ERROR.
"""
import json
print(json.dumps([1, 2, 3]))
