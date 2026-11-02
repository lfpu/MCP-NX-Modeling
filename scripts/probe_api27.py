# -*- coding: utf-8 -*-
'''Probe CoordinateSystem creation from NXOpen.Point + NXMatrix and sketch NewCsys.'''
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
    results = {}
    for plane in ('xy', 'yz', 'xz'):
        path = os.path.join(ROOT, 'examples', 'output', 'probe27_' + plane + '.prt')
        call('new_part', path=path, overwrite=True)
        results[plane] = call('debug_sketch_csystem_point_api', plane=plane, offset=4.0)
    text = json.dumps(results, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(ROOT, 'logs', 'probe27.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
