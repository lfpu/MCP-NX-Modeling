# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from nx_mcp.tools._common import run

Vec = Union[str, List[float]]


def register(mcp):
    @mcp.tool(description=(
        '特征阵列：把 features（FEATURE id 列表，如拉伸、凸台、孔特征）复制成阵列。'
        'kind=linear：沿 direction 方向，count 个实例（含原特征）、间距 spacing；'
        'kind=grid：再加 direction2、count2、spacing2；'
        'kind=circular：绕 axis_origin + axis_direction 的轴，count 个实例，angle 为总角度（默认 360）。'
        '注意：nx_create_hole 生成的是多个独立布尔特征，批量孔建议直接用 nx_pattern_points 生成坐标。'))
    def nx_pattern_feature(
        features: List[str],
        kind: str = 'linear',
        direction: Vec = 'x',
        count: int = 2,
        spacing: float = 10.0,
        direction2: Optional[Vec] = None,
        count2: int = 1,
        spacing2: Optional[float] = None,
        axis_origin: Optional[List[float]] = None,
        axis_direction: Optional[Vec] = None,
        angle: float = 360.0,
    ) -> dict:
        return run('pattern_feature', features=features, kind=kind, direction=direction, count=count, spacing=spacing,
                   direction2=direction2, count2=count2, spacing2=spacing2, axis_origin=axis_origin,
                   axis_direction=axis_direction, angle=angle)
