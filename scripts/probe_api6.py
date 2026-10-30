# -*- coding: utf-8 -*-
'''Sixth probe round (compact): shell / pattern enums / mirror plane / STL selection / assembly constraint enums.
Usage: python scripts/probe_api6.py > logs/probe6.txt'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

DIRS = [
    'NXOpen.Features.ShellBuilder',
    'NXOpen.Features.ShellBuilder.Types',
    'NXOpen.Features.ShellBuilderTypes',
    'NXOpen.GeometricUtilities.PatternDefinition.PatternEnum',
    'NXOpen.GeometricUtilities.PatternDefinitionPatternEnum',
    'NXOpen.GeometricUtilities.PatternSpacing.SpacingType',
    'NXOpen.GeometricUtilities.PatternSpacingSpacingType',
    'NXOpen.STLCreator.OutputTypeEnum',
    'NXOpen.Positioning.ConstraintType',
    'NXOpen.Positioning.ConstraintAlignment',
]

BUILDERS = [
    ('Features.CreateShellBuilder', None),
    ('Features.CreateMirrorBodyBuilder', 'Plane'),
    ('Features.CreatePatternFeatureBuilder', 'PatternService.RectangularDefinition.XSpacing'),
    ('Features.CreatePatternFeatureBuilder', 'PatternService.CircularDefinition.AngularSpacing'),
]

CREATES = [
    ('session.DexManager.CreateStlCreator', 'ExportSelectionBlock'),
]


def show(title, r):
    print('== %s -> %d' % (title, r['count']))
    print('   ' + ', '.join(r['names']))


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe.prt'), overwrite=True)
    call('create_block', length=10, width=10, height=10)
    for path in DIRS:
        try:
            show(path, call('debug_dir', path=path))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:120]))
    for fac, sub in BUILDERS:
        try:
            show('%s %s' % (fac, sub or ''), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s %s ERR %s' % (fac, sub, str(exc)[:120]))
    for path, sub in CREATES:
        try:
            show('%s %s' % (path, sub or ''), call('debug_create', path=path, sub=sub))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:120]))


if __name__ == '__main__':
    main()
