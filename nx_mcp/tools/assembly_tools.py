# -*- coding: utf-8 -*-
from typing import List, Optional

from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool(description='把一个 .prt 作为组件加入当前装配（当前工作 Part 即装配）。origin 为放置位置，默认原点。')
    def nx_add_component(path: str, name: Optional[str] = None, origin: Optional[List[float]] = None, reference_set: str = 'Entire Part') -> dict:
        return run('add_component', path=path, name=name, origin=origin, reference_set=reference_set)

    @mcp.tool(description='列出当前装配的组件（id、名称、位置）。')
    def nx_get_components(max_depth: int = 1) -> dict:
        return run('get_components', max_depth=max_depth)

    @mcp.tool(description='按 [dx, dy, dz] 平移组件（相对移动）。')
    def nx_move_component(component: str, translation: List[float]) -> dict:
        return run('move_component', component=component, translation=translation)
