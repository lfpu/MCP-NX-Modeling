# -*- coding: utf-8 -*-
from typing import List, Optional

from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool()
    def nx_create_block(
        length: float,
        width: float,
        height: float,
        origin: Optional[List[float]] = None,
        boolean: str = 'create',
        target_body: Optional[str] = None,
    ) -> dict:
        '''创建长方体。length/width/height 分别沿 X/Y/Z，单位为 Part 单位；origin 为角点 [x,y,z]，默认原点。
        boolean: create(新实体)/unite/subtract/intersect；非 create 时 target_body 为目标实体 id（只有一个实体时可省略）。
        返回 feature 与 bodies（含 id、bbox），后续操作可直接使用这些 id。'''
        return run('create_block', length=length, width=width, height=height, origin=origin, boolean=boolean, target_body=target_body)

    @mcp.tool()
    def nx_create_cylinder(
        diameter: float,
        height: float,
        origin: Optional[List[float]] = None,
        direction: Optional[List[float]] = None,
        boolean: str = 'create',
        target_body: Optional[str] = None,
    ) -> dict:
        '''创建圆柱。origin 为底面圆心，direction 为轴线方向（默认 [0,0,1]）。boolean 同 nx_create_block。'''
        return run('create_cylinder', diameter=diameter, height=height, origin=origin, direction=direction, boolean=boolean, target_body=target_body)

    @mcp.tool()
    def nx_create_cone(
        base_diameter: float,
        top_diameter: float,
        height: float,
        origin: Optional[List[float]] = None,
        direction: Optional[List[float]] = None,
        boolean: str = 'create',
        target_body: Optional[str] = None,
    ) -> dict:
        '''创建圆锥/圆台。top_diameter=0 为尖锥。origin 为底面圆心，direction 为轴线方向（默认 [0,0,1]）。'''
        return run('create_cone', base_diameter=base_diameter, top_diameter=top_diameter, height=height, origin=origin, direction=direction, boolean=boolean, target_body=target_body)

    @mcp.tool()
    def nx_create_sphere(
        diameter: float,
        center: Optional[List[float]] = None,
        boolean: str = 'create',
        target_body: Optional[str] = None,
    ) -> dict:
        '''创建球体。center 为球心 [x,y,z]，默认原点。'''
        return run('create_sphere', diameter=diameter, center=center, boolean=boolean, target_body=target_body)
