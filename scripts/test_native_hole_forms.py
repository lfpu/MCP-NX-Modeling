# -*- coding: utf-8 -*-
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from nx_mcp.client import call, stop_worker


def top_face():
    faces = call('find_faces', type='planar', extreme='top')['faces']
    if not faces:
        raise RuntimeError('top face not found')
    return faces[0]['id']


def run_case(name, kwargs):
    path = os.path.join(ROOT, 'examples', 'output', 'native_' + name + '.prt')
    call('new_part', path=path, overwrite=True)
    call('create_block', length=80, width=60, height=20)
    before = call('mass_properties')['volume_mm3']
    result = call('hole_native', face=top_face(), positions=[[40, 30, 20]], fallback=False, **kwargs)
    after = call('mass_properties')['volume_mm3']
    print(name + '=' + json.dumps({'result': result, 'before': before, 'after': after, 'removed': before - after}, ensure_ascii=False, default=str))
    call('save_part')


def main():
    stop_worker()
    time.sleep(3)
    run_case('simple_blind', dict(diameter=10.0, depth=8.0, through=False, hole_form='simple'))
    run_case('counterbore', dict(diameter=8.0, depth=12.0, through=False, hole_form='counterbore', cbore_diameter=14.0, cbore_depth=4.0))
    run_case('countersink', dict(diameter=8.0, through=True, hole_form='countersink', csink_diameter=14.0, csink_angle=90.0))


if __name__ == '__main__':
    main()
