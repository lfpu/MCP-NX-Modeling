# -*- coding: utf-8 -*-
'''STEP / IGES export and STEP import through NX DexManager. Unverified in NX 2412 until run.'''
import os

import NXOpen

from nx_worker import ctx
from nx_worker.handlers.workspace import resolve_path
from nx_worker.registry import command

_CACHE = {}


def _find_def(names):
    key = tuple(names)
    if key in _CACHE:
        return _CACHE[key]
    found = None
    try:
        base = ctx.session().GetEnvironmentVariableValue('UGII_BASE_DIR')
        for sub in os.listdir(base):
            for n in names:
                p = os.path.join(base, sub, n)
                if os.path.isfile(p):
                    found = p
                    break
            if found:
                break
    except Exception:
        pass
    _CACHE[key] = found
    return found


def _target(path, ext, overwrite):
    p = resolve_path(path)
    if not p.lower().endswith(ext):
        p += ext
    if os.path.exists(p):
        if not overwrite:
            raise ctx.NxError('文件已存在: %s；如确需覆盖请设置 overwrite=true' % p)
        os.remove(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def _export(kind, path, overwrite):
    ctx.work_part()
    dm = ctx.session().DexManager
    if kind == 'step':
        maker = getattr(dm, 'CreateStepCreator', None) or getattr(dm, 'CreateStep214Creator', None)
        if maker is None:
            raise ctx.NxError('此 NX 版本找不到 STEP 导出器')
        c = maker()
        ext, defs = '.stp', ['ugstep214.def', 'ugstep.def']
    else:
        c = dm.CreateIgesCreator()
        ext, defs = '.igs', ['igesexport.def']
    p = _target(path, ext, overwrite)
    try:
        opt = getattr(type(c), 'ExportFromOption', None)
        if opt is not None:
            c.ExportFrom = opt.DisplayPart
        c.OutputFile = p
        settings = _find_def(defs)
        if settings:
            c.SettingsFile = settings
        c.Commit()
    finally:
        c.Destroy()
    if not os.path.isfile(p):
        raise ctx.NxError('导出命令执行了但没有生成文件: ' + p)
    return {'path': p, 'size_bytes': os.path.getsize(p), 'format': kind}


@command('export_step', 'session')
def export_step(path, overwrite=False):
    return _export('step', path, overwrite)


@command('export_iges', 'session')
def export_iges(path, overwrite=False):
    return _export('iges', path, overwrite)


@command('import_step', 'session')
def import_step(path, output_part, overwrite=False):
    '''Import a STEP file into a NEW .prt (output_part); open it afterwards with nx_open_part.'''
    src = resolve_path(path)
    if not os.path.isfile(src):
        raise ctx.NxError('STEP 文件不存在: ' + src)
    dst = _target(output_part, '.prt', overwrite)
    dm = ctx.session().DexManager
    imp = dm.CreateStep214Importer()
    try:
        opt = getattr(type(imp), 'ImportToOption', None)
        if opt is not None and hasattr(opt, 'NewPart'):
            imp.ImportTo = opt.NewPart
        imp.InputFile = src
        imp.OutputFile = dst
        settings = _find_def(['ugstep214import.def', 'ugstep214.def'])
        if settings:
            imp.SettingsFile = settings
        imp.Commit()
    finally:
        imp.Destroy()
    if not os.path.isfile(dst):
        raise ctx.NxError('导入命令执行了但没有生成 prt: ' + dst)
    return {'part_path': dst, 'size_bytes': os.path.getsize(dst)}


@command('export_stl', 'session')
def export_stl(path, overwrite=False):
    '''Export the display part as STL (best effort: default NX STL settings).'''
    ctx.work_part()
    p = _target(path, '.stl', overwrite)
    maker = getattr(ctx.session().DexManager, 'CreateStlCreator', None)
    if maker is None:
        raise ctx.NxError('此 NX 版本找不到 STL 导出器')
    c = maker()
    try:
        c.OutputFile = p
        try:
            c.OutputType = ctx.enum_member(['STLCreator.OutputTypeEnum'], ['Binary'])
        except Exception:
            pass
        bodies = ctx.solid_bodies(ctx.work_part())
        if not bodies:
            raise ctx.NxError('没有可导出的实体')
        sel = c.ExportSelectionBlock
        try:
            for bd in bodies:
                sel.Add(bd)
        except Exception:
            sel.SetArray(bodies)
        c.Commit()
    finally:
        c.Destroy()
    if not os.path.isfile(p):
        raise ctx.NxError('导出命令执行了但没有生成文件: ' + p)
    return {'path': p, 'size_bytes': os.path.getsize(p), 'format': 'stl'}
