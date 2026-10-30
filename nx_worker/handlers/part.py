# -*- coding: utf-8 -*-
'''Part / session level commands (Phase 1).'''
import os

import NXOpen

from nx_worker import ctx
from nx_worker.registry import command


def _abs(path):
    from nx_worker.handlers.workspace import resolve_path
    return resolve_path(path)


def part_brief(part):
    d = {'name': part.Name, 'path': None, 'modified': None}
    try:
        d['path'] = part.FullPath
    except Exception:
        pass
    try:
        d['modified'] = bool(part.IsModified)
    except Exception:
        pass
    try:
        d['units'] = str(part.PartUnits)
    except Exception:
        pass
    return d


@command('status', 'read')
def status():
    s = ctx.session()
    info = {'connected': True}
    for key in ('UGII_BASE_DIR', 'UGII_VERSION'):
        try:
            info[key] = s.GetEnvironmentVariableValue(key)
        except Exception:
            info[key] = None
    work = s.Parts.Work
    info['work_part'] = part_brief(work) if work is not None else None
    info['open_parts'] = [part_brief(p) for p in s.Parts]
    return info


@command('new_part', 'session')
def new_part(path, units='mm', overwrite=False):
    s = ctx.session()
    p = _abs(path)
    if not p.lower().endswith('.prt'):
        p += '.prt'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        if not overwrite:
            raise ctx.NxError('文件已存在: %s；如确需覆盖请设置 overwrite=true' % p)
        try:
            os.remove(p)
        except OSError as exc:
            raise ctx.NxError('无法覆盖已有文件（可能正被 NX 打开）: %s' % exc)
    u = str(units).lower()
    if u in ('mm', 'millimeter', 'millimeters'):
        unit = NXOpen.Part.Units.Millimeters
    elif u in ('inch', 'in', 'inches'):
        unit = NXOpen.Part.Units.Inches
    else:
        raise ctx.NxError('units 只能是 mm 或 inch')
    part = s.Parts.NewDisplay(p, unit)
    return {'part': part_brief(part)}


@command('open_part', 'session')
def open_part(path):
    s = ctx.session()
    p = _abs(path)
    if not os.path.isfile(p):
        raise ctx.NxError('文件不存在: ' + p)
    base_part, status = s.Parts.OpenBaseDisplay(p)
    try:
        status.Dispose()
    except Exception:
        pass
    work = s.Parts.Work
    return {'part': part_brief(work if work is not None else base_part)}


@command('save_part', 'session')
def save_part():
    part = ctx.work_part()
    part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
    return {'part': part_brief(part)}


@command('save_part_as', 'session')
def save_part_as(path, overwrite=False):
    part = ctx.work_part()
    p = _abs(path)
    if not p.lower().endswith('.prt'):
        p += '.prt'
    if os.path.exists(p) and not overwrite:
        raise ctx.NxError('文件已存在: %s；如确需覆盖请设置 overwrite=true' % p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    part.SaveAs(p)
    return {'part': part_brief(part)}


def _close(part):
    part.Close(NXOpen.BasePart.CloseWholeTree.TrueValue, NXOpen.BasePart.CloseModified.CloseModified, None)


@command('close_part', 'session')
def close_part(save=True):
    '''Close the work part. save=True saves first, so nothing is lost.'''
    part = ctx.work_part()
    brief = part_brief(part)
    if save:
        part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
    elif part.IsModified:
        raise ctx.NxError('Part 有未保存的修改；请先保存，或使用 nx_close_part_discard 放弃修改')
    _close(part)
    return {'closed': brief, 'saved': bool(save)}


@command('close_part_discard', 'dangerous')
def close_part_discard():
    '''Close the work part and DISCARD unsaved changes.'''
    part = ctx.work_part()
    brief = part_brief(part)
    _close(part)
    return {'closed': brief, 'saved': False}
