# -*- coding: utf-8 -*-
'''Probe NX 2412 SketchInPlaceBuilder option types and enum members.'''
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
    path = os.path.join(ROOT, 'examples', 'output', 'probe22.prt')
    call('new_part', path=path, overwrite=True)
    result = call('debug_sketch_builder_options', plane='yz', offset=4.0)
    text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(ROOT, 'logs', 'probe22.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
