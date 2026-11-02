# -*- coding: utf-8 -*-
'''NX 2412 real-machine tests for colors, spur gear and native threaded hole.''' 
import json
import multiprocessing
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker


def show(label, command, **kwargs):
    value = call(command, **kwargs)
    print(label + '=' + json.dumps(value, ensure_ascii=False, default=str))
    return value


def feature_id(value):
    return value['feature']['id']


def test_colors():
    path = os.path.join(ROOT, 'examples', 'output', 'color_test.prt')
    show('color_new', 'new_part', path=path, overwrite=True)
    block = show('color_block', 'create_block', length=40, width=30, height=20)
    body = block['bodies'][0]['id']
    show('body_color', 'color_bodies', bodies=[body], color=186, apply_to_all_faces=True)
    faces = show('color_faces_query', 'find_faces', body=body, type='planar')['faces']
    if not faces:
        raise AssertionError('color test did not find faces')
    show('face_color', 'color_faces', faces=[faces[0]['id']], color=36)
    info = show('colored_face_info', 'get_object_info', object_id=faces[0]['id'])
    if int(info.get('face', {}).get('color', -1)) != 36:
        raise AssertionError('face color was not retained: %s' % info)
    show('color_save', 'save_part')


def test_gear():
    path = os.path.join(ROOT, 'examples', 'output', 'spur_gear.prt')
    show('gear_new', 'new_part', path=path, overwrite=True)
    gear = show('gear_create', 'create_spur_gear', module=2.0, teeth=20, width=8.0,
                pressure_angle=20.0, bore_diameter=10.0, name='M2_Z20')
    bodies = show('gear_bodies', 'get_bodies')['bodies']
    if len(bodies) != 1 or not bodies[0].get('solid', True):
        raise AssertionError('gear expected one solid body: %s' % bodies)
    mass = show('gear_mass', 'mass_properties')
    if float(mass['volume_mm3']) <= 0:
        raise AssertionError('gear volume must be positive')
    if gear['gear']['teeth'] != 20 or abs(gear['gear']['pitch_diameter'] - 40.0) > 1.0e-6:
        raise AssertionError('gear parameters mismatch: %s' % gear['gear'])
    show('gear_save', 'save_part')


def test_threaded_hole():
    path = os.path.join(ROOT, 'examples', 'output', 'threaded_hole.prt')
    show('thread_new', 'new_part', path=path, overwrite=True)
    show('thread_block', 'create_block', length=60, width=40, height=20)
    face = show('thread_top', 'find_faces', type='planar', extreme='top')['faces'][0]['id']
    before = show('thread_before', 'mass_properties')['volume_mm3']
    result = show('thread_create', 'threaded_hole', face=face, positions=[[30, 20, 20]],
                  thread_standard='Metric Coarse', thread_size='M6',
                  tap_drill_diameter=5.0, hole_depth=14.0, thread_depth=12.0,
                  through=False, thread_length_option='custom', left_hand=False,
                  fallback=True)
    after = show('thread_after', 'mass_properties')['volume_mm3']
    if after >= before:
        raise AssertionError('threaded-hole operation did not remove material')
    if not result.get('native_thread', result.get('native', False)) and not result.get('warning'):
        raise AssertionError('thread fallback must report its limitation explicitly')
    show('thread_save', 'save_part')


def main():
    stop_worker()
    time.sleep(3)
    test_colors()
    test_gear()
    test_threaded_hole()
    print('DONE')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
