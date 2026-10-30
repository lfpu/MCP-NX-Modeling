# -*- coding: utf-8 -*-
'''Fourth probe round: Drawings module, pattern definitions, Positioning constraints, PDF export.
Restarts the worker first. Usage: python scripts/probe_api4.py'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

DIRS = [
    ('NXOpen.Drawings', ['DrawingSheet', 'BaseView', 'ProjectedView', 'DraftingView']),
    ('NXOpen.Drawings.DrawingSheetBuilder', None),
    ('NXOpen.Positioning', ['Constraint', 'Network', 'Component', 'Positioner']),
    ('NXOpen.GeometricUtilities', ['Rectangular', 'Spacing']),
    ('part.PlotManager', None),
    ('part.DrawingSheets', None),
    ('part.ModelingViews', ['Find', 'Get', 'Create']),
]

BUILDERS = [
    ('Features.CreatePatternFeatureBuilder', 'PatternService.RectangularDefinition'),
    ('Features.CreatePatternFeatureBuilder', 'PatternService.CircularDefinition'),
    ('Features.CreatePatternFeatureBuilder', 'PatternService.PatternType'),
]


def show(title, r):
    print('== %s -> %d' % (title, r['count']))
    print('   ' + ', '.join(r['names']))


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe.prt'), overwrite=True)
    call('create_block', length=10, width=10, height=10)
    for path, keys in DIRS:
        try:
            show(path, call('debug_dir', path=path, contains=keys))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))
    for fac, sub in BUILDERS:
        try:
            show('%s %s' % (fac, sub), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s %s ERR %s' % (fac, sub, str(exc)[:200]))


if __name__ == '__main__':
    main()
