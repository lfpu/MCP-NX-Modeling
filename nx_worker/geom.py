# -*- coding: utf-8 -*-
'''Geometry info builders and vector helpers (Phase 2 + 5).

Conventions: top=+Z bottom=-Z right=+X left=-X back=+Y front=-Y (absolute coordinate system).
Planar face normals are OUTWARD normals.
NX 2412 stringifies enums as numbers and the UF API may be unavailable, so every UF call has a pure
vertex-based geometry fallback.
'''
import math

import NXOpen

from nx_worker import ctx

AXES = {
    'top': (0, 0, 1), 'bottom': (0, 0, -1),
    'right': (1, 0, 0), 'left': (-1, 0, 0),
    'back': (0, 1, 0), 'front': (0, -1, 0),
    '+x': (1, 0, 0), '-x': (-1, 0, 0), 'x': (1, 0, 0),
    '+y': (0, 1, 0), '-y': (0, -1, 0), 'y': (0, 1, 0),
    '+z': (0, 0, 1), '-z': (0, 0, -1), 'z': (0, 0, 1),
}

TYPE_ALIAS = {
    'plane': 'planar', 'cylinder': 'cylindrical', 'cone': 'conical', 'sphere': 'spherical',
    'line': 'linear', 'circle': 'circular', 'arc': 'circular', 'ellipse': 'elliptical',
}

# numeric codes: NXOpen.Edge.EdgeType (1 = linear observed in NX 2412) and UF face types
EDGE_CODES = {1: 'linear', 2: 'circular', 3: 'elliptical', 4: 'intersection', 5: 'spline',
              6: 'sp_curve', 7: 'foreign', 8: 'const_param', 9: 'trim_curve'}
UF_FACE_CODES = {16: 'cylindrical', 17: 'conical', 18: 'spherical', 19: 'toroidal', 20: 'revolved',
                 21: 'parametric', 22: 'planar', 23: 'blending', 43: 'offset', 65: 'foreign'}


# ------------------------------------------------------------ vectors

def unit(v):
    n = math.sqrt(sum(float(x) * float(x) for x in v))
    if n < 1e-12:
        return None
    return [float(x) / n for x in v]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def angle_deg(a, b):
    d = max(-1.0, min(1.0, dot(a, b)))
    return math.degrees(math.acos(d))


def mid(bb):
    return [(bb[0][i] + bb[1][i]) / 2.0 for i in range(3)]


def dist(a, b):
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def parse_dir(spec):
    '''top / +z / [0,0,1] -> unit vector list; None stays None.'''
    if spec is None:
        return None
    if isinstance(spec, str):
        key = spec.strip().lower()
        if key not in AXES:
            raise ctx.NxError('方向名称无效: %s（可用: %s，或直接给 [x,y,z]）' % (spec, ', '.join(sorted(AXES))))
        v = AXES[key]
    else:
        v = spec
        if len(v) != 3:
            raise ctx.NxError('方向必须是 [x, y, z]')
    u = unit(v)
    if u is None:
        raise ctx.NxError('方向不能是零向量')
    return u


def enum_name(v, cls=None, table=None):
    '''NX 2412 may stringify enums as numbers (e.g. 1): resolve a readable name.'''
    n = getattr(v, 'name', None)
    if isinstance(n, str) and n:
        return n
    s = str(v)
    if not s.lstrip('-').isdigit():
        return s.split('.')[-1]
    try:
        iv = int(s)
    except Exception:
        return s
    if cls is not None:
        for attr in dir(cls):
            if attr.startswith('_'):
                continue
            try:
                if int(getattr(cls, attr)) == iv:
                    return attr
            except Exception:
                continue
    if table and iv in table:
        return table[iv]
    return s


def type_match(actual, wanted):
    if not wanted:
        return True
    w = TYPE_ALIAS.get(str(wanted).lower(), str(wanted).lower())
    return actual == w or actual.startswith(w)


# ------------------------------------------------------------ faces

def _uf_face_data(face):
    try:
        r = ctx.ufs().Modeling.AskFaceData(face.Tag)
        # (face_type, point, dir, box, radius, rad_data, norm_dir)
        return {'code': int(r[0]), 'point': list(r[1]), 'dir': list(r[2]), 'radius': float(r[4]), 'norm_dir': int(r[6])}
    except Exception:
        return None


def _plane_normal(pts, tol=1e-3):
    if len(pts) < 3:
        return None
    p0 = pts[0]
    n = None
    for i in range(1, len(pts)):
        for j in range(i + 1, len(pts)):
            c = cross(sub(pts[i], p0), sub(pts[j], p0))
            if math.sqrt(dot(c, c)) > 1e-6:
                n = unit(c)
                break
        if n:
            break
    if n is None:
        return None
    for p in pts:
        if abs(dot(sub(p, p0), n)) > tol:
            return None
    return n


def _planar_fallback(face):
    '''Planar test + outward normal computed from vertices only (no UF).'''
    pts = ctx.vertex_points(face)
    n = _plane_normal(pts)
    if n is None:
        return None
    c = [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    try:
        bc = mid(ctx.bbox(face.GetBody()))
        if dot(n, sub(c, bc)) < 0:
            n = [-x for x in n]
    except Exception:
        pass
    return {'point': c, 'normal': n}


def face_data(face):
    '''dict(point, dir, radius, norm_dir). Falls back to geometry for planar faces (outward normal, norm_dir=1).'''
    d = _uf_face_data(face)
    if d:
        return d
    fb = _planar_fallback(face)
    if fb:
        return {'code': 22, 'point': fb['point'], 'dir': fb['normal'], 'radius': 0.0, 'norm_dir': 1, 'source': 'geometry'}
    return None


def face_area(face):
    try:
        part = ctx.work_part()
        uc = part.UnitCollection
        units = [NXOpen.Unit.Null] * 5
        units[0] = uc.FindObject('SquareMilliMeter')
        units[1] = uc.FindObject('CubicMilliMeter')
        units[2] = uc.FindObject('Kilogram')
        units[3] = uc.FindObject('Newton')
        units[4] = uc.FindObject('MilliMeter')
        mf = part.MeasureManager.NewFaceProperties(units, 0.99, [face])
        try:
            return float(mf.Area)
        finally:
            mf.Dispose()
    except Exception:
        pass
    try:
        bb = ctx.bbox(face)
        ext = sorted([bb[1][i] - bb[0][i] for i in range(3)])
        return ext[1] * ext[2]  # approximation, exact for rectangular planar faces
    except Exception:
        return None


def face_info(face, with_area=False):
    info = {'id': ctx.oid(face)}
    fd = _uf_face_data(face)
    ftype = UF_FACE_CODES.get(fd['code']) if fd else None
    if ftype is None:
        nm = enum_name(face.SolidFaceType, getattr(NXOpen.Face, 'FaceType', None))
        if not nm.lstrip('-').isdigit():
            ftype = nm.lower()
        else:
            info['type_code'] = nm
    fb = None
    if ftype is None or ftype == 'planar':
        fb = _planar_fallback(face)
        if ftype is None:
            ftype = 'planar' if fb else 'other'
    info['type'] = ftype
    bb = ctx.bbox(face)
    if bb:
        info['bbox'] = bb
        info['center'] = ctx.short(mid(bb), 4)
    if ftype == 'planar':
        if fd:
            n = unit(fd['dir'])
            if n:
                s = -1.0 if fd['norm_dir'] < 0 else 1.0
                info['normal'] = [round(x * s, 6) + 0.0 for x in n]
        elif fb:
            info['normal'] = [round(x, 6) + 0.0 for x in fb['normal']]
            info['normal_source'] = 'geometry'
    elif fd and ftype in ('cylindrical', 'conical'):
        n = unit(fd['dir'])
        if n:
            info['axis'] = [round(x, 6) + 0.0 for x in n]
            info['axis_point'] = ctx.short(fd['point'], 4)
            info['radius'] = round(fd['radius'], 6)
    elif fd and ftype == 'spherical':
        info['center_point'] = ctx.short(fd['point'], 4)
        info['radius'] = round(fd['radius'], 6)
    if with_area:
        a = face_area(face)
        if a is not None:
            info['area'] = round(a, 4)
    return info


# ------------------------------------------------------------ edges

def arc_radius(edge):
    uf = None
    ev = None
    try:
        uf = ctx.ufs()
        ev = uf.Eval.Initialize2(edge.Tag)
        arc = uf.Eval.AskArc(ev)
        return float(arc.radius)
    except Exception:
        return None
    finally:
        if ev is not None and uf is not None:
            try:
                uf.Eval.Free(ev)
            except Exception:
                pass


def edge_info(edge):
    nm = enum_name(edge.SolidEdgeType, getattr(NXOpen.Edge, 'EdgeType', None), EDGE_CODES)
    etype = nm.lower()
    info = {'id': ctx.oid(edge)}
    sa = sb = None
    try:
        a, b = edge.GetVertices()
        sa, sb = ctx.p3(a), ctx.p3(b)
        info['start'] = sa
        info['end'] = sb
    except Exception:
        pass
    length = None
    try:
        length = float(edge.GetLength())
    except Exception:
        pass
    if etype.lstrip('-').isdigit() and sa and sb and length is not None and abs(length - dist(sa, sb)) < 1e-6:
        etype = 'linear'
    info['type'] = etype
    if length is not None:
        info['length'] = round(length, 6)
    bb = ctx.bbox(edge)
    if bb:
        info['bbox'] = bb
        info['center'] = ctx.short(mid(bb), 4)
    if etype == 'linear' and sa and sb:
        d = unit(sub(sb, sa))
        if d:
            info['direction'] = [round(x, 6) + 0.0 for x in d]
    if etype == 'circular':
        r = arc_radius(edge)
        if r is not None:
            info['radius'] = round(r, 6)
    try:
        info['faces'] = [ctx.oid(f) for f in edge.GetFaces()]
    except Exception:
        pass
    return info
