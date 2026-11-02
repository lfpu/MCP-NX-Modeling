# -*- coding: utf-8 -*-
from typing import List, Optional

from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool(description=(
        '创建外啮合直齿轮实体。module 为模数，teeth 为齿数，width 为齿宽，pressure_angle 默认 20 度，'
        'bore_diameter 可创建中心孔。当前齿形使用适合常规模型和装配展示的六点近似渐开线轮廓，'
        '不是制造级精确渐开线；当前仅沿 +Z 拉伸。'))
    def nx_create_spur_gear(
        module: float,
        teeth: int,
        width: float,
        pressure_angle: float = 20.0,
        bore_diameter: float = 0.0,
        center: Optional[List[float]] = None,
        direction: Optional[List[float]] = None,
        name: Optional[str] = None,
    ) -> dict:
        return run('create_spur_gear', module=module, teeth=teeth, width=width,
                   pressure_angle=pressure_angle, bore_diameter=bore_diameter,
                   center=center, direction=direction, name=name)
