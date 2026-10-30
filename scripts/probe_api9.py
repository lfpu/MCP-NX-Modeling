# -*- coding: utf-8 -*-
'''Ninth probe: native Hole position/diameter types, PatternService (circular/rectangular), Sketch dimension helpers.
Usage: python scripts/probe_api9.py > logs/probe9.txt'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402


def show(title, r):
    print('== %s -> %d' % (title, r['count']))
    print('   ' + ', '.join(r['names']))


PATHS = [
    'NXOpen.Features.HolePackageBuilder.HoleForms',
    'NXOpen.Features.HolePackageBuilder.Types',
    'NXOpen.Features.HolePackageBuilder.HoleDepthLimitOptions',
    'NXOpen.Features.HolePackageBuilder.CounterBoreDepthLimitOptions',
    'NXOpen.Features.HolePackageBuilder.HoleDepthOptions',
    'NXOpen.Features.HolePosition',
    'NXOpen.Features.HolePositionBuilder',
    'NXOpen.Features.PatternServiceBuilder',
    'NXOpen.Features.PatternService',
    'NXOpen.GeometricUtilities.PatternServiceBuilder',
    'NXOpen.GeometricUtilities.PatternService',
    'NXOpen.GeometricUtilities.PatternDefinition',
    'NXOpen.GeometricUtilities.LinearPatternDefinition',
    'NXOpen.GeometricUtilities.CircularPatternDefinition',
    'NXOpen.GeometricUtilities.RectangularPatternDefinition',
    'NXOpen.GeometricUtilities.PatternServiceBuilder.PatternLayouts',
    'NXOpen.GeometricUtilities.PatternServiceBuilder.PatternMethods',
    'NXOpen.Features.PatternFeatureBuilder.PatternMethodOptions',
    'NXOpen.Features.PatternFeatureBuilder.OutputOptions',
    'NXOpen.Sketch.DimensionOption',
    'NXOpen.Sketch.InferConstraintsOption',
    'NXOpen.Sketch.ConstraintPointType',
    'NXOpen.Sketch.PointType',
    'NXOpen.SketchDimensionalConstraint.DimensionStateType',
    'NXOpen.Sketch.CreateDimension',
    'NXOpen.Sketch.CreateRadialDimension',
    'NXOpen.Sketch.CreateDiameterDimension',
    'NXOpen.Sketch.CreateHorizontalConstraint',
    'NXOpen.Sketch.CreateCoincidentConstraint',
]


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe9.prt'), overwrite=True)
    call('create_block', length=60, width=40, height=20)
    for path in PATHS:
        try:
            show(path, call('debug_dir', path=path))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))
    for fac, sub in [('Features.CreatePatternFeatureBuilder', 'PatternService'),
                     ('Features.CreatePatternFeatureBuilder', 'PatternMethod')]:
        try:
            show('%s %s' % (fac, sub), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s %s ERR %s' % (fac, sub, str(exc)[:200]))


if __name__ == '__main__':
    main()
