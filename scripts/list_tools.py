# -*- coding: utf-8 -*-
'''Register all MCP tools and print their names (no NX needed). Verifies the SDK version works.
Usage: python scripts/list_tools.py'''
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nx_mcp.server import mcp, register_all  # noqa: E402

register_all()
tools = asyncio.run(mcp.list_tools())
names = sorted(t.name for t in tools)
print('registered tools: %d' % len(names))
for n in names:
    print('  ' + n)
