# -*- coding: utf-8 -*-
'''Second probe round: attribute names of the builders needed for mirror / pattern / drawing / assembly / PDF.
Restarts the worker first so new code is loaded. Usage: python scripts/probe_api2.py'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

BUILDERS = [
    ('Features.CreateMirrorFeatureBuilder', None),
    ('Features.CreateMirrorBodyBuilder', None),
    ('Features.CreateMirrorBuilder', None),
    ('Features.CreateInstanceFeatureBuilder', None),
    ('Features.CreatePatternFeatureBuilder', 'PatternService'),
    ('DrawingSheets.DrawingSheetBuilder', None),
    ('DraftingViews.CreateBaseViewBuilder', None),
    ('DraftingViews.CreateProjectedViewBuilder', None),
]

DIRS = [
    ('part.ComponentAssembly.Positioner', None),
    ('session', ['Pdf']),
    ('NXOpen', ['PatternService', 'ComponentPositioner', 'ComponentConstraint', 'Mirror']),
]


def show(title, r):
    print('== %s -> %d' % (title, r['count']))
    print('   ' + ', '.join(r['names']))


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe.prt'), overwrite=True)
    call('create_block', length=10, width=10, height=10)
    for fac, sub in BUILDERS:
        try:
            show('%s %s' % (fac, sub or ''), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s ERR %s' % (fac, str(exc)[:200]))
    for path, keys in DIRS:
        try:
            show(path, call('debug_dir', path=path, contains=keys))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))


if __name__ == '__main__':
    main()
