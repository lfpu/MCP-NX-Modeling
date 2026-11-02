# -*- coding: utf-8 -*-
'''Body and face colors, integrated with dispatcher undo/rollback.'''
from nx_worker import ctx
from nx_worker.registry import command


def _apply_color(ids, kind, color, all_faces):
    if isinstance(color, bool) or not isinstance(color, int) or not 1 <= color <= 216:
        raise ctx.NxError('color must be an NX palette index from 1 to 216')
    if not ids:
        raise ctx.NxError('At least one object id is required')
    objects = ctx.get_many(ids, kind)
    unique = {int(obj.Tag): obj for obj in objects}
    objects = list(unique.values())
    old_colors = [{'id': ctx.oid(obj), 'color': int(obj.Color)} for obj in objects]
    modification = ctx.session().DisplayManager.NewDisplayModification()
    try:
        modification.ApplyToAllFaces = bool(all_faces)
        modification.ApplyToOwningParts = False
        modification.NewColor = color
        modification.Apply(objects)
    finally:
        modification.Dispose()
    return {'objects': [ctx.oid(obj) for obj in objects], 'color': color,
            'apply_to_all_faces': bool(all_faces), 'previous_object_colors': old_colors}


@command('color_bodies', 'modify')
def color_bodies(bodies, color, apply_to_all_faces=True):
    return _apply_color(bodies, 'BODY', color, apply_to_all_faces)


@command('color_faces', 'modify')
def color_faces(faces, color):
    return _apply_color(faces, 'FACE', color, False)
