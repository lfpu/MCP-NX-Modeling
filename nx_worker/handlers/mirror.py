# -*- coding: utf-8 -*-
'''Mirror a body about a plane (MirrorBodyBuilder). Unverified in NX 2412 until run.'''
import NXOpen
import NXOpen.Features

from nx_worker import ctx, geom
from nx_worker.handlers.feat_sweep import result
from nx_worker.registry import command

STD_NORMAL = {'xy': (0.0, 0.0, 1.0), 'yz': (1.0, 0.0, 0.0), 'xz': (0.0, 1.0, 0.0)}


def make_plane(part, plane, offset, origin, normal):
    if origin is not None or normal is not None:
        if origin is None or normal is None:
            raise ctx.NxError('origin 和 normal 必须同时给出')
        o = [float(x) for x in origin]
        n = geom.parse_dir(normal)
    else:
        key = str(plane or 'xy').lower()
        if key not in STD_NORMAL:
            raise ctx.NxError('plane 只能是 xy / yz / xz，或改用 origin + normal')
        n = list(STD_NORMAL[key])
        o = [n[i] * float(offset or 0.0) for i in range(3)]
    from nx_worker.handlers import sketch as sk_mod
    return sk_mod._fixed_datum(part, {'origin': o, 'n': n})


@command('mirror_body', 'modify')
def mirror_body(body=None, plane='xy', offset=0.0, origin=None, normal=None):
    part = ctx.work_part()
    src = ctx.get_obj(body, 'BODY') if body else ctx.default_target_body(part)
    pl = make_plane(part, plane, offset, origin, normal)
    b = part.Features.CreateMirrorBodyBuilder(NXOpen.Features.Feature.Null)
    try:
        try:
            b.Plane = pl
        except AttributeError:
            # Plane is read-only in NX 2412: configure the builder's own plane object instead
            try:
                b.Plane.Value = pl
            except Exception as exc:
                raise ctx.NxError('设置镜像平面失败(平面类型 %s): %s' % (type(pl).__name__, str(exc)[:120]))
        notes = []
        done = False
        try:
            col = part.ScCollectors.CreateCollector()
            col.ReplaceRules([part.ScRuleFactory.CreateRuleBodyDumb([src], True)], False)
            b.MirrorBodyCollector = col
            done = True
        except Exception as exc:
            notes.append('collector: %s' % str(exc)[:100])
        if not done:
            try:
                b.MirrorBodyList.Add([src])
                done = True
            except Exception as exc:
                notes.append('list: %s' % str(exc)[:100])
        if not done:
            raise ctx.NxError('无法设置要镜像的实体: ' + ' | '.join(notes))
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return result(feat)
