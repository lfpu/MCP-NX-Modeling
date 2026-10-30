# -*- coding: utf-8 -*-
'''NX 2412 real-machine test for sketch constraints and dimensions.'''
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


def main():
    stop_worker()
    time.sleep(3)
    path = os.path.join(ROOT, 'examples', 'output', 'sketch_constraints.prt')
    show('new_part', 'new_part', path=path, overwrite=True)

    result = show(
        'create_line_sketch',
        'create_sketch',
        plane='xy',
        name='ConstraintLines',
        shapes=[
            {'type': 'line', 'start': [0, 0], 'end': [30, 2]},
            {'type': 'line', 'start': [30, 2], 'end': [32, 22]},
            {'type': 'line', 'start': [32, 22], 'end': [0, 22]},
        ],
    )
    sketch = result['sketch']['id']
    show('horizontal_0', 'sketch_add_constraint', sketch=sketch, constraint_type='horizontal', geometry_index=0)
    show('vertical_1', 'sketch_add_constraint', sketch=sketch, constraint_type='vertical', geometry_index=1)
    show('coincident_0_1', 'sketch_add_constraint', sketch=sketch, constraint_type='coincident', geometry_index=0, point_type='end', geometry_index2=1, point_type2='start')
    show('horizontal_length', 'sketch_add_dimension', sketch=sketch, dimension_type='horizontal', geometry_index=0, value=30.0, assoc_type='start', geometry_index2=0, assoc_type2='end', origin=[15, -8, 0])
    show('vertical_length', 'sketch_add_dimension', sketch=sketch, dimension_type='vertical', geometry_index=1, value=20.0, assoc_type='start', geometry_index2=1, assoc_type2='end', origin=[40, 12, 0])

    result = show(
        'create_circle_sketch',
        'create_sketch',
        plane='xy',
        offset=5.0,
        name='DimensionCircles',
        shapes=[
            {'type': 'circle', 'center': [15, 15], 'diameter': 12},
            {'type': 'circle', 'center': [40, 15], 'diameter': 10},
        ],
    )
    circles = result['sketch']['id']
    show('diameter', 'sketch_add_dimension', sketch=circles, dimension_type='diameter', geometry_index=0, value=16.0, origin=[15, 25, 5])
    show('radius', 'sketch_add_dimension', sketch=circles, dimension_type='radius', geometry_index=1, value=7.0, origin=[48, 22, 5])
    show('save', 'save_part')
    print('DONE=' + path)


if __name__ == '__main__':
    main()
