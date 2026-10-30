# -*- coding: utf-8 -*-
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker


def main():
    stop_worker()
    time.sleep(3)
    path = os.path.join(ROOT, 'examples', 'output', 'native_hole_probe.prt')
    print(json.dumps(call('new_part', path=path, overwrite=True), ensure_ascii=False))
    call('create_block', length=60, width=40, height=20)
    faces = call('find_faces', type='planar', extreme='top')['faces']
    if not faces:
        raise RuntimeError('top face not found')
    face = faces[0]['id']
    before = call('mass_properties')['volume_mm3']
    r = call('hole_native', face=face, positions=[[30, 20, 20]], diameter=10.0, through=True, hole_form='simple', fallback=False)
    after = call('mass_properties')['volume_mm3']
    print('RESULT=' + json.dumps(r, ensure_ascii=False, default=str))
    print('VOLUME_BEFORE=%s' % before)
    print('VOLUME_AFTER=%s' % after)
    print('REMOVED=%s' % (before - after))
    call('save_part')


if __name__ == '__main__':
    main()
