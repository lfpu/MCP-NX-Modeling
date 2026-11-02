# -*- coding: utf-8 -*-
from typing import List, Optional

from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool(description=(
        '创建 NX 2412 原生 Threaded HolePackage 螺纹孔。face 必须是平面 FACE id；positions 是绝对坐标点。'
        'thread_standard 和 thread_size 必须使用当前 NX 安装螺纹表中存在的名称，例如公制标准及 M6 等规格；'
        'tap_drill_diameter、hole_depth、thread_depth 单位随 Part。fallback=true 时，如果当前 NX 安装缺少匹配的螺纹标准数据，'
        '会创建攻丝底孔并在结果中保留螺纹参数和 warning；fallback=false 则严格要求原生 Threaded HolePackage。'))
    def nx_threaded_hole(
        face: str,
        positions: List[List[float]],
        thread_standard: str,
        thread_size: str,
        tap_drill_diameter: float,
        hole_depth: float,
        thread_depth: Optional[float] = None,
        through: bool = False,
        thread_length_option: str = 'custom',
        left_hand: bool = False,
        fallback: bool = True,
    ) -> dict:
        return run('threaded_hole', face=face, positions=positions,
                   thread_standard=thread_standard, thread_size=thread_size,
                   tap_drill_diameter=tap_drill_diameter, hole_depth=hole_depth,
                   thread_depth=thread_depth, through=through,
                   thread_length_option=thread_length_option, left_hand=left_hand,
                   fallback=fallback)
