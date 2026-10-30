# -*- coding: utf-8 -*-
'''Print NX API diagnostics. Needs a work part with a body (run examples/smoke_test.py first, or open a part).
Usage: python scripts/probe.py'''
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nx_mcp.client import call  # noqa: E402

print(json.dumps(call('debug_probe'), ensure_ascii=False, indent=2))
