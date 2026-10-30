# -*- coding: utf-8 -*-
'''Advanced features: shell, datum axis, suppress/unsuppress, rename. NXOpen calls are unverified in NX 2412 until run.'''
import NXOpen
import NXOpen.Features

from nx_worker import ctx
from nx_worker.handlers.feat_sweep import result
from nx_worker.registry import command


def do_update():
    s = ctx.session()
    mark = s.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, 'update')
    s.UpdateManager.DoUpdate(mark)
    try:
        s.DeleteUndoMark(mark, None)
    except Exception:
        pass


@command('shell', 'modify')
def shell(faces, thickness):
    '''Hollow out a solid: faces are removed (opened), the remaining walls get the given thickness.'''
    part = ctx.work_part()
    t = float(thickness)
    if t <= 0:
        raise ctx.NxError('thickness 必须大于 0')
    fs = ctx.get_many(faces, 'FACE')
    col = part.ScCollectors.CreateCollector()
    col.ReplaceRules([part.ScRuleFactory.CreateRuleFaceDumb(fs)], False)
    b = part.Features.CreateShellBuilder(NXOpen.Features.Feature.Null)
    try:
        try:
            b.Type = ctx.enum_member(['Features.ShellBuilder.Types', 'Features.ShellBuilder.Type', 'Features.ShellBuilderTypes', 'Features.ShellBuilderType'], ['RemoveFacesThenShell', 'RemoveFaces'])
        except Exception:
            pass  # keep the builder default
        try:
            b.RemovedFacesCollector.ReplaceRules([part.ScRuleFactory.CreateRuleFaceDumb(fs)], False)
        except Exception:
            b.RemovedFacesCollector = col
        b.Body = fs[0].GetBody()
        b.Tolerance = 0.01
        b.DefaultThickness.RightHandSide = ctx.num(t)
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return result(feat)


@command('create_datum_axis', 'modify')
def create_datum_axis(origin, direction):
    part = ctx.work_part()
    o = ctx.pt(origin)
    v = ctx.vec(direction)
    # CreateFixedDatumAxis takes two points: the axis runs from origin to origin + direction
    ax = part.Datums.CreateFixedDatumAxis(o, NXOpen.Point3d(o.X + v.X, o.Y + v.Y, o.Z + v.Z))
    return {'datum_axis': ctx.oid(ax), 'origin': ctx.short(origin, 4), 'direction': ctx.short(direction, 4)}


@command('suppress_feature', 'modify')
def suppress_feature(feature, suppress=True):
    part = ctx.work_part()
    feat = ctx.get_obj(feature, 'FEATURE')
    fn = getattr(feat, 'Suppress' if suppress else 'Unsuppress', None)
    if fn is not None:
        fn()
    else:
        sf = getattr(part.Features, 'SuppressFeatures' if suppress else 'UnsuppressFeatures', None)
        if sf is None:
            raise ctx.NxError('此 NX 版本没有找到抑制/解抑制接口')
        sf([feat])
    do_update()
    return {'feature': ctx.feature_info(feat), 'suppressed_requested': bool(suppress)}


@command('rename_object', 'modify')
def rename_object(object_id, name):
    obj = ctx.get_obj(object_id)
    if not str(name).strip():
        raise ctx.NxError('name 不能为空')
    obj.SetName(str(name))
    return {'id': ctx.oid(obj), 'name': str(name)}
