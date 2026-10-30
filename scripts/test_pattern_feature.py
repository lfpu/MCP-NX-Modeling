# -*- coding: utf-8 -*-
'''NX 2412 real-machine tests for circular and grid feature patterns.'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker


def show(title, command, **kwargs):
    result = call(command, **kwargs)
    print(title + '=' + json.dumps(result, ensure_ascii=False, default=str))
    return result


def feature_id(result):
    feature = result.get('feature') or {}
    value = feature.get('id')
    if not value:
        raise RuntimeError('feature id not found: %r' % result)
    return value


def test_grid():
    path = os.path.join(ROOT, 'examples', 'output', 'pattern_grid.prt')
    show('grid_new_part', 'new_part', path=path, overwrite=True)
    seed = show('grid_seed', 'create_block', length=6.0, width=5.0, height=4.0, origin=[0.0, 0.0, 0.0])
    result = show(
        'grid_pattern',
        'pattern_feature',
        features=[feature_id(seed)],
        kind='grid',
        direction='x',
        count=3,
        spacing=12.0,
        direction2='y',
        count2=2,
        spacing2=10.0,
    )
    bodies = show('grid_bodies', 'get_bodies')
    if len(bodies.get('bodies', [])) != 6:
        raise AssertionError('grid expected 6 bodies, got %s' % len(bodies.get('bodies', [])))
    show('grid_save', 'save_part')
    return result


def test_circular():
    path = os.path.join(ROOT, 'examples', 'output', 'pattern_circular.prt')
    show('circular_new_part', 'new_part', path=path, overwrite=True)
    seed = show('circular_seed', 'create_block', length=5.0, width=5.0, height=4.0, origin=[20.0, -2.5, 0.0])
    result = show(
        'circular_pattern',
        'pattern_feature',
        features=[feature_id(seed)],
        kind='circular',
        count=4,
        axis_origin=[0.0, 0.0, 0.0],
        axis_direction='z',
        angle=360.0,
    )
    bodies = show('circular_bodies', 'get_bodies')
    if len(bodies.get('bodies', [])) != 4:
        raise AssertionError('circular expected 4 bodies, got %s' % len(bodies.get('bodies', [])))
    show('circular_save', 'save_part')
    return result


def main():
    stop_worker()
    time.sleep(3)
    test_grid()
    test_circular()
    print('DONE')


if __name__ == '__main__':
    main()
