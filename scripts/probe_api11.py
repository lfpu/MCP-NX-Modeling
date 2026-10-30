# -*- coding: utf-8 -*-
'''Probe HolePosition Section method signatures and ProjectionDirection defaults.'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402


def main():
    stop_worker()
    time.sleep(3)
    path = os.path.join(ROOT, 'examples', 'output', 'probe11.prt')
    call('new_part', path=path, overwrite=True)
    call('create_block', length=60, width=40, height=20)
    result = call('debug_hole_position_methods')
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
