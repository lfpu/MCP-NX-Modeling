# -*- coding: utf-8 -*-
'''Stop the running NX worker (it keeps old code loaded, so run this after editing nx_worker/*).
The next MCP call / smoke_test auto-starts a fresh worker.  Usage: python scripts/stop_worker.py'''
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nx_mcp.client import stop_worker  # noqa: E402

stop_worker()
print('shutdown sent (no error means the worker stopped or was not running)')
