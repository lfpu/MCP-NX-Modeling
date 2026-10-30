# -*- coding: utf-8 -*-
'''Probe NX 2412 STEP creator input-source properties and enums.'''
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
    path = os.path.join(ROOT, 'examples', 'output', 'step_probe.prt')
    call('new_part', path=path, overwrite=True)
    call('create_block', length=20, width=15, height=10)
    call('save_part')
    result = call('debug_create', path='session.DexManager.CreateStepCreator')
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    for path in (
        'NXOpen.StepCreator.ExportFromOption',
        'NXOpen.Step214Creator.ExportFromOption',
        'NXOpen.StepCreator',
        'NXOpen.Step214Creator',
    ):
        try:
            result = call('debug_dir', path=path)
            print('== ' + path)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        except Exception as exc:
            print('== ' + path + ' ERROR ' + str(exc))


if __name__ == '__main__':
    main()
