# -*- coding: utf-8 -*-
'''Inspect NX 2412 UF sketch APIs for explicit plane and coordinate-system creation.'''
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
    path = os.path.join(ROOT, 'examples', 'output', 'probe36.prt')
    call('new_part', path=path, overwrite=True)
    result = call('debug_uf_sketch_api')
    text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(ROOT, 'logs', 'probe36.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
