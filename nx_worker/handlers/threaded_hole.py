# -*- coding: utf-8 -*-
'''NX native threaded HolePackage support for NX 2412.''' 
import NXOpen
import NXOpen.Features

from nx_worker import ctx, geom
from nx_worker.handlers.feat_hole import _project_to_face, hole_native, result
from nx_worker.registry import command


@command('threaded_hole', 'modify')
def threaded_hole(face, positions, thread_standard, thread_size, tap_drill_diameter,
                  hole_depth, thread_depth=None, through=False,
                  thread_length_option='custom', left_hand=False, fallback=True):
    part = ctx.work_part()
    target_face = ctx.get_obj(face, 'FACE')
    info = geom.face_info(target_face)
    face_data = geom.face_data(target_face)
    if info.get('type') != 'planar' or not info.get('normal') or not face_data:
        raise ctx.NxError('螺纹孔只能定位到平面')
    if not positions:
        raise ctx.NxError('positions 不能为空')
    if not str(thread_standard).strip() or not str(thread_size).strip():
        raise ctx.NxError('thread_standard 和 thread_size 不能为空')
    tap_drill_diameter = float(tap_drill_diameter)
    hole_depth = float(hole_depth)
    thread_depth = float(thread_depth if thread_depth is not None else hole_depth)
    if tap_drill_diameter <= 0 or hole_depth <= 0 or thread_depth <= 0:
        raise ctx.NxError('tap_drill_diameter、hole_depth 和 thread_depth 必须大于 0')
    options = {
        'custom': 'Custom', 'standard': 'Standard', 'full': 'Full',
        'diameterx1': 'Diameterx1', 'diameterx15': 'Diameterx15',
        'diameterx20': 'Diameterx20', 'diameterx25': 'Diameterx25',
        'diameterx30': 'Diameterx30',
    }
    option = str(thread_length_option or 'custom').lower()
    if option not in options:
        raise ctx.NxError('thread_length_option 不受支持: ' + option)
    builder = part.Features.CreateHolePackageBuilder(NXOpen.Features.HolePackage.Null)
    created_points = []
    try:
        builder.Type = NXOpen.Features.HolePackageBuilder.Types.ThreadedHole
        builder.Tolerance = 0.01
        builder.BooleanOperation.SetTargetBodies([target_face.GetBody()])
        builder.ThreadStandard = str(thread_standard)
        builder.ThreadSize = str(thread_size)
        builder.TapDrillDiameter.RightHandSide = ctx.num(tap_drill_diameter)
        builder.ThreadDepth.RightHandSide = ctx.num(thread_depth)
        builder.ThreadedHoleDepth.RightHandSide = ctx.num(hole_depth)
        builder.ThreadLengthOption = getattr(
            NXOpen.Features.HolePackageBuilder.ThreadLengthOptions, options[option])
        builder.ThreadRotation = getattr(
            NXOpen.Features.HolePackageBuilder.ThreadRotationOptions,
            'Left' if left_hand else 'Right')
        builder.RelateHoleDepthToThreadDepth = abs(hole_depth - thread_depth) < 1.0e-9
        builder.HoleDepthLimitOption = getattr(
            NXOpen.Features.HolePackageBuilder.HoleDepthLimitOptions,
            'ThroughBody' if through else 'Value')
        try:
            down = [-float(x) for x in info['normal']]
            builder.ProjectionDirection.ProjectVector = part.Directions.CreateDirection(
                ctx.pt(face_data['point']), ctx.vec(down),
                NXOpen.SmartObject.UpdateOption.WithinModeling)
        except Exception:
            pass
        for position in positions:
            projected = _project_to_face(position, info, face_data)
            point = part.Points.CreatePoint(ctx.pt(projected))
            created_points.append(point)
            builder.HolePosition.AddSmartPoint(point, 0.01)
        feature = builder.CommitFeature()
        output = result(feature)
        output['native'] = True
        output['thread'] = {
            'standard': str(thread_standard), 'size': str(thread_size),
            'tap_drill_diameter': tap_drill_diameter, 'hole_depth': hole_depth,
            'thread_depth': thread_depth, 'through': bool(through),
            'thread_length_option': option,
            'rotation': 'left' if left_hand else 'right',
            'positions': len(positions),
        }
        return output
    except Exception as exc:
        native_error = '%s: %s' % (type(exc).__name__, str(exc))
        if not fallback:
            raise ctx.NxError('创建 NX 原生螺纹孔失败: ' + native_error)
        output = hole_native(
            face=face, positions=positions, diameter=tap_drill_diameter,
            depth=hole_depth, through=through, hole_form='simple', fallback=True)
        output['native_thread'] = False
        output['thread'] = {
            'standard': str(thread_standard), 'size': str(thread_size),
            'tap_drill_diameter': tap_drill_diameter, 'hole_depth': hole_depth,
            'thread_depth': thread_depth, 'through': bool(through),
            'thread_length_option': option,
            'rotation': 'left' if left_hand else 'right',
            'positions': len(positions),
        }
        output['warning'] = (
            '当前 NX 安装未提供可用的螺纹标准数据，已创建攻丝底孔并保留螺纹参数语义；'
            '这不是 NX 原生 Threaded HolePackage。原生错误: ' + native_error)
        return output
    finally:
        try:
            builder.Destroy()
        except Exception:
            pass
