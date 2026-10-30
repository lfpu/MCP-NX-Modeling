# -*- coding: utf-8 -*-
'''NX 2412 integrated smoke test for native holes, sketch constraints/dimensions and feature patterns.
Run from project root: python examples/smoke_native.py
'''
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker

OUT_DIR = os.path.join(ROOT, 'examples', 'output', 'native')


def step(title, command, **kwargs):
    result = call(command, **kwargs)
    print(title + '=' + json.dumps(result, ensure_ascii=False, default=str))
    return result


def feature_id(result):
    value = (result.get('feature') or {}).get('id')
    if not value:
        raise AssertionError('missing feature id: %r' % result)
    return value


def top_face():
    faces = call('find_faces', type='planar', extreme='top').get('faces', [])
    if not faces:
        raise AssertionError('top face not found')
    return faces[0]['id']


def assert_close(actual, expected, tolerance, label):
    if abs(float(actual) - float(expected)) > float(tolerance):
        raise AssertionError('%s: actual=%s expected=%s tolerance=%s' % (label, actual, expected, tolerance))


def test_native_holes():
    path = os.path.join(OUT_DIR, 'native_holes.prt')
    step('hole_new_part', 'new_part', path=path, overwrite=True)
    step('hole_block', 'create_block', length=100.0, width=60.0, height=20.0)
    before = step('hole_mass_before', 'mass_properties')['volume_mm3']

    simple = step('simple_through', 'hole_native', face=top_face(), positions=[[20, 20, 20]], diameter=10.0, through=True, hole_form='simple', fallback=False)
    if not simple.get('native') or (simple.get('feature') or {}).get('type') != 'HOLE PACKAGE':
        raise AssertionError('simple through hole is not a native HOLE PACKAGE')

    blind = step('simple_blind', 'hole_native', face=top_face(), positions=[[45, 20, 20]], diameter=8.0, depth=8.0, through=False, hole_form='simple', fallback=False)
    if not blind.get('native'):
        raise AssertionError('simple blind hole did not use native API')

    counterbore = step('counterbore', 'hole_native', face=top_face(), positions=[[70, 20, 20]], diameter=8.0, depth=12.0, through=False, hole_form='counterbore', cbore_diameter=14.0, cbore_depth=4.0, fallback=False)
    if not counterbore.get('native'):
        raise AssertionError('counterbore did not use native API')

    countersink = step('countersink', 'hole_native', face=top_face(), positions=[[45, 45, 20]], diameter=8.0, through=True, hole_form='countersink', csink_diameter=14.0, csink_angle=90.0, fallback=False)
    if not countersink.get('native'):
        raise AssertionError('countersink did not use native API')

    after = step('hole_mass_after', 'mass_properties')['volume_mm3']
    if after >= before:
        raise AssertionError('holes did not remove material')
    step('hole_save', 'save_part')


def test_sketch_constraints():
    path = os.path.join(OUT_DIR, 'sketch_constraints.prt')
    step('sketch_new_part', 'new_part', path=path, overwrite=True)
    result = step('line_sketch', 'create_sketch', plane='xy', name='ConstraintLines', shapes=[
        {'type': 'line', 'start': [0, 0], 'end': [30, 2]},
        {'type': 'line', 'start': [30, 2], 'end': [32, 22]},
    ])
    sketch = result['sketch']['id']
    step('horizontal', 'sketch_add_constraint', sketch=sketch, constraint_type='horizontal', geometry_index=0)
    step('vertical', 'sketch_add_constraint', sketch=sketch, constraint_type='vertical', geometry_index=1)
    step('coincident', 'sketch_add_constraint', sketch=sketch, constraint_type='coincident', geometry_index=0, point_type='end', geometry_index2=1, point_type2='start')
    step('horizontal_dimension', 'sketch_add_dimension', sketch=sketch, dimension_type='horizontal', geometry_index=0, value=30.0, assoc_type='start', geometry_index2=0, assoc_type2='end', origin=[15, -8, 0])
    step('vertical_dimension', 'sketch_add_dimension', sketch=sketch, dimension_type='vertical', geometry_index=1, value=20.0, assoc_type='start', geometry_index2=1, assoc_type2='end', origin=[40, 12, 0])

    circles = step('circle_sketch', 'create_sketch', plane='xy', offset=5.0, name='DimensionCircles', shapes=[
        {'type': 'circle', 'center': [15, 15], 'diameter': 12},
        {'type': 'circle', 'center': [40, 15], 'diameter': 10},
    ])['sketch']['id']
    step('diameter_dimension', 'sketch_add_dimension', sketch=circles, dimension_type='diameter', geometry_index=0, value=16.0, origin=[15, 25, 5])
    step('radius_dimension', 'sketch_add_dimension', sketch=circles, dimension_type='radius', geometry_index=1, value=7.0, origin=[48, 22, 5])
    step('sketch_save', 'save_part')


def test_patterns():
    grid_path = os.path.join(OUT_DIR, 'pattern_grid.prt')
    step('grid_new_part', 'new_part', path=grid_path, overwrite=True)
    seed = step('grid_seed', 'create_block', length=6.0, width=5.0, height=4.0)
    step('grid_pattern', 'pattern_feature', features=[feature_id(seed)], kind='grid', direction='x', count=3, spacing=12.0, direction2='y', count2=2, spacing2=10.0)
    grid_bodies = step('grid_bodies', 'get_bodies').get('bodies', [])
    if len(grid_bodies) != 6:
        raise AssertionError('grid expected 6 bodies, got %s' % len(grid_bodies))
    step('grid_save', 'save_part')

    circular_path = os.path.join(OUT_DIR, 'pattern_circular.prt')
    step('circular_new_part', 'new_part', path=circular_path, overwrite=True)
    seed = step('circular_seed', 'create_block', length=5.0, width=5.0, height=4.0, origin=[20.0, -2.5, 0.0])
    step('circular_pattern', 'pattern_feature', features=[feature_id(seed)], kind='circular', count=4, axis_origin=[0.0, 0.0, 0.0], axis_direction='z', angle=360.0)
    circular_bodies = step('circular_bodies', 'get_bodies').get('bodies', [])
    if len(circular_bodies) != 4:
        raise AssertionError('circular expected 4 bodies, got %s' % len(circular_bodies))
    step('circular_save', 'save_part')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    stop_worker()
    time.sleep(3)
    test_native_holes()
    test_sketch_constraints()
    test_patterns()
    print('ALL_NATIVE_SMOKE_TESTS_PASSED')


if __name__ == '__main__':
    main()
