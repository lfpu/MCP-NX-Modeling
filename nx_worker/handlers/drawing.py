# -*- coding: utf-8 -*-
'''Drawing sheets, base / projected views and PDF export.
Attribute names come from NX 2412 probes (NXOpen.Drawings must be imported explicitly). Unverified until run.
'''
import os

import NXOpen

try:
    import NXOpen.Drawings
except ImportError:
    pass

from nx_worker import ctx, geom
from nx_worker.handlers.workspace import resolve_path
from nx_worker.registry import command

SHEET_SIZES = {'A0': (1189.0, 841.0), 'A1': (841.0, 594.0), 'A2': (594.0, 420.0), 'A3': (420.0, 297.0), 'A4': (297.0, 210.0)}
STD_VIEWS = {'top': 'Top', 'front': 'Front', 'right': 'Right', 'left': 'Left', 'back': 'Back', 'bottom': 'Bottom',
             'iso': 'Isometric', 'isometric': 'Isometric', 'trimetric': 'Trimetric'}


def _enum(paths, name):
    for path in paths:
        obj = NXOpen
        try:
            for seg in path.split('.'):
                obj = getattr(obj, seg)
            return getattr(obj, name)
        except AttributeError:
            continue
    raise ctx.NxError('找不到枚举成员 %s' % name)


def _sheet_info(s):
    info = {'id': ctx.oid(s), 'name': s.Name}
    for attr in ('Height', 'Length', 'ScaleNumerator', 'ScaleDenominator'):
        try:
            info[attr.lower()] = float(getattr(s, attr))
        except Exception:
            pass
    return info


def _find_sheet(part, sheet):
    sheets = list(part.DrawingSheets)
    if not sheets:
        raise ctx.NxError('当前 Part 没有图纸，请先调用 nx_create_drawing_sheet')
    if sheet:
        for s in sheets:
            if ctx.oid(s) == sheet or s.Name == sheet:
                return s
        raise ctx.NxError('找不到图纸 %s（现有: %s）' % (sheet, ', '.join(s.Name for s in sheets)))
    try:
        cur = part.DrawingSheets.CurrentDrawingSheet
        if cur is not None:
            return cur
    except Exception:
        pass
    return sheets[-1]


def _model_view(part, name):
    key = str(name or 'front').lower()
    nm = STD_VIEWS.get(key)
    if nm is None:
        raise ctx.NxError('view 只能是: ' + ' / '.join(sorted(STD_VIEWS)))
    mv = part.ModelingViews.FindObject(nm)
    if mv is None:
        raise ctx.NxError('找不到模型视图 %s' % nm)
    return mv


def _place(builder, part, xy):
    pt = NXOpen.Point3d(float(xy[0]), float(xy[1]), 0.0)
    pl = builder.Placement.Placement
    errs = []
    cands = []
    for holder in ('Views', 'ModelingViews'):
        try:
            cands.append((NXOpen.NXObject.Null, getattr(part, holder).WorkView, pt))
        except Exception:
            pass
    cands.append((pt,))
    for args in cands:
        try:
            pl.SetValue(*args)
            return
        except Exception as exc:
            errs.append(str(exc)[:80])
    raise ctx.NxError('无法设置视图位置: ' + ' | '.join(errs))


def _view_info(v):
    info = {'id': ctx.oid(v)}
    try:
        info['name'] = v.Name
    except Exception:
        pass
    return info


@command('create_drawing_sheet', 'modify')
def create_drawing_sheet(size='A3', name=None, scale=1.0, third_angle=False):
    part = ctx.work_part()
    key = str(size).upper()
    if key not in SHEET_SIZES:
        raise ctx.NxError('size 只能是: ' + ' / '.join(sorted(SHEET_SIZES)))
    length, height = SHEET_SIZES[key]
    sc = float(scale)
    if sc <= 0:
        raise ctx.NxError('scale 必须大于 0')
    b = part.DrawingSheets.DrawingSheetBuilder(NXOpen.Drawings.DrawingSheet.Null)
    notes = []
    try:
        b.Option = _enum(['Drawings.DrawingSheetBuilder.SheetOption', 'Drawings.DrawingSheetBuilderSheetOption'], 'CustomSize')
        b.Units = _enum(['Drawings.DrawingSheetBuilder.SheetUnits', 'Drawings.DrawingSheetBuilderSheetUnits'], 'Metric')
        b.Height = height
        b.Length = length
        b.ScaleNumerator = sc
        b.ScaleDenominator = 1.0
        b.Name = str(name) if name else 'SHEET_%s' % key
        try:
            b.AutoStartViewCreation = False
        except Exception as exc:
            notes.append('AutoStartViewCreation: %s' % str(exc)[:60])
        try:
            ang = 'ThirdAngle' if third_angle else 'FirstAngle'
            b.ProjectionAngle = _enum(['Drawings.DrawingSheetBuilder.SheetProjectionAngle', 'Drawings.DrawingSheetBuilderSheetProjectionAngle'], ang)
        except Exception as exc:
            notes.append('ProjectionAngle: %s' % str(exc)[:80])
        sheet = b.Commit()
    finally:
        b.Destroy()
    try:
        sheet.Open()
    except Exception as exc:
        notes.append('Open: %s' % str(exc)[:80])
    out = {'sheet': _sheet_info(sheet), 'size': key}
    if notes:
        out['notes'] = notes
    return out


@command('add_base_view', 'modify')
def add_base_view(view='front', position=None, scale=1.0, sheet=None):
    part = ctx.work_part()
    sh = _find_sheet(part, sheet)
    try:
        sh.Open()
    except Exception:
        pass
    b = part.DraftingViews.CreateBaseViewBuilder(NXOpen.Drawings.BaseView.Null)
    try:
        _select_model_view(b, part, view)
        try:
            b.Style.ViewStyleBase.Part = part
        except Exception:
            pass
        b.Scale.Numerator = float(scale)
        b.Scale.Denominator = 1.0
        _place(b, part, position or [100.0, 100.0])
        feat = b.Commit()
    finally:
        b.Destroy()
    return {'view': _view_info(feat), 'sheet': sh.Name, 'orientation': str(view)}


@command('add_projected_view', 'modify')
def add_projected_view(parent, position, sheet=None):
    '''parent: id of an existing view (from nx_add_base_view). position: where to place it on the sheet [x, y].'''
    part = ctx.work_part()
    sh = _find_sheet(part, sheet)
    try:
        sh.Open()
    except Exception:
        pass
    pv = ctx.get_obj(parent)
    b = part.DraftingViews.CreateProjectedViewBuilder(NXOpen.Drawings.ProjectedView.Null)
    try:
        sel = b.Parent.View
        try:
            sel.Value = pv
        except Exception as exc:
            attrs = [n for n in dir(sel) if not n.startswith('_')]
            raise ctx.NxError('设置父视图失败(View 类型 %s, 父视图类型 %s): %s; View 的属性: %s' % (type(sel).__name__, type(pv).__name__, str(exc)[:120], attrs[:40]))
        _place(b, part, position)
        feat = b.Commit()
    finally:
        b.Destroy()
    return {'view': _view_info(feat), 'parent': parent, 'sheet': sh.Name}


@command('get_drawing_sheets', 'read')
def get_drawing_sheets():
    part = ctx.work_part()
    out = []
    for s in part.DrawingSheets:
        row = _sheet_info(s)
        try:
            row['views'] = [_view_info(v) for v in s.GetDraftingViews()]
        except Exception:
            pass
        out.append(row)
    return {'count': len(out), 'sheets': out}


@command('export_drawing_pdf', 'session')
def export_drawing_pdf(path, sheet=None, overwrite=False):
    part = ctx.work_part()
    sh = _find_sheet(part, sheet)
    p = resolve_path(path)
    if not p.lower().endswith('.pdf'):
        p += '.pdf'
    if os.path.exists(p):
        if not overwrite:
            raise ctx.NxError('文件已存在: %s；如确需覆盖请设置 overwrite=true' % p)
        os.remove(p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    b = part.PlotManager.CreatePrintPdfbuilder()
    notes = []
    try:
        b.SourceBuilder.SetSheets([sh])
        b.Filename = p
        for attr, paths, member in (
            ('Colors', ['PrintPDFBuilder.Color', 'PrintPDFBuilderColor'], 'BlackOnWhite'),
            ('Size', ['PrintPDFBuilder.SizeOption', 'PrintPDFBuilderSizeOption'], 'FullScale'),
        ):
            try:
                setattr(b, attr, _enum(paths, member))
            except Exception as exc:
                notes.append('%s: %s' % (attr, str(exc)[:80]))
        b.Commit()
    finally:
        b.Destroy()
    if not os.path.isfile(p):
        raise ctx.NxError('导出命令执行了但没有生成 PDF: ' + p)
    out = {'path': p, 'size_bytes': os.path.getsize(p), 'sheet': sh.Name}
    if notes:
        out['notes'] = notes
    return out


def _select_model_view(b, part, view):
    '''Try several candidate names (NX standard model views are usually upper case, e.g. FRONT).'''
    key = str(view or 'front').lower()
    nm = STD_VIEWS.get(key)
    if nm is None:
        raise ctx.NxError('view 只能是: ' + ' / '.join(sorted(STD_VIEWS)))
    if key in ('iso', 'isometric'):
        cands = ['TFR-ISO', 'ISOMETRIC', 'Isometric']
    elif key == 'trimetric':
        cands = ['TFR-TRI', 'TRIMETRIC', 'Trimetric']
    else:
        cands = [nm.upper(), nm, nm.lower()]
    errs = []
    for c in cands:
        try:
            mv = part.ModelingViews.FindObject(c)
            b.SelectModelView.SelectedView = mv
            return c
        except Exception as exc:
            errs.append('%s: %s' % (c, str(exc)[:50]))
    names = []
    try:
        names = [v.Name for v in part.ModelingViews]
    except Exception:
        pass
    raise ctx.NxError('找不到可用的模型视图（%s）；Part 中的视图: %s' % (' | '.join(errs), names[:20]))
