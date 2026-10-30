# -*- coding: utf-8 -*-
'''Primitive solids: block / cylinder / cone / sphere (Phase 1).'''
import NXOpen
import NXOpen.Features

from nx_worker import ctx
from nx_worker.registry import command


def _pos(name, v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ctx.NxError('%s 必须是数字' % name)
    if f <= 0:
        raise ctx.NxError('%s 必须大于 0（收到 %s）' % (name, v))
    return f


def _result(part, feat):
    out = {'feature': ctx.feature_info(feat)}
    bodies = []
    try:
        bodies = [ctx.body_info(b) for b in feat.GetBodies()]
    except Exception:
        pass
    out['bodies'] = bodies
    return out


def _set_axis(builder, part, origin, direction):
    axis = ctx.make_axis(part, origin, direction)
    try:
        builder.Axis = axis
    except Exception:
        builder.Axis.Point = ctx.pt(origin)
        builder.Axis.Direction = ctx.vec(direction)


@command('create_block', 'modify')
def create_block(length, width, height, origin=None, boolean='create', target_body=None):
    part = ctx.work_part()
    l = _pos('length', length)
    w = _pos('width', width)
    h = _pos('height', height)
    builder = part.Features.CreateBlockFeatureBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Type = NXOpen.Features.BlockFeatureBuilder.Types.OriginAndEdgeLengths
        builder.SetOriginAndLengths(ctx.pt(origin), ctx.num(l), ctx.num(w), ctx.num(h))
        ctx.apply_boolean(builder, boolean, target_body, part)
        feat = builder.CommitFeature()
    finally:
        builder.Destroy()
    return _result(part, feat)


@command('create_cylinder', 'modify')
def create_cylinder(diameter, height, origin=None, direction=None, boolean='create', target_body=None):
    part = ctx.work_part()
    d = _pos('diameter', diameter)
    h = _pos('height', height)
    builder = part.Features.CreateCylinderBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Type = NXOpen.Features.CylinderBuilder.Types.AxisDiameterAndHeight
        builder.Diameter.RightHandSide = ctx.num(d)
        builder.Height.RightHandSide = ctx.num(h)
        _set_axis(builder, part, origin, direction)
        ctx.apply_boolean(builder, boolean, target_body, part)
        feat = builder.CommitFeature()
    finally:
        builder.Destroy()
    return _result(part, feat)


@command('create_cone', 'modify')
def create_cone(base_diameter, top_diameter, height, origin=None, direction=None, boolean='create', target_body=None):
    part = ctx.work_part()
    bd = _pos('base_diameter', base_diameter)
    td = float(top_diameter)
    if td < 0:
        raise ctx.NxError('top_diameter 不能为负数')
    h = _pos('height', height)
    builder = part.Features.CreateConeBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Type = NXOpen.Features.ConeBuilder.Types.DiametersAndHeight
        builder.BaseDiameter.RightHandSide = ctx.num(bd)
        builder.TopDiameter.RightHandSide = ctx.num(td)
        builder.Height.RightHandSide = ctx.num(h)
        _set_axis(builder, part, origin, direction)
        ctx.apply_boolean(builder, boolean, target_body, part)
        feat = builder.CommitFeature()
    finally:
        builder.Destroy()
    return _result(part, feat)


@command('create_sphere', 'modify')
def create_sphere(diameter, center=None, boolean='create', target_body=None):
    part = ctx.work_part()
    d = _pos('diameter', diameter)
    builder = part.Features.CreateSphereBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Type = NXOpen.Features.SphereBuilder.Types.CenterPointAndDiameter
        builder.CenterPoint = part.Points.CreatePoint(ctx.pt(center))
        builder.Diameter.RightHandSide = ctx.num(d)
        ctx.apply_boolean(builder, boolean, target_body, part)
        feat = builder.CommitFeature()
    finally:
        builder.Destroy()
    return _result(part, feat)
