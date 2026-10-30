# -*- coding: utf-8 -*-
'''NX 2412 real-machine tests for assembly concentric, distance, parallel, perpendicular and angle constraints.
Each constraint runs in a fresh assembly to avoid interactions between solver networks.
'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker

OUT = os.path.join(ROOT, 'examples', 'output', 'assembly_constraints')


def step(title, command, **kwargs):
    result = call(command, **kwargs)
    print(title + '=' + json.dumps(result, ensure_ascii=False, default=str))
    return result


def component_id(result):
    return result['component']['id']


def first_face(component, face_type='planar', normal=None, extreme=None):
    kwargs = {'component': component, 'type': face_type}
    if normal is not None:
        kwargs['normal'] = normal
    if extreme is not None:
        kwargs['extreme'] = extreme
    faces = call('component_faces', **kwargs).get('faces', [])
    if not faces:
        raise AssertionError('face not found: %r' % kwargs)
    return faces[0]


def make_parts():
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, 'base.prt')
    plate = os.path.join(OUT, 'plate.prt')
    cylinder = os.path.join(OUT, 'cylinder.prt')

    step('base_new', 'new_part', path=base, overwrite=True)
    step('base_block', 'create_block', length=60.0, width=40.0, height=10.0)
    step('base_save', 'save_part')

    step('plate_new', 'new_part', path=plate, overwrite=True)
    step('plate_block', 'create_block', length=30.0, width=20.0, height=5.0)
    step('plate_save', 'save_part')

    step('cylinder_new', 'new_part', path=cylinder, overwrite=True)
    step('cylinder_body', 'create_cylinder', diameter=12.0, height=20.0, origin=[0.0, 0.0, 0.0], direction=[0.0, 0.0, 1.0])
    step('cylinder_save', 'save_part')
    return base, plate, cylinder


def fresh_assembly(name, base_path, moving_path, moving_origin):
    asm = os.path.join(OUT, name + '.prt')
    step(name + '_new', 'new_part', path=asm, overwrite=True)
    fixed = component_id(step(name + '_add_fixed', 'add_component', path=base_path, name='FIXED'))
    moving = component_id(step(name + '_add_moving', 'add_component', path=moving_path, name='MOVING', origin=moving_origin))
    step(name + '_fix', 'add_constraint', kind='fix', component1=fixed)
    return asm, fixed, moving


def assert_constraint_result(name, result):
    if not isinstance(result, dict):
        raise AssertionError('%s returned invalid result: %r' % (name, result))
    text = json.dumps(result, ensure_ascii=False, default=str).lower()
    if 'fail' in text or 'error' in text and 'notes' not in result:
        raise AssertionError('%s failed: %r' % (name, result))


def test_parallel(base, plate):
    asm, fixed, moving = fresh_assembly('parallel', base, plate, [80.0, 0.0, 30.0])
    f1 = first_face(fixed, 'planar', normal='top')['id']
    f2 = first_face(moving, 'planar', normal='top')['id']
    result = step('parallel_constraint', 'add_constraint', kind='parallel', component1=fixed, face1=f1, component2=moving, face2=f2, alignment='coalign')
    assert_constraint_result('parallel', result)
    step('parallel_save', 'save_part')


def test_perpendicular(base, plate):
    asm, fixed, moving = fresh_assembly('perpendicular', base, plate, [80.0, 0.0, 30.0])
    f1 = first_face(fixed, 'planar', normal='top')['id']
    f2 = first_face(moving, 'planar', normal='right')['id']
    result = step('perpendicular_constraint', 'add_constraint', kind='perpendicular', component1=fixed, face1=f1, component2=moving, face2=f2, alignment='infer')
    assert_constraint_result('perpendicular', result)
    step('perpendicular_save', 'save_part')


def test_distance(base, plate):
    asm, fixed, moving = fresh_assembly('distance', base, plate, [80.0, 0.0, 30.0])
    f1 = first_face(fixed, 'planar', extreme='top')['id']
    f2 = first_face(moving, 'planar', extreme='bottom')['id']
    result = step('distance_constraint', 'add_constraint', kind='distance', component1=fixed, face1=f1, component2=moving, face2=f2, distance=15.0, alignment='contra')
    assert_constraint_result('distance', result)
    step('distance_save', 'save_part')


def test_angle(base, plate):
    asm, fixed, moving = fresh_assembly('angle', base, plate, [80.0, 0.0, 30.0])
    f1 = first_face(fixed, 'planar', normal='top')['id']
    f2 = first_face(moving, 'planar', normal='top')['id']
    result = step('angle_constraint', 'add_constraint', kind='angle', component1=fixed, face1=f1, component2=moving, face2=f2, distance=30.0, alignment='infer')
    assert_constraint_result('angle', result)
    step('angle_save', 'save_part')


def test_concentric(cylinder):
    asm = os.path.join(OUT, 'concentric.prt')
    step('concentric_new', 'new_part', path=asm, overwrite=True)
    fixed = component_id(step('concentric_add_fixed', 'add_component', path=cylinder, name='FIXED_CYL'))
    moving = component_id(step('concentric_add_moving', 'add_component', path=cylinder, name='MOVING_CYL', origin=[30.0, 20.0, 0.0]))
    step('concentric_fix', 'add_constraint', kind='fix', component1=fixed)
    f1 = first_face(fixed, 'cylindrical')['id']
    f2 = first_face(moving, 'cylindrical')['id']
    result = step('concentric_constraint', 'add_constraint', kind='concentric', component1=fixed, face1=f1, component2=moving, face2=f2, alignment='coalign')
    assert_constraint_result('concentric', result)
    step('concentric_save', 'save_part')


def main():
    stop_worker()
    time.sleep(3)
    call('set_workspace', path=OUT, create=True)
    base, plate, cylinder = make_parts()
    test_parallel(base, plate)
    test_perpendicular(base, plate)
    test_distance(base, plate)
    test_angle(base, plate)
    test_concentric(cylinder)
    print('ASSEMBLY_CONSTRAINT_TESTS_PASSED')


if __name__ == '__main__':
    main()
