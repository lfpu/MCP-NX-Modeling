# -*- coding: utf-8 -*-
'''Ask the NX worker which API names exist in this NX version (mirror / pattern / draft / constraints / drafting).
Restarts the worker first so new code is loaded. Usage: python scripts/probe_api.py'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

QUERIES = [
    ('part.Features', ['Mirror', 'Pattern', 'Instance', 'Draft']),
    ('part.ComponentAssembly', ['Constraint', 'Fix', 'Move', 'Position']),
    ('part', ['Drawing', 'Drafting', 'View']),
    ('part.DrawingSheets', ['Create', 'Sheet']),
    ('part.DraftingViews', ['Create']),
    ('session.DexManager', ['Create', 'Stl', 'Pdf']),
    ('NXOpen', ['Constraint', 'MirrorSet', 'PatternFeature', 'DraftBuilder', 'Pdf', 'Stl']),
]

BUILDERS = [
    'Features.CreateMirrorSetBuilder',
    'Features.CreatePatternFeatureBuilder',
    'Features.CreateDraftBuilder',
]


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe.prt'), overwrite=True)
    call('create_block', length=10, width=10, height=10)
    for path, keys in QUERIES:
        try:
            r = call('debug_dir', path=path, contains=keys)
            print('== %s %s -> %d' % (path, keys, r['count']))
            print('   ' + ', '.join(r['names']))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:150]))
    for fac in BUILDERS:
        try:
            r = call('debug_builder', factory=fac)
            print('== builder %s -> %d' % (fac, r['count']))
            print('   ' + ', '.join(r['names']))
        except Exception as exc:
            print('== builder %s ERR %s' % (fac, str(exc)[:150]))


if __name__ == '__main__':
    main()
