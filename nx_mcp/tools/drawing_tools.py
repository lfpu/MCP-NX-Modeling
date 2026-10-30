# -*- coding: utf-8 -*-
from typing import List, Optional

from nx_mcp.tools._common import run

VIEWS = 'top / front / right / left / back / bottom / iso / trimetric'


def register(mcp):
    @mcp.tool(description='新建工程图图纸。size: A0~A4（毫米，自定义尺寸）；scale 为图纸比例（1 即 1:1）；third_angle=true 为第三角投影，默认第一角。')
    def nx_create_drawing_sheet(size: str = 'A3', name: Optional[str] = None, scale: float = 1.0, third_angle: bool = False) -> dict:
        return run('create_drawing_sheet', size=size, name=name, scale=scale, third_angle=third_angle)

    @mcp.tool(description='在图纸上添加基本视图。view: ' + VIEWS + '；position 为图纸上的 [x, y]（毫米），scale 为视图比例。sheet 省略时用当前图纸。')
    def nx_add_base_view(view: str = 'front', position: Optional[List[float]] = None, scale: float = 1.0, sheet: Optional[str] = None) -> dict:
        return run('add_base_view', view=view, position=position, scale=scale, sheet=sheet)

    @mcp.tool(description='基于已有视图添加投影视图。parent 为父视图 id（nx_add_base_view 的返回值）；position 为新视图在图纸上的 [x, y]，位置决定投影方向（放在父视图右侧得右视图，上方得俯视图）。')
    def nx_add_projected_view(parent: str, position: List[float], sheet: Optional[str] = None) -> dict:
        return run('add_projected_view', parent=parent, position=position, sheet=sheet)

    @mcp.tool(description='列出当前 Part 的图纸及其视图。')
    def nx_get_drawing_sheets() -> dict:
        return run('get_drawing_sheets')

    @mcp.tool(description='把图纸导出为 PDF。相对路径相对工作区；sheet 省略时用当前图纸；已存在的文件默认不覆盖。')
    def nx_export_drawing_pdf(path: str, sheet: Optional[str] = None, overwrite: bool = False) -> dict:
        return run('export_drawing_pdf', path=path, sheet=sheet, overwrite=overwrite)
