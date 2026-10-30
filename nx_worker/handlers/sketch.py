# -*- coding: utf-8 -*-
'''Sketch commands (Phase 3).

Sketch geometry is created from absolute 3D points computed here, so every shape is placed exactly.
2D coordinates are [u, v] in the sketch basis:
  plane xy: u=X v=Y normal=+Z | plane yz: u=Y v=Z normal=+X | plane xz: u=X v=Z normal=-Y
  on a planar face: normal = face outward normal, origin = world origin projected onto the face plane.
'''
import math

import NXOpen

from nx_worker import ctx, geom
from nx_worker.registry import command

BASIS = {}  # sketch tag -> {origin, u, v, n}

STD = {
    'xy': ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    'yz': ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    'xz': ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
}


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def basis_from_normal(n, origin):
    n = geom.unit(n)
    ref = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
    d = geom.dot(ref, n)
    u = geom.unit([ref[i] - d * n[i] for i in range(3)])
    v = cross(n, u)
    return {'origin': list(origin), 'u': u, 'v': v, 'n': n}


def resolve_basis(plane, face, offset):
    if face:
        f = ctx.get_obj(face, 'FACE')
        info = geom.face_info(f)
        fd = geom.face_data(f)
        if info.get('type') != 'planar' or not info.get('normal') or not fd:
            raise ctx.NxError('只能在平面上建立草图，%s 不是平面' % face)
        n = info['normal']
        d = geom.dot(fd['point'], n)
        return basis_from_normal(n, [n[i] * d for i in range(3)]), f
    key = str(plane or 'xy').lower()
    if key not in STD:
        raise ctx.NxError('plane 只能是 xy / yz / xz，或改用 face 参数')
    u, v = STD[key]
    n = cross(u, v)
    off = float(offset or 0.0)
    return {'origin': [n[i] * off for i in range(3)], 'u': list(u), 'v': list(v), 'n': n}, None


def _fixed_datum(part, basis):
    b = part.Features.CreateDatumPlaneBuilder(NXOpen.Features.Feature.Null)
    try:
        pl = b.GetPlane()
        pl.SetMethod(NXOpen.PlaneTypes.MethodType.Fixed)
        pl.Origin = ctx.pt(basis['origin'])
        pl.Normal = ctx.vec(basis['n'])
        pl.Evaluate()
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return feat.DatumPlane


def _smart_plane(part, basis):
    return part.Planes.CreatePlane(ctx.pt(basis['origin']), ctx.vec(basis['n']), NXOpen.SmartObject.UpdateOption.WithinModeling)


def _commit_sketch(part, ref):
    b = None
    for name in ('CreateNewSketchInPlaceBuilder', 'CreateSketchInPlaceBuilder2'):
        fn = getattr(part.Sketches, name, None)
        if fn is not None:
            b = fn(NXOpen.Sketch.Null)
            break
    if b is None:
        raise ctx.NxError('当前 NX 版本没有可用的 SketchInPlaceBuilder')
    try:
        b.PlaneReference = ref
        return b.Commit()
    finally:
        b.Destroy()


def new_sketch(part, basis, face_obj):
    # SketchInPlaceBuilder.PlaneReference needs a Plane object, not a Face: for a face we build a fixed
    # datum plane from the face basis (origin/normal), so the sketch is not associative to the face.
    errors = []
    for maker in (_fixed_datum, _smart_plane):
        try:
            return _commit_sketch(part, maker(part, basis))
        except Exception as exc:
            errors.append('%s: %s' % (maker.__name__, exc))
    raise ctx.NxError('创建草图平面失败: ' + ' | '.join(errors))


def _uv(p, what='点'):
    if p is None or len(p) != 2:
        raise ctx.NxError('%s 必须是草图坐标 [u, v]' % what)
    return float(p[0]), float(p[1])


def _p3(basis, uv):
    return NXOpen.Point3d(*[basis['origin'][i] + basis['u'][i] * uv[0] + basis['v'][i] * uv[1] for i in range(3)])


def _arc(part, basis, center_uv, radius, a0, a1):
    if radius <= 0:
        raise ctx.NxError('半径必须大于 0')
    m = NXOpen.Matrix3x3()
    u, v, n = basis['u'], basis['v'], basis['n']
    m.Xx, m.Xy, m.Xz = u[0], u[1], u[2]
    m.Yx, m.Yy, m.Yz = v[0], v[1], v[2]
    m.Zx, m.Zy, m.Zz = n[0], n[1], n[2]
    c = _p3(basis, center_uv)
    try:
        return part.Curves.CreateArc(c, m, radius, a0, a1)
    except Exception:
        return part.Curves.CreateArc(c, part.NXMatrices.Create(m), radius, a0, a1)


def _line(part, basis, a, b):
    if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
        raise ctx.NxError('线段起点和终点重合')
    return part.Curves.CreateLine(_p3(basis, a), _p3(basis, b))


def shape_curves(part, basis, shape):
    t = str(shape.get('type', '')).lower()
    out = []
    if t == 'line':
        out.append(_line(part, basis, _uv(shape.get('start'), 'start'), _uv(shape.get('end'), 'end')))
    elif t == 'rectangle':
        w = float(shape['width'])
        h = float(shape['height'])
        if w <= 0 or h <= 0:
            raise ctx.NxError('rectangle 的 width/height 必须大于 0')
        if shape.get('center') is not None:
            cu, cv = _uv(shape['center'], 'center')
            u0, v0 = cu - w / 2.0, cv - h / 2.0
        else:
            u0, v0 = _uv(shape.get('corner', [0, 0]), 'corner')
        pts = [(u0, v0), (u0 + w, v0), (u0 + w, v0 + h), (u0, v0 + h)]
        for i in range(4):
            out.append(_line(part, basis, pts[i], pts[(i + 1) % 4]))
    elif t == 'polyline':
        pts = [_uv(p) for p in shape.get('points', [])]
        if len(pts) < 2:
            raise ctx.NxError('polyline 至少需要 2 个点')
        n = len(pts)
        last = n if shape.get('closed') else n - 1
        for i in range(last):
            out.append(_line(part, basis, pts[i], pts[(i + 1) % n]))
    elif t == 'circle':
        if shape.get('radius') is not None:
            r = float(shape['radius'])
        else:
            r = float(shape['diameter']) / 2.0
        out.append(_arc(part, basis, _uv(shape.get('center', [0, 0]), 'center'), r, 0.0, 2.0 * math.pi))
    elif t == 'arc':
        a0 = math.radians(float(shape.get('start_angle', 0.0)))
        a1 = math.radians(float(shape['end_angle']))
        if a1 <= a0:
            a1 += 2.0 * math.pi
        out.append(_arc(part, basis, _uv(shape.get('center', [0, 0]), 'center'), float(shape['radius']), a0, a1))
    else:
        raise ctx.NxError('未知图形类型 %r，可用: line / rectangle / polyline / circle / arc' % t)
    return out


def add_shapes(part, sketch, basis, shapes):
    if not shapes:
        raise ctx.NxError('shapes 不能为空')
    count = 0
    sketch.Activate(NXOpen.Sketch.ViewReorient.FalseValue)
    try:
        for sh in shapes:
            for c in shape_curves(part, basis, sh):
                sketch.AddGeometry(c, NXOpen.Sketch.InferConstraintsOption.InferNoConstraints)
                count += 1
    finally:
        try:
            sketch.Deactivate(NXOpen.Sketch.ViewReorient.FalseValue, NXOpen.Sketch.UpdateLevel.Model)
        except Exception:
            pass
    return count


def _key(p):
    return (round(p.X, 3), round(p.Y, 3), round(p.Z, 3))


def profile_loops(curves):
    '''Group curves into connected chains/loops by shared end points.'''
    parent = list(range(len(curves)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, c in enumerate(curves):
        try:
            ends = (c.StartPoint, c.EndPoint)
        except Exception:
            continue
        for p in ends:
            k = _key(p)
            if k in seen:
                parent[find(i)] = find(seen[k])
            else:
                seen[k] = i
    groups = {}
    for i, c in enumerate(curves):
        groups.setdefault(find(i), []).append(c)
    return list(groups.values())


def sketch_curves(sketch):
    curves = [g for g in sketch.GetAllGeometry() if isinstance(g, NXOpen.Curve)]
    if not curves:
        raise ctx.NxError('草图 %s 中没有曲线' % ctx.oid(sketch))
    return curves


def build_section(part, sketch):
    curves = sketch_curves(sketch)
    loops = profile_loops(curves)
    section = part.Sections.CreateSection(0.0095, 0.01, 0.5)
    section.SetAllowedEntityTypes(NXOpen.Section.AllowTypes.OnlyCurves)
    for group in loops:
        rule = part.ScRuleFactory.CreateRuleCurveDumb(group)
        section.AddToSection([rule], group[0], NXOpen.NXObject.Null, NXOpen.NXObject.Null, NXOpen.Point3d(0.0, 0.0, 0.0), NXOpen.Section.Mode.Create, False)
    return section, len(loops)


def sketch_basis(sketch):
    b = BASIS.get(sketch.Tag)
    if b is None:
        raise ctx.NxError('不知道草图 %s 的方向（它不是本服务创建的）；请显式给出 direction 参数' % ctx.oid(sketch))
    return b


def sketch_info(sketch, basis=None):
    info = {'id': ctx.oid(sketch), 'name': sketch.Name}
    try:
        info['curves'] = len(sketch_curves(sketch))
    except Exception:
        info['curves'] = 0
    b = basis or BASIS.get(sketch.Tag)
    if b:
        info['origin'] = ctx.short(b['origin'], 4)
        info['u_axis'] = ctx.short(b['u'], 4)
        info['v_axis'] = ctx.short(b['v'], 4)
        info['normal'] = ctx.short(b['n'], 4)
    return info


@command('create_sketch', 'modify')
def create_sketch(shapes, plane='xy', face=None, offset=0.0, name=None):
    part = ctx.work_part()
    basis, face_obj = resolve_basis(plane, face, offset)
    sk = new_sketch(part, basis, face_obj)
    BASIS[sk.Tag] = basis
    if name:
        try:
            sk.SetName(str(name))
        except Exception:
            pass
    add_shapes(part, sk, basis, shapes)
    return {'sketch': sketch_info(sk, basis)}


@command('add_to_sketch', 'modify')
def add_to_sketch(sketch, shapes):
    part = ctx.work_part()
    sk = ctx.get_obj(sketch, 'SKETCH')
    add_shapes(part, sk, sketch_basis(sk), shapes)
    return {'sketch': sketch_info(sk)}




def _sketch_geometry(sketch, index):
    geometry = list(sketch.GetAllGeometry())
    i = int(index)
    if i < 0 or i >= len(geometry):
        raise ctx.NxError('geometry_index %s 超出范围，草图共有 %s 个几何对象' % (i, len(geometry)))
    return geometry[i]


def _constraint_geometry(geometry, point_type='none'):
    data = NXOpen.Sketch.ConstraintGeometry()
    data.Geometry = geometry
    names = {
        'none': 'NotSet',
        'notset': 'NotSet',
        'start': 'StartVertex',
        'end': 'EndVertex',
        'mid': 'MidVertex',
        'center': 'ArcCenter',
        'arc_center': 'ArcCenter',
    }
    key = str(point_type or 'none').lower()
    if key not in names:
        raise ctx.NxError('point_type 只能是 none/start/end/mid/center')
    data.PointType = getattr(NXOpen.Sketch.ConstraintPointType, names[key])
    data.SplineDefiningPointIndex = 0
    return data


def _dimension_geometry(geometry, assoc_type='none', help_point=None):
    data = NXOpen.Sketch.DimensionGeometry()
    data.Geometry = geometry
    assoc_names = {
        'none': 'NotSet',
        'start': 'StartPoint',
        'end': 'EndPoint',
        'mid': 'MidPoint',
        'center': 'Center',
        'arc_center': 'Center',
    }
    key = str(assoc_type or 'none').lower()
    if key not in assoc_names:
        raise ctx.NxError('assoc_type 只能是 none/start/end/mid/center')
    data.AssocType = getattr(NXOpen.Sketch.AssocType, assoc_names[key])
    data.AssocValue = 0
    hp = help_point or [0.0, 0.0, 0.0]
    data.HelpPoint = NXOpen.Point3d(float(hp[0]), float(hp[1]), float(hp[2]))
    data.View = NXOpen.NXObject.Null
    return data


def _dimension_option(reference):
    return NXOpen.Sketch.DimensionOption.CreateAsReference if reference else NXOpen.Sketch.DimensionOption.CreateAsDriving


@command('sketch_add_constraint', 'modify')
def sketch_add_constraint(sketch, constraint_type, geometry_index, geometry_index2=None,
                          point_type='none', point_type2='none', help_point=None, help_point2=None):
    sk = ctx.get_obj(sketch, 'SKETCH')
    kind = str(constraint_type or '').lower()
    sk.Activate(NXOpen.Sketch.ViewReorient.FalseValue)
    g1 = _sketch_geometry(sk, geometry_index)
    c1 = _constraint_geometry(g1, point_type)
    one = {
        'horizontal': 'CreateHorizontalConstraint',
        'vertical': 'CreateVerticalConstraint',
        'fixed': 'CreateFixedConstraint',
    }
    two = {
        'coincident': 'CreateCoincidentConstraint',
        'parallel': 'CreateParallelConstraint',
        'perpendicular': 'CreatePerpendicularConstraint',
        'concentric': 'CreateConcentricConstraint',
    }
    if kind in one:
        constraint = getattr(sk, one[kind])(c1)
    elif kind in two:
        if geometry_index2 is None:
            raise ctx.NxError('%s 约束需要 geometry_index2' % kind)
        c2 = _constraint_geometry(_sketch_geometry(sk, geometry_index2), point_type2)
        constraint = getattr(sk, two[kind])(c1, c2)
    elif kind == 'tangent':
        if geometry_index2 is None:
            raise ctx.NxError('tangent 约束需要 geometry_index2')
        c2 = _constraint_geometry(_sketch_geometry(sk, geometry_index2), point_type2)
        hp1 = help_point or [0.0, 0.0, 0.0]
        hp2 = help_point2 or [0.0, 0.0, 0.0]
        constraint = sk.CreateTangentConstraint(
            c1, NXOpen.Point3d(float(hp1[0]), float(hp1[1]), float(hp1[2])),
            c2, NXOpen.Point3d(float(hp2[0]), float(hp2[1]), float(hp2[2])))
    else:
        raise ctx.NxError('constraint_type 只能是 horizontal/vertical/fixed/coincident/tangent/parallel/perpendicular/concentric')
    sk.LocalUpdate()
    sk.Deactivate(NXOpen.Sketch.ViewReorient.FalseValue, NXOpen.Sketch.UpdateLevel.Model)
    return {
        'sketch': sketch_info(sk),
        'constraint_type': kind,
        'constraint': ctx.oid(constraint) if constraint is not None else None,
    }


@command('sketch_add_dimension', 'modify')
def sketch_add_dimension(sketch, dimension_type, geometry_index, value,
                         geometry_index2=None, assoc_type='none', assoc_type2='none',
                         origin=None, help_point=None, help_point2=None, reference=False):
    sk = ctx.get_obj(sketch, 'SKETCH')
    kind = str(dimension_type or '').lower()
    sk.Activate(NXOpen.Sketch.ViewReorient.FalseValue)
    g1 = _sketch_geometry(sk, geometry_index)
    d1 = _dimension_geometry(g1, assoc_type, help_point)
    pos = origin or [0.0, 0.0, 0.0]
    dim_origin = NXOpen.Point3d(float(pos[0]), float(pos[1]), float(pos[2]))
    option = _dimension_option(bool(reference))
    part = ctx.work_part()
    numeric_value = float(value)
    if kind == 'angular':
        unit = part.UnitCollection.FindObject('Radian')
        expression = part.Expressions.CreateSystemExpressionWithUnits(ctx.num(math.radians(numeric_value)), unit)
    else:
        unit = part.UnitCollection.FindObject('MilliMeter')
        expression = part.Expressions.CreateSystemExpressionWithUnits(ctx.num(numeric_value), unit)
    if kind == 'radius':
        dimension = sk.CreateRadialDimension(d1, dim_origin, expression, option)
    elif kind == 'diameter':
        dimension = sk.CreateDiameterDimension(d1, dim_origin, expression, option)
    else:
        dim_types = {
            'horizontal': 'HorizontalDim',
            'vertical': 'VerticalDim',
            'parallel': 'ParallelDim',
            'perpendicular': 'PerpendicularDim',
            'angular': 'AngularDim',
        }
        if kind not in dim_types:
            raise ctx.NxError('dimension_type 只能是 horizontal/vertical/parallel/perpendicular/angular/radius/diameter')
        if geometry_index2 is None:
            d2 = NXOpen.Sketch.DimensionGeometry()
        else:
            d2 = _dimension_geometry(_sketch_geometry(sk, geometry_index2), assoc_type2, help_point2)
        dimension = sk.CreateDimension(getattr(NXOpen.Sketch.ConstraintType, dim_types[kind]), d1, d2, dim_origin, expression, option)
    sk.LocalUpdate()
    sk.Deactivate(NXOpen.Sketch.ViewReorient.FalseValue, NXOpen.Sketch.UpdateLevel.Model)
    return {
        'sketch': sketch_info(sk),
        'dimension_type': kind,
        'dimension': ctx.oid(dimension) if dimension is not None else None,
        'expression': ctx.oid(expression) if expression is not None else None,
        'value': float(value),
        'reference': bool(reference),
    }
@command('get_sketches', 'read')
def get_sketches():
    part = ctx.work_part()
    return {'sketches': [sketch_info(s) for s in part.Sketches]}
