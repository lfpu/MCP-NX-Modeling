# -*- coding: utf-8 -*-
'''Parametric external spur gear generated from a closed tooth profile and extruded as one solid.''' 
import math

from nx_worker import ctx
from nx_worker.handlers import feat_sweep
from nx_worker.handlers import sketch as sketch_handler
from nx_worker.registry import command


def _point(radius, angle):
    return [radius * math.cos(angle), radius * math.sin(angle)]


def _profile(module, teeth, pressure_angle, bore_diameter):
    pitch_radius = module * teeth / 2.0
    addendum_radius = pitch_radius + module
    dedendum_radius = max(module * 0.25, pitch_radius - 1.25 * module)
    base_radius = pitch_radius * math.cos(math.radians(pressure_angle))
    tooth_pitch = 2.0 * math.pi / teeth
    half_tooth = math.pi / (2.0 * teeth)
    points = []
    for index in range(teeth):
        center = index * tooth_pitch
        points.extend([
            _point(dedendum_radius, center - half_tooth),
            _point(pitch_radius, center - half_tooth * 0.68),
            _point(addendum_radius, center - half_tooth * 0.34),
            _point(addendum_radius, center + half_tooth * 0.34),
            _point(pitch_radius, center + half_tooth * 0.68),
            _point(dedendum_radius, center + half_tooth),
        ])
    shapes = [{'type': 'polyline', 'points': points, 'closed': True}]
    if bore_diameter and bore_diameter > 0:
        shapes.append({'type': 'circle', 'center': [0.0, 0.0], 'diameter': bore_diameter})
    return shapes, pitch_radius, base_radius, addendum_radius, dedendum_radius


@command('create_spur_gear', 'modify')
def create_spur_gear(module, teeth, width, pressure_angle=20.0, bore_diameter=0.0,
                     center=None, direction=None, name=None):
    module = float(module)
    teeth = int(teeth)
    width = float(width)
    pressure_angle = float(pressure_angle)
    bore_diameter = float(bore_diameter or 0.0)
    if module <= 0 or width <= 0:
        raise ctx.NxError('module 和 width 必须大于 0')
    if teeth < 6:
        raise ctx.NxError('teeth 必须至少为 6')
    if pressure_angle <= 0 or pressure_angle >= 45:
        raise ctx.NxError('pressure_angle 必须在 0 到 45 度之间')
    pitch_diameter = module * teeth
    root_diameter = max(module * 0.5, pitch_diameter - 2.5 * module)
    if bore_diameter < 0 or bore_diameter >= root_diameter:
        raise ctx.NxError('bore_diameter 必须大于等于 0 且小于齿根圆直径')
    if direction not in (None, [0, 0, 1], [0.0, 0.0, 1.0]):
        raise ctx.NxError('当前直齿轮仅支持沿 +Z 方向创建；可在创建后使用装配或移动功能定位')
    center = center or [0.0, 0.0, 0.0]
    if len(center) != 3:
        raise ctx.NxError('center 必须为 [x,y,z]')
    shapes, pitch_radius, base_radius, outside_radius, root_radius = _profile(
        module, teeth, pressure_angle, bore_diameter)
    for shape in shapes:
        if shape['type'] == 'polyline':
            shape['points'] = [[p[0] + float(center[0]), p[1] + float(center[1])] for p in shape['points']]
        elif shape['type'] == 'circle':
            shape['center'] = [float(center[0]), float(center[1])]
    sketch_result = sketch_handler.create_sketch(
        shapes=shapes, plane='xy', offset=float(center[2]), face=None,
        name=(name + '_PROFILE') if name else 'SPUR_GEAR_PROFILE')
    result = feat_sweep.extrude(
        sketch=sketch_result['sketch']['id'], distance=width, start=0.0,
        symmetric=False, direction=None, boolean='create', target_body=None,
        draft_angle=0.0)
    result['gear'] = {
        'name': name or 'SpurGear', 'module': module, 'teeth': teeth,
        'width': width, 'pressure_angle': pressure_angle,
        'bore_diameter': bore_diameter, 'pitch_diameter': 2.0 * pitch_radius,
        'base_diameter': 2.0 * base_radius, 'outside_diameter': 2.0 * outside_radius,
        'root_diameter': 2.0 * root_radius,
        'profile': 'simplified involute-compatible six-point tooth approximation'
    }
    result['sketch'] = sketch_result['sketch']
    return result
