# -*- coding: utf-8 -*-
'''Assembly constraints via ComponentPositioner. Attribute names come from NX 2412 probes;
the call order follows NX journals. Unverified until run.

component1 stays in place (fix hint), component2 is the one that moves.
'''
import NXOpen

try:
    import NXOpen.Positioning
except ImportError:
    pass

from nx_worker import ctx, geom
from nx_worker.handlers.assembly import _comp_info
from nx_worker.registry import command

KINDS = {'fix': 'Fix', 'touch': 'Touch', 'concentric': 'Concentric', 'distance': 'Distance',
         'parallel': 'Parallel', 'perpendicular': 'Perpendicular', 'angle': 'Angle'}
ALIGN = {'infer': 'InferAlign', 'coalign': 'CoAlign', 'contra': 'ContraAlign'}


def _pos_enum(cls_name, member):
    cls = getattr(NXOpen.Positioning, cls_name, None)
    if cls is None:
        raise ctx.NxError('找不到 NXOpen.Positioning.%s' % cls_name)
    return getattr(cls, member)


def _occurrence(comp, proto_face):
    fn = getattr(comp, 'FindOccurrence', None)
    if fn is None:
        raise ctx.NxError('Component 没有 FindOccurrence 接口')
    occ = fn(proto_face)
    if occ is None:
        raise ctx.NxError('找不到面在组件中的实例')
    return occ


@command('component_faces', 'read')
def component_faces(component, type=None, normal=None, extreme=None, limit=20):
    '''Faces of a component (as occurrences in the assembly), usable as face1/face2 of add_constraint.'''
    comp = ctx.get_obj(component, 'COMP')
    proto = comp.Prototype
    if not hasattr(proto, 'Bodies'):
        raise ctx.NxError('无法读取组件的 Part（Prototype 没有 Bodies），组件可能未加载')
    n_dir = geom.parse_dir(normal)
    ext = geom.parse_dir(extreme)
    rows = []
    for body in proto.Bodies:
        if not body.IsSolidBody:
            continue
        for f in body.GetFaces():
            info = geom.face_info(_occurrence(comp, f))
            info.pop('bbox', None)
            if not geom.type_match(info.get('type', ''), type):
                continue
            if n_dir is not None:
                fn = info.get('normal')
                if not fn or geom.angle_deg(fn, n_dir) > 1.0:
                    continue
            rows.append(info)
    if ext is not None:
        cand = [(r, geom.dot(r['center'], ext)) for r in rows if r.get('center')]
        best = max([c[1] for c in cand]) if cand else None
        rows = [r for r, p in cand if p >= best - 1e-3] if cand else []
    total = len(rows)
    return {'component': component, 'count': total, 'truncated': total > int(limit),
            'faces': rows[:int(limit)],
            'note': '坐标为装配坐标（已在冒烟测试中验证）'}


@command('add_constraint', 'modify')
def add_constraint(kind, component1, face1=None, component2=None, face2=None, distance=None, alignment='infer'):
    part = ctx.work_part()
    k = str(kind).lower()
    if k not in KINDS:
        raise ctx.NxError('kind 只能是: ' + ' / '.join(sorted(KINDS)))
    c1 = ctx.get_obj(component1, 'COMP')
    c2 = g1 = g2 = None
    if k == 'fix':
        g1 = c1
    else:
        if not (face1 and component2 and face2):
            raise ctx.NxError('%s 约束需要 face1、component2、face2' % k)
        g1 = ctx.get_obj(face1)
        c2 = ctx.get_obj(component2, 'COMP')
        g2 = ctx.get_obj(face2)
    if k in ('distance', 'angle') and distance is None:
        raise ctx.NxError('%s 约束需要 distance（距离或角度值）' % k)
    al = ALIGN.get(str(alignment).lower())
    if al is None:
        raise ctx.NxError('alignment 只能是 infer / coalign / contra')
    pos = part.ComponentAssembly.Positioner
    notes = []
    status = None
    pos.ClearNetwork()
    pos.BeginAssemblyConstraints()
    try:
        net = pos.EstablishNetwork()
        try:
            net.MoveObjectsState = True
        except Exception as exc:
            notes.append('MoveObjectsState: %s' % str(exc)[:80])
        con = pos.CreateConstraint(True)
        con.ConstraintType = _pos_enum('ConstraintType', KINDS[k])
        if k != 'fix':
            try:
                con.ConstraintAlignment = _pos_enum('ConstraintAlignment', al)
            except Exception as exc:
                notes.append('alignment: %s' % str(exc)[:80])
        if distance is not None and k in ('distance', 'angle'):
            try:
                con.Expression.RightHandSide = ctx.num(distance)
            except Exception:
                con.OffsetExpression.RightHandSide = ctx.num(distance)
        r1 = con.CreateConstraintReference(c1, g1, False, False, False)
        try:
            r1.SetFixHint(True)
        except Exception as exc:
            notes.append('SetFixHint: %s' % str(exc)[:80])
        if k != 'fix':
            con.CreateConstraintReference(c2, g2, False, False, False)
        net.AddConstraint(con)
        if c2 is not None:
            try:
                net.SetMovingGroup([c2])
            except Exception as exc:
                notes.append('SetMovingGroup: %s' % str(exc)[:80])
        status = net.Solve()
    finally:
        for name in ('ClearNetwork', 'DeleteNonPersistentConstraints'):
            try:
                getattr(pos, name)()
            except Exception as exc:
                notes.append('%s: %s' % (name, str(exc)[:60]))
        try:
            pos.EndAssemblyConstraints()
        except Exception as exc:
            notes.append('EndAssemblyConstraints: %s' % str(exc)[:80])
    out = {'constraint': ctx.oid(con), 'kind': k, 'solver_status': str(status), 'component1': _comp_info(c1)}
    if c2 is not None:
        out['component2'] = _comp_info(c2)
    if notes:
        out['notes'] = notes
    return out
