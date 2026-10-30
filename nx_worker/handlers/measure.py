# -*- coding: utf-8 -*-
'''Measurement / analysis: mass properties and distance (read-only).'''
import NXOpen

from nx_worker import ctx, geom
from nx_worker.registry import command


def _units(part):
    uc = part.UnitCollection
    u = [NXOpen.Unit.Null] * 5
    u[0] = uc.FindObject('SquareMilliMeter')
    u[1] = uc.FindObject('CubicMilliMeter')
    u[2] = uc.FindObject('Kilogram')
    u[3] = uc.FindObject('Newton')
    u[4] = uc.FindObject('MilliMeter')
    return u


@command('mass_properties', 'read')
def mass_properties(body=None):
    '''Volume (mm^3), surface area (mm^2) and centroid of a solid body (assumes a millimeter part).'''
    part = ctx.work_part()
    b = ctx.get_obj(body, 'BODY') if body else ctx.default_target_body(part)
    mp = part.MeasureManager.NewMassProperties(_units(part), 0.99, [b])
    try:
        out = {'body': ctx.oid(b), 'volume_mm3': round(float(mp.Volume), 4), 'area_mm2': round(float(mp.Area), 4)}
        try:
            out['centroid'] = ctx.p3(mp.Centroid)
        except Exception:
            pass
    finally:
        mp.Dispose()
    return out


def _as_point(v):
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return [float(x) for x in v]
    return None


@command('measure_distance', 'read')
def measure_distance(a, b):
    '''a, b: both [x,y,z] points, or both object ids (FACE/EDGE/BODY).'''
    pa, pb = _as_point(a), _as_point(b)
    if pa and pb:
        return {'distance': round(geom.dist(pa, pb), 6), 'method': 'points'}
    if pa or pb:
        raise ctx.NxError('a 和 b 必须同为坐标点，或同为对象 id')
    oa, ob = ctx.get_obj(a), ctx.get_obj(b)
    part = ctx.work_part()
    note = None
    try:
        mm = part.UnitCollection.FindObject('MilliMeter')
        d = part.MeasureManager.NewDistance(mm, oa, ob)
        try:
            val = float(d.Value)
        finally:
            d.Dispose()
        return {'distance': round(val, 6), 'method': 'nx_measure'}
    except Exception as exc:
        note = '%s: %s' % (type(exc).__name__, str(exc)[:120])
    ba, bb = ctx.bbox(oa), ctx.bbox(ob)
    if not ba or not bb:
        raise ctx.NxError('NX 测量失败且无法估算: ' + note)
    return {'distance': round(geom.dist(geom.mid(ba), geom.mid(bb)), 6), 'method': 'center_to_center_approx', 'warning': 'NX 精确测量不可用，这是包围盒中心距离: ' + note}
