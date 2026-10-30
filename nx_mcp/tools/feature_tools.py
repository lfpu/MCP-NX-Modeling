# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from nx_mcp.tools._common import run

Vec = Union[str, List[float]]


def register(mcp):
    @mcp.tool(description=(
        '拉伸草图。默认沿草图法向，从 start 到 distance；symmetric=true 时向两侧各拉伸 distance；reverse 反向；'
        'draft_angle 为拔模角（度）。boolean: create / unite / subtract / intersect；'
        '非 create 时 target_body 为目标实体 id（只有一个实体时可省略）。'))
    def nx_extrude(
        sketch: str,
        distance: float,
        start: float = 0.0,
        symmetric: bool = False,
        reverse: bool = False,
        direction: Optional[Vec] = None,
        boolean: str = 'create',
        target_body: Optional[str] = None,
        draft_angle: Optional[float] = None,
    ) -> dict:
        return run('extrude', sketch=sketch, distance=distance, start=start, symmetric=symmetric, reverse=reverse,
                   direction=direction, boolean=boolean, target_body=target_body, draft_angle=draft_angle)

    @mcp.tool(description=(
        '用草图轮廓切除材料：沿草图法向的反方向切（草图建在实体表面上时即切入实体）。'
        'depth 为深度，through=true 为贯穿。'))
    def nx_pocket(
        sketch: str,
        depth: Optional[float] = None,
        through: bool = False,
        target_body: Optional[str] = None,
        draft_angle: Optional[float] = None,
    ) -> dict:
        return run('pocket', sketch=sketch, depth=depth, through=through, target_body=target_body, draft_angle=draft_angle)

    @mcp.tool(description=(
        '旋转草图轮廓。旋转轴用绝对坐标：axis_origin=[x,y,z]，axis_direction 为 [x,y,z] 或 top/right/back 等名称。'))
    def nx_revolve(
        sketch: str,
        axis_origin: List[float],
        axis_direction: Vec,
        angle: float = 360.0,
        start_angle: float = 0.0,
        boolean: str = 'create',
        target_body: Optional[str] = None,
    ) -> dict:
        return run('revolve', sketch=sketch, axis_origin=axis_origin, axis_direction=axis_direction, angle=angle,
                   start_angle=start_angle, boolean=boolean, target_body=target_body)

    @mcp.tool(description=(
        '在平面上打孔（可多个）。positions 为绝对坐标点列表 [[x,y,z],...]，会被投影到该面；沿面外法向的反方向钻入。'
        'depth 为盲孔深度，through=true 为通孔；cbore_* 为沉头孔，csink_* 为锥形沉孔。'
        '孔由布尔减去圆柱/圆锥实现，不是 NX 的 Hole 特征。阵列孔可先用 nx_pattern_points 生成 positions。'))
    def nx_create_hole(
        face: str,
        positions: List[List[float]],
        diameter: float,
        depth: Optional[float] = None,
        through: bool = False,
        cbore_diameter: Optional[float] = None,
        cbore_depth: Optional[float] = None,
        csink_diameter: Optional[float] = None,
        csink_angle: float = 90.0,
    ) -> dict:
        return run('create_hole', face=face, positions=positions, diameter=diameter, depth=depth, through=through,
                   cbore_diameter=cbore_diameter, cbore_depth=cbore_depth, csink_diameter=csink_diameter, csink_angle=csink_angle)


    @mcp.tool(description=(
        '创建 NX 原生 HolePackage 孔特征。hole_form: simple / counterbore / countersink / tapered；'
        'positions 为投影到目标平面的绝对坐标点。through=true 为贯穿孔，否则需要 depth。'
        '原生接口失败时默认回退到现有布尔减孔；fallback=false 可禁止回退并返回原始错误。'))
    def nx_hole_native(
        face: str,
        positions: List[List[float]],
        diameter: float,
        depth: Optional[float] = None,
        through: bool = False,
        hole_form: str = 'simple',
        cbore_diameter: Optional[float] = None,
        cbore_depth: Optional[float] = None,
        csink_diameter: Optional[float] = None,
        csink_angle: float = 90.0,
        fallback: bool = True,
    ) -> dict:
        return run('hole_native', face=face, positions=positions, diameter=diameter, depth=depth,
                   through=through, hole_form=hole_form, cbore_diameter=cbore_diameter,
                   cbore_depth=cbore_depth, csink_diameter=csink_diameter,
                   csink_angle=csink_angle, fallback=fallback)
    @mcp.tool(description='对已有实体做布尔运算。operation: unite / subtract / intersect；target 和 tools 都是 BODY id。')
    def nx_boolean(operation: str, target: str, tools: List[str]) -> dict:
        return run('boolean', operation=operation, target=target, tools=tools)

    @mcp.tool(description='对指定边倒圆角。edges 为 EDGE id 列表（可先用 nx_find_edges 查找）。')
    def nx_edge_blend(edges: List[str], radius: float) -> dict:
        return run('edge_blend', edges=edges, radius=radius)

    @mcp.tool(description='对指定边倒斜角。只给 distance 为对称；加 distance2 为不对称；加 angle（度）为距离加角度。')
    def nx_chamfer(edges: List[str], distance: float, distance2: Optional[float] = None, angle: Optional[float] = None) -> dict:
        return run('chamfer', edges=edges, distance=distance, distance2=distance2, angle=angle)

    @mcp.tool(description='创建固定基准平面。origin 为平面上一点，normal 为法向。')
    def nx_create_datum_plane(origin: List[float], normal: Vec) -> dict:
        return run('create_datum_plane', origin=origin, normal=normal)

    @mcp.tool(description='修改 Part 表达式（参数）并更新模型。value 可以是数字或公式字符串。')
    def nx_edit_expression(name: str, value: str) -> dict:
        return run('edit_expression', name=name, value=str(value))

    @mcp.tool(description='【危险】删除特征/实体/草图。必须先征得用户同意，再以 confirm=true 调用；可用 nx_undo_last 撤销。')
    def nx_delete_object(object_id: str, confirm: bool = False) -> dict:
        return run('delete_object', object_id=object_id, confirm=confirm)
