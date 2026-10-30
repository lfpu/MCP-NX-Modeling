# -*- coding: utf-8 -*-
'''Advanced smoke test: every high-level feature runs in its own fresh part and gets a PASS/FAIL line.
One failure does not stop the others. Results are also written to logs/smoke_adv.json.
Usage: python examples/smoke_advanced.py   (restarts the NX worker first so new code is loaded)
Not covered: assembly constraints (need two saved parts) and STEP import.'''
import json
import math
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import NxWorkerError, call, stop_worker  # noqa: E402

OUT = os.path.join(ROOT, 'examples', 'output', 'adv')
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def S(label, cmd, **params):
    try:
        return call(cmd, **params)
    except NxWorkerError as exc:
        raise RuntimeError('%s: %s' % (label, str(exc)[:240]))


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def near(a, b, tol=1.0):
    return abs(a - b) <= tol


def fresh(name):
    S('new_part', 'new_part', path=name + '.prt', overwrite=True)


def block(name, l=60, w=40, h=30):
    fresh(name)
    return S('block', 'create_block', length=l, width=w, height=h)


def vol():
    return S('mass', 'mass_properties')['volume_mm3']


def top_face():
    r = S('find top face', 'find_faces', type='planar', extreme='top')
    check(r['faces'], 'top face not found')
    return r['faces'][0]['id']


def boss(name):
    block(name, 60, 40, 10)
    r = S('boss', 'create_cylinder', diameter=5, height=5, origin=[5, 5, 10], boolean='unite')
    return r['feature']['id']


@test
def t_workspace():
    S('set', 'set_workspace', path=OUT, create=True)
    got = S('get', 'get_workspace')['workspace']
    check(got.lower() == os.path.abspath(OUT).lower(), 'workspace mismatch: %s' % got)


@test
def t_extrude_pocket():
    fresh('t_extrude')
    shapes = [{'type': 'rectangle', 'corner': [0, 0], 'width': 60, 'height': 40}]
    sk = S('sketch', 'create_sketch', shapes=shapes, plane='xy')['sketch']['id']
    S('extrude', 'extrude', sketch=sk, distance=10)
    v = vol()
    check(near(v, 24000), 'extrude volume %s expected 24000' % v)
    hole = [{'type': 'circle', 'center': [30, 20], 'diameter': 10}]
    sk2 = S('sketch on face', 'create_sketch', shapes=hole, face=top_face())['sketch']['id']
    S('pocket', 'pocket', sketch=sk2, depth=5)
    v2 = vol()
    expect = 24000 - math.pi * 25 * 5
    check(near(v2, expect, 2), 'pocket volume %s expected %.1f' % (v2, expect))


@test
def t_shell():
    block('t_shell')
    S('shell', 'shell', faces=[top_face()], thickness=3)
    v = vol()
    # outer 60*40*30 = 72000, cavity (60-6)*(40-6)*(30-3) = 49572 -> 22428
    check(near(v, 22428, 5), 'shell volume %s expected 22428' % v)


@test
def t_pattern():
    fid = boss('t_pattern')
    v0 = vol()
    S('pattern', 'pattern_feature', features=[fid], kind='linear', direction='x', count=3, spacing=20)
    extra = 2 * math.pi * 2.5 ** 2 * 5
    added = vol() - v0
    check(near(added, extra, 1), 'pattern added %.2f expected %.2f' % (added, extra))


@test
def t_suppress_rename():
    fid = boss('t_suppress')
    v0 = vol()
    S('suppress', 'suppress_feature', feature=fid, suppress=True)
    v1 = vol()
    check(v1 < v0 - 1, 'suppress did not reduce volume (%s -> %s)' % (v0, v1))
    S('unsuppress', 'suppress_feature', feature=fid, suppress=False)
    v2 = vol()
    check(near(v2, v0), 'unsuppress volume %s expected %s' % (v2, v0))
    S('rename', 'rename_object', object_id=fid, name='BOSS')


@test
def t_mirror():
    block('t_mirror', 20, 20, 20)
    S('mirror', 'mirror_body', plane='yz')
    size = S('info', 'part_info')['size']
    check(near(size[0], 40, 0.1), 'size after mirror %s expected x=40' % size)


@test
def t_datum_axis():
    block('t_datum', 10, 10, 10)
    r = S('axis', 'create_datum_axis', origin=[0, 0, 0], direction=[0, 0, 1])
    check(r.get('datum_axis'), 'no datum axis id: %s' % r)


@test
def t_measure():
    block('t_measure', 10, 10, 10)
    r = S('points', 'measure_distance', a=[0, 0, 0], b=[3, 4, 0])
    check(near(r['distance'], 5, 1e-6), 'point distance %s' % r)
    top = top_face()
    bot = S('bottom', 'find_faces', type='planar', extreme='bottom')['faces'][0]['id']
    r = S('faces', 'measure_distance', a=top, b=bot)
    check(near(r['distance'], 10, 0.01), 'face distance %s' % r)
    check(r.get('method') == 'nx_measure', 'NX exact measure unavailable, fell back to: %s' % r.get('method'))


def _export(cmd, fname):
    block('t_' + cmd)
    r = S(cmd, cmd, path=fname, overwrite=True)
    check(r['size_bytes'] > 0 and os.path.isfile(r['path']), 'empty or missing file: %s' % r)


@test
def t_export_step():
    _export('export_step', 'out.stp')


@test
def t_export_stl():
    _export('export_stl', 'out.stl')


@test
def t_export_iges():
    _export('export_iges', 'out.igs')


@test
def t_undo_and_confirm():
    block('t_safety', 10, 10, 10)
    bid = S('bodies', 'get_bodies')['bodies'][0]['id']
    r = S('delete without confirm', 'delete_object', object_id=bid)
    check(r.get('needs_confirmation'), 'delete_object did not ask for confirmation: %s' % r)
    S('undo', 'undo_last')
    left = len(S('bodies', 'get_bodies')['bodies'])
    check(left == 0, 'body still exists after undo (%d)' % left)


@test
def t_drawing():
    block('t_drawing')
    S('sheet', 'create_drawing_sheet', size='A3')
    v = S('base view', 'add_base_view', view='front', position=[150, 150])['view']['id']
    S('projected view', 'add_projected_view', parent=v, position=[150, 230])
    check(S('sheets', 'get_drawing_sheets')['count'] >= 1, 'no sheet listed')
    r = S('pdf', 'export_drawing_pdf', path='drawing.pdf', overwrite=True)
    check(r['size_bytes'] > 0, 'empty pdf')


def main():
    stop_worker()
    time.sleep(3)
    rows = []
    for fn in TESTS:
        t0 = time.time()
        row = {'name': fn.__name__, 'ok': True}
        try:
            fn()
        except Exception as exc:
            row['ok'] = False
            row['error'] = str(exc)[:300]
        row['ms'] = int((time.time() - t0) * 1000)
        rows.append(row)
        print('%s %-22s %6d ms%s' % ('PASS' if row['ok'] else 'FAIL', row['name'], row['ms'], '' if row['ok'] else '  ' + row['error']))
    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    with open(os.path.join(ROOT, 'logs', 'smoke_adv.json'), 'w', encoding='utf-8') as fp:
        json.dump(rows, fp, ensure_ascii=False, indent=1)
    bad = [r for r in rows if not r['ok']]
    print('%d/%d passed' % (len(rows) - len(bad), len(rows)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
