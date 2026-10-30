# -*- coding: utf-8 -*-
from typing import Optional

from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool()
    def nx_get_part_info() -> dict:
        '''当前工作 Part 概览：名称、路径、单位、实体/特征/草图数量、整体包围盒与尺寸。'''
        return run('part_info')

    @mcp.tool()
    def nx_get_bodies() -> dict:
        '''列出所有 Body（id、实体/片体、面数、边数、包围盒）。'''
        return run('get_bodies')

    @mcp.tool()
    def nx_get_features(limit: int = 50, offset: int = 0, type: Optional[str] = None, name: Optional[str] = None) -> dict:
        '''列出特征树（按创建顺序），可按类型/名称关键字过滤并分页。'''
        return run('get_features', limit=limit, offset=offset, type=type, name=name)

    @mcp.tool()
    def nx_get_expressions(name: Optional[str] = None, limit: int = 50) -> dict:
        '''列出 Part 表达式（参数名、公式、值），可按名称关键字过滤。'''
        return run('get_expressions', name=name, limit=limit)

    @mcp.tool()
    def nx_get_object_info(object_id: str) -> dict:
        '''查询任意对象详情。object_id 形如 FACE_123 / EDGE_45 / BODY_7 / FEATURE_9。面会带面积，特征会带其表达式。'''
        return run('get_object_info', object_id=object_id)

    @mcp.tool()
    def nx_get_selected_objects() -> dict:
        '''读取用户当前在 NX 界面中选中的对象（无界面模式下为空）。'''
        return run('get_selected_objects')
