# -*- coding: utf-8 -*-
'''Basic assembly commands (Phase 7, best effort): add / list / move components.'''
import os

import NXOpen

from nx_worker import ctx
from nx_worker.registry import command


def _comp_info(c):
    info = {'id': ctx.oid(c), 'name': c.Name}
    try:
        info['display_name'] = c.DisplayName
    except Exception:
        pass
    try:
        info['origin'] = ctx.p3(c.GetPosition()[0])
    except Exception:
        pass
    return info


def _walk(c, out, depth, max_depth):
    for ch in c.GetChildren():
        row = _comp_info(ch)
        row['depth'] = depth
        out.append(row)
        if depth < max_depth:
            _walk(ch, out, depth + 1, max_depth)


def _identity():
    m = NXOpen.Matrix3x3()
    m.Xx, m.Yy, m.Zz = 1.0, 1.0, 1.0
    return m


@command('add_component', 'modify')
def add_component(path, name=None, origin=None, reference_set='Entire Part'):
    part = ctx.work_part()
    from nx_worker.handlers.workspace import resolve_path
    p = resolve_path(path)
    if not os.path.isfile(p):
        raise ctx.NxError('文件不存在: ' + p)
    inst = name or os.path.splitext(os.path.basename(p))[0].upper()
    comp, status = part.ComponentAssembly.AddComponent(p, reference_set, inst, ctx.pt(origin), _identity(), -1)
    try:
        status.Dispose()
    except Exception:
        pass
    return {'component': _comp_info(comp)}


@command('get_components', 'read')
def get_components(max_depth=1):
    part = ctx.work_part()
    root = part.ComponentAssembly.RootComponent
    if root is None:
        return {'components': [], 'note': '当前 Part 没有装配组件'}
    out = []
    _walk(root, out, 1, int(max_depth))
    return {'count': len(out), 'components': out}


@command('move_component', 'modify')
def move_component(component, translation):
    '''Translate a component by [dx, dy, dz] (relative move).'''
    part = ctx.work_part()
    c = ctx.get_obj(component, 'COMP')
    if len(translation) != 3:
        raise ctx.NxError('translation 必须是 [dx, dy, dz]')
    t = NXOpen.Vector3d(float(translation[0]), float(translation[1]), float(translation[2]))
    try:
        part.ComponentAssembly.MoveComponent(c, t, _identity())
    except TypeError:
        part.ComponentAssembly.MoveComponent(c, t)
    return {'component': _comp_info(c)}
