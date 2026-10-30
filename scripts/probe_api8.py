# -*- coding: utf-8 -*-
'''Eighth probe: native Hole (HolePackageBuilder), sketch constraints/dimensions, circular/rectangular patterns.
Usage: python scripts/probe_api8.py > logs/probe8.txt'''
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
    'NXOpen.Features.HolePackageBuilder',
    'NXOpen.Features.HolePackageBuilder.Type',
    'NXOpen.Features.HolePackageBuilder.Types',
    'NXOpen.Features.HolePackageBuilder.GeneralHoleTypes',
    'NXOpen.Features.HolePackageBuilder.HoleForms',
    'NXOpen.Features.HolePackageBuilder.Forms',
    'NXOpen.Features.HolePackageBuilder.ExtentType',
    'NXOpen.Features.HolePackageBuilder.Extents',
    'NXOpen.Features.PatternFeatureBuilder',
    'NXOpen.Features.PatternDefinition',
    'NXOpen.Features.CircularPatternDefinition',
    'NXOpen.Features.RectangularPatternDefinition',
    'NXOpen.Sketch',
    'NXOpen.SketchConstraint',
    'NXOpen.SketchDimensionalConstraint',
    'NXOpen.Sketch.ConstraintType',
    'NXOpen.Sketch.DimensionType',
    'NXOpen.Sketch.ConstraintGeometry',
]


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe8.prt'), overwrite=True)
    call('create_block', length=60, width=40, height=20)
    for path in PATHS:
        try:
            show(path, call('debug_dir', path=path))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))
    for fac, sub in [('Features.CreateHolePackageBuilder', ''),
                     ('Features.CreatePatternFeatureBuilder', ''),
                     ('Features.CreatePatternFeatureBuilder', 'PatternDefinition')]:
        try:
            show('%s %s' % (fac, sub), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s %s ERR %s' % (fac, sub, str(exc)[:200]))


if __name__ == '__main__':
    main()
