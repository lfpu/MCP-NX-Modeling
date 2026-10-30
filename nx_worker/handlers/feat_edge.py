# -*- coding: utf-8 -*-
'''Edge blend / chamfer (Phase 4).'''
import NXOpen
import NXOpen.Features

from nx_worker import ctx
from nx_worker.handlers.feat_sweep import result
from nx_worker.registry import command


def _edge_collector(part, edge_ids):
    edges = ctx.get_many(edge_ids, 'EDGE')
    col = part.ScCollectors.CreateCollector()
    col.ReplaceRules([part.ScRuleFactory.CreateRuleEdgeDumb(edges)], False)
    return col


@command('edge_blend', 'modify')
def edge_blend(edges, radius):
    part = ctx.work_part()
    r = float(radius)
    if r <= 0:
        raise ctx.NxError('radius 必须大于 0')
    col = _edge_collector(part, edges)
    b = part.Features.CreateEdgeBlendBuilder(NXOpen.Features.Feature.Null)
    try:
        b.Tolerance = 0.01
        b.AddChainset(col, ctx.num(r))
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return result(feat)


@command('chamfer', 'modify')
def chamfer(edges, distance, distance2=None, angle=None):
    '''distance only: symmetric. distance+distance2: asymmetric. distance+angle(deg): offset and angle.'''
    part = ctx.work_part()
    d1 = float(distance)
    if d1 <= 0:
        raise ctx.NxError('distance 必须大于 0')
    col = _edge_collector(part, edges)
    b = part.Features.CreateChamferBuilder(NXOpen.Features.Feature.Null)
    try:
        opts = NXOpen.Features.ChamferBuilder.ChamferOption
        if angle is not None:
            b.Option = opts.OffsetAndAngle
            b.Angle = ctx.num(angle)
        elif distance2 is not None:
            b.Option = opts.AsymmetricOffsets
            b.SecondOffset = ctx.num(distance2)
        else:
            b.Option = opts.SymmetricOffsets
        try:
            b.Method = NXOpen.Features.ChamferBuilder.OffsetMethod.EdgesAlongFaces
        except Exception:
            pass
        b.FirstOffset = ctx.num(d1)
        b.Tolerance = 0.01
        b.SmartCollector = col
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return result(feat)
