# -*- coding: utf-8 -*-
'''Fifth probe round: pattern spacing, assembly constraint classes, drawing view sub-objects, PDF builder.
Restarts the worker first. Usage: python scripts/probe_api5.py'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

BUILDERS = [
    ('Features.CreatePatternFeatureBuilder', 'PatternService.RectangularDefinition.XSpacing'),
    ('Features.CreatePatternFeatureBuilder', 'PatternService.CircularDefinition.AngularSpacing'),
    ('Features.CreatePatternFeatureBuilder', 'FeatureList'),
    ('DraftingViews.CreateBaseViewBuilder', 'Style.ViewStyleBase'),
    ('DraftingViews.CreateBaseViewBuilder', 'Placement'),
    ('DraftingViews.CreateBaseViewBuilder', 'Placement.Placement'),
    ('DraftingViews.CreateBaseViewBuilder', 'SelectModelView'),
    ('DraftingViews.CreateBaseViewBuilder', 'Scale'),
    ('DraftingViews.CreateProjectedViewBuilder', 'Placement.Placement'),
]

DIRS = [
    ('NXOpen.Positioning.Constraint', None),
    ('NXOpen.Positioning.ConstraintType', None),
    ('NXOpen.Positioning.ConstraintAlignment', None),
    ('NXOpen.Positioning.ComponentNetwork', None),
    ('NXOpen.Positioning.ConstraintReference', None),
    ('NXOpen.PrintPDFBuilder', None),
    ('NXOpen.PrintPDFBuilder.Color', None),
    ('NXOpen.PrintPDFBuilder.SizeOption', None),
    ('NXOpen.Drawings.DrawingSheetBuilder.SheetOption', None),
    ('NXOpen.Drawings.DrawingSheetBuilder.SheetUnits', None),
    ('part.ModelingViews', None),
]

CREATES = [
    ('part.PlotManager.CreatePrintPdfbuilder', None),
    ('part.PlotManager.CreatePrintPdfbuilder', 'SourceBuilder'),
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
            show('%s %s' % (fac, sub), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s %s ERR %s' % (fac, sub, str(exc)[:200]))
    for path, keys in DIRS:
        try:
            show(path, call('debug_dir', path=path, contains=keys))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))
    for path, sub in CREATES:
        try:
            show('%s %s' % (path, sub or ''), call('debug_create', path=path, sub=sub))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))


if __name__ == '__main__':
    main()
