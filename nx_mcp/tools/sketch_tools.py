# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from nx_mcp.tools._common import run

SHAPES_HELP = (
    'shapes 是图形列表，坐标均为草图坐标 [u, v]：\n'
    '- {type:line, start:[u,v], end:[u,v]}\n'
    '- {type:rectangle, corner:[u,v] 或 center:[u,v], width:W, height:H}\n'
    '- {type:circle, center:[u,v], diameter:D（或 radius:R）}\n'
    '- {type:arc, center:[u,v], radius:R, start_angle:度, end_angle:度}（逆时针）\n'
    '- {type:polyline, points:[[u,v],...], closed:true/false}'
)

CREATE_DOC = (
    '创建草图并一次性画好图形。plane: xy(u=X,v=Y,法向+Z) / yz(u=Y,v=Z,法向+X) / xz(u=X,v=Z,法向-Y)，'
    'offset 为沿法向的偏移；或用 face 指定一个平面（法向为该面外法向，原点为世界原点在该面上的投影）。'
    '闭合外轮廓加内部闭合轮廓（如圆）拉伸时会自动形成孔。\n'
    + SHAPES_HELP +
    '\n返回 sketch.id 以及 u_axis/v_axis/normal，供后续拉伸、切除、旋转使用。'
)


def register(mcp):
    @mcp.tool(description=CREATE_DOC)
    def nx_create_sketch(
        shapes: List[Dict[str, Any]],
        plane: str = 'xy',
        face: Optional[str] = None,
        offset: float = 0.0,
        name: Optional[str] = None,
    ) -> dict:
        return run('create_sketch', shapes=shapes, plane=plane, face=face, offset=offset, name=name)

    @mcp.tool(description='向已有草图追加图形（仅限本服务创建的草图）。\n' + SHAPES_HELP)
    def nx_add_to_sketch(sketch: str, shapes: List[Dict[str, Any]]) -> dict:
        return run('add_to_sketch', sketch=sketch, shapes=shapes)

    @mcp.tool(description='列出当前 Part 的草图（id、名称、曲线数、方向）。')
    def nx_get_sketches() -> dict:
        return run('get_sketches')
