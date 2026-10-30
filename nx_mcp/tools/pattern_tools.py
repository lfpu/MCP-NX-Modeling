# -*- coding: utf-8 -*-
'''Pure-python helper: generate point lists for hole patterns (no NX call needed).'''
import math
from typing import List, Optional


def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    if n < 1e-12:
        raise ValueError('方向不能是零向量')
    return [x / n for x in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _linear(start, direction, spacing, count, direction2, spacing2, count2):
    d1 = _unit(direction)
    d2 = _unit(direction2) if direction2 is not None else [0.0, 0.0, 0.0]
    pts = []
    for j in range(int(count2)):
        for i in range(int(count)):
            pts.append([round(start[a] + d1[a] * spacing * i + d2[a] * spacing2 * j, 6) for a in range(3)])
    return pts


def _circular(center, radius, count, normal, start_angle, total_angle):
    n = _unit(normal or [0.0, 0.0, 1.0])
    ref = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
    dd = sum(ref[i] * n[i] for i in range(3))
    u = _unit([ref[i] - dd * n[i] for i in range(3)])
    v = _cross(n, u)
    full = abs(total_angle - 360.0) < 1e-9
    if full:
        step = total_angle / count
    else:
        step = total_angle / (count - 1) if count > 1 else 0.0
    pts = []
    for i in range(int(count)):
        a = math.radians(start_angle + step * i)
        pts.append([round(center[t] + radius * (math.cos(a) * u[t] + math.sin(a) * v[t]), 6) for t in range(3)])
    return pts


def register(mcp):
    @mcp.tool(description=(
        '生成阵列点，结果可直接作为 nx_create_hole 的 positions。'
        'kind=linear: start、direction、spacing、count；'
        'kind=grid: 再加 direction2、spacing2、count2；'
        'kind=circular: center、radius、count，normal 默认 [0,0,1]，start_angle/total_angle 为度。'))
    def nx_pattern_points(
        kind: str,
        start: Optional[List[float]] = None,
        direction: Optional[List[float]] = None,
        spacing: Optional[float] = None,
        count: int = 1,
        direction2: Optional[List[float]] = None,
        spacing2: Optional[float] = None,
        count2: int = 1,
        center: Optional[List[float]] = None,
        radius: Optional[float] = None,
        normal: Optional[List[float]] = None,
        start_angle: float = 0.0,
        total_angle: float = 360.0,
    ) -> dict:
        try:
            k = str(kind).lower()
            if k in ('linear', 'grid'):
                if start is None or direction is None or spacing is None:
                    return {'success': False, 'error': 'linear/grid 需要 start、direction、spacing'}
                if k == 'grid':
                    if direction2 is None or spacing2 is None:
                        return {'success': False, 'error': 'grid 还需要 direction2 和 spacing2'}
                    pts = _linear(start, direction, spacing, count, direction2, spacing2, count2)
                else:
                    pts = _linear(start, direction, spacing, count, None, 0.0, 1)
            elif k == 'circular':
                if center is None or radius is None or count < 1:
                    return {'success': False, 'error': 'circular 需要 center、radius、count'}
                pts = _circular(center, radius, count, normal, start_angle, total_angle)
            else:
                return {'success': False, 'error': 'kind 只能是 linear / grid / circular'}
            return {'success': True, 'count': len(pts), 'positions': pts}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}
