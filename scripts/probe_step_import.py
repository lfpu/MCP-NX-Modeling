# -*- coding: utf-8 -*-
'''Probe NX 2412 STEP importer properties, enums and current defaults.'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from nx_mcp.client import call, stop_worker


def dump(title, value):
    print('== ' + title)
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main():
    stop_worker()
    time.sleep(3)
    for factory in (
        'session.DexManager.CreateStep214Importer',
        'session.DexManager.CreateStepImporter',
    ):
        try:
            dump(factory, call('debug_create', path=factory))
        except Exception as exc:
            print('== ' + factory + ' ERROR ' + str(exc))
    for path in (
        'NXOpen.Step214Importer',
        'NXOpen.StepImporter',
        'NXOpen.Step214Importer.ImportToOption',
        'NXOpen.StepImporter.ImportToOption',
    ):
        try:
            dump(path, call('debug_dir', path=path))
        except Exception as exc:
            print('== ' + path + ' ERROR ' + str(exc))


if __name__ == '__main__':
    main()
