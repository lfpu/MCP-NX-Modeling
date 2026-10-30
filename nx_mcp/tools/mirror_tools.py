# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool(description=(
        '沿平面镜像实体（生成镜像副本）。plane: xy / yz / xz（法向分别为 Z / X / Y），offset 为平面沿法向的偏移；'
        '或用 origin + normal 指定任意平面。body 省略时用唯一的实体。'))
    def nx_mirror_body(
        body: Optional[str] = None,
        plane: str = 'xy',
        offset: float = 0.0,
        origin: Optional[List[float]] = None,
        normal: Optional[Union[str, List[float]]] = None,
    ) -> dict:
        return run('mirror_body', body=body, plane=plane, offset=offset, origin=origin, normal=normal)

    @mcp.tool(description='导出当前显示 Part 为 STL（.stl），使用 NX 默认 STL 设置。')
    def nx_export_stl(path: str, overwrite: bool = False) -> dict:
        return run('export_stl', path=path, overwrite=overwrite)
