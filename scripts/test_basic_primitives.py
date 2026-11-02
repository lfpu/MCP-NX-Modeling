# -*- coding: utf-8 -*-
'''NX 2412 regression test for sphere, cone and circle/arc sketch planes.'''
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from nx_mcp.client import call, stop_worker

OUT = os.path.join(ROOT, 'examples', 'output', 'basic_primitives')
LOG = os.path.join(ROOT, 'logs', 'basic_primitives_test.txt')


def check_close(name, actual, expected, rel=0.01):
    if not math.isclose(float(actual), float(expected), rel_tol=rel):
        raise AssertionError('%s: actual=%s expected=%s' % (name, actual, expected))


def new_part(name):
    path = os.path.join(OUT, name + '.prt')
    return call('new_part', path=path, overwrite=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    stop_worker()
    time.sleep(3)
    results = {}

    new_part('sphere')
    sphere = call('create_sphere', diameter=20.0, center=[5.0, 6.0, 7.0])
    sphere_mass = call('mass_properties')
    sphere_expected = 4.0 / 3.0 * math.pi * 10.0 ** 3
    check_close('sphere volume', sphere_mass['volume_mm3'], sphere_expected)
    call('save_part')
    results['sphere'] = {
        'feature': sphere.get('feature'),
        'volume': sphere_mass['volume_mm3'],
        'expected_volume': sphere_expected,
    }

    new_part('cone')
    cone = call(
        'create_cone',
        base_diameter=20.0,
        top_diameter=10.0,
        height=30.0,
        origin=[0.0, 0.0, 0.0],
        direction=[0.0, 0.0, 1.0],
    )
    cone_mass = call('mass_properties')
    r1, r2, height = 10.0, 5.0, 30.0
    cone_expected = math.pi * height * (r1 * r1 + r1 * r2 + r2 * r2) / 3.0
    check_close('cone volume', cone_mass['volume_mm3'], cone_expected)
    call('save_part')
    results['cone'] = {
        'feature': cone.get('feature'),
        'volume': cone_mass['volume_mm3'],
        'expected_volume': cone_expected,
    }

    for plane in ('xy', 'yz', 'xz'):
        new_part('sketch_' + plane)
        sketch = call(
            'create_sketch',
            plane=plane,
            offset=4.0,
            name='CircleArc_' + plane.upper(),
            shapes=[
                {'type': 'circle', 'center': [10.0, 20.0], 'diameter': 12.0},
                {'type': 'arc', 'center': [-10.0, -5.0], 'radius': 8.0, 'start_angle': 0.0, 'end_angle': 180.0},
            ],
        )
        sketches = call('get_sketches')
        matching = [s for s in sketches.get('sketches', sketches if isinstance(sketches, list) else []) if s.get('name', '').upper() == 'CIRCLEARC_' + plane.upper()]
        if not matching:
            raise AssertionError('%s sketch was created but not returned by get_sketches' % plane)
        curve_count = matching[0].get('curves', matching[0].get('curve_count'))
        if isinstance(curve_count, list):
            curve_count = len(curve_count)
        call('save_part')
        results['sketch_' + plane] = {
            'sketch': sketch.get('sketch'),
            'curve_count': curve_count,
            'plane': plane,
        }
        if curve_count != 2:
            raise AssertionError('%s sketch expected 2 curves, got %s' % (plane, curve_count))

    text = json.dumps({'ok': True, 'results': results}, ensure_ascii=False, indent=2, default=str)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
