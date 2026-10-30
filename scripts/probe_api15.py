# -*- coding: utf-8 -*-
'''Probe NX 2412 sketch constraint/dimension data classes and enums.'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from nx_mcp.client import call, stop_worker


def main():
    stop_worker()
    time.sleep(3)
    path = os.path.join(ROOT, 'examples', 'output', 'probe15.prt')
    call('new_part', path=path, overwrite=True)
    print(json.dumps(call('debug_sketch_data_types'), ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
