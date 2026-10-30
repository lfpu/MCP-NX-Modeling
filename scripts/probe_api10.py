# -*- coding: utf-8 -*-
'''Tenth probe: inspect NX 2412 builder instances and sketch method metadata.
Usage: python scripts/probe_api10.py > logs/probe10.txt
'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402


def dump(title, value):
    print('== ' + title)
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main():
    stop_worker()
    time.sleep(3)
    path = os.path.join(ROOT, 'examples', 'output', 'probe10.prt')
    call('new_part', path=path, overwrite=True)
    call('create_block', length=60, width=40, height=20)

    dump('HolePackageBuilder details', call(
        'debug_builder_details',
        factory='Features.CreateHolePackageBuilder',
        paths=[
            'HolePosition',
            'ProjectionDirection',
            'GeneralSimpleHoleDiameter',
            'GeneralSimpleHoleDepth',
            'GeneralCounterboreDiameter',
            'GeneralCounterboreDepth',
            'GeneralCountersinkDiameter',
            'GeneralCountersinkAngle',
        ],
    ))

    dump('PatternFeatureBuilder details', call(
        'debug_builder_details',
        factory='Features.CreatePatternFeatureBuilder',
        paths=[
            'PatternService',
            'PatternService.CircularDefinition',
            'PatternService.CircularDefinition.AngularSpacing',
            'PatternService.RectangularDefinition',
            'PatternService.RectangularDefinition.XSpacing',
            'PatternService.RectangularDefinition.YSpacing',
        ],
    ))

    dump('Sketch method metadata', call('debug_sketch_methods'))


if __name__ == '__main__':
    main()
