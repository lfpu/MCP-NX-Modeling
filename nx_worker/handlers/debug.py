# -*- coding: utf-8 -*-
'''Diagnostics: report which NX / UF APIs work in this NX version (used by scripts/probe.py).'''
import NXOpen

from nx_worker import ctx
from nx_worker.registry import command


def _t(out, name, fn):
    try:
        out[name] = repr(fn())[:240]
    except Exception as exc:
        out[name] = 'ERR %s: %s' % (type(exc).__name__, str(exc)[:200])


@command('debug_probe', 'read')
def debug_probe():
    out = {}
    _t(out, 'import NXOpen.UF', lambda: __import__('NXOpen.UF'))
    _t(out, 'getattr NXOpen.UF', lambda: getattr(NXOpen, 'UF', None))
    _t(out, 'ufs()', lambda: ctx.ufs())
    _t(out, 'NXOpen.Face.FaceType', lambda: getattr(NXOpen.Face, 'FaceType', None))
    _t(out, 'NXOpen.Edge.EdgeType', lambda: getattr(NXOpen.Edge, 'EdgeType', None))
    _t(out, 'TaggedObjectManager', lambda: getattr(NXOpen, 'TaggedObjectManager', None))
    part = ctx.work_part()
    bodies = list(part.Bodies)
    if not bodies:
        out['note'] = 'no body in work part'
        return out
    body = bodies[0]
    faces = list(body.GetFaces())
    edges = list(body.GetEdges())
    f = faces[0]
    e = edges[0]
    _t(out, 'face.SolidFaceType', lambda: f.SolidFaceType)
    _t(out, 'face.SolidFaceType type', lambda: type(f.SolidFaceType))
    _t(out, 'edge.SolidEdgeType', lambda: e.SolidEdgeType)
    _t(out, 'edge.SolidEdgeType type', lambda: type(e.SolidEdgeType))
    _t(out, 'AskBoundingBox(tag)', lambda: ctx.ufs().Modeling.AskBoundingBox(f.Tag))
    _t(out, 'AskBoundingBox(tag, box)', lambda: ctx.ufs().Modeling.AskBoundingBox(f.Tag, [0.0] * 6))
    _t(out, 'AskFaceData(tag)', lambda: ctx.ufs().Modeling.AskFaceData(f.Tag))
    _t(out, 'AskEdgeType(tag)', lambda: ctx.ufs().Modeling.AskEdgeType(e.Tag))
    _t(out, 'ctx.bbox(face)', lambda: ctx.bbox(f))
    _t(out, 'ctx.bbox(body)', lambda: ctx.bbox(body))
    _t(out, 'ctx.get_obj(face id)', lambda: ctx.get_obj(ctx.oid(f)))
    return out


def _resolve(path):
    '''Dotted path starting at part / session / NXOpen, e.g. part.Features.'''
    root, _, rest = str(path).partition('.')
    if root == 'part':
        obj = ctx.work_part()
    elif root == 'session':
        obj = ctx.session()
    elif root == 'NXOpen':
        obj = NXOpen
    else:
        raise ctx.NxError('path 必须以 part / session / NXOpen 开头')
    for seg in [s for s in rest.split('.') if s]:
        try:
            obj = getattr(obj, seg)
        except AttributeError:
            modname = getattr(obj, '__name__', '')
            if isinstance(modname, str) and modname.startswith('NXOpen') and '.' not in seg and seg[:1].isupper():
                import importlib
                obj = importlib.import_module(modname + '.' + seg)
            else:
                raise
    return obj


def _filter(names, contains):
    names = [n for n in names if not n.startswith('_')]
    if contains:
        keys = [contains] if isinstance(contains, str) else list(contains)
        keys = [k.lower() for k in keys]
        names = [n for n in names if any(k in n.lower() for k in keys)]
    return names


@command('debug_dir', 'read')
def debug_dir(path, contains=None):
    '''List attribute names of an NX object, optionally filtered by substring(s) (case-insensitive).'''
    names = _filter(dir(_resolve(path)), contains)
    return {'path': path, 'count': len(names), 'names': names[:150]}


@command('debug_builder', 'read')
def debug_builder(factory, contains=None):
    '''Create a builder via part.<factory>(Feature.Null), list its attributes, then destroy it.'''
    fn = _resolve('part.' + factory)
    try:
        b = fn(NXOpen.Features.Feature.Null)
    except TypeError:
        b = fn()
    try:
        names = _filter(dir(b), contains)
        return {'factory': factory, 'count': len(names), 'names': names[:150]}
    finally:
        try:
            b.Destroy()
        except Exception:
            pass


def _null_candidates():
    out = []
    for path in ('Features.Feature', 'Drawings.DrawingSheet', 'Drawings.BaseView', 'Drawings.DraftingView', 'Drawings.ProjectedView'):
        obj = NXOpen
        try:
            for seg in path.split('.'):
                obj = getattr(obj, seg)
            out.append(obj.Null)
        except Exception:
            pass
    return out


@command('debug_builder_ex', 'read')
def debug_builder_ex(factory, sub=None, contains=None):
    '''Create a builder (trying several Null argument types), list attributes of builder[.sub], then destroy it.'''
    fn = _resolve('part.' + factory)
    b = None
    errs = []
    for nul in _null_candidates():
        try:
            b = fn(nul)
            break
        except Exception as exc:
            errs.append(str(exc)[:60])
    if b is None:
        try:
            b = fn()
        except Exception as exc:
            raise ctx.NxError('无法创建 builder %s: %s | %s' % (factory, str(exc)[:80], ' ; '.join(errs)[:200]))
    try:
        target = b
        for seg in [s for s in str(sub or '').split('.') if s]:
            target = getattr(target, seg)
        names = _filter(dir(target), contains)
        return {'factory': factory, 'sub': sub, 'count': len(names), 'names': names[:150]}
    finally:
        try:
            b.Destroy()
        except Exception:
            pass


@command('debug_create', 'read')
def debug_create(path, sub=None, contains=None):
    '''Call a no-argument factory such as session.DexManager.CreateStepCreator, list attributes, then destroy.'''
    fn = _resolve(path)
    obj = fn()
    try:
        target = obj
        for seg in [s for s in str(sub or '').split('.') if s]:
            target = getattr(target, seg)
        names = _filter(dir(target), contains)
        return {'path': path, 'count': len(names), 'names': names[:150]}
    finally:
        try:
            obj.Destroy()
        except Exception:
            pass
