# -*- coding: utf-8 -*-
'''Assembly constraint smoke test: base block + plate component, fix the base and touch the plate onto its top.
Usage: python examples/smoke_assembly.py   (restarts the NX worker first)'''
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402

OUT = os.path.join(ROOT, 'examples', 'output', 'asm')


def step(title, cmd, **params):
    print('== ' + title)
    res = call(cmd, **params)
    print(json.dumps(res, ensure_ascii=False)[:700])
    return res


def main():
    stop_worker()
    time.sleep(3)
    call('set_workspace', path=OUT, create=True)
    base = os.path.join(OUT, 'base.prt')
    plate = os.path.join(OUT, 'plate.prt')
    asm = os.path.join(OUT, 'asm.prt')
    call('new_part', path=base, overwrite=True)
    call('create_block', length=60, width=40, height=10)
    call('save_part')
    call('new_part', path=plate, overwrite=True)
    call('create_block', length=30, width=20, height=5, origin=[100, 100, 100])
    call('save_part')
    call('new_part', path=asm, overwrite=True)
    c1 = step('add base', 'add_component', path=base, name='BASE')['component']['id']
    c2 = step('add plate', 'add_component', path=plate, name='PLATE', origin=[100, 100, 100])['component']['id']
    step('fix base', 'add_constraint', kind='fix', component1=c1)
    f1 = step('base top face', 'component_faces', component=c1, type='planar', extreme='top')['faces'][0]['id']
    f2 = step('plate bottom face', 'component_faces', component=c2, type='planar', extreme='bottom')['faces'][0]['id']
    step('touch', 'add_constraint', kind='touch', component1=c1, face1=f1, component2=c2, face2=f2, alignment='contra')
    step('components after', 'get_components')
    bottom = call('component_faces', component=c2, type='planar', extreme='bottom')['faces'][0]
    z = bottom['center'][2]
    ok = abs(z - 10.0) < 0.01
    print('plate bottom face z after touch = %.4f (expected 10.0) -> %s' % (z, 'PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
