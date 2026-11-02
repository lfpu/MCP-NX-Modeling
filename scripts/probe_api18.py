# -*- coding: utf-8 -*-
'''Probe NX 2412 sphere/cone typed Null builders and sketch arc plane matrices.'''
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
    path = os.path.join(ROOT, 'examples', 'output', 'probe18.prt')
    call('new_part', path=path, overwrite=True)
    result = call('debug_primitive_sketch_api')
    log_path = os.path.join(ROOT, 'logs', 'probe18.txt')
    text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
