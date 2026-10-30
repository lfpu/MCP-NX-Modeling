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
    for path in ('Features.Feature', 'Features.HolePackage', 'Features.PatternFeature', 'Drawings.DrawingSheet', 'Drawings.BaseView', 'Drawings.DraftingView', 'Drawings.ProjectedView'):
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


@command('debug_builder_details', 'read')
def debug_builder_details(factory, paths):
    '''Create a builder and report type, repr and public children for selected dotted attribute paths.'''
    fn = _resolve('part.' + factory)
    b = None
    errs = []
    for nul in _null_candidates():
        try:
            b = fn(nul)
            break
        except Exception as exc:
            errs.append(str(exc)[:80])
    if b is None:
        try:
            b = fn()
        except Exception as exc:
            raise ctx.NxError('无法创建 builder %s: %s | %s' % (factory, str(exc)[:100], ' ; '.join(errs)[:240]))
    out = {}
    try:
        for path in paths:
            target = b
            try:
                for seg in [s for s in str(path).split('.') if s]:
                    target = getattr(target, seg)
                names = _filter(dir(target), None)
                out[path] = {
                    'type': '%s.%s' % (type(target).__module__, type(target).__name__),
                    'repr': repr(target)[:300],
                    'names': names[:150],
                }
            except Exception as exc:
                out[path] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:240])}
        return {'factory': factory, 'details': out}
    finally:
        try:
            b.Destroy()
        except Exception:
            pass


@command('debug_sketch_methods', 'read')
def debug_sketch_methods():
    '''Create a temporary sketch and report callable metadata for constraint/dimension methods.'''
    part = ctx.work_part()
    plane = part.Planes.CreatePlane(NXOpen.Point3d(0.0, 0.0, 0.0), NXOpen.Vector3d(0.0, 0.0, 1.0), NXOpen.SmartObject.UpdateOption.WithinModeling)
    maker = getattr(part.Sketches, 'CreateNewSketchInPlaceBuilder', None) or getattr(part.Sketches, 'CreateSketchInPlaceBuilder2', None)
    if maker is None:
        raise ctx.NxError('当前 NX 版本没有 SketchInPlaceBuilder')
    b = maker(NXOpen.Sketch.Null)
    try:
        b.PlaneReference = plane
        sk = b.Commit()
    finally:
        b.Destroy()
    methods = ['CreateDimension', 'CreateRadialDimension', 'CreateDiameterDimension',
               'CreateHorizontalConstraint', 'CreateVerticalConstraint',
               'CreateCoincidentConstraint', 'CreateTangentConstraint',
               'CreateParallelConstraint', 'CreatePerpendicularConstraint',
               'CreateConcentricConstraint', 'CreateFixedConstraint']
    out = {}
    for name in methods:
        try:
            fn = getattr(sk, name)
            item = {'type': '%s.%s' % (type(fn).__module__, type(fn).__name__), 'repr': repr(fn)[:300]}
            for attr in ('__doc__', '__text_signature__'):
                try:
                    value = getattr(fn, attr, None)
                    if value:
                        item[attr] = str(value)[:1200]
                except Exception:
                    pass
            out[name] = item
        except Exception as exc:
            out[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:240])}
    return {'methods': out}


@command('debug_hole_position_methods', 'read')
def debug_hole_position_methods():
    '''Inspect HolePosition Section and ProjectionDirection callable signatures on NX 2412.'''
    part = ctx.work_part()
    b = part.Features.CreateHolePackageBuilder(NXOpen.Features.HolePackage.Null)
    try:
        targets = {
            'HolePosition.AddSmartPoint': b.HolePosition.AddSmartPoint,
            'HolePosition.AddToSection': b.HolePosition.AddToSection,
            'HolePosition.SetAllowedEntityTypes': b.HolePosition.SetAllowedEntityTypes,
        }
        out = {}
        for name, fn in targets.items():
            item = {'type': '%s.%s' % (type(fn).__module__, type(fn).__name__), 'repr': repr(fn)[:300]}
            for attr in ('__doc__', '__text_signature__'):
                try:
                    value = getattr(fn, attr, None)
                    if value:
                        item[attr] = str(value)[:1600]
                except Exception:
                    pass
            out[name] = item
        for name in ('DirectionType', 'ProjectDirectionMethod', 'ProjectVector'):
            try:
                value = getattr(b.ProjectionDirection, name)
                out['ProjectionDirection.' + name] = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value)[:500],
                }
            except Exception as exc:
                out['ProjectionDirection.' + name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:300])}
        return {'methods': out}
    finally:
        b.Destroy()


@command('debug_hole_boolean', 'read')
def debug_hole_boolean():
    '''Inspect HolePackage BooleanOperation and target-body APIs on NX 2412.'''
    part = ctx.work_part()
    b = part.Features.CreateHolePackageBuilder(NXOpen.Features.HolePackage.Null)
    try:
        targets = {
            'BooleanOperation': b.BooleanOperation,
            'HolePosition': b.HolePosition,
        }
        out = {}
        for name, obj in targets.items():
            item = {
                'type': '%s.%s' % (type(obj).__module__, type(obj).__name__),
                'repr': repr(obj)[:400],
                'names': [n for n in dir(obj) if not n.startswith('_')],
            }
            out[name] = item
        for name in ('SetTargetBodies', 'GetTargetBodies', 'SetTargetBody', 'TargetBody', 'Targets'):
            try:
                value = getattr(b.BooleanOperation, name)
                item = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value)[:400],
                }
                for attr in ('__doc__', '__text_signature__'):
                    try:
                        text = getattr(value, attr, None)
                        if text:
                            item[attr] = str(text)[:2000]
                    except Exception:
                        pass
                out['BooleanOperation.' + name] = item
            except Exception as exc:
                out['BooleanOperation.' + name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:300])}
        try:
            body = list(part.Bodies)[0]
            out['sample_body'] = {'id': ctx.oid(body), 'type': '%s.%s' % (type(body).__module__, type(body).__name__)}
        except Exception as exc:
            out['sample_body'] = {'error': str(exc)[:300]}
        return out
    finally:
        b.Destroy()


@command('debug_hole_tolerance', 'read')
def debug_hole_tolerance():
    '''Inspect HolePackage tolerance-related properties and current values on NX 2412.'''
    part = ctx.work_part()
    b = part.Features.CreateHolePackageBuilder(NXOpen.Features.HolePackage.Null)
    try:
        out = {}
        for name in ('Tolerance', 'HolePosition', 'ProjectionDirection', 'ProjectPointOntoTargetEnabled'):
            try:
                value = getattr(b, name)
                item = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value)[:500],
                }
                if name == 'Tolerance':
                    try:
                        item['value'] = value
                    except Exception:
                        pass
                out[name] = item
            except Exception as exc:
                out[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:300])}
        for name in ('SetToleranceValues', 'SetTolerance', 'Tolerance'):
            try:
                value = getattr(b.HolePosition, name)
                item = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value)[:500],
                }
                for attr in ('__doc__', '__text_signature__'):
                    try:
                        text = getattr(value, attr, None)
                        if text:
                            item[attr] = str(text)[:2000]
                    except Exception:
                        pass
                out['HolePosition.' + name] = item
            except Exception as exc:
                out['HolePosition.' + name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:300])}
        return out
    finally:
        b.Destroy()


@command('debug_sketch_constraint_methods', 'read')
def debug_sketch_constraint_methods():
    '''Inspect NX 2412 sketch constraint/dimension method signatures and related enum/data types.'''
    part = ctx.work_part()
    plane = part.Planes.CreatePlane(NXOpen.Point3d(0.0, 0.0, 0.0), NXOpen.Vector3d(0.0, 0.0, 1.0), NXOpen.SmartObject.UpdateOption.WithinModeling)
    maker = getattr(part.Sketches, 'CreateNewSketchInPlaceBuilder', None) or getattr(part.Sketches, 'CreateSketchInPlaceBuilder2', None)
    if maker is None:
        raise ctx.NxError('当前 NX 版本没有 SketchInPlaceBuilder')
    b = maker(NXOpen.Sketch.Null)
    try:
        b.PlaneReference = plane
        sk = b.Commit()
    finally:
        b.Destroy()
    names = [
        'CreateHorizontalConstraint', 'CreateVerticalConstraint', 'CreateCoincidentConstraint',
        'CreateTangentConstraint', 'CreateParallelConstraint', 'CreatePerpendicularConstraint',
        'CreateConcentricConstraint', 'CreateFixedConstraint', 'CreateDimension',
        'CreateRadialDimension', 'CreateDiameterDimension'
    ]
    out = {}
    for name in names:
        try:
            fn = getattr(sk, name)
            item = {'type': '%s.%s' % (type(fn).__module__, type(fn).__name__), 'repr': repr(fn)[:400]}
            for attr in ('__doc__', '__text_signature__'):
                try:
                    value = getattr(fn, attr, None)
                    if value:
                        item[attr] = str(value)[:4000]
                except Exception:
                    pass
            out[name] = item
        except Exception as exc:
            out[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:400])}
    for path in ('ConstraintPointType', 'DimensionOption', 'InferConstraintsOption'):
        try:
            obj = getattr(NXOpen.Sketch, path)
            out[path] = {'type': '%s.%s' % (type(obj).__module__, type(obj).__name__), 'names': [n for n in dir(obj) if not n.startswith('_')]}
        except Exception as exc:
            out[path] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:400])}
    return out


@command('debug_sketch_data_types', 'read')
def debug_sketch_data_types():
    '''Inspect constructors, fields and enums required to create sketch constraints and dimensions.'''
    out = {}
    targets = {
        'Sketch.ConstraintGeometry': getattr(NXOpen.Sketch, 'ConstraintGeometry', None),
        'Sketch.DimensionGeometry': getattr(NXOpen.Sketch, 'DimensionGeometry', None),
        'Sketch.ConstraintType': getattr(NXOpen.Sketch, 'ConstraintType', None),
        'Sketch.ConstraintPointType': getattr(NXOpen.Sketch, 'ConstraintPointType', None),
        'Sketch.DimensionOption': getattr(NXOpen.Sketch, 'DimensionOption', None),
    }
    for name, obj in targets.items():
        if obj is None:
            out[name] = {'error': 'not found'}
            continue
        item = {
            'type': '%s.%s' % (type(obj).__module__, type(obj).__name__),
            'repr': repr(obj)[:500],
            'names': [n for n in dir(obj) if not n.startswith('_')],
        }
        try:
            value = obj()
            item['instance_type'] = '%s.%s' % (type(value).__module__, type(value).__name__)
            item['instance_repr'] = repr(value)[:500]
            item['instance_names'] = [n for n in dir(value) if not n.startswith('_')]
            for field in ('Geometry', 'PointType', 'SplineDefiningIndex', 'Associativity'):
                try:
                    field_value = getattr(value, field)
                    item[field] = {
                        'type': '%s.%s' % (type(field_value).__module__, type(field_value).__name__),
                        'repr': repr(field_value)[:300],
                    }
                except Exception as exc:
                    item[field] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:240])}
        except Exception as exc:
            item['construct_error'] = '%s: %s' % (type(exc).__name__, str(exc)[:500])
        for attr in ('__doc__', '__text_signature__'):
            try:
                text = getattr(obj, attr, None)
                if text:
                    item[attr] = str(text)[:3000]
            except Exception:
                pass
        out[name] = item
    return out


@command('debug_sketch_activation', 'read')
def debug_sketch_activation():
    '''Inspect NX 2412 sketch activation, update and deactivation APIs required before adding constraints.'''
    part = ctx.work_part()
    plane = part.Planes.CreatePlane(NXOpen.Point3d(0.0, 0.0, 0.0), NXOpen.Vector3d(0.0, 0.0, 1.0), NXOpen.SmartObject.UpdateOption.WithinModeling)
    maker = getattr(part.Sketches, 'CreateNewSketchInPlaceBuilder', None) or getattr(part.Sketches, 'CreateSketchInPlaceBuilder2', None)
    if maker is None:
        raise ctx.NxError('当前 NX 版本没有 SketchInPlaceBuilder')
    b = maker(NXOpen.Sketch.Null)
    try:
        b.PlaneReference = plane
        sk = b.Commit()
    finally:
        b.Destroy()
    out = {}
    for name in ('Activate', 'Deactivate', 'Update', 'Solve', 'LocalUpdate'):
        try:
            fn = getattr(sk, name)
            item = {
                'type': '%s.%s' % (type(fn).__module__, type(fn).__name__),
                'repr': repr(fn)[:500],
            }
            for attr in ('__doc__', '__text_signature__'):
                try:
                    text = getattr(fn, attr, None)
                    if text:
                        item[attr] = str(text)[:3000]
                except Exception:
                    pass
            out[name] = item
        except Exception as exc:
            out[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:400])}
    try:
        out['ActiveSketch'] = {
            'type': '%s.%s' % (type(part.Sketches.ActiveSketch).__module__, type(part.Sketches.ActiveSketch).__name__),
            'repr': repr(part.Sketches.ActiveSketch)[:500],
        }
    except Exception as exc:
        out['ActiveSketch'] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:400])}
    return out


@command('debug_sketch_expression_api', 'read')
def debug_sketch_expression_api():
    '''Inspect NX 2412 expression creation APIs and dimension method signatures without truncation.'''
    part = ctx.work_part()
    out = {}
    for name in ('CreateSystemExpression', 'CreateSystemExpressionWithUnits', 'CreateExpression', 'CreateExpressionWithUnits'):
        try:
            fn = getattr(part.Expressions, name)
            item = {
                'type': '%s.%s' % (type(fn).__module__, type(fn).__name__),
                'repr': repr(fn)[:500],
            }
            for attr in ('__doc__', '__text_signature__'):
                try:
                    text = getattr(fn, attr, None)
                    if text:
                        item[attr] = str(text)[:6000]
                except Exception:
                    pass
            out['Expressions.' + name] = item
        except Exception as exc:
            out['Expressions.' + name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:500])}
    try:
        uc = part.UnitCollection
        out['units'] = {}
        for name in ('MilliMeter', 'Degree', 'Radian', 'Unitless'):
            try:
                unit = uc.FindObject(name)
                out['units'][name] = {
                    'type': '%s.%s' % (type(unit).__module__, type(unit).__name__),
                    'repr': repr(unit)[:500],
                }
            except Exception as exc:
                out['units'][name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:300])}
    except Exception as exc:
        out['units_error'] = str(exc)[:500]
    plane = part.Planes.CreatePlane(NXOpen.Point3d(0.0, 0.0, 0.0), NXOpen.Vector3d(0.0, 0.0, 1.0), NXOpen.SmartObject.UpdateOption.WithinModeling)
    maker = getattr(part.Sketches, 'CreateNewSketchInPlaceBuilder', None) or getattr(part.Sketches, 'CreateSketchInPlaceBuilder2', None)
    b = maker(NXOpen.Sketch.Null)
    try:
        b.PlaneReference = plane
        sk = b.Commit()
    finally:
        b.Destroy()
    for name in ('CreateDimension', 'CreateRadialDimension', 'CreateDiameterDimension'):
        try:
            fn = getattr(sk, name)
            item = {
                'type': '%s.%s' % (type(fn).__module__, type(fn).__name__),
                'repr': repr(fn)[:500],
            }
            for attr in ('__doc__', '__text_signature__'):
                try:
                    text = getattr(fn, attr, None)
                    if text:
                        item[attr] = str(text)[:10000]
                except Exception:
                    pass
            out['Sketch.' + name] = item
        except Exception as exc:
            out['Sketch.' + name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:500])}
    return out


@command('debug_step_importer', 'read')
def debug_step_importer():
    '''Inspect NX 2412 Step214Importer defaults, property types and method signatures.'''
    imp = ctx.session().DexManager.CreateStep214Importer()
    try:
        out = {}
        for name in (
            'ImportTo', 'InputFile', 'OutputFile', 'FileOpenFlag',
            'ProcessHoldFlag', 'Mode', 'LayerDefault', 'SewSurfaces',
            'Optimize', 'SimplifyGeometry', 'FlattenAssembly', 'SettingsFile'
        ):
            try:
                value = getattr(imp, name)
                out[name] = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value)[:800],
                }
            except Exception as exc:
                out[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:500])}
        for name in ('SetMode', 'GetMode', 'Commit', 'GetCommittedObjects'):
            try:
                fn = getattr(imp, name)
                item = {
                    'type': '%s.%s' % (type(fn).__module__, type(fn).__name__),
                    'repr': repr(fn)[:500],
                }
                for attr in ('__doc__', '__text_signature__'):
                    try:
                        text = getattr(fn, attr, None)
                        if text:
                            item[attr] = str(text)[:5000]
                    except Exception:
                        pass
                out[name] = item
            except Exception as exc:
                out[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc)[:500])}
        for path, obj in (
            ('ImportToOption', getattr(type(imp), 'ImportToOption', None)),
            ('ModeType', getattr(type(imp), 'ModeType', None)),
        ):
            if obj is None:
                out[path] = {'error': 'not found'}
            else:
                out[path] = {
                    'type': '%s.%s' % (type(obj).__module__, type(obj).__name__),
                    'names': [n for n in dir(obj) if not n.startswith('_')],
                }
        return out
    finally:
        imp.Destroy()
