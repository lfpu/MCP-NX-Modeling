# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from nx_mcp.tools._common import run

Vec = Union[str, List[float]]


def register(mcp):
    @mcp.tool()
    def nx_find_faces(
        body: Optional[str] = None,
        type: Optional[str] = None,
        normal: Optional[Vec] = None,
        extreme: Optional[Vec] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        radius: Optional[float] = None,
        within_box: Optional[List[List[float]]] = None,
        near: Optional[List[float]] = None,
        sort: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        '''按条件查找面，返回精简结果（id、类型、中心、法向/轴线/半径、面积）。
        body 省略时在所有实体中查找；type: planar/cylindrical/conical/spherical；
        normal: 平面外法向，可写 top/bottom/left/right/front/back 或 [x,y,z]；
        extreme: 取沿该方向最靠外的平面（如 extreme="top" 即顶面）；
        radius: 圆柱/圆锥/球面半径；near: 按到该点距离计算 distance；
        sort 形如 area_desc、z_asc、dist_asc。方向约定：top=+Z，right=+X，back=+Y。'''
        return run('find_faces', body=body, type=type, normal=normal, extreme=extreme, min_area=min_area,
                   max_area=max_area, radius=radius, within_box=within_box, near=near, sort=sort, limit=limit)

    @mcp.tool()
    def nx_find_edges(
        body: Optional[str] = None,
        type: Optional[str] = None,
        parallel: Optional[Vec] = None,
        on_face: Optional[str] = None,
        min_length: Optional[float] = None,
        max_length: Optional[float] = None,
        radius: Optional[float] = None,
        within_box: Optional[List[List[float]]] = None,
        near: Optional[List[float]] = None,
        sort: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        '''按条件查找边。type: linear/circular；parallel: 与该方向平行的直线边（如 "top" 或 [0,0,1] 即竖直边）；
        on_face: 只看某个面的边；radius: 圆边半径；sort 形如 length_desc、z_asc、dist_asc。'''
        return run('find_edges', body=body, type=type, parallel=parallel, on_face=on_face, min_length=min_length,
                   max_length=max_length, radius=radius, within_box=within_box, near=near, sort=sort, limit=limit)

    @mcp.tool()
    def nx_get_faces(body: Optional[str] = None, type: Optional[str] = None, limit: int = 20) -> dict:
        '''列出面（简单版，等价于不带高级条件的 nx_find_faces）。'''
        return run('find_faces', body=body, type=type, limit=limit)

    @mcp.tool()
    def nx_get_edges(body: Optional[str] = None, type: Optional[str] = None, limit: int = 20) -> dict:
        '''列出边（简单版，等价于不带高级条件的 nx_find_edges）。'''
        return run('find_edges', body=body, type=type, limit=limit)

    @mcp.tool()
    def nx_face_neighbors(face_id: str) -> dict:
        '''返回与指定面共享边的相邻面，以及共享边的 id。'''
        return run('face_neighbors', face_id=face_id)
