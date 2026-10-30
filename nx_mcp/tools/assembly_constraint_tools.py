# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from nx_mcp.tools._common import run

Vec = Union[str, List[float]]


def register(mcp):
    @mcp.tool(description=(
        '列出某个装配组件的面（组件内的实例），返回 id、类型、中心、法向，可用作 nx_add_constraint 的 face1/face2。'
        'type: planar/cylindrical；normal 可写 top/bottom/left/right/front/back 或 [x,y,z]；extreme 取沿该方向最靠外的面。'
        '返回的坐标为装配坐标。'))
    def nx_component_faces(
        component: str,
        type: Optional[str] = None,
        normal: Optional[Vec] = None,
        extreme: Optional[Vec] = None,
        limit: int = 20,
    ) -> dict:
        return run('component_faces', component=component, type=type, normal=normal, extreme=extreme, limit=limit)

    @mcp.tool(description=(
        '添加装配约束。kind: fix（固定 component1，无需面）/ touch（面贴合）/ concentric（同心）/ distance（距离，需 distance）/'
        ' parallel / perpendicular / angle（需 distance 作为角度）。'
        '除 fix 外都需要 face1（component1 的面）、component2、face2（component2 的面）；component1 保持不动，component2 被移动。'
        'alignment: infer / coalign / contra。面 id 请用 nx_component_faces 获取。'))
    def nx_add_constraint(
        kind: str,
        component1: str,
        face1: Optional[str] = None,
        component2: Optional[str] = None,
        face2: Optional[str] = None,
        distance: Optional[float] = None,
        alignment: str = 'infer',
    ) -> dict:
        return run('add_constraint', kind=kind, component1=component1, face1=face1, component2=component2,
                   face2=face2, distance=distance, alignment=alignment)
