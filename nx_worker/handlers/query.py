# -*- coding: utf-8 -*-
'''Observation commands (Phase 2): part/bodies/features/expressions/object info/UI selection.'''
import NXOpen

from nx_worker import ctx, geom
from nx_worker.handlers.part import part_brief
from nx_worker.registry import command


def _union_bbox(bodies):
    lo = [None] * 3
    hi = [None] * 3
    for b in bodies:
        bb = ctx.bbox(b)
        if not bb:
            continue
        for i in range(3):
            lo[i] = bb[0][i] if lo[i] is None else min(lo[i], bb[0][i])
            hi[i] = bb[1][i] if hi[i] is None else max(hi[i], bb[1][i])
    if lo[0] is None:
        return None
    return [lo, hi]


@command('part_info', 'read')
def part_info():
    part = ctx.work_part()
    info = part_brief(part)
    bodies = list(part.Bodies)
    solids = [b for b in bodies if b.IsSolidBody]
    info['solid_bodies'] = len(solids)
    info['sheet_bodies'] = len([b for b in bodies if b.IsSheetBody])
    try:
        info['features'] = len(list(part.Features))
    except Exception:
        pass
    try:
        info['sketches'] = len(list(part.Sketches))
    except Exception:
        pass
    bb = _union_bbox(solids)
    if bb:
        info['bbox'] = bb
        info['size'] = ctx.short([bb[1][i] - bb[0][i] for i in range(3)], 4)
    return info


@command('get_bodies', 'read')
def get_bodies():
    part = ctx.work_part()
    return {'bodies': [ctx.body_info(b) for b in part.Bodies]}


@command('get_features', 'read')
def get_features(limit=50, offset=0, type=None, name=None):
    part = ctx.work_part()
    feats = list(part.Features)
    if type:
        t = str(type).lower()
        feats = [f for f in feats if t in str(f.FeatureType).lower()]
    if name:
        n = str(name).lower()
        feats = [f for f in feats if n in str(f.Name).lower()]
    total = len(feats)
    page = feats[int(offset):int(offset) + int(limit)]
    return {'total': total, 'offset': int(offset), 'features': [ctx.feature_info(f) for f in page]}


@command('get_expressions', 'read')
def get_expressions(name=None, limit=50):
    part = ctx.work_part()
    items = []
    n = str(name).lower() if name else None
    for e in part.Expressions:
        try:
            if n and n not in e.Name.lower():
                continue
            row = {'name': e.Name, 'equation': e.RightHandSide}
            try:
                row['value'] = e.Value
            except Exception:
                pass
            items.append(row)
        except Exception:
            continue
    total = len(items)
    return {'total': total, 'expressions': items[:int(limit)]}


@command('get_object_info', 'read')
def get_object_info(object_id):
    obj = ctx.get_obj(object_id)
    kind = ctx.kind_of(obj)
    if kind == 'FACE':
        return {'kind': kind, 'face': geom.face_info(obj, with_area=True)}
    if kind == 'EDGE':
        return {'kind': kind, 'edge': geom.edge_info(obj)}
    if kind == 'BODY':
        return {'kind': kind, 'body': ctx.body_info(obj)}
    if kind == 'FEATURE':
        info = ctx.feature_info(obj)
        try:
            info['expressions'] = [{'name': e.Name, 'equation': e.RightHandSide} for e in obj.GetExpressions()]
        except Exception:
            pass
        return {'kind': kind, 'feature': info}
    info = {'id': ctx.oid(obj), 'kind': kind}
    for attr in ('Name', 'JournalIdentifier'):
        try:
            info[attr.lower()] = getattr(obj, attr)
        except Exception:
            pass
    return {'kind': kind, 'object': info}


@command('get_selected_objects', 'read')
def get_selected_objects():
    '''Objects currently selected by the user in the NX GUI (empty in headless mode).'''
    try:
        sm = NXOpen.UI.GetUI().SelectionManager
        n = sm.GetNumSelectedObjects()
        objs = [sm.GetSelectedTaggedObject(i) for i in range(n)]
    except Exception as exc:
        return {'selected': [], 'note': '无法读取界面选择（无界面模式下不可用）: %s' % exc}
    out = []
    for o in objs:
        kind = ctx.kind_of(o)
        if kind == 'FACE':
            out.append(geom.face_info(o))
        elif kind == 'EDGE':
            out.append(geom.edge_info(o))
        else:
            out.append({'id': ctx.oid(o), 'kind': kind})
    return {'selected': out}
