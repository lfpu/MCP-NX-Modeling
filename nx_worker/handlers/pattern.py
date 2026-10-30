# -*- coding: utf-8 -*-
'''Feature patterns (linear / grid / circular) via PatternFeatureBuilder.
Attribute names come from NX 2412 probes; spacing attribute names have fallbacks. Unverified until run.
'''
import NXOpen
import NXOpen.Features
import NXOpen.GeometricUtilities

from nx_worker import ctx, geom
from nx_worker.handlers.feat_sweep import result
from nx_worker.registry import command

PATTERN_ENUM = ['GeometricUtilities.PatternDefinition.PatternEnum', 'GeometricUtilities.PatternDefinitionPatternEnum']
SPACING_ENUM = ['GeometricUtilities.PatternSpacing.SpacingType', 'GeometricUtilities.PatternSpacingSpacingType']
METHOD_ENUM = ['Features.PatternFeatureBuilder.PatternMethodOptions', 'Features.PatternFeatureBuilderPatternMethodOptions']


def _enum(paths, name):
    return ctx.enum_member(paths, list(name) if isinstance(name, (list, tuple)) else [name])


def _set_value(obj, names, value):
    errs = []
    for n in names:
        if not hasattr(obj, n):
            continue
        tgt = getattr(obj, n)
        try:
            tgt.RightHandSide = ctx.num(value)
            return n
        except Exception as exc:
            errs.append('%s.RightHandSide: %s' % (n, str(exc)[:60]))
        try:
            setattr(obj, n, value)
            return n
        except Exception as exc:
            errs.append('%s=: %s' % (n, str(exc)[:60]))
    raise ctx.NxError('无法设置 %s（%s）' % ('/'.join(names), ' | '.join(errs)[:260]))


def _spacing(sp, count, pitch, pitch_names):
    try:
        sp.SpacingType = _enum(SPACING_ENUM, 'NumberAndPitch')
    except Exception:
        pass
    _set_value(sp, ['NCopies', 'NumberOfCopies', 'NumberOfCopiesExpression'], count)
    _set_value(sp, pitch_names, pitch)


def _direction(part, d):
    return part.Directions.CreateDirection(ctx.pt([0.0, 0.0, 0.0]), ctx.vec(d), NXOpen.SmartObject.UpdateOption.WithinModeling)


def _perp(d):
    ref = [0.0, 0.0, 1.0] if abs(d[2]) < 0.9 else [1.0, 0.0, 0.0]
    c = [d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0]]
    return geom.unit(c)


@command('pattern_feature', 'modify')
def pattern_feature(features, kind='linear', direction='x', count=2, spacing=10.0, direction2=None,
                    count2=1, spacing2=None, axis_origin=None, axis_direction=None, angle=360.0):
    '''kind: linear / grid / circular. count includes the original feature (total instances).'''
    part = ctx.work_part()
    k = str(kind).lower()
    if k not in ('linear', 'grid', 'circular'):
        raise ctx.NxError('kind 只能是 linear / grid / circular')
    if int(count) < 2 and k != 'grid':
        raise ctx.NxError('count 必须 >= 2（含原特征）')
    feats = ctx.get_many(features, 'FEATURE')
    b = part.Features.CreatePatternFeatureBuilder(NXOpen.Features.Feature.Null)
    try:
        try:
            b.PatternMethod = _enum(METHOD_ENUM, 'Simple')
        except Exception:
            pass
        for f in feats:
            try:
                b.FeatureList.Add(f)
            except Exception:
                b.FeatureList.Add([f])
        svc = b.PatternService
        if k == 'circular':
            if axis_origin is None or axis_direction is None:
                raise ctx.NxError('circular 需要 axis_origin 和 axis_direction')
            svc.PatternType = _enum(PATTERN_ENUM, 'Circular')
            cd = svc.CircularDefinition
            cd.RotationAxis = ctx.make_axis(part, axis_origin, geom.parse_dir(axis_direction))
            total = float(angle)
            n = int(count)
            pitch = total / n if abs(total - 360.0) < 1e-9 else total / (n - 1)
            _spacing(cd.AngularSpacing, n, pitch, ['PitchAngle', 'PitchAngleExpression', 'PitchDistance'])
        else:
            svc.PatternType = _enum(PATTERN_ENUM, ['Rectangular', 'Linear'])
            rd = svc.RectangularDefinition
            d1 = geom.parse_dir(direction)
            rd.XDirection = _direction(part, d1)
            _spacing(rd.XSpacing, int(count), float(spacing), ['PitchDistance', 'PitchDistanceExpression'])
            if k == 'grid':
                if direction2 is None or spacing2 is None:
                    raise ctx.NxError('grid 需要 direction2 和 spacing2')
                d2 = geom.parse_dir(direction2)
                n2, s2 = int(count2), float(spacing2)
            else:
                d2, n2, s2 = _perp(d1), 1, 1.0
            try:
                rd.UseYDirectionToggle = (k == 'grid')
            except Exception:
                pass
            if k == 'grid':
                rd.YDirection = _direction(part, d2)
                _spacing(rd.YSpacing, n2, s2, ['PitchDistance', 'PitchDistanceExpression'])
        try:
            b.UseInferredReferencePoint = True
        except Exception:
            pass
        feat = b.CommitFeature()
    finally:
        b.Destroy()
    return result(feat)
