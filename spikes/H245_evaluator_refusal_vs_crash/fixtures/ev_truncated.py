#!/usr/bin/env python3
"""DIED MID-WRITE: half a JSON object on stdout, non-zero exit.

The case that decides whether "parses as JSON" is a strong enough test of
"a measurement exists".
"""
import sys
sys.stdout.write('{"hygiene_score": 0.0, "hygiene_reco')
sys.stdout.flush()
sys.exit(1)
