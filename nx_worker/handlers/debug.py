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


@command('debug_primitive_sketch_api', 'read')
def debug_primitive_sketch_api():
    '''Verify typed Null objects for sphere/cone builders and arc orientation matrices on NX 2412.'''
    part = ctx.work_part()
    out = {'typed_nulls': {}, 'builders': {}, 'matrix_fields': {}, 'arcs': {}}

    for name in ('Sphere', 'Cone'):
        try:
            cls = getattr(NXOpen.Features, name)
            nul = cls.Null
            out['typed_nulls'][name] = {
                'class': '%s.%s' % (cls.__module__, cls.__name__),
                'null_type': '%s.%s' % (type(nul).__module__, type(nul).__name__),
                'null_repr': repr(nul),
            }
        except Exception as exc:
            out['typed_nulls'][name] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}

    factories = (
        ('sphere', part.Features.CreateSphereBuilder, getattr(NXOpen.Features, 'Sphere').Null),
        ('cone', part.Features.CreateConeBuilder, getattr(NXOpen.Features, 'Cone').Null),
    )
    for name, factory, nul in factories:
        builder = None
        try:
            builder = factory(nul)
            out['builders'][name] = {
                'ok': True,
                'type': '%s.%s' % (type(builder).__module__, type(builder).__name__),
                'names': [n for n in dir(builder) if not n.startswith('_')],
            }
        except Exception as exc:
            out['builders'][name] = {'ok': False, 'error': '%s: %s' % (type(exc).__name__, str(exc))}
        finally:
            if builder is not None:
                try:
                    builder.Destroy()
                except Exception:
                    pass

    matrix = NXOpen.Matrix3x3()
    matrix_names = [n for n in dir(matrix) if not n.startswith('_')]
    out['matrix_fields'] = {
        'type': '%s.%s' % (type(matrix).__module__, type(matrix).__name__),
        'names': matrix_names,
    }

    planes = {
        'xy': ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        'yz': ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
        'xz': ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    for plane_name, basis in planes.items():
        arc = None
        try:
            x_axis, y_axis, normal = basis
            m = NXOpen.Matrix3x3()
            m.Xx, m.Xy, m.Xz = x_axis
            m.Yx, m.Yy, m.Yz = y_axis
            m.Zx, m.Zy, m.Zz = normal
            nx_matrix = part.NXMatrices.Create(m)
            arc = part.Curves.CreateArc(NXOpen.Point3d(0.0, 0.0, 0.0), nx_matrix, 10.0, 0.0, 2.0 * 3.141592653589793)
            box = ctx.bbox(arc)
            out['arcs'][plane_name] = {
                'ok': True,
                'id': ctx.oid(arc),
                'bbox': box,
                'expected_constant_axis': {'xy': 'z', 'yz': 'x', 'xz': 'y'}[plane_name],
            }
        except Exception as exc:
            out['arcs'][plane_name] = {'ok': False, 'error': '%s: %s' % (type(exc).__name__, str(exc))}
    return out


@command('debug_sketch_plane_orientation', 'read')
def debug_sketch_plane_orientation(plane='yz', offset=4.0):
    '''Probe the actual orientation returned by NX for a committed standard-plane sketch.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, face_obj = sk_mod.resolve_basis(plane, None, offset)
    sk = sk_mod.new_sketch(part, basis, face_obj)
    sk_mod.BASIS[sk.Tag] = basis
    out = {
        'plane': plane,
        'requested_basis': basis,
        'sketch': ctx.oid(sk),
        'sketch_names': [name for name in dir(sk) if not name.startswith('_')],
    }

    for attr in ('Orientation', 'Origin', 'Axis', 'Normal'):
        try:
            value = getattr(sk, attr)
            item = {
                'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                'repr': repr(value),
                'names': [name for name in dir(value) if not name.startswith('_')],
            }
            for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz', 'X', 'Y', 'Z'):
                try:
                    item[field] = float(getattr(value, field))
                except Exception:
                    pass
            try:
                element = value.Element
                item['element_type'] = '%s.%s' % (type(element).__module__, type(element).__name__)
                item['element'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                    if hasattr(element, field)
                }
            except Exception as exc:
                item['element_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            out[attr] = item
        except Exception as exc:
            out[attr] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}
    return out


@command('debug_sketch_builder_plane', 'read')
def debug_sketch_builder_plane(plane='yz', offset=4.0):
    '''Probe SketchCollection and SketchInPlaceBuilder plane/orientation APIs on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    datum = sk_mod._fixed_datum(part, basis)
    out = {
        'plane': plane,
        'basis': basis,
        'sketch_collection_names': [n for n in dir(part.Sketches) if not n.startswith('_')],
        'datum_type': '%s.%s' % (type(datum).__module__, type(datum).__name__),
        'datum_names': [n for n in dir(datum) if not n.startswith('_')],
    }

    for method_name in ('CreateNewSketchInPlaceBuilder', 'CreateSketchInPlaceBuilder2'):
        fn = getattr(part.Sketches, method_name, None)
        if fn is None:
            out[method_name] = {'available': False}
            continue
        builder = None
        try:
            builder = fn(NXOpen.Sketch.Null)
            item = {
                'available': True,
                'builder_type': '%s.%s' % (type(builder).__module__, type(builder).__name__),
                'builder_names': [n for n in dir(builder) if not n.startswith('_')],
            }
            for attr in ('PlaneReference', 'SketchPlane', 'Plane', 'Orientation', 'Origin', 'Axis'):
                try:
                    value = getattr(builder, attr)
                    item[attr] = {
                        'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                        'repr': repr(value),
                    }
                except Exception as exc:
                    item[attr] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}
            try:
                builder.PlaneReference = datum
                item['plane_reference_after_set'] = {
                    'type': '%s.%s' % (type(builder.PlaneReference).__module__, type(builder.PlaneReference).__name__),
                    'repr': repr(builder.PlaneReference),
                }
            except Exception as exc:
                item['plane_reference_set_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            try:
                committed = builder.Commit()
                item['committed_type'] = '%s.%s' % (type(committed).__module__, type(committed).__name__)
                item['committed_id'] = ctx.oid(committed)
                item['committed_origin'] = ctx.p3(committed.Origin)
                element = committed.Orientation.Element
                item['committed_orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            out[method_name] = item
        except Exception as exc:
            out[method_name] = {'available': True, 'create_error': '%s: %s' % (type(exc).__name__, str(exc))}
        finally:
            if builder is not None:
                try:
                    builder.Destroy()
                except Exception:
                    pass
    return out


@command('debug_smart_sketch_plane', 'read')
def debug_smart_sketch_plane(plane='yz', offset=4.0):
    '''Verify NXOpen.Plane assignment and committed sketch orientation on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    ref = sk_mod._smart_plane(part, basis)
    out = {
        'plane': plane,
        'basis': basis,
        'reference_type': '%s.%s' % (type(ref).__module__, type(ref).__name__),
        'reference_origin': ctx.p3(ref.Origin),
        'reference_normal': ctx.p3(ref.Normal),
    }

    for property_name in ('PlaneReference', 'Plane'):
        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        try:
            item = {}
            try:
                setattr(builder, property_name, ref)
                item['set_ok'] = True
            except Exception as exc:
                item['set_ok'] = False
                item['set_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['id'] = ctx.oid(sketch)
                item['origin'] = ctx.p3(sketch.Origin)
                item['orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            out[property_name] = item
        finally:
            builder.Destroy()
    return out


@command('debug_sketch_builder_options', 'read')
def debug_sketch_builder_options(plane='yz', offset=4.0):
    '''Probe SketchInPlaceBuilder option types, enum members and writable orientation inputs on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    ref = sk_mod._smart_plane(part, basis)
    builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
    out = {'plane': plane, 'basis': basis}
    try:
        attrs = (
            'PlaneReference', 'PlaneOption', 'PlaneOrFace', 'Axis', 'AxisReference',
            'AxisOrientation', 'AxisOrientationInfer', 'Csystem', 'SketchOrigin',
            'OriginOption', 'OriginOptionInfer', 'ProjectWorkPartOrigin',
            'MakeOriginAssociative', 'ReverseAxis', 'ReversePlaneNormal'
        )
        for attr in attrs:
            item = {}
            try:
                value = getattr(builder, attr)
                item['read_ok'] = True
                item['type'] = '%s.%s' % (type(value).__module__, type(value).__name__)
                item['repr'] = repr(value)
                item['names'] = [n for n in dir(value) if not n.startswith('_')]
            except Exception as exc:
                item['read_ok'] = False
                item['read_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            out[attr] = item

        for enum_name in ('PlaneOption', 'AxisOrientation', 'AxisOrientationInfer', 'OriginOption', 'OriginOptionInfer'):
            try:
                enum_type = type(getattr(builder, enum_name))
            except Exception:
                enum_type = None
            if enum_type is None:
                out['enum_' + enum_name] = {'available': False}
                continue
            members = {}
            for name in dir(enum_type):
                if name.startswith('_'):
                    continue
                try:
                    value = getattr(enum_type, name)
                    members[name] = {'repr': repr(value), 'value': int(value)}
                except Exception:
                    pass
            out['enum_' + enum_name] = {
                'available': True,
                'type': '%s.%s' % (enum_type.__module__, enum_type.__name__),
                'members': members,
            }

        builder.PlaneReference = ref
        candidates = {
            'PlaneOption': ('ExistingPlane', 'Plane', 'Inferred'),
            'OriginOption': ('Specify', 'Point', 'Projected'),
            'AxisOrientation': ('Horizontal', 'Vertical', 'Inferred'),
        }
        for attr, names in candidates.items():
            try:
                enum_type = type(getattr(builder, attr))
            except Exception:
                enum_type = None
            attempts = []
            if enum_type is not None:
                for name in names:
                    if not hasattr(enum_type, name):
                        continue
                    try:
                        setattr(builder, attr, getattr(enum_type, name))
                        attempts.append({'name': name, 'ok': True, 'after': repr(getattr(builder, attr))})
                    except Exception as exc:
                        attempts.append({'name': name, 'ok': False, 'error': '%s: %s' % (type(exc).__name__, str(exc))})
            out['set_' + attr] = attempts
    finally:
        try:
            builder.Destroy()
        except Exception as exc:
            out['builder_destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
    return out


@command('debug_sketch_selector_plane', 'read')
def debug_sketch_selector_plane(plane='yz', offset=4.0):
    '''Probe PlaneOrFace selector and integer option members for standard-plane sketches on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    ref = sk_mod._smart_plane(part, basis)
    out = {'plane': plane, 'basis': basis}

    for mode in ('set_value', 'value_property'):
        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        try:
            item = {
                'plane_option_before': int(builder.PlaneOption.value),
                'axis_orientation_before': int(builder.AxisOrientation.value),
                'origin_option_before': int(builder.OriginOption.value),
            }
            try:
                if mode == 'set_value':
                    builder.PlaneOrFace.SetValue(ref)
                else:
                    builder.PlaneOrFace.Value = ref
                item['selector_set_ok'] = True
                try:
                    selected = builder.PlaneOrFace.GetValue()
                except Exception:
                    selected = builder.PlaneOrFace.Value
                item['selected_type'] = '%s.%s' % (type(selected).__module__, type(selected).__name__)
            except Exception as exc:
                item['selector_set_ok'] = False
                item['selector_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                builder.PlaneReference = ref
                item['reference_set_ok'] = True
            except Exception as exc:
                item['reference_set_ok'] = False
                item['reference_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['id'] = ctx.oid(sketch)
                item['origin'] = ctx.p3(sketch.Origin)
                item['orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            out[mode] = item
        finally:
            builder.Destroy()

    option_values = {}
    for value in range(0, 8):
        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        try:
            item = {}
            try:
                builder.PlaneOption.value = value
                item['set_ok'] = True
                item['after'] = int(builder.PlaneOption.value)
            except Exception as exc:
                item['set_ok'] = False
                item['error'] = '%s: %s' % (type(exc).__name__, str(exc))
            option_values[str(value)] = item
        finally:
            builder.Destroy()
    out['plane_option_values'] = option_values
    return out


@command('debug_sketch_option_constants', 'read')
def debug_sketch_option_constants():
    '''Find NX 2412 constants and constructors for SketchInPlaceBuilder options.'''
    part = ctx.work_part()
    builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
    try:
        out = {
            'nxopen_matching_names': [
                name for name in dir(NXOpen)
                if any(token in name.lower() for token in ('sketchplane', 'originmethod', 'axisorientation'))
            ],
            'builder_property_values': {},
            'matching_objects': {},
        }
        for prop in ('PlaneOption', 'OriginOption', 'OriginOptionInfer', 'AxisOrientation', 'AxisOrientationInfer'):
            try:
                value = getattr(builder, prop)
                out['builder_property_values'][prop] = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value),
                    'int': int(value),
                    'value': int(value.value),
                    'names': [name for name in dir(value) if not name.startswith('_')],
                }
            except Exception as exc:
                out['builder_property_values'][prop] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}

        for name in out['nxopen_matching_names']:
            obj = getattr(NXOpen, name)
            item = {
                'type': '%s.%s' % (type(obj).__module__, type(obj).__name__),
                'repr': repr(obj),
                'names': [member for member in dir(obj) if not member.startswith('_')],
            }
            members = {}
            for member in item['names']:
                try:
                    value = getattr(obj, member)
                    members[member] = {
                        'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                        'repr': repr(value),
                        'int': int(value),
                    }
                except Exception:
                    pass
            item['integer_members'] = members
            out['matching_objects'][name] = item
        return out
    finally:
        builder.Destroy()


@command('debug_sketch_existing_plane_option', 'read')
def debug_sketch_existing_plane_option(plane='yz', offset=4.0):
    '''Verify SketchPlaneOption.ExistingPlane with PlaneReference on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    ref = sk_mod._smart_plane(part, basis)
    out = {'plane': plane, 'basis': basis}

    options = (
        ('ExistingPlane', NXOpen.SketchPlaneOption.ExistingPlane),
        ('NewPlane', NXOpen.SketchPlaneOption.NewPlane),
        ('Inferred', NXOpen.SketchPlaneOption.Inferred),
    )
    for option_name, option in options:
        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        try:
            item = {'option_repr': repr(option)}
            try:
                builder.PlaneOption = option
                item['option_set_ok'] = True
            except Exception as exc:
                item['option_set_ok'] = False
                item['option_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            try:
                builder.PlaneReference = ref
                item['reference_set_ok'] = True
            except Exception as exc:
                item['reference_set_ok'] = False
                item['reference_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['id'] = ctx.oid(sketch)
                item['origin'] = ctx.p3(sketch.Origin)
                item['orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            out[option_name] = item
        finally:
            builder.Destroy()
    return out


@command('debug_sketch_csystem_api', 'read')
def debug_sketch_csystem_api(plane='yz', offset=4.0):
    '''Probe coordinate-system factories and SketchInPlaceBuilder Csystem assignment on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
    try:
        out = {
            'plane': plane,
            'basis': basis,
            'coordinate_systems_type': '%s.%s' % (type(part.CoordinateSystems).__module__, type(part.CoordinateSystems).__name__),
            'coordinate_systems_names': [name for name in dir(part.CoordinateSystems) if not name.startswith('_')],
            'nx_matrices_names': [name for name in dir(part.NXMatrices) if not name.startswith('_')],
        }
        for attr in ('Csystem', 'SketchOrigin', 'Axis', 'AxisReference', 'PlaneOrFace'):
            try:
                value = getattr(builder, attr)
                out[attr] = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value),
                    'names': [name for name in dir(value) if not name.startswith('_')],
                }
            except Exception as exc:
                out[attr] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}

        matrix = NXOpen.Matrix3x3()
        u, v, n = basis['u'], basis['v'], basis['n']
        matrix.Xx, matrix.Xy, matrix.Xz = u[0], u[1], u[2]
        matrix.Yx, matrix.Yy, matrix.Yz = v[0], v[1], v[2]
        matrix.Zx, matrix.Zy, matrix.Zz = n[0], n[1], n[2]
        nx_matrix = part.NXMatrices.Create(matrix)
        out['matrix'] = {
            'type': '%s.%s' % (type(nx_matrix).__module__, type(nx_matrix).__name__),
            'names': [name for name in dir(nx_matrix) if not name.startswith('_')],
        }

        factories = {}
        for name in dir(part.CoordinateSystems):
            if not name.startswith('Create'):
                continue
            fn = getattr(part.CoordinateSystems, name)
            factories[name] = {
                'type': '%s.%s' % (type(fn).__module__, type(fn).__name__),
                'repr': repr(fn),
            }
        out['factories'] = factories

        attempts = []
        origin = ctx.pt(basis['origin'])
        for factory_name in factories:
            fn = getattr(part.CoordinateSystems, factory_name)
            argument_sets = (
                ('origin_nxmatrix', (origin, nx_matrix)),
                ('origin_matrix', (origin, matrix)),
                ('origin_nxmatrix_update', (origin, nx_matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
                ('origin_matrix_update', (origin, matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
            )
            for signature, args in argument_sets:
                record = {'factory': factory_name, 'signature': signature}
                csys = None
                try:
                    csys = fn(*args)
                    record['created'] = True
                    record['type'] = '%s.%s' % (type(csys).__module__, type(csys).__name__)
                    record['names'] = [name for name in dir(csys) if not name.startswith('_')]
                    try:
                        builder.Csystem = csys
                        record['assigned'] = True
                    except Exception as exc:
                        record['assigned'] = False
                        record['assign_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                except Exception as exc:
                    record['created'] = False
                    record['create_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                attempts.append(record)
                if record.get('assigned'):
                    try:
                        builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
                        sketch = builder.Commit()
                        element = sketch.Orientation.Element
                        record['committed'] = True
                        record['origin'] = ctx.p3(sketch.Origin)
                        record['orientation'] = {
                            field: float(getattr(element, field))
                            for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                        }
                    except Exception as exc:
                        record['committed'] = False
                        record['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                    break
            if attempts and attempts[-1].get('assigned'):
                break
        out['attempts'] = attempts
        return out
    finally:
        builder.Destroy()


@command('debug_sketch_csystem_point_api', 'read')
def debug_sketch_csystem_point_api(plane='yz', offset=4.0):
    '''Verify CoordinateSystem creation with NXOpen.Point + NXMatrix on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    matrix = NXOpen.Matrix3x3()
    u, v, n = basis['u'], basis['v'], basis['n']
    matrix.Xx, matrix.Xy, matrix.Xz = u[0], u[1], u[2]
    matrix.Yx, matrix.Yy, matrix.Yz = v[0], v[1], v[2]
    matrix.Zx, matrix.Zy, matrix.Zz = n[0], n[1], n[2]
    nx_matrix = part.NXMatrices.Create(matrix)
    point = part.Points.CreatePoint(ctx.pt(basis['origin']))

    out = {
        'plane': plane,
        'basis': basis,
        'point_type': '%s.%s' % (type(point).__module__, type(point).__name__),
        'point_names': [name for name in dir(point) if not name.startswith('_')],
    }

    attempts = (
        ('point_nxmatrix', (point, nx_matrix)),
        ('point_nxmatrix_update', (point, nx_matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
        ('point_matrix', (point, matrix)),
        ('point_matrix_update', (point, matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
    )
    for signature, args in attempts:
        item = {}
        csys = None
        try:
            csys = part.CoordinateSystems.CreateCoordinateSystem(*args)
            item['created'] = True
            item['type'] = '%s.%s' % (type(csys).__module__, type(csys).__name__)
            item['names'] = [name for name in dir(csys) if not name.startswith('_')]
            try:
                origin, x_dir, y_dir = part.CoordinateSystems.GetOriginAndDirections(csys)
                item['origin'] = ctx.p3(origin)
                item['x_direction'] = ctx.p3(x_dir)
                item['y_direction'] = ctx.p3(y_dir)
            except Exception as exc:
                item['query_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        except Exception as exc:
            item['created'] = False
            item['create_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[signature] = item

        if csys is not None:
            builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
            try:
                try:
                    builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
                    builder.Csystem = csys
                    item['assigned'] = True
                except Exception as exc:
                    item['assigned'] = False
                    item['assign_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                try:
                    sketch = builder.Commit()
                    element = sketch.Orientation.Element
                    item['committed'] = True
                    item['sketch_id'] = ctx.oid(sketch)
                    item['sketch_origin'] = ctx.p3(sketch.Origin)
                    item['sketch_orientation'] = {
                        field: float(getattr(element, field))
                        for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                    }
                except Exception as exc:
                    item['committed'] = False
                    item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            finally:
                builder.Destroy()
            break
    return out


@command('debug_xform_csystem_api', 'read')
def debug_xform_csystem_api(plane='yz', offset=4.0):
    '''Probe Xform creation, CoordinateSystem creation and Sketch NewCsys on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    out = {
        'plane': plane,
        'basis': basis,
        'part_matching_names': [
            name for name in dir(part)
            if any(token in name.lower() for token in ('xform', 'coordinate', 'matrix', 'point'))
        ],
    }

    collections = {}
    for attr in ('Xforms', 'CoordinateSystems', 'NXMatrices', 'Points'):
        try:
            value = getattr(part, attr)
            collections[attr] = {
                'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                'names': [name for name in dir(value) if not name.startswith('_')],
            }
        except Exception as exc:
            collections[attr] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}
    out['collections'] = collections

    matrix = NXOpen.Matrix3x3()
    u, v, n = basis['u'], basis['v'], basis['n']
    matrix.Xx, matrix.Xy, matrix.Xz = u[0], u[1], u[2]
    matrix.Yx, matrix.Yy, matrix.Yz = v[0], v[1], v[2]
    matrix.Zx, matrix.Zy, matrix.Zz = n[0], n[1], n[2]
    nx_matrix = part.NXMatrices.Create(matrix)
    point3d = ctx.pt(basis['origin'])
    point = part.Points.CreatePoint(point3d)

    xforms = getattr(part, 'Xforms', None)
    attempts = []
    created_xforms = []
    if xforms is not None:
        factories = [name for name in dir(xforms) if name.startswith('Create')]
        out['xform_factories'] = factories
        argument_sets = (
            ('point3d_matrix', (point3d, matrix)),
            ('point3d_nxmatrix', (point3d, nx_matrix)),
            ('point_matrix', (point, matrix)),
            ('point_nxmatrix', (point, nx_matrix)),
            ('matrix_point3d', (matrix, point3d)),
            ('nxmatrix_point3d', (nx_matrix, point3d)),
            ('point3d_matrix_update', (point3d, matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
            ('point3d_nxmatrix_update', (point3d, nx_matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
            ('point_matrix_update', (point, matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
            ('point_nxmatrix_update', (point, nx_matrix, NXOpen.SmartObject.UpdateOption.WithinModeling)),
        )
        for factory_name in factories:
            fn = getattr(xforms, factory_name)
            for signature, args in argument_sets:
                item = {'factory': factory_name, 'signature': signature}
                try:
                    xform = fn(*args)
                    item['created'] = True
                    item['type'] = '%s.%s' % (type(xform).__module__, type(xform).__name__)
                    item['names'] = [name for name in dir(xform) if not name.startswith('_')]
                    created_xforms.append((factory_name + ':' + signature, xform, item))
                except Exception as exc:
                    item['created'] = False
                    item['error'] = '%s: %s' % (type(exc).__name__, str(exc))
                attempts.append(item)
    out['xform_attempts'] = attempts

    csys_attempts = []
    for source_name, xform, xform_item in created_xforms:
        argument_sets = (
            ('xform', (xform,)),
            ('xform_update', (xform, NXOpen.SmartObject.UpdateOption.WithinModeling)),
        )
        for signature, args in argument_sets:
            item = {'source': source_name, 'signature': signature}
            csys = None
            try:
                csys = part.CoordinateSystems.CreateCoordinateSystem(*args)
                item['created'] = True
                item['type'] = '%s.%s' % (type(csys).__module__, type(csys).__name__)
                try:
                    origin, x_dir, y_dir = part.CoordinateSystems.GetOriginAndDirections(csys)
                    item['origin'] = ctx.p3(origin)
                    item['x_direction'] = ctx.p3(x_dir)
                    item['y_direction'] = ctx.p3(y_dir)
                except Exception as exc:
                    item['query_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            except Exception as exc:
                item['created'] = False
                item['error'] = '%s: %s' % (type(exc).__name__, str(exc))
            csys_attempts.append(item)

            if csys is not None:
                builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
                try:
                    try:
                        builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
                        builder.Csystem = csys
                        builder.ProjectWorkPartOrigin = False
                        item['assigned'] = True
                    except Exception as exc:
                        item['assigned'] = False
                        item['assign_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                    try:
                        sketch = builder.Commit()
                        element = sketch.Orientation.Element
                        item['committed'] = True
                        item['sketch_id'] = ctx.oid(sketch)
                        item['sketch_origin'] = ctx.p3(sketch.Origin)
                        item['sketch_orientation'] = {
                            field: float(getattr(element, field))
                            for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                        }
                    except Exception as exc:
                        item['committed'] = False
                        item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                finally:
                    builder.Destroy()
                if item.get('committed'):
                    break
        if csys_attempts and csys_attempts[-1].get('committed'):
            break
    out['coordinate_system_attempts'] = csys_attempts
    return out


@command('debug_point_direction_xform', 'read')
def debug_point_direction_xform(plane='yz', offset=4.0):
    '''Probe CreateXformByPointXDirZDir/YDirZDir exact signatures and Sketch NewCsys on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
    x_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['u']), NXOpen.SmartObject.UpdateOption.WithinModeling)
    y_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['v']), NXOpen.SmartObject.UpdateOption.WithinModeling)
    z_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['n']), NXOpen.SmartObject.UpdateOption.WithinModeling)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling

    out = {
        'plane': plane,
        'basis': basis,
        'origin_type': '%s.%s' % (type(origin).__module__, type(origin).__name__),
        'direction_type': '%s.%s' % (type(x_direction).__module__, type(x_direction).__name__),
    }

    attempts = (
        ('xdir_zdir_point_dirs_scale_update', part.Xforms.CreateXformByPointXDirZDir,
         (origin, x_direction, z_direction, 1.0, update)),
        ('xdir_zdir_point_dirs_update_scale', part.Xforms.CreateXformByPointXDirZDir,
         (origin, x_direction, z_direction, update, 1.0)),
        ('xdir_zdir_point_dirs_false_update', part.Xforms.CreateXformByPointXDirZDir,
         (origin, x_direction, z_direction, False, update)),
        ('xdir_zdir_point_dirs_update_false', part.Xforms.CreateXformByPointXDirZDir,
         (origin, x_direction, z_direction, update, False)),
        ('ydir_zdir_point_dirs_scale_update', part.Xforms.CreateXformByPointYDirZDir,
         (origin, y_direction, z_direction, 1.0, update)),
        ('ydir_zdir_point_dirs_update_scale', part.Xforms.CreateXformByPointYDirZDir,
         (origin, y_direction, z_direction, update, 1.0)),
        ('ydir_zdir_point_dirs_false_update', part.Xforms.CreateXformByPointYDirZDir,
         (origin, y_direction, z_direction, False, update)),
        ('ydir_zdir_point_dirs_update_false', part.Xforms.CreateXformByPointYDirZDir,
         (origin, y_direction, z_direction, update, False)),
    )

    for name, factory, args in attempts:
        item = {}
        xform = None
        try:
            xform = factory(*args)
            item['xform_created'] = True
            item['xform_type'] = '%s.%s' % (type(xform).__module__, type(xform).__name__)
        except Exception as exc:
            item['xform_created'] = False
            item['xform_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[name] = item

        if xform is None:
            continue

        csys = None
        for csys_signature, csys_args in (
            ('xform_update', (xform, update)),
            ('xform', (xform,)),
        ):
            try:
                csys = part.CoordinateSystems.CreateCoordinateSystem(*csys_args)
                item['csys_signature'] = csys_signature
                item['csys_created'] = True
                break
            except Exception as exc:
                item.setdefault('csys_errors', []).append(
                    {'signature': csys_signature, 'error': '%s: %s' % (type(exc).__name__, str(exc))})

        if csys is None:
            continue

        try:
            csys_origin, csys_x, csys_y = part.CoordinateSystems.GetOriginAndDirections(csys)
            item['csys_origin'] = ctx.p3(csys_origin)
            item['csys_x'] = ctx.p3(csys_x)
            item['csys_y'] = ctx.p3(csys_y)
        except Exception as exc:
            item['csys_query_error'] = '%s: %s' % (type(exc).__name__, str(exc))

        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        try:
            builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
            builder.Csystem = csys
            builder.ProjectWorkPartOrigin = False
            sketch = builder.Commit()
            element = sketch.Orientation.Element
            item['sketch_committed'] = True
            item['sketch_id'] = ctx.oid(sketch)
            item['sketch_origin'] = ctx.p3(sketch.Origin)
            item['sketch_orientation'] = {
                field: float(getattr(element, field))
                for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
            }
        except Exception as exc:
            item['sketch_committed'] = False
            item['sketch_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        finally:
            builder.Destroy()

        if item.get('sketch_committed'):
            break
    return out


@command('debug_single_xform_sketch', 'read')
def debug_single_xform_sketch(plane='yz', offset=4.0):
    '''Test one isolated Point/XDir/ZDir Xform to CoordinateSystem to Sketch chain.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    try:
        origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
        x_direction = part.Directions.CreateDirection(
            ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
        z_direction = part.Directions.CreateDirection(
            ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
        out['objects_created'] = True
    except Exception as exc:
        out['objects_created'] = False
        out['object_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        return out

    xform = None
    signatures = (
        ('scale_update', (origin, x_direction, z_direction, 1.0, update)),
        ('update_scale', (origin, x_direction, z_direction, update, 1.0)),
        ('false_update', (origin, x_direction, z_direction, False, update)),
        ('update_false', (origin, x_direction, z_direction, update, False)),
    )
    for name, args in signatures:
        try:
            xform = part.Xforms.CreateXformByPointXDirZDir(*args)
            out['xform_signature'] = name
            out['xform_created'] = True
            break
        except Exception as exc:
            out.setdefault('xform_errors', []).append(
                {'signature': name, 'error': '%s: %s' % (type(exc).__name__, str(exc))})
    if xform is None:
        out['xform_created'] = False
        return out

    csys = None
    for name, args in (
        ('xform_update', (xform, update)),
        ('xform', (xform,)),
    ):
        try:
            csys = part.CoordinateSystems.CreateCoordinateSystem(*args)
            out['csys_signature'] = name
            out['csys_created'] = True
            break
        except Exception as exc:
            out.setdefault('csys_errors', []).append(
                {'signature': name, 'error': '%s: %s' % (type(exc).__name__, str(exc))})
    if csys is None:
        out['csys_created'] = False
        return out

    builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
    try:
        builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
        builder.Csystem = csys
        builder.ProjectWorkPartOrigin = False
        sketch = builder.Commit()
        element = sketch.Orientation.Element
        out['sketch_committed'] = True
        out['sketch_id'] = ctx.oid(sketch)
        out['sketch_origin'] = ctx.p3(sketch.Origin)
        out['sketch_orientation'] = {
            field: float(getattr(element, field))
            for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
        }
    except Exception as exc:
        out['sketch_committed'] = False
        out['sketch_error'] = '%s: %s' % (type(exc).__name__, str(exc))
    finally:
        try:
            builder.Destroy()
        except Exception as exc:
            out['builder_destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
    return out


@command('debug_intermediate_csys_sketch', 'read')
def debug_intermediate_csys_sketch(plane='yz', offset=4.0):
    '''Verify CreateIntermediateDatumCsys workflow for SketchPlaneOption.NewCsys on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
    x_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
    z_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
    xform = part.Xforms.CreateXformByPointXDirZDir(
        origin, x_direction, z_direction, update, 1.0)
    csys = part.CoordinateSystems.CreateCoordinateSystem(xform, update)
    out['xform_created'] = True
    out['csys_created'] = True

    attempts = (
        ('assign_then_intermediate', True),
        ('intermediate_then_assign', False),
    )
    for name, assign_first in attempts:
        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        item = {}
        try:
            builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
            builder.ProjectWorkPartOrigin = False
            if assign_first:
                builder.Csystem = csys
            try:
                intermediate = builder.CreateIntermediateDatumCsys()
                item['intermediate_created'] = True
                item['intermediate_type'] = '%s.%s' % (type(intermediate).__module__, type(intermediate).__name__)
                item['intermediate_repr'] = repr(intermediate)
            except Exception as exc:
                intermediate = None
                item['intermediate_created'] = False
                item['intermediate_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            if not assign_first:
                builder.Csystem = csys
            try:
                item['validate'] = bool(builder.Validate())
            except Exception as exc:
                item['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))
            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['sketch_id'] = ctx.oid(sketch)
                item['sketch_origin'] = ctx.p3(sketch.Origin)
                item['sketch_orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        except Exception as exc:
            item['setup_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        finally:
            try:
                builder.Destroy()
            except Exception as exc:
                item['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[name] = item
        if item.get('committed'):
            break
    return out


@command('debug_intermediate_csys_flag', 'read')
def debug_intermediate_csys_flag(plane='yz', offset=4.0):
    '''Verify CreateIntermediateDatumCsys boolean flag with NewCsys on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    try:
        origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
        x_direction = part.Directions.CreateDirection(
            ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
        z_direction = part.Directions.CreateDirection(
            ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
        xform = part.Xforms.CreateXformByPointXDirZDir(
            origin, x_direction, z_direction, update, 1.0)
        csys = part.CoordinateSystems.CreateCoordinateSystem(xform, update)
        out['objects_created'] = True
    except Exception as exc:
        out['objects_created'] = False
        out['object_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        return out

    builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
    try:
        out['flag_before'] = bool(builder.CreateIntermediateDatumCsys)
        builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
        builder.CreateIntermediateDatumCsys = True
        out['flag_after'] = bool(builder.CreateIntermediateDatumCsys)
        builder.Csystem = csys
        builder.ProjectWorkPartOrigin = False

        try:
            out['validate'] = bool(builder.Validate())
        except Exception as exc:
            out['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))

        try:
            sketch = builder.Commit()
            element = sketch.Orientation.Element
            out['committed'] = True
            out['sketch_id'] = ctx.oid(sketch)
            out['sketch_origin'] = ctx.p3(sketch.Origin)
            out['sketch_orientation'] = {
                field: float(getattr(element, field))
                for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
            }
        except Exception as exc:
            out['committed'] = False
            out['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
    except Exception as exc:
        out['setup_error'] = '%s: %s' % (type(exc).__name__, str(exc))
    finally:
        try:
            builder.Destroy()
        except Exception as exc:
            out['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
    return out


@command('debug_csystem_tag_sketch', 'read')
def debug_csystem_tag_sketch(plane='yz', offset=4.0):
    '''Verify whether SketchInPlaceBuilder Csystem expects a CoordinateSystem tag and explicit origin/axis inputs.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
    x_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
    z_direction = part.Directions.CreateDirection(
        ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
    xform = part.Xforms.CreateXformByPointXDirZDir(
        origin, x_direction, z_direction, update, 1.0)
    csys = part.CoordinateSystems.CreateCoordinateSystem(xform, update)

    out['origin_tag'] = int(origin.Tag)
    out['x_direction_tag'] = int(x_direction.Tag)
    out['z_direction_tag'] = int(z_direction.Tag)
    out['xform_tag'] = int(xform.Tag)
    out['csys_tag'] = int(csys.Tag)

    variants = (
        ('csys_object', csys, False, False),
        ('csys_tag', int(csys.Tag), False, False),
        ('csys_tag_origin', int(csys.Tag), True, False),
        ('csys_tag_origin_axis', int(csys.Tag), True, True),
    )

    for name, csys_value, set_origin, set_axis in variants:
        builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
        item = {}
        try:
            builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
            builder.CreateIntermediateDatumCsys = True
            builder.ProjectWorkPartOrigin = False

            try:
                builder.Csystem = csys_value
                item['csystem_set_ok'] = True
                item['csystem_after_type'] = '%s.%s' % (
                    type(builder.Csystem).__module__, type(builder.Csystem).__name__)
                item['csystem_after_repr'] = repr(builder.Csystem)
            except Exception as exc:
                item['csystem_set_ok'] = False
                item['csystem_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            if set_origin:
                try:
                    builder.SketchOrigin = origin
                    item['origin_object_set_ok'] = True
                except Exception as exc:
                    item['origin_object_set_ok'] = False
                    item['origin_object_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                    try:
                        builder.SketchOrigin = int(origin.Tag)
                        item['origin_tag_set_ok'] = True
                    except Exception as tag_exc:
                        item['origin_tag_set_ok'] = False
                        item['origin_tag_error'] = '%s: %s' % (type(tag_exc).__name__, str(tag_exc))

            if set_axis:
                try:
                    builder.Axis.SetValue(x_direction)
                    item['axis_selector_set_ok'] = True
                except Exception as exc:
                    item['axis_selector_set_ok'] = False
                    item['axis_selector_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                try:
                    builder.AxisReference = x_direction
                    item['axis_reference_object_set_ok'] = True
                except Exception as exc:
                    item['axis_reference_object_set_ok'] = False
                    item['axis_reference_object_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                    try:
                        builder.AxisReference = int(x_direction.Tag)
                        item['axis_reference_tag_set_ok'] = True
                    except Exception as tag_exc:
                        item['axis_reference_tag_set_ok'] = False
                        item['axis_reference_tag_error'] = '%s: %s' % (type(tag_exc).__name__, str(tag_exc))

            try:
                item['validate'] = bool(builder.Validate())
            except Exception as exc:
                item['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['sketch_id'] = ctx.oid(sketch)
                item['sketch_origin'] = ctx.p3(sketch.Origin)
                item['sketch_orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        except Exception as exc:
            item['setup_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        finally:
            try:
                builder.Destroy()
            except Exception as exc:
                item['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[name] = item
        if item.get('committed'):
            break
    return out


@command('debug_fresh_csystem_sketch_inputs', 'read')
def debug_fresh_csystem_sketch_inputs(plane='yz', offset=4.0):
    '''Test fresh NewCsys chains with explicit SketchOrigin and AxisReference inputs on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    variants = (
        ('csys_only', False, False),
        ('csys_origin', True, False),
        ('csys_axis', False, True),
        ('csys_origin_axis', True, True),
    )

    for name, set_origin, set_axis in variants:
        item = {}
        builder = None
        try:
            origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
            x_direction = part.Directions.CreateDirection(
                ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
            z_direction = part.Directions.CreateDirection(
                ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
            xform = part.Xforms.CreateXformByPointXDirZDir(
                origin, x_direction, z_direction, update, 1.0)
            csys = part.CoordinateSystems.CreateCoordinateSystem(xform, update)
            item['fresh_objects_created'] = True

            builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
            builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
            builder.CreateIntermediateDatumCsys = True
            builder.ProjectWorkPartOrigin = False
            builder.Csystem = csys
            item['csystem_set_ok'] = True

            if set_origin:
                builder.SketchOrigin = origin
                item['origin_set_ok'] = True

            if set_axis:
                builder.AxisReference = x_direction
                item['axis_reference_set_ok'] = True

            try:
                item['validate'] = bool(builder.Validate())
            except Exception as exc:
                item['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['sketch_id'] = ctx.oid(sketch)
                item['sketch_origin'] = ctx.p3(sketch.Origin)
                item['sketch_orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        except Exception as exc:
            item['setup_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        finally:
            if builder is not None:
                try:
                    builder.Destroy()
                except Exception as exc:
                    item['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[name] = item
        if item.get('committed'):
            break
    return out


@command('debug_csystem_origin_axis_options', 'read')
def debug_csystem_origin_axis_options(plane='yz', offset=4.0):
    '''Test explicit OriginMethod and AxisOrientation options for NewCsys sketches on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    variants = (
        ('specified_horizontal', NXOpen.OriginMethod.SpecifyPoint, NXOpen.AxisOrientation.Horizontal),
        ('specified_vertical', NXOpen.OriginMethod.SpecifyPoint, NXOpen.AxisOrientation.Vertical),
        ('work_origin_horizontal', NXOpen.OriginMethod.WorkPartOrigin, NXOpen.AxisOrientation.Horizontal),
        ('work_origin_vertical', NXOpen.OriginMethod.WorkPartOrigin, NXOpen.AxisOrientation.Vertical),
    )

    for name, origin_method, axis_orientation in variants:
        item = {}
        builder = None
        try:
            origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
            x_direction = part.Directions.CreateDirection(
                ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
            z_direction = part.Directions.CreateDirection(
                ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
            xform = part.Xforms.CreateXformByPointXDirZDir(
                origin, x_direction, z_direction, update, 1.0)
            csys = part.CoordinateSystems.CreateCoordinateSystem(xform, update)

            builder = part.Sketches.CreateNewSketchInPlaceBuilder(NXOpen.Sketch.Null)
            builder.PlaneOption = NXOpen.SketchPlaneOption.NewCsys
            builder.CreateIntermediateDatumCsys = True
            builder.ProjectWorkPartOrigin = False
            builder.Csystem = csys
            builder.OriginOption = origin_method
            builder.OriginOptionInfer = origin_method
            builder.AxisOrientation = axis_orientation
            builder.AxisOrientationInfer = axis_orientation
            item['options_set_ok'] = True

            if origin_method == NXOpen.OriginMethod.SpecifyPoint:
                builder.SketchOrigin = origin
                item['origin_set_ok'] = True
            builder.AxisReference = x_direction
            item['axis_reference_set_ok'] = True

            try:
                item['validate'] = bool(builder.Validate())
            except Exception as exc:
                item['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['sketch_id'] = ctx.oid(sketch)
                item['sketch_origin'] = ctx.p3(sketch.Origin)
                item['sketch_orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        except Exception as exc:
            item['setup_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        finally:
            if builder is not None:
                try:
                    builder.Destroy()
                except Exception as exc:
                    item['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[name] = item
        if item.get('committed'):
            break
    return out


@command('debug_uf_sketch_api', 'read')
def debug_uf_sketch_api():
    '''Inspect NXOpen.UF sketch APIs for direct creation with an explicit coordinate system.'''
    import NXOpen.UF

    uf = NXOpen.UF.UFSession.GetUFSession()
    out = {
        'uf_type': '%s.%s' % (type(uf).__module__, type(uf).__name__),
        'uf_matching_names': [
            name for name in dir(uf)
            if any(token in name.lower() for token in ('sketch', 'csys', 'xform', 'matrix'))
        ],
    }

    for attr in ('Sketch', 'Csys', 'Math', 'Modl', 'Obj'):
        try:
            value = getattr(uf, attr)
            item = {
                'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                'names': [name for name in dir(value) if not name.startswith('_')],
            }
            methods = {}
            for name in item['names']:
                if not any(token in name.lower() for token in (
                        'create', 'attach', 'plane', 'orient', 'matrix', 'csys', 'sketch')):
                    continue
                try:
                    member = getattr(value, name)
                    methods[name] = {
                        'type': '%s.%s' % (type(member).__module__, type(member).__name__),
                        'repr': repr(member),
                    }
                except Exception as exc:
                    methods[name] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}
            item['matching_methods'] = methods
            out[attr] = item
        except Exception as exc:
            out[attr] = {'error': '%s: %s' % (type(exc).__name__, str(exc))}
    return out


@command('debug_sketch_collection_factories', 'read')
def debug_sketch_collection_factories():
    '''Inspect all SketchCollection creation factories and UF Csys signatures on NX 2412.'''
    import NXOpen.UF

    part = ctx.work_part()
    uf = NXOpen.UF.UFSession.GetUFSession()
    out = {
        'sketch_collection_type': '%s.%s' % (
            type(part.Sketches).__module__, type(part.Sketches).__name__),
        'sketch_factories': {},
        'uf_csys_methods': {},
    }

    for name in dir(part.Sketches):
        if not name.startswith('Create'):
            continue
        try:
            value = getattr(part.Sketches, name)
            out['sketch_factories'][name] = {
                'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                'repr': repr(value),
            }
        except Exception as exc:
            out['sketch_factories'][name] = {
                'error': '%s: %s' % (type(exc).__name__, str(exc))
            }

    for name in ('CreateMatrix', 'CreateCsys', 'CreateTempCsys', 'AskCsysInfo', 'AskMatrixValues'):
        try:
            value = getattr(uf.Csys, name)
            out['uf_csys_methods'][name] = {
                'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                'repr': repr(value),
            }
        except Exception as exc:
            out['uf_csys_methods'][name] = {
                'error': '%s: %s' % (type(exc).__name__, str(exc))
            }
    return out


@command('debug_simple_sketch_builder', 'read')
def debug_simple_sketch_builder(plane='yz', offset=4.0):
    '''Probe CreateSimpleSketchInPlaceBuilder for explicit plane sketches on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    out = {'plane': plane, 'basis': basis}

    factory = part.Sketches.CreateSimpleSketchInPlaceBuilder
    builder = None
    create_attempts = (
        ('sketch_null', (NXOpen.Sketch.Null,)),
        ('no_args', ()),
    )
    for name, args in create_attempts:
        try:
            builder = factory(*args)
            out['builder_create_signature'] = name
            out['builder_created'] = True
            break
        except Exception as exc:
            out.setdefault('builder_create_errors', []).append({
                'signature': name,
                'error': '%s: %s' % (type(exc).__name__, str(exc)),
            })
    if builder is None:
        out['builder_created'] = False
        return out

    try:
        out['builder_type'] = '%s.%s' % (type(builder).__module__, type(builder).__name__)
        out['builder_names'] = [name for name in dir(builder) if not name.startswith('_')]

        for attr in out['builder_names']:
            if not any(token in attr.lower() for token in (
                    'plane', 'origin', 'axis', 'csys', 'matrix', 'reference', 'coordinate', 'normal')):
                continue
            try:
                value = getattr(builder, attr)
                out.setdefault('relevant_properties', {})[attr] = {
                    'type': '%s.%s' % (type(value).__module__, type(value).__name__),
                    'repr': repr(value),
                    'names': [name for name in dir(value) if not name.startswith('_')],
                }
            except Exception as exc:
                out.setdefault('relevant_properties', {})[attr] = {
                    'error': '%s: %s' % (type(exc).__name__, str(exc)),
                }

        references = (
            ('smart_plane', sk_mod._smart_plane(part, basis)),
            ('datum_plane', sk_mod._fixed_datum(part, basis)),
        )
        property_names = (
            'PlaneReference', 'Plane', 'PlaneOrFace', 'SketchPlane', 'ReferencePlane',
        )
        for ref_name, ref in references:
            for prop_name in property_names:
                if not hasattr(builder, prop_name):
                    continue
                item = {'reference': ref_name, 'property': prop_name}
                try:
                    prop = getattr(builder, prop_name)
                    if hasattr(prop, 'SetValue'):
                        prop.SetValue(ref)
                    else:
                        setattr(builder, prop_name, ref)
                    item['set_ok'] = True
                except Exception as exc:
                    item['set_ok'] = False
                    item['set_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                if not item['set_ok']:
                    out.setdefault('attempts', []).append(item)
                    continue
                try:
                    item['validate'] = bool(builder.Validate())
                except Exception as exc:
                    item['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                try:
                    sketch = builder.Commit()
                    element = sketch.Orientation.Element
                    item['committed'] = True
                    item['sketch_id'] = ctx.oid(sketch)
                    item['sketch_origin'] = ctx.p3(sketch.Origin)
                    item['sketch_orientation'] = {
                        field: float(getattr(element, field))
                        for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                    }
                except Exception as exc:
                    item['committed'] = False
                    item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                out.setdefault('attempts', []).append(item)
                if item.get('committed'):
                    return out
        return out
    finally:
        try:
            builder.Destroy()
        except Exception as exc:
            out['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))


@command('debug_simple_sketch_csystem', 'read')
def debug_simple_sketch_csystem(plane='yz', offset=4.0):
    '''Verify SimpleSketchInPlaceBuilder with an explicit CartesianCoordinateSystem on NX 2412.'''
    from nx_worker.handlers import sketch as sk_mod

    part = ctx.work_part()
    basis, _ = sk_mod.resolve_basis(plane, None, offset)
    update = NXOpen.SmartObject.UpdateOption.WithinModeling
    out = {'plane': plane, 'basis': basis}

    variants = (
        ('csys_only', False, False),
        ('csys_origin', True, False),
        ('csys_origin_horizontal', True, True),
    )

    for name, set_origin, set_horizontal in variants:
        item = {}
        builder = None
        try:
            origin = part.Points.CreatePoint(ctx.pt(basis['origin']))
            x_direction = part.Directions.CreateDirection(
                ctx.pt(basis['origin']), ctx.vec(basis['u']), update)
            z_direction = part.Directions.CreateDirection(
                ctx.pt(basis['origin']), ctx.vec(basis['n']), update)
            xform = part.Xforms.CreateXformByPointXDirZDir(
                origin, x_direction, z_direction, update, 1.0)
            csys = part.CoordinateSystems.CreateCoordinateSystem(xform, update)
            item['fresh_objects_created'] = True

            builder = part.Sketches.CreateSimpleSketchInPlaceBuilder()
            builder.CoordinateSystem = csys
            builder.UseWorkPartOrigin = False
            item['coordinate_system_set_ok'] = True

            if set_origin:
                builder.SketchOrigin = origin
                item['origin_set_ok'] = True

            if set_horizontal:
                try:
                    builder.HorizontalReference.SetValue(x_direction)
                    item['horizontal_direction_set_ok'] = True
                except Exception as exc:
                    item['horizontal_direction_set_ok'] = False
                    item['horizontal_direction_error'] = '%s: %s' % (type(exc).__name__, str(exc))
                try:
                    builder.HorizontalReference.SetValue(xform)
                    item['horizontal_xform_set_ok'] = True
                except Exception as exc:
                    item['horizontal_xform_set_ok'] = False
                    item['horizontal_xform_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                item['validate'] = bool(builder.Validate())
            except Exception as exc:
                item['validate_error'] = '%s: %s' % (type(exc).__name__, str(exc))

            try:
                sketch = builder.Commit()
                element = sketch.Orientation.Element
                item['committed'] = True
                item['sketch_id'] = ctx.oid(sketch)
                item['sketch_origin'] = ctx.p3(sketch.Origin)
                item['sketch_orientation'] = {
                    field: float(getattr(element, field))
                    for field in ('Xx', 'Xy', 'Xz', 'Yx', 'Yy', 'Yz', 'Zx', 'Zy', 'Zz')
                }
            except Exception as exc:
                item['committed'] = False
                item['commit_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        except Exception as exc:
            item['setup_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        finally:
            if builder is not None:
                try:
                    builder.Destroy()
                except Exception as exc:
                    item['destroy_error'] = '%s: %s' % (type(exc).__name__, str(exc))
        out[name] = item
        if item.get('committed'):
            break
    return out


@command('debug_color_thread_api', 'read')
def debug_color_thread_api():
    '''Inspect color and threaded-hole APIs without committing model changes.'''
    part = ctx.work_part()
    out = {}
    b = part.Features.CreateHolePackageBuilder(NXOpen.Features.HolePackage.Null)
    try:
        names = [n for n in dir(b) if not n.startswith('_') and any(k in n.lower() for k in ('thread', 'tap', 'standard', 'size', 'type', 'depth'))]
        out['hole_properties'] = {}
        for name in names:
            try:
                value = getattr(b, name)
                out['hole_properties'][name] = {'type': str(type(value)), 'value': str(value), 'members': [n for n in dir(value) if not n.startswith('_')][:60]}
            except Exception as exc:
                out['hole_properties'][name] = {'error': str(exc)}
        out['hole_builder_enums'] = {}
        for name in dir(NXOpen.Features.HolePackageBuilder):
            if any(k in name.lower() for k in ('type', 'thread', 'tap')) and not name.startswith('_'):
                value = getattr(NXOpen.Features.HolePackageBuilder, name)
                out['hole_builder_enums'][name] = [n for n in dir(value) if not n.startswith('_')]
    finally:
        b.Destroy()
    dm = ctx.session().DisplayManager.NewDisplayModification()
    try:
        out['display_modification'] = [n for n in dir(dm) if not n.startswith('_')]
    finally:
        dm.Dispose()
    out['thread_factories'] = [n for n in dir(part.Features) if 'thread' in n.lower()]
    return out
