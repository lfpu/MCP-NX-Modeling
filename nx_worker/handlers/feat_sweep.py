# -*- coding: utf-8 -*-
'''Sweep features: extrude / pocket / revolve (Phase 3).'''
import NXOpen
import NXOpen.Features

from nx_worker import ctx, geom
from nx_worker.handlers import sketch as sk_mod
from nx_worker.registry import command


def result(feat):
    out = {'feature': ctx.feature_info(feat)}
    try:
        out['bodies'] = [ctx.body_info(b) for b in feat.GetBodies()]
    except Exception:
        out['bodies'] = []
    return out


def body_diag(body):
    bb = ctx.bbox(body)
    if not bb:
        return 1000.0
    return geom.dist(bb[0], bb[1])


def pick_target(part, target_body):
    if target_body:
        return ctx.get_obj(target_body, 'BODY')
    return ctx.default_target_body(part)


def _extrude(part, sketch_id, start, end, direction, boolean, target_body, draft_angle):
    sk = ctx.get_obj(sketch_id, 'SKETCH')
    basis = sk_mod.BASIS.get(sk.Tag)
    if direction is None:
        d = sk_mod.sketch_basis(sk)['n']
    else:
        d = direction
    origin = basis['origin'] if basis else [0.0, 0.0, 0.0]
    section, _loops = sk_mod.build_section(part, sk)
    b = part.Features.CreateExtrudeBuilder(NXOpen.Features.Feature.Null)
    try:
        b.Section = section
        b.Direction = part.Directions.CreateDirection(ctx.pt(origin), ctx.vec(d), NXOpen.SmartObject.UpdateOption.WithinModeling)
        b.Limits.StartExtend.Value.RightHandSide = ctx.num(start)
        b.Limits.EndExtend.Value.RightHandSide = ctx.num(end)
        if draft_angle:
            b.Draft.DraftOption = NXOpen.GeometricUtilities.SimpleDraft.SimpleDraftType.SimpleFromProfile
            b.Draft.FrontDraftAngle.RightHandSide = ctx.num(draft_angle)
        ctx.apply_boolean(b, boolean, target_body, part)
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return feat


@command('extrude', 'modify')
def extrude(sketch, distance, start=0.0, symmetric=False, reverse=False, direction=None,
            boolean='create', target_body=None, draft_angle=None):
    part = ctx.work_part()
    dist = float(distance)
    if dist <= 0:
        raise ctx.NxError('distance 必须大于 0')
    if symmetric:
        s, e = -dist, dist
    else:
        s, e = float(start), dist
        if e <= s:
            raise ctx.NxError('distance 必须大于 start')
    d = geom.parse_dir(direction) if direction is not None else None
    if reverse:
        if d is None:
            d = sk_mod.sketch_basis(ctx.get_obj(sketch, 'SKETCH'))['n']
        d = [-x for x in d]
    return result(_extrude(part, sketch, s, e, d, boolean, target_body, draft_angle))


@command('pocket', 'modify')
def pocket(sketch, depth=None, through=False, target_body=None, draft_angle=None):
    '''Cut material: extrude opposite to the sketch normal.'''
    part = ctx.work_part()
    body = pick_target(part, target_body)
    if through:
        dist = body_diag(body) + 1.0
    else:
        if depth is None or float(depth) <= 0:
            raise ctx.NxError('请给出 depth（>0），或设置 through=true')
        dist = float(depth)
    sk = ctx.get_obj(sketch, 'SKETCH')
    d = [-x for x in sk_mod.sketch_basis(sk)['n']]
    return result(_extrude(part, sketch, 0.0, dist, d, 'subtract', ctx.oid(body), draft_angle))


@command('revolve', 'modify')
def revolve(sketch, axis_origin, axis_direction, angle=360.0, start_angle=0.0, boolean='create', target_body=None):
    '''Revolve a sketch profile about an axis given in absolute coordinates.'''
    part = ctx.work_part()
    a = float(angle)
    if a <= 0 or a > 360:
        raise ctx.NxError('angle 必须在 (0, 360]')
    sk = ctx.get_obj(sketch, 'SKETCH')
    section, _l = sk_mod.build_section(part, sk)
    b = part.Features.CreateRevolveBuilder(NXOpen.Features.Feature.Null)
    try:
        b.Section = section
        b.Axis = ctx.make_axis(part, axis_origin, geom.parse_dir(axis_direction))
        b.Limits.StartExtend.Value.RightHandSide = ctx.num(start_angle)
        b.Limits.EndExtend.Value.RightHandSide = ctx.num(float(start_angle) + a)
        ctx.apply_boolean(b, boolean, target_body, part)
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return result(feat)
