# -*- coding: utf-8 -*-
'''Third probe round: DEX creators, drawing sheet enums, pattern definitions.
Restarts the worker first. Usage: python scripts/probe_api3.py'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

CREATES = [
    'session.DexManager.CreateStepCreator',
    'session.DexManager.CreateStlCreator',
    'session.DexManager.CreateIgesCreator',
    'session.DexManager.CreateStep214Importer',
]

DIRS = [
    ('NXOpen.Drawings.DrawingSheetBuilder', None),
    ('NXOpen.Drawings.BaseViewBuilder', None),
    ('NXOpen.Drawings.DrawingSheetCollection', ['Create', 'Insert', 'Sheet']),
    ('NXOpen.Features.PatternFeatureBuilder', None),
    ('NXOpen.Features.PatternFeatureBuilder.PatternMethodOptions', None),
    ('NXOpen.GeometricUtilities', ['Pattern', 'Rectangular', 'Circular', 'Layout']),
    ('NXOpen.Features', ['Pattern', 'Instance']),
    ('NXOpen.Features.DraftBuilder', None),
]


def show(title, r):
    print('== %s -> %d' % (title, r['count']))
    print('   ' + ', '.join(r['names']))


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe.prt'), overwrite=True)
    call('create_block', length=10, width=10, height=10)
    for path in CREATES:
        try:
            show(path, call('debug_create', path=path))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))
    for path, keys in DIRS:
        try:
            show(path, call('debug_dir', path=path, contains=keys))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))


if __name__ == '__main__':
    main()
