# -*- coding: utf-8 -*-
'''Holes (built as boolean-subtracted cylinders/cones) and body booleans (Phase 3/4).'''
import math

import NXOpen
import NXOpen.Features

from nx_worker import ctx, geom
from nx_worker.handlers import primitives
from nx_worker.handlers.feat_sweep import body_diag, result
from nx_worker.registry import command


@command('create_hole', 'modify')
def create_hole(face, positions, diameter, depth=None, through=False, cbore_diameter=None,
                cbore_depth=None, csink_diameter=None, csink_angle=90.0):
    '''Holes on a planar face. positions: absolute [x,y,z] points projected onto the face plane.
    Drilled opposite to the face outward normal.'''
    f = ctx.get_obj(face, 'FACE')
    info = geom.face_info(f)
    fd = geom.face_data(f)
    if info.get('type') != 'planar' or not info.get('normal') or not fd:
        raise ctx.NxError('孔只能打在平面上，%s 不是平面' % face)
    d = float(diameter)
    if d <= 0:
        raise ctx.NxError('diameter 必须大于 0')
    if not through and (depth is None or float(depth) <= 0):
        raise ctx.NxError('请给出 depth（>0），或设置 through=true')
    if cbore_diameter is not None and csink_diameter is not None:
        raise ctx.NxError('沉头孔和锥形沉孔不能同时指定')
    if cbore_diameter is not None:
        if float(cbore_diameter) <= d or cbore_depth is None or float(cbore_depth) <= 0:
            raise ctx.NxError('cbore_diameter 必须大于 diameter，且需要 cbore_depth > 0')
    if csink_diameter is not None and float(csink_diameter) <= d:
        raise ctx.NxError('csink_diameter 必须大于 diameter')
    if not positions:
        raise ctx.NxError('positions 不能为空')
    n = info['normal']
    body = f.GetBody()
    body_id = ctx.oid(body)
    c = fd['point']
    margin = 1.0
    if through:
        length = body_diag(body) + 2.0 * margin
    else:
        length = float(depth) + margin
    down = [-x for x in n]
    made = []
    for p in positions:
        if len(p) != 3:
            raise ctx.NxError('每个 position 必须是 [x, y, z]')
        dd = geom.dot([p[i] - c[i] for i in range(3)], n)
        base = [p[i] - n[i] * dd for i in range(3)]
        top = [base[i] + n[i] * margin for i in range(3)]
        r = primitives.create_cylinder(d, length, origin=top, direction=down, boolean='subtract', target_body=body_id)
        made.append(r['feature']['id'])
        if cbore_diameter is not None:
            r = primitives.create_cylinder(float(cbore_diameter), float(cbore_depth) + margin, origin=top, direction=down, boolean='subtract', target_body=body_id)
            made.append(r['feature']['id'])
        if csink_diameter is not None:
            half = math.radians(float(csink_angle)) / 2.0
            h = (float(csink_diameter) - d) / 2.0 / math.tan(half)
            r = primitives.create_cone(float(csink_diameter), d, h, origin=base, direction=down, boolean='subtract', target_body=body_id)
            made.append(r['feature']['id'])
    return {'holes': len(positions), 'features': made, 'body': ctx.body_info(body)}




def _hole_enum(enum_type, name):
    try:
        return getattr(enum_type, name)
    except Exception:
        return ctx.enum_member([
            'Features.HolePackageBuilder.' + enum_type.__name__,
            'Features.HolePackageBuilder' + enum_type.__name__,
        ], [name])


def _project_to_face(position, face_info, face_data):
    if position is None or len(position) != 3:
        raise ctx.NxError('position 必须是 [x, y, z]')
    p = [float(x) for x in position]
    n = face_info['normal']
    origin = face_data['point']
    distance = geom.dot([p[i] - origin[i] for i in range(3)], n)
    return [p[i] - n[i] * distance for i in range(3)]


@command('hole_native', 'modify')
def hole_native(face, positions, diameter, depth=None, through=False, hole_form='simple',
                cbore_diameter=None, cbore_depth=None, csink_diameter=None,
                csink_angle=90.0, fallback=True):
    '''Create an associative NX HolePackage feature; optionally fall back to boolean holes.'''
    part = ctx.work_part()
    f = ctx.get_obj(face, 'FACE')
    info = geom.face_info(f)
    fd = geom.face_data(f)
    if info.get('type') != 'planar' or not info.get('normal') or not fd:
        raise ctx.NxError('原生孔只能定位到平面，%s 不是平面' % face)
    if not positions:
        raise ctx.NxError('positions 不能为空')
    dia = float(diameter)
    if dia <= 0:
        raise ctx.NxError('diameter 必须大于 0')
    form = str(hole_form or 'simple').lower()
    aliases = {
        'simple': 'Simple',
        'counterbore': 'Counterbored',
        'counterbored': 'Counterbored',
        'cbore': 'Counterbored',
        'countersink': 'Countersink',
        'csink': 'Countersink',
        'tapered': 'Tapered',
    }
    if form not in aliases:
        raise ctx.NxError('hole_form 只能是 simple / counterbore / countersink / tapered')
    if not through and (depth is None or float(depth) <= 0):
        raise ctx.NxError('盲孔需要 depth > 0，或设置 through=true')
    if form == 'counterbore':
        form = 'counterbored'
    if form in ('counterbored', 'cbore'):
        if cbore_diameter is None or cbore_depth is None:
            raise ctx.NxError('沉孔需要 cbore_diameter 和 cbore_depth')
        if float(cbore_diameter) <= dia or float(cbore_depth) <= 0:
            raise ctx.NxError('cbore_diameter 必须大于 diameter，cbore_depth 必须大于 0')
    if form in ('countersink', 'csink'):
        if csink_diameter is None or float(csink_diameter) <= dia:
            raise ctx.NxError('锥形沉孔需要 csink_diameter > diameter')
    b = part.Features.CreateHolePackageBuilder(NXOpen.Features.HolePackage.Null)
    created_points = []
    native_error = None
    try:
        b.Type = NXOpen.Features.HolePackageBuilder.Types.GeneralHole
        b.Tolerance = 0.01
        b.BooleanOperation.SetTargetBodies([f.GetBody()])
        b.GeneralHoleForm = getattr(NXOpen.Features.HolePackageBuilder.HoleForms, aliases[form])
        if form == 'simple':
            b.GeneralSimpleHoleDiameter.RightHandSide = ctx.num(dia)
            if not through:
                b.GeneralSimpleHoleDepth.RightHandSide = ctx.num(float(depth))
        elif form in ('counterbored', 'cbore'):
            b.GeneralCounterboreHoleDiameter.RightHandSide = ctx.num(dia)
            b.GeneralCounterboreDiameter.RightHandSide = ctx.num(float(cbore_diameter))
            b.GeneralCounterboreDepth.RightHandSide = ctx.num(float(cbore_depth))
            if not through:
                b.GeneralCounterboreHoleDepth.RightHandSide = ctx.num(float(depth))
        elif form in ('countersink', 'csink'):
            b.GeneralCountersinkHoleDiameter.RightHandSide = ctx.num(dia)
            b.GeneralCountersinkDiameter.RightHandSide = ctx.num(float(csink_diameter))
            b.GeneralCountersinkAngle.RightHandSide = ctx.num(float(csink_angle))
            if not through:
                b.GeneralCountersinkHoleDepth.RightHandSide = ctx.num(float(depth))
        elif form == 'tapered':
            b.GeneralTaperedHoleDiameter.RightHandSide = ctx.num(dia)
            if not through:
                b.GeneralTaperedHoleDepth.RightHandSide = ctx.num(float(depth))
        if through:
            b.HoleDepthLimitOption = NXOpen.Features.HolePackageBuilder.HoleDepthLimitOptions.ThroughBody
        else:
            b.HoleDepthLimitOption = NXOpen.Features.HolePackageBuilder.HoleDepthLimitOptions.Value
        try:
            down = [-float(x) for x in info['normal']]
            b.ProjectionDirection.ProjectVector = part.Directions.CreateDirection(
                NXOpen.Point3d(float(fd['point'][0]), float(fd['point'][1]), float(fd['point'][2])),
                NXOpen.Vector3d(float(down[0]), float(down[1]), float(down[2])),
                NXOpen.SmartObject.UpdateOption.WithinModeling)
        except Exception:
            pass
        for position in positions:
            projected = _project_to_face(position, info, fd)
            point = part.Points.CreatePoint(NXOpen.Point3d(float(projected[0]), float(projected[1]), float(projected[2])))
            created_points.append(point)
            b.HolePosition.AddSmartPoint(point, 0.01)
        feat = b.CommitFeature()
        out = result(feat)
        out['native'] = True
        out['hole_form'] = aliases[form]
        out['positions'] = len(positions)
        return out
    except Exception as exc:
        native_error = '%s: %s' % (type(exc).__name__, str(exc))
    finally:
        try:
            b.Destroy()
        except Exception:
            pass
    if not fallback:
        raise ctx.NxError('创建原生 NX Hole 特征失败: ' + native_error)
    fallback_result = create_hole(
        face=face,
        positions=positions,
        diameter=diameter,
        depth=depth,
        through=through,
        cbore_diameter=cbore_diameter if form in ('counterbored', 'cbore') else None,
        cbore_depth=cbore_depth if form in ('counterbored', 'cbore') else None,
        csink_diameter=csink_diameter if form in ('countersink', 'csink') else None,
        csink_angle=csink_angle,
    )
    fallback_result['native'] = False
    fallback_result['native_error'] = native_error
    fallback_result['fallback'] = 'boolean_subtract'
    return fallback_result
@command('boolean', 'modify')
def boolean(operation, target, tools):
    '''operation: unite / subtract / intersect. target: body id. tools: list of body ids.'''
    part = ctx.work_part()
    op = str(operation).lower()
    if op not in ('unite', 'subtract', 'intersect'):
        raise ctx.NxError('operation 只能是 unite / subtract / intersect')
    tgt = ctx.get_obj(target, 'BODY')
    tool_bodies = ctx.get_many(tools, 'BODY')
    if any(t.Tag == tgt.Tag for t in tool_bodies):
        raise ctx.NxError('target 不能同时是 tool')
    op_enum = getattr(NXOpen.Features.Feature.BooleanType, op.capitalize())
    maker = getattr(part.Features, 'CreateBooleanBuilderUsingCollector', None)
    if maker is not None:
        b = maker(NXOpen.Features.BooleanFeature.Null)
        try:
            b.Target = tgt
            col = part.ScCollectors.CreateCollector()
            col.ReplaceRules([part.ScRuleFactory.CreateRuleBodyDumb(tool_bodies, True)], False)
            b.ToolBodyCollector = col
            b.Operation = op_enum
            feat = b.CommitFeature()
        finally:
            b.Destroy()
    else:
        b = part.Features.CreateBooleanBuilder(NXOpen.Features.BooleanFeature.Null)
        try:
            b.Target = tgt
            for t in tool_bodies:
                b.Tools.Add(t)
            b.Operation = op_enum
            feat = b.CommitFeature()
        finally:
            b.Destroy()
    return result(feat)
