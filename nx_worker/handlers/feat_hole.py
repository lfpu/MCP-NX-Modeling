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
