# -*- coding: utf-8 -*-
'''Geometry selection system (Phase 5): find faces / edges by semantic conditions.
All filtering happens here so the LLM only receives a few small, structured results.'''
from nx_worker import ctx, geom
from nx_worker.registry import command


def _bodies(body):
    if body:
        return [ctx.get_obj(body, 'BODY')]
    solids = ctx.solid_bodies(ctx.work_part())
    if not solids:
        raise ctx.NxError('当前没有实体')
    return solids


def _in_box(center, box):
    if not box or len(box) != 2:
        raise ctx.NxError('within_box 格式应为 [[xmin,ymin,zmin],[xmax,ymax,zmax]]')
    return all(min(box[0][i], box[1][i]) - 1e-6 <= center[i] <= max(box[0][i], box[1][i]) + 1e-6 for i in range(3))


def _sort(rows, sort, keyf):
    '''rows: list of (obj, info). sort like area_desc / z_asc / length_desc / dist_asc.'''
    if not sort:
        return rows
    key, _, order = str(sort).lower().rpartition('_')
    if order not in ('asc', 'desc') or not key:
        raise ctx.NxError('sort 格式应为 <key>_<asc|desc>，例如 area_desc、z_asc')
    return sorted(rows, key=lambda r: keyf(r[1], key), reverse=(order == 'desc'))


def _face_key(info, key):
    if key in ('x', 'y', 'z'):
        return (info.get('center') or [0, 0, 0])['xyz'.index(key)]
    if key == 'dist':
        return info.get('distance', 0.0)
    return info.get(key, 0.0) or 0.0


def _edge_key(info, key):
    return _face_key(info, key)


def _finish_faces(rows, total, limit, need_area, verbose):
    rows = rows[:int(limit)]
    out = []
    for f, info in rows:
        if not need_area and 'area' not in info:
            a = geom.face_area(f)
            if a is not None:
                info['area'] = round(a, 4)
        if not verbose:
            info.pop('bbox', None)
        out.append(info)
    return {'count': total, 'returned': len(out), 'truncated': total > len(out), 'faces': out}


@command('find_faces', 'read')
def find_faces(body=None, type=None, normal=None, extreme=None, min_area=None, max_area=None,
               radius=None, angle_tol=1.0, tol=1e-3, within_box=None, near=None,
               sort=None, limit=20, verbose=False):
    n_dir = geom.parse_dir(normal)
    ext = geom.parse_dir(extreme)
    need_area = min_area is not None or max_area is not None or bool(sort and str(sort).lower().startswith('area'))
    rows = []
    for b in _bodies(body):
        for f in b.GetFaces():
            info = geom.face_info(f, need_area)
            info['body'] = ctx.oid(b)
            if not geom.type_match(info['type'], type):
                continue
            if n_dir is not None:
                fn = info.get('normal')
                if not fn or geom.angle_deg(fn, n_dir) > float(angle_tol):
                    continue
            if radius is not None:
                r = info.get('radius')
                if r is None or abs(r - float(radius)) > float(tol) * max(1.0, float(radius)):
                    continue
            if need_area:
                a = info.get('area')
                if a is None:
                    continue
                if min_area is not None and a < float(min_area):
                    continue
                if max_area is not None and a > float(max_area):
                    continue
            if within_box is not None and not _in_box(info.get('center') or [0, 0, 0], within_box):
                continue
            if near is not None:
                info['distance'] = round(geom.dist(info.get('center') or [0, 0, 0], near), 4)
            rows.append((f, info))

    if ext is not None:
        cand = []
        for f, info in rows:
            fn = info.get('normal')
            if fn and geom.angle_deg(fn, ext) <= float(angle_tol) and info.get('center'):
                cand.append((f, info, geom.dot(info['center'], ext)))
        if not cand:
            rows = []
        else:
            best = max(c[2] for c in cand)
            rows = [(f, info) for f, info, p in cand if p >= best - 1e-3]

    total = len(rows)
    rows = _sort(rows, sort, _face_key)
    return _finish_faces(rows, total, limit, need_area, verbose)


@command('find_edges', 'read')
def find_edges(body=None, type=None, parallel=None, on_face=None, min_length=None, max_length=None,
               radius=None, angle_tol=1.0, tol=1e-3, within_box=None, near=None,
               sort=None, limit=20, verbose=False):
    par = geom.parse_dir(parallel)
    if on_face:
        face = ctx.get_obj(on_face, 'FACE')
        edges = list(face.GetEdges())
    else:
        edges = []
        for b in _bodies(body):
            edges.extend(b.GetEdges())
    rows = []
    for e in edges:
        info = geom.edge_info(e)
        if not geom.type_match(info['type'], type):
            continue
        if par is not None:
            d = info.get('direction')
            if not d:
                continue
            ang = geom.angle_deg(d, par)
            if min(ang, 180.0 - ang) > float(angle_tol):
                continue
        ln = info.get('length')
        if min_length is not None and (ln is None or ln < float(min_length) - 1e-6):
            continue
        if max_length is not None and (ln is None or ln > float(max_length) + 1e-6):
            continue
        if radius is not None:
            r = info.get('radius')
            if r is None or abs(r - float(radius)) > float(tol) * max(1.0, float(radius)):
                continue
        if within_box is not None and not _in_box(info.get('center') or [0, 0, 0], within_box):
            continue
        if near is not None:
            info['distance'] = round(geom.dist(info.get('center') or [0, 0, 0], near), 4)
        rows.append((e, info))
    total = len(rows)
    rows = _sort(rows, sort, _edge_key)[:int(limit)]
    out = []
    for _e, info in rows:
        if not verbose:
            info.pop('bbox', None)
        out.append(info)
    return {'count': total, 'returned': len(out), 'truncated': total > len(out), 'edges': out}


@command('face_neighbors', 'read')
def face_neighbors(face_id):
    '''Faces that share an edge with the given face, with the shared edge ids.'''
    face = ctx.get_obj(face_id, 'FACE')
    nb = {}
    for e in face.GetEdges():
        try:
            for f in e.GetFaces():
                if f.Tag != face.Tag:
                    nb.setdefault(f.Tag, {'face': f, 'edges': []})['edges'].append(ctx.oid(e))
        except Exception:
            continue
    out = []
    for item in nb.values():
        info = geom.face_info(item['face'])
        info.pop('bbox', None)
        info['shared_edges'] = item['edges']
        out.append(info)
    return {'face': face_id, 'neighbors': out}
