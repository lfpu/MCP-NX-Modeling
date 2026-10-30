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
            # ExistingPart + InputFile is more reliable than DisplayPart for
            # NX 2412 batch/run_journal sessions, where DisplayPart may be empty.
            work = ctx.work_part()
            source_path = str(getattr(work, 'FullPath', '') or '')
            if source_path and os.path.isfile(source_path):
                c.ExportFrom = opt.ExistingPart
                c.InputFile = source_path
            else:
                c.ExportFrom = opt.DisplayPart
        c.OutputFile = p
        settings = _find_def(defs)
        if settings:
            c.SettingsFile = settings
        try:
            c.ProcessHoldFlag = True
        except Exception:
            pass
        c.Commit()
    finally:
        c.Destroy()
    # 某些 NX DEX 转换器即使 Commit 已返回，仍可能在后台完成文件写入。
    # ProcessHoldFlag 通常会等待转换完成；这里保留短时间轮询作为兼容兜底。
    if not os.path.isfile(p):
        import time
        for _ in range(100):
            time.sleep(0.1)
            if os.path.isfile(p):
                break
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
    '''Import a STEP file into a new NX Part and leave it as the current work/display Part.'''
    src = resolve_path(path)
    if not os.path.isfile(src):
        raise ctx.NxError('STEP 文件不存在: ' + src)
    dst = _target(output_part, '.prt', overwrite)
    session = ctx.session()
    imp = session.DexManager.CreateStep214Importer()
    committed = []
    try:
        opt = getattr(type(imp), 'ImportToOption', None)
        if opt is not None and hasattr(opt, 'NewPart'):
            imp.ImportTo = opt.NewPart
        imp.InputFile = src
        try:
            # NewPart 模式下让 NX 打开转换生成的新 Part，之后由本服务 SaveAs 到目标路径。
            imp.FileOpenFlag = True
        except Exception:
            pass
        try:
            imp.ProcessHoldFlag = True
        except Exception:
            pass
        settings = _find_def(['ugstep214import.def', 'ugstep214.def'])
        if settings:
            imp.SettingsFile = settings
        imp.Commit()
        try:
            committed = list(imp.GetCommittedObjects())
        except Exception:
            committed = []
    finally:
        try:
            imp.Destroy()
        except Exception:
            pass

    # FileOpenFlag=true 会把由 STEP 转换得到的新 Part 设为当前工作 Part。
    # OutputFile 在 NX 2412 NewPart 模式下不保证落盘，因此显式 SaveAs 到目标路径。
    imported_part = session.Parts.Work
    if imported_part is None:
        raise ctx.NxError('STEP 导入后没有生成或打开新的工作 Part')
    bodies = list(imported_part.Bodies)
    if not bodies:
        raise ctx.NxError('STEP 导入后生成的 Part 中没有 Body')
    imported_part.SaveAs(dst)
    if not os.path.isfile(dst):
        raise ctx.NxError('STEP 已导入，但另存目标 Part 失败: ' + dst)
    return {
        'part_path': dst,
        'size_bytes': os.path.getsize(dst),
        'bodies': len(bodies),
        'committed_objects': len(committed),
        'import_to': 'new_part',
    }


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
