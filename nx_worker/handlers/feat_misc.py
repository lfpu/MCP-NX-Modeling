# -*- coding: utf-8 -*-
'''Datum plane, expressions, delete (Phase 4 + 6).'''
import NXOpen
import NXOpen.Features

from nx_worker import ctx, geom
from nx_worker.handlers import sketch as sk_mod
from nx_worker.registry import command


@command('create_datum_plane', 'modify')
def create_datum_plane(origin, normal):
    part = ctx.work_part()
    basis = {'origin': [float(x) for x in origin], 'n': geom.parse_dir(normal)}
    plane = sk_mod._fixed_datum(part, basis)
    return {'datum_plane': ctx.oid(plane), 'origin': ctx.short(basis['origin'], 4), 'normal': ctx.short(basis['n'], 4)}


@command('edit_expression', 'modify')
def edit_expression(name, value):
    '''Edit a Part expression (number or formula string) and update the model.'''
    part = ctx.work_part()
    expr = None
    for e in part.Expressions:
        if e.Name == name:
            expr = e
            break
    if expr is None:
        raise ctx.NxError('找不到表达式 %s（先用 nx_get_expressions 查看）' % name)
    old = expr.RightHandSide
    s = ctx.session()
    mark = s.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, 'update')
    part.Expressions.Edit(expr, str(value))
    s.UpdateManager.DoUpdate(mark)
    try:
        s.DeleteUndoMark(mark, None)
    except Exception:
        pass
    new = None
    try:
        new = expr.Value
    except Exception:
        pass
    return {'name': name, 'old': old, 'new': str(value), 'value': new}


@command('delete_object', 'dangerous')
def delete_object(object_id):
    '''Delete a feature / body / sketch. Can be reverted with nx_undo_last.'''
    obj = ctx.get_obj(object_id)
    kind = ctx.kind_of(obj)
    if kind in ('FACE', 'EDGE'):
        raise ctx.NxError('不能直接删除面或边，请删除生成它们的特征')
    s = ctx.session()
    mark = s.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, 'delete')
    um = s.UpdateManager
    try:
        um.AddObjectsToDeleteList([obj])
    except Exception:
        um.AddToDeleteList(obj)
    um.DoUpdate(mark)
    try:
        s.DeleteUndoMark(mark, None)
    except Exception:
        pass
    return {'deleted': object_id, 'kind': kind}
