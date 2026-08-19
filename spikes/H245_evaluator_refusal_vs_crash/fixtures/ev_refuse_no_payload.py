#!/usr/bin/env python3
"""DECLARED REFUSAL: the documented exit-2 no-metric contract.

`config.json` states determinism "REFUSES with exit 2 if numpy is absent and
emits NO metric". Must stay an ERROR: there is no measurement to keep.
"""
import sys
print("numpy is absent; refusing", file=sys.stderr)
sys.exit(2)
