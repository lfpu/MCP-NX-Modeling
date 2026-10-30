# -*- coding: utf-8 -*-
'''NX 2412 real-machine tests for chamfer, revolve and STEP import.'''
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker

OUT = os.path.join(ROOT, 'examples', 'output', 'remaining')


def step(title, command, **kwargs):
    result = call(command, **kwargs)
    print(title + '=' + json.dumps(result, ensure_ascii=False, default=str))
    return result


def feature_type(result):
    return str((result.get('feature') or {}).get('type', '')).lower()


def test_chamfer():
    path = os.path.join(OUT, 'chamfer.prt')
    step('chamfer_new_part', 'new_part', path=path, overwrite=True)
    step('chamfer_block', 'create_block', length=40.0, width=30.0, height=20.0)
    edges = step('chamfer_edges', 'find_edges', type='linear', parallel='top').get('edges', [])
    if not edges:
        raise AssertionError('no vertical edges found for chamfer')
    result = step('chamfer_result', 'chamfer', edges=[edges[0]['id']], distance=3.0)
    if 'chamfer' not in feature_type(result):
        raise AssertionError('unexpected chamfer feature: %r' % result)
    step('chamfer_save', 'save_part')


def test_revolve():
    path = os.path.join(OUT, 'revolve.prt')
    step('revolve_new_part', 'new_part', path=path, overwrite=True)
    sketch = step('revolve_sketch', 'create_sketch', plane='xy', name='RevolveProfile', shapes=[
        {'type': 'rectangle', 'corner': [0.0, 10.0], 'width': 20.0, 'height': 8.0},
    ])['sketch']['id']
    result = step('revolve_result', 'revolve', sketch=sketch, axis_origin=[0.0, 0.0, 0.0], axis_direction='x', angle=360.0)
    bodies = step('revolve_bodies', 'get_bodies').get('bodies', [])
    if len(bodies) != 1 or not bodies[0].get('is_solid'):
        raise AssertionError('revolve did not create one solid body: %r' % bodies)
    expected = math.pi * (18.0 * 18.0 - 10.0 * 10.0) * 20.0
    actual = step('revolve_mass', 'mass_properties')['volume_mm3']
    if abs(actual - expected) > expected * 0.002:
        raise AssertionError('revolve volume mismatch: actual=%s expected=%s' % (actual, expected))
    step('revolve_save', 'save_part')


def test_step_roundtrip():
    source_part = os.path.join(OUT, 'step_source.prt')
    step_file = os.path.join(OUT, 'step_source.stp')
    imported_part = os.path.join(OUT, 'step_imported.prt')
    step('step_new_part', 'new_part', path=source_part, overwrite=True)
    step('step_block', 'create_block', length=32.0, width=24.0, height=12.0)
    expected = step('step_source_mass', 'mass_properties')['volume_mm3']
    step('step_save_source', 'save_part')
    exported = step('step_export', 'export_step', path=step_file, overwrite=True)
    if exported.get('size_bytes', 0) <= 0:
        raise AssertionError('STEP export is empty')
    imported = step('step_import', 'import_step', path=step_file, output_part=imported_part, overwrite=True)
    if imported.get('size_bytes', 0) <= 0:
        raise AssertionError('STEP import did not create a part')
    # import_step 使用 FileOpenFlag=true，导入后的 Part 已经是当前工作 Part；
    # 再次 open_part 会因为同一路径已在 NX 中打开而返回 File already exists。
    bodies = step('step_imported_bodies', 'get_bodies').get('bodies', [])
    if len(bodies) != 1:
        raise AssertionError('STEP import expected one body, got %s' % len(bodies))
    actual = step('step_imported_mass', 'mass_properties')['volume_mm3']
    if abs(actual - expected) > expected * 0.001:
        raise AssertionError('STEP roundtrip volume mismatch: actual=%s expected=%s' % (actual, expected))


def main():
    os.makedirs(OUT, exist_ok=True)
    stop_worker()
    time.sleep(3)
    test_chamfer()
    test_revolve()
    test_step_roundtrip()
    print('REMAINING_FEATURE_TESTS_PASSED')


if __name__ == '__main__':
    main()
