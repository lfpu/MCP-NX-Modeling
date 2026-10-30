# -*- coding: utf-8 -*-
'''Shared helpers for NX handlers: session/part access, object ids, geometry helpers.'''
import NXOpen
import NXOpen.Features
import NXOpen.GeometricUtilities

try:
    import NXOpen.Utilities as _Utilities
except ImportError:
    _Utilities = None
try:
    import NXOpen.Assemblies
except ImportError:
    pass


def _by_tag(tag):
    '''tag -> NX object. NX 2412 Python has no importable NXOpen.Utilities, so use TaggedObjectManager first.'''
    tom = getattr(NXOpen, 'TaggedObjectManager', None)
    if tom is not None:
        try:
            return tom.GetTaggedObject(tag)
        except Exception:
            pass
    if _Utilities is not None:
        try:
            return _Utilities.NXObjectManager.Get(tag)
        except Exception:
            pass
    return None


class NxError(Exception):
    '''Error with a message that is safe/friendly to show to the LLM.'''


def session():
    return NXOpen.Session.GetSession()


def ufs():
    try:
        import NXOpen.UF
    except ImportError:
        pass
    uf = getattr(NXOpen, 'UF', None)
    if uf is None:
        raise NxError('NXOpen.UF 不可用')
    return uf.UFSession.GetUFSession()


def work_part():
    part = session().Parts.Work
    if part is None:
        raise NxError('没有打开的工作 Part，请先调用 nx_new_part 或 nx_open_part')
    return part


# ------------------------------------------------------------ value helpers

def num(v):
    '''float -> expression string used by NX builders.'''
    return repr(float(v))


def pt(v, default=(0.0, 0.0, 0.0)):
    v = default if v is None else v
    if len(v) != 3:
        raise NxError('坐标必须是 [x, y, z] 三个数')
    return NXOpen.Point3d(float(v[0]), float(v[1]), float(v[2]))


def vec(v, default=(0.0, 0.0, 1.0)):
    v = default if v is None else v
    if len(v) != 3:
        raise NxError('方向必须是 [x, y, z] 三个数')
    if abs(v[0]) + abs(v[1]) + abs(v[2]) == 0:
        raise NxError('方向向量不能为零向量')
    return NXOpen.Vector3d(float(v[0]), float(v[1]), float(v[2]))


def p3(p):
    return [round(p.X, 6), round(p.Y, 6), round(p.Z, 6)]


def short(v, nd=6):
    return [round(float(x), nd) for x in v]


# ------------------------------------------------------------ object ids

def _kind_classes():
    out = []
    for kind, path in (
        ('FACE', 'Face'),
        ('EDGE', 'Edge'),
        ('BODY', 'Body'),
        ('FEATURE', 'Features.Feature'),
        ('SKETCH', 'Sketch'),
        ('COMP', 'Assemblies.Component'),
        ('DATUM', 'DatumPlane'),
        ('DAXIS', 'DatumAxis'),
        ('CURVE', 'Curve'),
        ('POINT', 'Point'),
    ):
        obj = NXOpen
        try:
            for p in path.split('.'):
                obj = getattr(obj, p)
            out.append((kind, obj))
        except AttributeError:
            pass
    return out


def kind_of(obj):
    for kind, cls in _kind_classes():
        try:
            if isinstance(obj, cls):
                return kind
        except Exception:
            pass
    return 'OBJ'


def oid(obj):
    return '%s_%d' % (kind_of(obj), obj.Tag)


def get_obj(ident, kind=None):
    '''Resolve an id like FACE_1234 (or a bare tag number) to an NX object.'''
    prefix = None
    if isinstance(ident, int):
        tag = ident
    else:
        s = str(ident).strip()
        try:
            if '_' in s:
                prefix, t = s.rsplit('_', 1)
                tag = int(t)
            else:
                tag = int(s)
        except ValueError:
            raise NxError('非法对象 id: %r（格式应类似 FACE_1234）' % (ident,))
    if kind and prefix and prefix.upper() != kind:
        raise NxError('对象 %s 不是 %s 类型' % (ident, kind))
    obj = _by_tag(tag)
    if obj is None:
        raise NxError('找不到对象 %s（可能已被删除，请重新查询）' % (ident,))
    return obj


def get_many(idents, kind=None):
    if not idents:
        raise NxError('对象 id 列表不能为空')
    return [get_obj(i, kind) for i in idents]


# ------------------------------------------------------------ info builders

def feature_info(feat):
    info = {
        'id': oid(feat),
        'name': feat.Name,
        'journal_id': feat.JournalIdentifier,
        'type': feat.FeatureType,
    }
    try:
        info['suppressed'] = bool(feat.Suppressed)
    except Exception:
        pass
    try:
        info['bodies'] = [oid(b) for b in feat.GetBodies()]
    except Exception:
        pass
    return info


def bbox(obj):
    '''Axis aligned bounding box [[xmin,ymin,zmin],[xmax,ymax,zmax]] or None.'''
    b = None
    for form in (0, 1):
        try:
            if form == 0:
                r = ufs().Modeling.AskBoundingBox(obj.Tag)
            else:
                box = [0.0] * 6
                r = ufs().Modeling.AskBoundingBox(obj.Tag, box)
                if r is None or len(r) < 6:
                    r = box
            vals = [float(x) for x in list(r)[:6]]
            if len(vals) == 6 and any(abs(x) > 0 for x in vals):
                b = vals
                break
        except Exception:
            continue
    if b:
        return [short(b[0:3], 4), short(b[3:6], 4)]
    # fallback without UF: bounding box of edge vertices (approximate for curved geometry)
    pts = vertex_points(obj)
    if not pts:
        return None
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return [short(lo, 4), short(hi, 4)]


def vertex_points(obj):
    '''Vertex coordinates of a face/body (via its edges) or of an edge.'''
    edges = []
    if hasattr(obj, 'GetEdges'):
        try:
            edges = list(obj.GetEdges())
        except Exception:
            edges = []
    elif hasattr(obj, 'GetVertices'):
        edges = [obj]
    pts = []
    for e in edges:
        try:
            a, b = e.GetVertices()
            pts.append([a.X, a.Y, a.Z])
            pts.append([b.X, b.Y, b.Z])
        except Exception:
            continue
    return pts


def body_info(body):
    info = {
        'id': oid(body),
        'name': body.Name,
        'journal_id': body.JournalIdentifier,
        'is_solid': bool(body.IsSolidBody),
        'is_sheet': bool(body.IsSheetBody),
        'faces': len(body.GetFaces()),
        'edges': len(body.GetEdges()),
    }
    bb = bbox(body)
    if bb:
        info['bbox'] = bb
    return info


def solid_bodies(part):
    return [b for b in part.Bodies if b.IsSolidBody]


def default_target_body(part):
    solids = solid_bodies(part)
    if len(solids) == 1:
        return solids[0]
    if not solids:
        raise NxError('当前没有实体可作为布尔目标，请先创建实体')
    raise NxError('当前有 %d 个实体，请用 target_body 指定布尔目标（先调用 nx_get_bodies）' % len(solids))


_BOOL = {'create': 'Create', 'unite': 'Unite', 'subtract': 'Subtract', 'intersect': 'Intersect'}


def apply_boolean(builder, op, target_body, part):
    '''Configure builder.BooleanOption. op: create|unite|subtract|intersect.'''
    op = (op or 'create').lower()
    if op not in _BOOL:
        raise NxError('boolean 只能是 create/unite/subtract/intersect，收到: %s' % op)
    # Block/Cylinder builders expose BooleanOption; Extrude/Revolve expose BooleanOperation.
    opt = getattr(builder, 'BooleanOption', None)
    if opt is None:
        opt = builder.BooleanOperation
    opt.Type = getattr(NXOpen.GeometricUtilities.BooleanOperation.BooleanType, _BOOL[op])
    if op != 'create':
        body = get_obj(target_body, 'BODY') if target_body else default_target_body(part)
        opt.SetTargetBodies([body])
    return op


def commit(builder):
    '''Commit a feature builder and always destroy it.'''
    try:
        return builder.CommitFeature()
    finally:
        builder.Destroy()


def make_axis(part, origin, direction):
    o = pt(origin)
    d = vec(direction)
    point = part.Points.CreatePoint(o)
    direction_obj = part.Directions.CreateDirection(o, d, NXOpen.SmartObject.UpdateOption.WithinModeling)
    return part.Axes.CreateAxis(point, direction_obj, NXOpen.SmartObject.UpdateOption.WithinModeling)


def enum_member(paths, candidates):
    '''Find an enum member: try several enum class paths and name candidates (case-insensitive substring fallback).'''
    for path in paths:
        obj = NXOpen
        try:
            for seg in path.split('.'):
                obj = getattr(obj, seg)
        except AttributeError:
            continue
        for cand in candidates:
            if hasattr(obj, cand):
                return getattr(obj, cand)
        names = [n for n in dir(obj) if not n.startswith('_') and n != 'ValueOf']
        for cand in candidates:
            for n in names:
                if cand.lower() in n.lower():
                    return getattr(obj, n)
    raise NxError('找不到枚举成员 %s（已尝试 %s）' % ('/'.join(candidates), '; '.join(paths)))
